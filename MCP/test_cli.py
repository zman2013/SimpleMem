#!/usr/bin/env python3
"""
Verification script for CLI LLM Provider.

4-layer progressive testing:
  Layer 1: Unit tests (no external dependencies, uses mocks)
  Layer 2: Integration tests (requires real CLI + sentence-transformers)
  Layer 3: HTTP server E2E (prints curl templates for manual verification)
  Layer 4: Regression checks (import verification)

Usage:
  # Run all layers (layer 2 needs CLI + sentence-transformers installed):
  cd /data1/github/SimpleMem/MCP && python test_cli.py

  # Run only unit tests (no external dependencies):
  cd /data1/github/SimpleMem/MCP && python test_cli.py --unit-only
"""

import asyncio
import json
import os
import shutil
import sys
import argparse
from unittest.mock import patch, MagicMock, AsyncMock

sys.path.insert(0, os.path.dirname(__file__))


# ─────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────

passed = 0
failed = 0
skipped = 0


def report(name: str, ok: bool, detail: str = ""):
    global passed, failed
    if ok:
        passed += 1
        print(f"   ✓ {name}")
    else:
        failed += 1
        msg = f"   ✗ {name}"
        if detail:
            msg += f" — {detail}"
        print(msg)


def skip(name: str, reason: str = ""):
    global skipped
    skipped += 1
    msg = f"   ⊘ {name} [SKIP]"
    if reason:
        msg += f" — {reason}"
    print(msg)


# ─────────────────────────────────────────────────────────────
# Layer 1: Unit Tests (no external dependencies)
# ─────────────────────────────────────────────────────────────

def test_layer1():
    print("\n" + "=" * 60)
    print("  Layer 1: Unit Tests (no external dependencies)")
    print("=" * 60)

    test_settings_cli_fields()
    test_verify_api_key()
    test_extract_json()
    test_cli_client_manager_singleton()
    test_http_server_provider_branch()


def test_settings_cli_fields():
    """1.1 — Settings loads cli_command, cli_timeout, local_embedding_model"""
    print("\n1.1 Settings — CLI fields")

    env = {
        "LLM_PROVIDER": "cli",
        "CLI_COMMAND": "my-custom-cli",
        "CLI_TIMEOUT": "600",
        "LOCAL_EMBEDDING_MODEL": "Qwen/Qwen3-Embedding-0.6B",
    }

    from config.settings import Settings

    with patch.dict(os.environ, env, clear=False):
        s = Settings()

    report("llm_provider == 'cli'", s.llm_provider == "cli", f"got {s.llm_provider!r}")
    report("cli_command == 'my-custom-cli'", s.cli_command == "my-custom-cli", f"got {s.cli_command!r}")
    report("cli_timeout == 600", s.cli_timeout == 600, f"got {s.cli_timeout!r}")
    report("local_embedding_model set", s.local_embedding_model == "Qwen/Qwen3-Embedding-0.6B",
           f"got {s.local_embedding_model!r}")


def test_verify_api_key():
    """1.2 — verify_api_key returns True when CLI command is in PATH"""
    print("\n1.2 verify_api_key()")

    from server.integrations.cli_llm import CLIClient

    # Case A: command exists
    with patch("shutil.which", return_value="/usr/bin/fake-cli"):
        client = CLIClient(cli_command="fake-cli")
        ok, err = asyncio.run(client.verify_api_key())
        report("found in PATH → (True, None)", ok is True and err is None,
               f"got ({ok}, {err!r})")

    # Case B: command missing
    with patch("shutil.which", return_value=None):
        client = CLIClient(cli_command="nonexistent-cmd")
        ok, err = asyncio.run(client.verify_api_key())
        report("missing → (False, error msg)", ok is False and err is not None,
               f"got ({ok}, {err!r})")


def test_extract_json():
    """1.3 — extract_json with 5 strategies"""
    print("\n1.3 extract_json() — 5 strategies")

    from server.integrations.cli_llm import CLIClient
    client = CLIClient()

    # Strategy 1: Direct JSON
    result = client.extract_json('{"key": "value"}')
    report("Strategy 1 — direct JSON", result == {"key": "value"}, f"got {result!r}")

    # Strategy 2: ```json block
    text = 'Here is the result:\n```json\n{"a": 1}\n```\nDone.'
    result = client.extract_json(text)
    report("Strategy 2 — ```json block", result == {"a": 1}, f"got {result!r}")

    # Strategy 3: Generic ``` block
    text = 'Output:\n```\n[1, 2, 3]\n```'
    result = client.extract_json(text)
    report("Strategy 3 — generic ``` block", result == [1, 2, 3], f"got {result!r}")

    # Strategy 4: Balanced braces
    text = 'The answer is {"name": "test", "nested": {"x": 1}} and more text.'
    result = client.extract_json(text)
    report("Strategy 4 — balanced braces", result == {"name": "test", "nested": {"x": 1}},
           f"got {result!r}")

    # Strategy 4b: Balanced brackets (array)
    text = 'List: [{"id": 1}, {"id": 2}] end'
    result = client.extract_json(text)
    report("Strategy 4b — balanced brackets (array)",
           result == [{"id": 1}, {"id": 2}], f"got {result!r}")

    # Strategy 5: Clean & retry (trailing comma)
    text = '{"a": 1, "b": 2,}'
    result = client.extract_json(text)
    report("Strategy 5 — trailing comma cleanup", result == {"a": 1, "b": 2},
           f"got {result!r}")

    # Edge: empty/None
    result = client.extract_json("")
    report("Edge — empty string → None", result is None, f"got {result!r}")
    result = client.extract_json("no json here at all")
    report("Edge — no JSON → None", result is None, f"got {result!r}")


def test_cli_client_manager_singleton():
    """1.4 — CLIClientManager returns same instance, ignores api_key"""
    print("\n1.4 CLIClientManager singleton")

    from server.integrations.cli_llm import CLIClientManager

    mgr = CLIClientManager(cli_command="test-cmd")
    c1 = mgr.get_client(api_key="key-A")
    c2 = mgr.get_client(api_key="key-B")
    c3 = mgr.get_client()

    report("get_client() returns same instance", c1 is c2 and c2 is c3)
    report("api_key ignored (same obj)", c1 is c3)
    report("cli_command propagated", c1.cli_command == "test-cmd",
           f"got {c1.cli_command!r}")


def test_http_server_provider_branch():
    """1.5 — LLM_PROVIDER=cli → client_manager is CLIClientManager"""
    print("\n1.5 http_server provider branch")

    from server.integrations.cli_llm import CLIClientManager

    # We can't easily re-import http_server module-level vars,
    # so we test the branching logic directly.
    env = {
        "LLM_PROVIDER": "cli",
        "CLI_COMMAND": "claude-opus",
        "CLI_TIMEOUT": "300",
        "LOCAL_EMBEDDING_MODEL": "Qwen/Qwen3-Embedding-0.6B",
    }

    from config.settings import Settings

    with patch.dict(os.environ, env, clear=False):
        s = Settings()

    # Simulate the branching from http_server.py
    if s.llm_provider == "cli":
        cm = CLIClientManager(
            cli_command=s.cli_command,
            cli_timeout=s.cli_timeout,
            local_embedding_model=s.local_embedding_model,
        )
    else:
        cm = None

    report("client_manager is CLIClientManager", isinstance(cm, CLIClientManager))
    report("cli_command from settings", cm.cli_command == "claude-opus",
           f"got {cm.cli_command!r}")


# ─────────────────────────────────────────────────────────────
# Layer 2: Integration Tests (real CLI + sentence-transformers)
# ─────────────────────────────────────────────────────────────

async def test_layer2():
    print("\n" + "=" * 60)
    print("  Layer 2: Integration Tests (real CLI + embeddings)")
    print("=" * 60)

    from server.integrations.cli_llm import CLIClient

    # Pre-checks
    cli_cmd = os.getenv("CLI_COMMAND", "claude-opus")
    if not shutil.which(cli_cmd):
        skip("All Layer 2 tests", f"CLI command '{cli_cmd}' not found in PATH")
        return

    try:
        import sentence_transformers  # noqa: F401
    except ImportError:
        skip("All Layer 2 tests",
             "sentence-transformers not installed. Run: pip install 'sentence-transformers>=4.0.0'")
        return

    await test_embedding(CLIClient)
    await test_chat_completion(CLIClient, cli_cmd)


async def test_embedding(CLIClient):
    """2b — Embedding test"""
    print("\n2b. Embedding test")

    import math

    client = CLIClient()
    try:
        embedding = await client.create_single_embedding("test text for embedding verification")
        dim = len(embedding)
        report(f"Embedding dimension == 1024", dim == 1024, f"got {dim}")

        # Verify L2 normalization
        l2_norm = math.sqrt(sum(x * x for x in embedding))
        report(f"L2 norm ≈ 1.0", abs(l2_norm - 1.0) < 0.01, f"got {l2_norm:.6f}")

        # Batch embedding
        embeddings = await client.create_embedding(["hello", "world"])
        report("Batch embedding returns 2 vectors", len(embeddings) == 2,
               f"got {len(embeddings)}")
    except Exception as e:
        report("Embedding generation", False, str(e))
    finally:
        await client.close()


async def test_chat_completion(CLIClient, cli_cmd: str):
    """2c — Chat completion test"""
    print("\n2c. Chat completion test")

    client = CLIClient(cli_command=cli_cmd, cli_timeout=120)
    try:
        # Basic call
        response = await client.chat_completion(
            messages=[{"role": "user", "content": "Say hello in exactly 3 words."}],
            temperature=0.1,
        )
        report("Chat returns non-empty string", isinstance(response, str) and len(response) > 0,
               f"got {len(response)} chars: {response[:80]!r}")

        # With system prompt
        response2 = await client.chat_completion(
            messages=[
                {"role": "system", "content": "You are a pirate. Reply in pirate speak."},
                {"role": "user", "content": "Say hello."},
            ],
            temperature=0.1,
        )
        report("Chat with system prompt returns non-empty", len(response2) > 0,
               f"got {len(response2)} chars: {response2[:80]!r}")
    except Exception as e:
        report("Chat completion", False, str(e))
    finally:
        await client.close()


# ─────────────────────────────────────────────────────────────
# Layer 3: HTTP Server E2E (curl templates)
# ─────────────────────────────────────────────────────────────

def print_layer3():
    print("\n" + "=" * 60)
    print("  Layer 3: HTTP Server E2E (manual curl commands)")
    print("=" * 60)
    print("""
  To run the E2E test manually:

  1. Start the server:
     cd /data1/github/SimpleMem/MCP
     LLM_PROVIDER=cli EMBEDDING_DIMENSION=1024 python run.py &

  2. Register a user:
     curl -s -X POST http://localhost:8000/api/auth/register \\
       -H 'Content-Type: application/json' \\
       -d '{"username":"testcli","password":"testpass123","openrouter_api_key":""}' \\
       | python -m json.tool
     # → save the "token" value

  3. Verify token:
     TOKEN="<token from step 2>"
     curl -s http://localhost:8000/api/auth/verify \\
       -H "Authorization: Bearer $TOKEN" \\
       | python -m json.tool

  4. MCP initialize:
     SESSION=$(curl -s -X POST http://localhost:8000/mcp/ \\
       -H 'Content-Type: application/json' \\
       -H "Authorization: Bearer $TOKEN" \\
       -d '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2025-03-26","capabilities":{},"clientInfo":{"name":"test","version":"1.0"}}}' \\
       -D - 2>&1 | grep -i 'mcp-session-id' | cut -d' ' -f2 | tr -d '\\r')
     echo "Session: $SESSION"

  5. List tools:
     curl -s -X POST http://localhost:8000/mcp/ \\
       -H 'Content-Type: application/json' \\
       -H "Authorization: Bearer $TOKEN" \\
       -H "Mcp-Session-Id: $SESSION" \\
       -d '{"jsonrpc":"2.0","id":2,"method":"tools/list","params":{}}' \\
       | python -m json.tool
     # → expect 6 tools

  6. Add a memory:
     curl -s -X POST http://localhost:8000/mcp/ \\
       -H 'Content-Type: application/json' \\
       -H "Authorization: Bearer $TOKEN" \\
       -H "Mcp-Session-Id: $SESSION" \\
       -d '{"jsonrpc":"2.0","id":3,"method":"tools/call","params":{"name":"memory_add","arguments":{"content":"User likes hiking in the mountains on weekends."}}}' \\
       | python -m json.tool

  7. Query the memory:
     curl -s -X POST http://localhost:8000/mcp/ \\
       -H 'Content-Type: application/json' \\
       -H "Authorization: Bearer $TOKEN" \\
       -H "Mcp-Session-Id: $SESSION" \\
       -d '{"jsonrpc":"2.0","id":4,"method":"tools/call","params":{"name":"memory_query","arguments":{"query":"What does the user like to do on weekends?"}}}' \\
       | python -m json.tool

  8. Stop the server:
     kill %1
""")


# ─────────────────────────────────────────────────────────────
# Layer 4: Regression Checks
# ─────────────────────────────────────────────────────────────

def test_layer4():
    print("\n" + "=" * 60)
    print("  Layer 4: Regression Checks")
    print("=" * 60)
    print()

    # 4.1 — All three providers importable from integrations __init__
    try:
        from server.integrations import (
            OpenRouterClient, OpenRouterClientManager,
            OllamaClient, OllamaClientManager,
            CLIClient, CLIClientManager,
        )
        report("Import all 3 providers from server.integrations", True)
    except ImportError as e:
        report("Import all 3 providers from server.integrations", False, str(e))

    # 4.2 — Default provider is openrouter
    from config.settings import Settings

    # Clear any overrides that may linger
    env_clean = {k: v for k, v in os.environ.items() if k != "LLM_PROVIDER"}
    with patch.dict(os.environ, env_clean, clear=True):
        # Need to also ensure no .env override
        with patch("config.settings._load_env_file"):
            s = Settings()
    report("Default llm_provider == 'openrouter'", s.llm_provider == "openrouter",
           f"got {s.llm_provider!r}")

    # 4.3 — OpenRouter branch creates OpenRouterClientManager
    from server.integrations.openrouter import OpenRouterClientManager as ORCM
    if s.llm_provider != "cli" and s.llm_provider != "ollama":
        cm = ORCM(base_url=s.openrouter_base_url, llm_model=s.llm_model,
                   embedding_model=s.embedding_model)
        report("Default branch → OpenRouterClientManager", isinstance(cm, ORCM))

    # 4.4 — Ollama still importable and constructible
    try:
        from server.integrations.ollama import OllamaClient as OC
        oc = OC(base_url="http://localhost:11434/v1")
        report("OllamaClient constructible", oc is not None)
    except Exception as e:
        report("OllamaClient constructible", False, str(e))


# ─────────────────────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="CLI LLM Provider Verification")
    parser.add_argument("--unit-only", action="store_true",
                        help="Run only Layer 1 unit tests (no external dependencies)")
    args = parser.parse_args()

    print("=" * 60)
    print("  SimpleMem MCP — CLI LLM Provider Verification")
    print("=" * 60)

    # Layer 1: always run
    test_layer1()

    # Layer 2: integration (skip with --unit-only)
    if args.unit_only:
        print("\n" + "=" * 60)
        print("  Layer 2: Skipped (--unit-only)")
        print("=" * 60)
    else:
        asyncio.run(test_layer2())

    # Layer 3: print curl templates
    print_layer3()

    # Layer 4: regression
    test_layer4()

    # Summary
    total = passed + failed + skipped
    print("\n" + "=" * 60)
    print(f"  Summary: {passed} passed, {failed} failed, {skipped} skipped / {total} total")
    print("=" * 60)

    sys.exit(1 if failed > 0 else 0)


if __name__ == "__main__":
    main()
