# Plan: 添加 CLI LLM 适配器（支持 claude-opus 等本地命令）

## 目标
让 `LLMClient` 支持通过 subprocess 调用本地 CLI 命令（如 `claude-opus -p "prompt"`）作为 LLM 后端，同时保持对现有 OpenAI API 后端的完全兼容，并方便扩展到其他 CLI 工具。

## 改动文件清单

| 文件 | 操作 | 说明 |
|------|------|------|
| `utils/llm_client.py` | 修改 | 提取 `BaseLLMClient` 基类；添加 `create_llm_client()` 工厂函数 |
| `utils/cli_llm_client.py` | **新建** | `CLILLMClient` 类，通过 subprocess 调用 CLI 命令 |
| `utils/__init__.py` | 修改 | 导出新符号 |
| `main.py` | 修改 | 用 `create_llm_client()` 替换 `LLMClient()` 直接构造 |
| `config.py.example` | 修改 | 添加 CLI 后端配置项 |

**不需要修改**: `core/memory_builder.py`, `core/hybrid_retriever.py`, `core/answer_generator.py`, `test_locomo10.py`

---

## 步骤 1: `config.py.example` — 添加配置项

在 "Advanced LLM Features" 段后添加:

```python
# ============================================================================
# LLM Backend Configuration
# ============================================================================

# Backend type: "api" (OpenAI-compatible HTTP) or "cli" (local CLI command)
LLM_BACKEND = "api"

# CLI Backend Settings (used when LLM_BACKEND = "cli")
CLI_COMMAND = "claude-opus"       # CLI executable name
CLI_TIMEOUT = 300                 # Timeout in seconds
```

---

## 步骤 2: `utils/llm_client.py` — 提取基类 + 工厂函数

### 2a. 添加 `BaseLLMClient` 基类（`LLMClient` 之前）

将 `extract_json`、`_clean_json_string`、`_extract_balanced_json` 三个纯文本解析方法从 `LLMClient` 移入基类，所有子类共享。

```python
from abc import ABC, abstractmethod

class BaseLLMClient(ABC):
    @abstractmethod
    def chat_completion(self, messages, temperature=0.2,
                        response_format=None, max_retries=3) -> str: ...

    def extract_json(self, text: str) -> Any:
        # 现有代码不变，从 LLMClient 移入
    def _clean_json_string(self, json_str: str) -> str:
        # 同上
    def _extract_balanced_json(self, text: str, start_char: str) -> Any:
        # 同上
```

### 2b. `LLMClient` 继承 `BaseLLMClient`

```python
class LLMClient(BaseLLMClient):
    # __init__, chat_completion, _handle_streaming_response 不变
    # 删除已移入基类的三个方法
```

### 2c. 文件末尾添加工厂函数

```python
def create_llm_client(**kwargs) -> BaseLLMClient:
    backend = getattr(config, 'LLM_BACKEND', 'api').lower()
    if backend == 'cli':
        from utils.cli_llm_client import CLILLMClient
        return CLILLMClient(
            command=kwargs.get('command'),
            timeout=kwargs.get('timeout'),
        )
    elif backend == 'api':
        return LLMClient(
            api_key=kwargs.get('api_key'),
            model=kwargs.get('model'),
            base_url=kwargs.get('base_url'),
            enable_thinking=kwargs.get('enable_thinking'),
            use_streaming=kwargs.get('use_streaming'),
        )
    else:
        raise ValueError(f"Unknown LLM_BACKEND: '{backend}'. Supported: 'api', 'cli'")
```

---

## 步骤 3: `utils/cli_llm_client.py` — 新建 CLI 适配器

### 经验证的关键事实

- `claude-opus` 支持 **stdin 管道输入**: `echo "prompt" | claude-opus -p`（无需传 `-` 参数）
- `claude-opus` 支持 `--system-prompt` 原生分离系统提示
- `claude-opus` 支持 `--output-format json` 结构化输出
- `claude-opus` 支持 `--json-schema` 约束 JSON 格式

### 核心设计

```python
import subprocess
from utils.llm_client import BaseLLMClient

class CLILLMClient(BaseLLMClient):
    def __init__(self, command=None, timeout=None):
        self.command = command or getattr(config, 'CLI_COMMAND', 'claude-opus')
        self.timeout = timeout or getattr(config, 'CLI_TIMEOUT', 300)

    def chat_completion(self, messages, temperature=0.2,
                        response_format=None, max_retries=3) -> str:
        system_prompt, user_prompt = self._split_messages(messages)
        cmd = [self.command, "-p"]
        if system_prompt:
            cmd.extend(["--system-prompt", system_prompt])

        # 重试逻辑（指数退避，与 LLMClient 一致）
        for attempt in range(max_retries):
            try:
                result = subprocess.run(
                    cmd,
                    input=user_prompt,      # 通过 stdin 传入，无长度限制
                    capture_output=True,
                    text=True,
                    timeout=self.timeout,
                )
                if result.returncode != 0:
                    raise RuntimeError(f"CLI failed ({result.returncode}): {result.stderr.strip()}")
                output = result.stdout.strip()
                if not output:
                    raise RuntimeError("CLI returned empty output")
                return output
            except subprocess.TimeoutExpired as e:
                # 超时处理 + 重试日志
            except Exception as e:
                # 失败处理 + 指数退避

        raise last_exception

    def _split_messages(self, messages):
        """从 messages 中分离 system prompt 和 user prompt。
        利用 claude CLI 的 --system-prompt 原生参数，保持语义分离。"""
        system_parts = []
        user_parts = []
        for msg in messages:
            role = msg.get("role", "user")
            content = msg.get("content", "")
            if role == "system":
                system_parts.append(content)
            else:
                user_parts.append(content)
        return "\n\n".join(system_parts) or None, "\n\n".join(user_parts)
```

### 关键决策

| 决策 | 说明 |
|------|------|
| **stdin 传 prompt** | 已验证可用，避免 OS 命令行参数长度限制 |
| **`--system-prompt` 分离** | 利用 claude CLI 原生支持，比拼接 `[System Instructions]` 标签更准确 |
| **`temperature` 忽略** | CLI 无此控制，不影响正确性 |
| **`response_format` 忽略** | caller 的 prompt 文本已含 JSON 格式指令，`extract_json()` 能处理 |
| **不用 `shell=True`** | 安全考虑，避免注入 |

---

## 步骤 4: `utils/__init__.py` — 更新导出

```python
from .llm_client import LLMClient, BaseLLMClient, create_llm_client
from .cli_llm_client import CLILLMClient
from .embedding import EmbeddingModel

__all__ = ['LLMClient', 'BaseLLMClient', 'CLILLMClient',
           'create_llm_client', 'EmbeddingModel']
```

---

## 步骤 5: `main.py` — 使用工厂函数

改动 2 行:

```python
# 之前:
from utils.llm_client import LLMClient
self.llm_client = LLMClient(api_key=api_key, model=model, ...)

# 之后:
from utils.llm_client import create_llm_client
self.llm_client = create_llm_client(api_key=api_key, model=model, ...)
```

当 `LLM_BACKEND = "api"` 时行为完全不变。

---

## 扩展性

添加新 CLI 工具只需改 `config.py`:
```python
CLI_COMMAND = "other-cli-tool"
```

如果工具调用方式不同（如无 `--system-prompt`），可子类化 `CLILLMClient` 覆写 `chat_completion`，在工厂中注册新 backend 名称。

---

## 验证方式

1. **默认回归**: `LLM_BACKEND = "api"` -> `python main.py` 确认无影响
2. **CLI 测试**: `LLM_BACKEND = "cli"`, `CLI_COMMAND = "claude-opus"` -> `python main.py` 跑完整管道
3. **工厂测试**: 验证 `create_llm_client()` 按 config 返回正确类实例
4. **异常测试**: CLI 不存在 / 超时 / 空输出
