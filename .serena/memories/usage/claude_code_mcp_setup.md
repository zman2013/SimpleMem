# 在 Claude Code 中使用 SimpleMem MCP

## 方式一：云服务（最简单）

1. 访问 https://mcp.simplemem.cloud 注册获取 token
2. 配置 `~/.claude/settings.json`：

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

## 方式二：自建服务

### 1. 启动 MCP Server

```bash
cd /data1/github/SimpleMem/MCP

# CLI provider（本地，不需要 API key）
LLM_PROVIDER=cli EMBEDDING_DIMENSION=1024 python run.py

# OpenRouter（需要 API key）
python run.py

# Ollama（本地 LLM）
LLM_PROVIDER=ollama LLM_MODEL=qwen3:4b-instruct python run.py
```

### 2. 注册获取 token

```bash
# CLI/Ollama provider（空 key 即可）
curl -s -X POST http://localhost:8000/api/auth/register \
  -H 'Content-Type: application/json' \
  -d '{"openrouter_api_key": ""}'

# OpenRouter provider
curl -s -X POST http://localhost:8000/api/auth/register \
  -H 'Content-Type: application/json' \
  -d '{"openrouter_api_key": "sk-or-..."}'
```

### 3. 配置 Claude Code

```json
// ~/.claude/settings.json
{
  "mcpServers": {
    "simplemem": {
      "url": "http://localhost:8000/mcp",
      "headers": {
        "Authorization": "Bearer <步骤2返回的token>"
      }
    }
  }
}
```

## 可用的 MCP 工具（6 个）

| 工具 | 功能 |
|------|------|
| `memory_add` | 添加单条对话（自动提取事实、解析代词、锚定时间） |
| `memory_add_batch` | 批量添加对话 |
| `memory_query` | 查询记忆（AI 合成回答） |
| `memory_retrieve` | 检索原始记忆条目 |
| `memory_stats` | 查看记忆统计 |
| `memory_clear` | 清空所有记忆 |

## LLM Provider 选项

| Provider | 环境变量 | 说明 |
|----------|---------|------|
| CLI | `LLM_PROVIDER=cli` | 调用本地 CLI（如 `claude-opus`）+ 本地 embedding，无需网络 |
| OpenRouter | `LLM_PROVIDER=openrouter` | 默认，需要 API key |
| Ollama | `LLM_PROVIDER=ollama` | 本地 Ollama 服务 |

## CLI Provider 配置项

| 环境变量 | 默认值 | 说明 |
|----------|--------|------|
| `CLI_COMMAND` | `claude-opus` | CLI 可执行文件 |
| `CLI_TIMEOUT` | `300` | 超时（秒） |
| `LOCAL_EMBEDDING_MODEL` | `Qwen/Qwen3-Embedding-0.6B` | 本地 embedding 模型 |
| `EMBEDDING_DIMENSION` | `2560`（CLI 用 `1024`） | embedding 向量维度 |

## Docker 部署

```bash
cd /data1/github/SimpleMem/MCP
cp .env.example .env  # 编辑配置
docker compose up -d
```

访问：http://localhost:8000/

## MCP 协议信息

- Protocol Version: 2025-03-26
- Transport: Streamable HTTP / SSE
- Message Format: JSON-RPC 2.0
- Authentication: Bearer Token
