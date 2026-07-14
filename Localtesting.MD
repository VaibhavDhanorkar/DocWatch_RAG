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
