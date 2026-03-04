# Plan: Add CLI LLM Provider to SimpleMem MCP Server + Configure Claude Code

## Goal
- MCP Server 新增 `cli` provider：chat_completion 走 `claude-opus` CLI，embedding 走本地 `sentence-transformers` (Qwen3-Embedding-0.6B)
- 配置 Claude Code user-level MCP 连接

## Files to Modify

### 1. `MCP/config/settings.py` — 新增 3 个配置字段
- `cli_command` (env: CLI_COMMAND, default: "claude-opus")
- `cli_timeout` (env: CLI_TIMEOUT, default: 300)
- `local_embedding_model` (env: LOCAL_EMBEDDING_MODEL, default: "Qwen/Qwen3-Embedding-0.6B")
- 更新 `llm_provider` 注释添加 `"cli"` 选项

### 2. `MCP/server/integrations/cli_llm.py` — 新建文件
**CLIClient** 类，实现完整接口：
- `async chat_completion()` — 用 `asyncio.create_subprocess_exec` 调 CLI 命令，stdin 传 prompt，`--system-prompt` 传 system 消息，含重试机制
- `async create_embedding()` — 用本地 `SentenceTransformer` 模型，`asyncio.to_thread()` 避免阻塞
- `async create_single_embedding()` — 包装 `create_embedding`
- `async verify_api_key()` — `shutil.which()` 检查命令存在
- `extract_json()` — 从 OllamaClient 复制（同步方法，5 策略 JSON 提取）
- `async close()` — 释放 embedding 模型

**CLIClientManager** 类（单例模式，同 OllamaClientManager）：
- `get_client(api_key=None)` — 忽略 api_key，返回单例
- `async close_all()` / `async remove_client()`

### 3. `MCP/server/integrations/__init__.py` — 添加导出
- 导入 `CLIClient`, `CLIClientManager`

### 4. `MCP/server/http_server.py` — 三处修改
- 添加 import `CLIClient, CLIClientManager`
- ~106 行 provider 选择添加 `elif settings.llm_provider == "cli"` 分支
- ~296 行 register 端点添加 `elif settings.llm_provider == "cli"` 分支（placeholder key）

### 5. `MCP/requirements.txt` — 添加依赖
- `sentence-transformers>=4.0.0`

### 6. `~/.claude/settings.json` — 添加 MCP server 配置
- 在 `mcpServers` 中添加 `simplemem` 条目

## Deployment
1. 安装依赖：`cd MCP && pip install -r requirements.txt`
2. 设置环境变量并启动：`LLM_PROVIDER=cli EMBEDDING_DIMENSION=1024 python run.py`
3. 注册获取 token：`curl -X POST http://localhost:8000/api/auth/register -H 'Content-Type: application/json' -d '{"openrouter_api_key": ""}'`
4. 将 token 写入 `~/.claude/settings.json`

## Key Design Decisions
- embedding dimension: Qwen3-Embedding-0.6B 是 1024 维（非 2560），需设 `EMBEDDING_DIMENSION=1024`
- 不复用 `utils/embedding.py`，因为它依赖 root config 模块，与 MCP config 体系不同
- `chat_completion` 用 `asyncio.create_subprocess_exec`（真正异步），不用 `to_thread`
- `create_embedding` 用 `asyncio.to_thread`（CPU 密集计算）
- 首次使用会自动下载 embedding 模型（~1.2GB）

## Verification
1. 启动 MCP Server 后访问 `http://localhost:8000/` 验证 Web UI
2. 注册用户获取 token
3. 在 Claude Code 中验证 SimpleMem MCP 工具可用（memory_add, memory_query 等）
4. 测试 `memory_add` 添加对话 → `memory_query` 查询
