import os
import sys
import time
import argparse
from typing import List
from pathlib import Path
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from pinecone import Pinecone, ServerlessSpec
from openai import OpenAI

# Initialize Clients from Environment Variables
openai_client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))
pc = Pinecone(api_key=os.environ.get("PINECONE_API_KEY"))

INDEX_NAME = "docwatch-index"
DIMENSION = 1536  # Dimension for OpenAI's text-embedding-3-small or text-embedding-ada-002

class DocWatchPineconeRAG:
    def __init__(self, target_dir: str):
        self.target_dir = Path(target_dir).resolve()
        self.supported_extensions = {'.txt', '.md', '.py', '.js', '.json', '.html', '.css', '.rs', '.sol'}
        
        # 1. Ensure Pinecone Index Exists (Serverless Deployment)
        if INDEX_NAME not in [idx.name for idx in pc.list_indexes()]:
            print(f"📡 Creating a new Serverless Pinecone Index: '{INDEX_NAME}'...")
            pc.create_index(
                name=INDEX_NAME,
                dimension=DIMENSION,
                metric="cosine",
                spec=ServerlessSpec(
                    cloud="aws",
                    region="us-east-1"  # Free tier default region
                )
            )
            # Wait for index initialization
            while not pc.describe_index(INDEX_NAME).status['ready']:
                time.sleep(1)
        
        self.index = pc.Index(INDEX_NAME)

    def get_embedding(self, text: str) -> List[float]:
        """Generates embeddings using OpenAI."""
        response = openai_client.embeddings.create(
            input=[text],
            model="text-embedding-3-small"
        )
        return response.data[0].embedding

    def chunk_text(self, text: str, chunk_size: int = 800, overlap: int = 150) -> List[str]:
        """Sliding-window word chunking."""
        words = text.split()
        chunks = []
        i = 0
        while i < len(words):
            chunk = " ".join(words[i:i + chunk_size])
            chunks.append(chunk)
            i += (chunk_size - overlap)
        return chunks

    def sanitize_id(self, file_path: Path, index: int) -> str:
        """Pinecone IDs must be ASCII strings. Sanitizes path names."""
        clean_name = file_path.name.replace(" ", "_")
        return f"{clean_name}-chunk-{index}"

    def index_file(self, file_path: Path):
        """Chunks, embeds, and upserts a file directly into Pinecone Cloud."""
        if file_path.suffix not in self.supported_extensions:
            return
            
        try:
            print(f"🔄 Processing file: {file_path.relative_to(self.target_dir)}")
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
                
            if not content.strip():
                return

            # Pinecone replaces/overwrites identical IDs on upsert. 
            # To be safe during structural changes, we clear historical vectors for this file.
            self.remove_file_from_index(file_path)

            chunks = self.chunk_text(content)
            if not chunks:
                return

            vectors_to_upsert = []
            for i, chunk in enumerate(chunks):
                vector_id = self.sanitize_id(file_path, i)
                embedding = self.get_embedding(chunk)
                
                # Metadata must be simple key-values for Pinecone filtering
                metadata = {
                    "source": str(file_path),
                    "filename": file_path.name,
                    "text": chunk, # Store raw text inside metadata to pull during query retrieval
                    "updated_at": time.time()
                }
                vectors_to_upsert.append((vector_id, embedding, metadata))

            # Cloud Upsert in batch
            self.index.upsert(vectors=vectors_to_upsert)
            print(f"✅ Cloud Indexed: {len(chunks)} chunks uploaded for {file_path.name}")
        except Exception as e:
            print(f"❌ Error indexing {file_path.name}: {e}")

    def remove_file_from_index(self, file_path: Path):
        """Deletes vectors matching the deleted local file path using Metadata Filters."""
        try:
            # Pinecone supports filtering deletes by metadata metadata expressions
            self.index.delete(filter={"source": {"$eq": str(file_path)}})
            print(f"🗑️ Cleaned old cloud index entries for: {file_path.name}")
        except Exception as e:
            pass # Graceful bypass if index is brand new and empty

    def initial_scan(self):
        """Performs a full walk of the path at startup."""
        print(f"🚀 Syncing local directory to Pinecone Cloud: {self.target_dir}")
        for root, _, files in os.walk(self.target_dir):
            for file in files:
                file_path = Path(root) / file
                self.index_file(file_path)
        print("🎉 Cloud Synchronization Complete. System is matching live.")

    def query(self, user_prompt: str, top_k: int = 3) -> str:
        """Queries Pinecone, pulls text from metadata fields, and feeds into LLM context."""
        query_vector = self.get_embedding(user_prompt)
        
        results = self.index.query(
            vector=query_vector,
            top_k=top_k,
            include_metadata=True
        )
        
        matches = results.get('matches', [])
        if not matches:
            return "I couldn't find any relevant local code or context in Pinecone to answer that."

        context_blocks = []
        for match in matches:
            meta = match.get('metadata', {})
            filename = meta.get('filename', 'Unknown Source')
            text = meta.get('text', '')
            context_blocks.append(f"--- Context Segment from [{filename}] (Confidence: {match['score']:.2f}) ---\n{text}")
            
        context_str = "\n\n".join(context_blocks)
        
        system_prompt = (
            "You are an elite, highly helpful AI code and directory copilot.\n"
            "Answer the user's question using the provided local file context retrieved from Pinecone. "
            "If the context doesn't contain the answer, explain honestly that you don't know.\n\n"
            f"=== RETRIEVED CONTEXT ===\n{context_str}\n"
        )
        
        try:
            response = openai_client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.2
            )
            return response.choices[0].message.content
        except Exception as e:
            return f"❌ Error querying OpenAI Completion API: {e}"


class FileWatcherHandler(FileSystemEventHandler):
    def __init__(self, engine: DocWatchPineconeRAG):
        self.engine = engine

    def on_modified(self, event):
        if not event.is_directory:
            self.engine.index_file(Path(event.src_path))

    def on_created(self, event):
        if not event.is_directory:
            self.engine.index_file(Path(event.src_path))

    def on_deleted(self, event):
        if not event.is_directory:
            self.engine.remove_file_from_index(Path(event.src_path))


def run_cli_interactive(engine: DocWatchPineconeRAG):
    print("\n" + "="*50)
    print("🤖 PINECONE DOCWATCH-RAG PILOT ACTIVE")
    print("Ask questions about your files. Type 'exit' to quit.")
    print("="*50 + "\n")
    
    while True:
        try:
            user_input = input("👤 Ask your codebase: ").strip()
            if not user_input:
                continue
            if user_input.lower() in ['exit', 'quit']:
                print("Goodbye!")
                break
                
            print("🧠 Searching Cloud Vector Space & generating answer...")
            answer = engine.query(user_input)
            print(f"\n🤖 Answer:\n{answer}\n" + "-"*50 + "\n")
        except KeyboardInterrupt:
            print("\nGoodbye!")
            break

if __name__ == "__main__":
    # Safety Check for API Keys
    if not os.environ.get("OPENAI_API_KEY") or not os.environ.get("PINECONE_API_KEY"):
        print("❌ Error: Both OPENAI_API_KEY and PINECONE_API_KEY environment variables must be exported.")
        sys.exit(1)

    parser = argparse.ArgumentParser(description="DocWatch-RAG: Pinecone Edition")
    parser.add_argument("--dir", type=str, default=".", help="Directory to watch (default: current directory)")
    args = parser.parse_args()

    # Launch Engine
    engine = DocWatchPineconeRAG(target_dir=args.dir)
    engine.initial_scan()
    
    # Watcher Loop
    observer = Observer()
    event_handler = FileWatcherHandler(engine)
    observer.schedule(event_handler, path=str(engine.target_dir), recursive=True)
    observer.start()
    print("👀 Live File Watcher is actively tracking workspace updates...")

    try:
        run_cli_interactive(engine)
    finally:
        observer.stop()
        observer.join()