# Codebase Structure

```
SimpleMem/
├── main.py                  # Entry point: SimpleMemSystem class + create_system()
├── config.py.example        # Configuration template (copy to config.py)
├── .env.example             # Docker env template
├── requirements.txt         # Python dependencies (pip)
├── requirements-gpu.txt     # GPU-specific dependencies
├── Dockerfile               # Docker image (python:3.11-slim)
├── docker-compose.yml       # Docker Compose config
├── SimpleMem.skill          # Skill definition file
├── test_locomo10.py         # LoComo10 benchmark test
│
├── core/                    # Core pipeline modules
│   ├── memory_builder.py    # MemoryBuilder: dialogue → memory entries (LLM extraction)
│   ├── hybrid_retriever.py  # HybridRetriever: semantic + keyword + structured search
│   └── answer_generator.py  # AnswerGenerator: context → answer generation
│
├── models/                  # Data models
│   └── memory_entry.py      # MemoryEntry (Pydantic), Dialogue
│
├── database/                # Storage layer
│   └── vector_store.py      # VectorStore: LanceDB + FTS (tantivy)
│
├── utils/                   # Utilities
│   ├── llm_client.py        # LLMClient: OpenAI-compatible API wrapper
│   └── embedding.py         # EmbeddingModel: Qwen3/SentenceTransformer
│
├── MCP/                     # MCP Server (multi-tenant)
│   ├── run.py               # Server runner (argparse + uvicorn)
│   ├── register.py          # User registration CLI
│   ├── requirements.txt     # MCP-specific dependencies
│   ├── server/
│   │   ├── http_server.py   # FastAPI app, REST/MCP/SSE endpoints
│   │   ├── mcp_handler.py   # MCP protocol handler (JSON-RPC)
│   │   ├── core/            # Server-side core (memory_builder, retriever, answer_generator)
│   │   ├── database/        # Server-side DB (vector_store, user_store)
│   │   ├── auth/            # JWT auth (token_manager, models)
│   │   └── integrations/    # LLM integrations (openrouter, ollama)
│   ├── frontend/            # Web UI
│   ├── config/              # Server config
│   └── reference/           # Reference materials
│
├── cross/                   # Cross-session memory
│   ├── orchestrator.py      # CrossMemOrchestrator: main entry point
│   ├── session_manager.py   # SessionManager: session lifecycle
│   ├── consolidation.py     # ConsolidationWorker: merge/decay/prune
│   ├── collectors.py        # Event collectors
│   ├── hooks.py             # Session hooks
│   ├── context_injector.py  # Context injection
│   ├── storage_sqlite.py    # SQLite storage backend
│   ├── storage_lancedb.py   # LanceDB storage backend
│   ├── api_http.py          # HTTP API
│   ├── api_mcp.py           # MCP API
│   └── types.py             # Type definitions (dataclasses/enums)
│
├── SKILL/                   # Skill integrations
│   └── simplemem-skill/     # Skill package
│
├── tests/                   # Tests
│   └── test_vector_store.py # VectorStore unit tests
│
├── scripts/                 # Scripts
│   └── docker-entrypoint.sh # Docker entrypoint
│
├── docs/                    # Documentation
├── fig/                     # Figures/images
└── test_ref/                # Test reference data
```
