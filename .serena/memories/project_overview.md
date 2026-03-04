# SimpleMem - Project Overview

## Purpose
SimpleMem is an **Efficient Lifelong Memory system for LLM Agents**. It stores, compresses, and retrieves long-term memories with semantic lossless compression. It works across Claude, Cursor, LM Studio, Cherry Studio, and any MCP-compatible client.

Based on the research paper: arXiv:2601.02553

## Tech Stack
- **Language**: Python 3.11+
- **LLM Integration**: OpenAI-compatible API (via `openai` SDK), LangChain, LiteLLM
- **Embedding**: Sentence Transformers, Qwen3-Embedding-0.6B (default, local)
- **Vector Database**: LanceDB with full-text search (tantivy)
- **Data Models**: Pydantic v2
- **MCP Server**: FastAPI + Uvicorn (HTTP/SSE transport)
- **Auth**: JWT tokens, encryption for API keys
- **Docker**: Python 3.11-slim, docker-compose
- **Testing**: Custom test scripts (no pytest framework), NLTK, BLEU/METEOR/ROUGE/BERTScore metrics
- **Evaluation Dataset**: LoComo10

## Architecture (Three-Stage Pipeline)
1. **Semantic Structured Compression** (Section 3.1): Dialogues → MemoryBuilder → MemoryEntry → VectorStore
2. **Online Semantic Synthesis** (Section 3.2): Intra-session consolidation during write
3. **Intent-Aware Retrieval Planning** (Section 3.3): Question → HybridRetriever → AnswerGenerator → Answer

## Key Modules
- `main.py` - `SimpleMemSystem` - Main orchestrator class
- `core/memory_builder.py` - `MemoryBuilder` - Converts dialogues to memory entries via LLM
- `core/hybrid_retriever.py` - `HybridRetriever` - Multi-strategy retrieval (semantic + keyword + structured)
- `core/answer_generator.py` - `AnswerGenerator` - Generates answers from retrieved contexts
- `models/memory_entry.py` - `MemoryEntry`, `Dialogue` - Core data models (Pydantic)
- `database/vector_store.py` - `VectorStore` - LanceDB wrapper with FTS
- `utils/llm_client.py` - `LLMClient` - OpenAI-compatible API client
- `utils/embedding.py` - `EmbeddingModel` - Embedding model wrapper (Qwen3/SentenceTransformer)
- `MCP/` - MCP Server (HTTP/SSE), multi-tenant, FastAPI-based, with Web UI
- `cross/` - Cross-session memory module (session tracking, consolidation, context injection)
- `SKILL/` - Skill integration for external platforms
- `tests/` - Test scripts

## Configuration
- `config.py` (from `config.py.example`) - Main config file (API keys, model settings, retrieval params, DB paths)
- `.env` (from `.env.example`) - Docker environment variables
- Config is **not committed** to git (in .gitignore)
