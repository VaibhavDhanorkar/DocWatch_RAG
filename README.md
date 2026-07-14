# 📂 DocWatch-RAG

> **An event-driven, real-time local directory RAG copilot.** Point it at any directory (codebases, markdown wikis, log repositories, system documentation), and it dynamically updates its vector database context the instant you hit save on any file.

Most Retrieval-Augmented Generation (RAG) applications query static PDFs or historical snapshots. **DocWatch-RAG** utilizes low-latency file system polling to process, clean, chunk, and update embeddings on the fly, guaranteeing your LLM prompts are always contextually aware of your absolute latest local work.

---

## ✨ Features

- **👀 Live File-System Watcher:** Leverages the native OS event system to capture additions, modifications, and deletions instantly.
- **⚡ Hot Re-Indexing:** Dynamically clears old document vectors and updates only the edited file, keeping your vector db perfectly synchronized with zero index bloating.
- **🗄️ Zero Cloud Overhead Database:** Runs on a persistent, local instance of ChromaDB—no external database servers to configure.
- **🐚 Interactive Terminal Chat:** A clean, terminal-based conversational UI loop to interrogate your folder structure instantly.

---

## 🏗️ Architecture

```text
  [ Local Folder ] 
        │
        ├── (Create/Modify/Delete Event)
        ▼
  [ Watchdog File Listener ]
        │
        ├── (Trigger Re-Chunking)
        ▼
  [ Vectorization Pipeline ] ──► [ Local PineconeDB Store ]
        │                                ▲
        ▼                                │ (Context Pull)
  [ OpenAI / LLM Query Server ] ─────────┘