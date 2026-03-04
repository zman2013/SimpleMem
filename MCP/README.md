# SimpleMem MCP Server

**Production-Ready Memory Service for LLM Agents via Model Context Protocol (MCP)**

SimpleMem MCP Server is a cloud-hosted long-term memory service for LLM agents, implementing the **Streamable HTTP** transport (MCP 2025-03-26 spec). It enables AI assistants like Claude, Cursor, and other MCP-compatible clients to store, retrieve, and query conversational memories with ease.

## Features

- **Semantic Lossless Compression**: Converts dialogues into atomic, self-contained facts
- **Coreference Resolution**: Automatically replaces pronouns (he/she/it) with actual names
- **Temporal Anchoring**: Converts relative times (tomorrow, next week) to absolute timestamps
- **Hybrid Retrieval**: Semantic search + keyword matching + metadata filtering
- **Intelligent Planning**: Automatic query decomposition and reflection for complex queries
- **Multi-tenant Isolation**: Per-user data tables with token authentication
- **Multiple LLM Backends**: OpenRouter API, Ollama (local), or CLI command (e.g. `claude-opus`)
- **Local Embedding Support**: Run embeddings locally with SentenceTransformer (Qwen3-Embedding-0.6B)
- **Production Optimized**: Faster response times compared to the academic reference implementation

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    SimpleMem MCP Server                         │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │              HTTP Server (FastAPI)                        │  │
│  │  ┌────────────┐  ┌────────────┐  ┌────────────────────┐  │  │
│  │  │  Web UI    │  │  REST API  │  │  MCP Streamable    │  │  │
│  │  │  (/)       │  │  (/api/*)  │  │  HTTP (/mcp)       │  │  │
│  │  └────────────┘  └────────────┘  └────────────────────┘  │  │
│  └──────────────────────────────────────────────────────────┘  │
│                              │                                  │
│                              ▼                                  │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │                  Token Authentication                     │  │
│  │            (JWT + AES-256 Encrypted API Keys)            │  │
│  └──────────────────────────────────────────────────────────┘  │
│                              │                                  │
│         ┌────────────────────┼────────────────────┐            │
│         ▼                    ▼                    ▼            │
│  ┌────────────┐       ┌────────────┐       ┌────────────┐     │
│  │  User A    │       │  User B    │       │  User C    │     │
│  │  Table     │       │  Table     │       │  Table     │     │
│  └────────────┘       └────────────┘       └────────────┘     │
│  └─────────────────── LanceDB ──────────────────────────┘     │
│                                                                 │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │            LLM Provider (configurable)                  │  │
│  │  ┌──────────────┐ ┌──────────────┐ ┌────────────────┐  │  │
│  │  │  OpenRouter   │ │    Ollama    │ │   CLI Command  │  │  │
│  │  │  (cloud API)  │ │   (local)   │ │ (e.g. claude)  │  │  │
│  │  └──────────────┘ └──────────────┘ └────────────────┘  │  │
│  └──────────────────────────────────────────────────────────┘  │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

## Quick Start

### Using the Cloud Service

The easiest way to use SimpleMem is via our hosted service at **https://mcp.simplemem.cloud**

1. Visit `https://mcp.simplemem.cloud`
2. Enter your OpenRouter API Key
3. Get your authentication token
4. Configure your MCP client (see below)

### Self-Hosting

#### 1. Install Dependencies

```bash
cd MCP
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

#### 2. Configure Environment Variables (Optional)

```bash
# Production environment recommended settings
export JWT_SECRET_KEY="your-secure-random-secret-key"
export ENCRYPTION_KEY="your-32-byte-encryption-key!!"
```

#### 3. Start the Server

```bash
# Default: OpenRouter provider
python run.py

# Ollama provider (local LLM)
LLM_PROVIDER=ollama python run.py

# CLI provider (e.g. claude-opus CLI + local embedding)
LLM_PROVIDER=cli EMBEDDING_DIMENSION=1024 python run.py
```

Output:
```
============================================================
  SimpleMem MCP Server
  Multi-tenant Memory Service for LLM Agents
============================================================

  Web UI:     http://localhost:8000/
  REST API:   http://localhost:8000/api/
  MCP:        http://localhost:8000/mcp

------------------------------------------------------------
```

## LLM Providers

SimpleMem supports three LLM backends, configured via the `LLM_PROVIDER` environment variable.

### OpenRouter (default)

Uses [OpenRouter](https://openrouter.ai/) cloud API for both LLM and embedding.

```bash
# No extra config needed (default)
python run.py
```

Register with your OpenRouter API key:
```bash
curl -X POST http://localhost:8000/api/auth/register \
  -H 'Content-Type: application/json' \
  -d '{"openrouter_api_key": "sk-or-..."}'
```

### Ollama (local LLM)

Uses a local [Ollama](https://ollama.com/) instance for both LLM and embedding.

```bash
LLM_PROVIDER=ollama LLM_MODEL=qwen3:4b-instruct python run.py
```

Register (no API key required):
```bash
curl -X POST http://localhost:8000/api/auth/register \
  -H 'Content-Type: application/json' \
  -d '{"openrouter_api_key": ""}'
```

### CLI (command-line LLM + local embedding)

Calls any CLI command (e.g. `claude-opus`, `llm`, or a custom script) for chat completion via stdin/stdout, and uses a local [SentenceTransformer](https://sbert.net/) model for embedding.

This is useful when you already have a CLI tool that wraps an LLM and want to reuse it without running a separate API server.

```bash
LLM_PROVIDER=cli EMBEDDING_DIMENSION=1024 python run.py
```

| Environment Variable | Default | Description |
|---------------------|---------|-------------|
| `CLI_COMMAND` | `claude-opus` | CLI executable name (must be in `$PATH`) |
| `CLI_TIMEOUT` | `300` | Timeout in seconds per LLM call |
| `LOCAL_EMBEDDING_MODEL` | `Qwen/Qwen3-Embedding-0.6B` | HuggingFace model ID for local embedding |
| `EMBEDDING_DIMENSION` | `2560` | Must match the model dimension (1024 for Qwen3-Embedding-0.6B) |

**How it works:**

- **Chat completion**: The user prompt is piped to the CLI command via stdin. System messages are passed with the `--system-prompt` flag. Includes automatic retry (3 attempts) on failure.
- **Embedding**: Uses `sentence-transformers` to run the embedding model locally. The model is downloaded automatically on first use (~1.2 GB for Qwen3-Embedding-0.6B).

Register (no API key required):
```bash
curl -X POST http://localhost:8000/api/auth/register \
  -H 'Content-Type: application/json' \
  -d '{"openrouter_api_key": ""}'
```

#### Claude Code Integration

After registering and getting a token, add SimpleMem to your Claude Code settings (`~/.claude/settings.json`):

```json
{
  "mcpServers": {
    "simplemem": {
      "url": "http://localhost:8000/mcp",
      "headers": {
        "Authorization": "Bearer YOUR_TOKEN"
      }
    }
  }
}
```

Then verify in Claude Code that the MCP tools (`memory_add`, `memory_query`, etc.) are available.

## MCP Protocol

### Protocol Information

| Item | Value |
|------|-------|
| Protocol Version | 2025-03-26 |
| Transport | Streamable HTTP |
| Message Format | JSON-RPC 2.0 |
| Authentication | Bearer Token |

### Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/mcp` | POST | Send JSON-RPC messages (requests, notifications) |
| `/mcp` | GET | Server-to-client SSE stream |
| `/mcp` | DELETE | Terminate session |

### Authentication

All MCP requests require a Bearer token in the Authorization header:

```
Authorization: Bearer <your-token>
```

After initialization, include the session ID header:

```
Mcp-Session-Id: <session-id>
```

## MCP Tools

| Tool | Description |
|------|-------------|
| `memory_add` | Add a single dialogue to memory (auto-extracts facts, resolves pronouns, anchors timestamps) |
| `memory_add_batch` | Add multiple dialogues at once |
| `memory_query` | Query memories and generate AI-synthesized answers (with planning + hybrid retrieval + reflection) |
| `memory_retrieve` | Retrieve relevant memory entries (returns raw data) |
| `memory_stats` | Get memory statistics |
| `memory_clear` | Clear all memories (irreversible) |

## Client Configuration

Add to your MCP JSON settings:

```json
{
  "mcpServers": {
    "simplemem": {
      "url": "https://mcp.simplemem.cloud/mcp",
      "headers": {
        "Authorization": "Bearer YOUR_TOKEN"
      }
    }
  }
}
```


## How It Works

### Write Flow (Dialogue -> Memory)

```
Dialogue Input                  Processing                     Memory Storage
───────────────────────────────────────────────────────────────────────────

"I'll meet Bob            ┌─────────────────┐
 at Starbucks             │ LLM Processing  │
 tomorrow at 3pm"      ──▶│                 │ ──────────────▶  Atomic Fact
                          └─────────────────┘
                                                      │
                                                      ▼
                                              ┌─────────────────────────┐
                                              │ Atomic Fact:            │
                                              │ "User will meet Bob at  │
                                              │  Starbucks on           │
                                              │  2025-01-15 at 15:00"   │
                                              │                         │
                                              │ persons: [User, Bob]    │
                                              │ location: Starbucks     │
                                              │ timestamp: 2025-01-15   │
                                              │ topic: Meeting          │
                                              └───────────┬─────────────┘
                                                          │
                                                          ▼
                                              ┌─────────────────────────┐
                                              │      Embedding          │
                                              │   (qwen3-embed-4b)      │
                                              └───────────┬─────────────┘
                                                          │
                                                          ▼
                                              ┌─────────────────────────┐
                                              │   LanceDB Vector Store  │
                                              └─────────────────────────┘
```

### Read Flow (Query -> Answer)

```
User Question: "When am I meeting Bob?"
                │
                ▼
┌───────────────────────────────┐
│  1. Query Complexity Analysis │
│     - Type: Temporal query    │
│     - Entity: Bob             │
│     - Complexity: 0.3 (simple)│
└───────────────┬───────────────┘
                │
                ▼
┌───────────────────────────────┐
│  2. Generate Search Queries   │
│     → "Bob meeting time"      │
└───────────────┬───────────────┘
                │
                ▼
┌───────────────────────────────┐
│  3. Hybrid Retrieval          │
│     - Semantic (vector)       │
│     - Keyword (BM25)          │
│     - Metadata (persons)      │
└───────────────┬───────────────┘
                │
                ▼
┌───────────────────────────────┐
│  4. Answer Generation         │
│     Context + Question → LLM  │
└───────────────┬───────────────┘
                │
                ▼
┌───────────────────────────────┐
│  Response:                    │
│  {                            │
│    "answer": "15 January 2025 │
│              at 3:00 PM at    │
│              Starbucks",      │
│    "confidence": "high",      │
│    "contexts_used": 1         │
│  }                            │
└───────────────────────────────┘
```

## Configuration Options

### General

| Environment Variable | Default | Description |
|---------------------|---------|-------------|
| `LLM_PROVIDER` | `openrouter` | LLM backend: `openrouter`, `ollama`, or `cli` |
| `LLM_MODEL` | `openai/gpt-4.1-mini` | LLM model name |
| `EMBEDDING_MODEL` | `qwen3-embedding:4b` | Embedding model (OpenRouter/Ollama) |
| `EMBEDDING_DIMENSION` | `2560` | Embedding vector dimension |

### CLI Provider

| Environment Variable | Default | Description |
|---------------------|---------|-------------|
| `CLI_COMMAND` | `claude-opus` | CLI executable for chat completion |
| `CLI_TIMEOUT` | `300` | Timeout per CLI call (seconds) |
| `LOCAL_EMBEDDING_MODEL` | `Qwen/Qwen3-Embedding-0.6B` | Local SentenceTransformer model |

### Server Tuning

| Option | Default | Description |
|--------|---------|-------------|
| `window_size` | 20 | Number of dialogues per processing batch |
| `semantic_top_k` | 25 | Semantic search result count |
| `keyword_top_k` | 5 | Keyword search result count |
| `enable_planning` | true | Enable query planning |
| `enable_reflection` | true | Enable reflection iteration |
| `max_reflection_rounds` | 2 | Maximum reflection rounds |

## Development

```bash
# Development mode (auto-reload)
python run.py --reload

# Specify port
python run.py --port 3000

# View help
python run.py --help
```

## License

MIT License

## Note

Built upon SimpleMem research implementation, refactored and optimized for production deployment with multi-tenant support, faster processing, and comprehensive user isolation.
