# 🧪 DocWatch RAG: Local Testing & Benchmarking Guide

This guide outlines the various testing configurations, local mocking strategies, and evaluation benchmarks available to run on your local machine to validate pipeline performance.

---

## 🏗️ 1. Prerequisites & Environment Mocking

Before running validation tests, ensure your local environment is configured. This framework supports both cloud-hosted APIs and local model orchestration via Ollama.

Ensure your `.env` contains the targets for your test variant:
```env
# Cloud-based Testing Variant
OPENAI_API_KEY=your_openai_api_key
EMBEDDING_MODEL=text-embedding-3-small
LLM_MODEL=gpt-4o-mini

# Local Offline Testing Variant (Optional)
# OLLAMA_BASE_URL=http://localhost:11434
# EMBEDDING_MODEL=all-minilm
# LLM_MODEL=llama3

## 2. Sample Testing Instructions:

a. Standard End-to-End Execution (CLI Query): Use this test to verify that the ingestion, chunking, and vector embedding pipelines are executing without errors, and that the LLM is receiving the synthesized context.

Python command: python main.py --query "What are the core compliance protocols outlined in the documentation?"

What it validates: Multi-format document parsing, embedding tokenization, vector store matching, and basic LLM completions.

b. Automated RAG Quality Evaluation (Ragas / DeepEval): To ensure code changes do not introduce hallucinations or degrade retrieval accuracy, run a regression testing matrix against a local ground-truth dataset (/tests/test_dataset.json).

Python command: python run_eval.py --dataset ./tests/test_dataset.json --output ./reports/eval_results.json

This testing scenario evaluates your pipeline across three production-critical axes:
Faithfulness: Quantifies whether the generated answer relies exclusively on the retrieved context (hallucination check).
Context Precision: Validates if the most relevant document chunks are ranked highest by the retriever.
Answer Relevancy: Measures how closely the final output addresses the original user prompt.

c. Concurrent Performance & Latency Stress Test
Run a concurrent test harness to benchmark performance times, verify text-chunk parsing overhead, and test API rate-limiting handling under simultaneous lookups.

Python command: python -m pytest tests/test_performance.py -v --concurrent-queries 10

3. ## Diagnostic Test Output Report
Upon completion of execution tests, output summaries are structured and saved to ./reports/eval_results.json for easy diffing:

JSON
{
  "test_run_id": "docwatch_eval_042",
  "metrics": {
    "avg_latency_seconds": 1.14,
    "faithfulness_score": 0.96,
    "context_precision": 0.92,
    "answer_relevancy": 0.95
  },
  "status": "PASS"
}
