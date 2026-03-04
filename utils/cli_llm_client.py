"""
CLI LLM Client - Calls local CLI commands (e.g. claude-opus) as LLM backend
"""
import subprocess
import time
from typing import List, Dict, Optional
import config
from utils.llm_client import BaseLLMClient


class CLILLMClient(BaseLLMClient):
    """
    LLM client that invokes a local CLI command via subprocess.
    Supports any CLI tool that accepts a prompt via stdin and outputs text to stdout.
    """

    def __init__(
        self,
        command: Optional[str] = None,
        timeout: Optional[int] = None
    ):
        self.command = command or getattr(config, 'CLI_COMMAND', 'claude-opus')
        self.timeout = timeout or getattr(config, 'CLI_TIMEOUT', 300)

    def chat_completion(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.2,
        response_format: Optional[Dict[str, str]] = None,
        max_retries: int = 3
    ) -> str:
        """
        Execute CLI command with prompt from messages.
        Uses stdin for user prompt and --system-prompt for system messages.

        Args:
        - messages: List of message dicts with 'role' and 'content'
        - temperature: Ignored (CLI has no temperature control)
        - response_format: Ignored (caller prompt already contains format instructions)
        - max_retries: Number of retry attempts with exponential backoff
        """
        system_prompt, user_prompt = self._split_messages(messages)
        cmd = [self.command, "-p"]
        if system_prompt:
            cmd.extend(["--system-prompt", system_prompt])

        last_exception = None
        for attempt in range(max_retries):
            try:
                result = subprocess.run(
                    cmd,
                    input=user_prompt,
                    capture_output=True,
                    text=True,
                    timeout=self.timeout,
                )
                if result.returncode != 0:
                    raise RuntimeError(
                        f"CLI command failed (exit code {result.returncode}): "
                        f"{result.stderr.strip()}"
                    )
                output = result.stdout.strip()
                if not output:
                    raise RuntimeError("CLI command returned empty output")
                return output

            except subprocess.TimeoutExpired:
                last_exception = RuntimeError(
                    f"CLI command timed out after {self.timeout}s"
                )
                if attempt < max_retries - 1:
                    wait_time = 2 ** attempt
                    print(f"CLI call timed out (attempt {attempt + 1}/{max_retries})")
                    print(f"Retrying in {wait_time} seconds...")
                    time.sleep(wait_time)
                else:
                    print(f"CLI call timed out after {max_retries} attempts")

            except Exception as e:
                last_exception = e
                if attempt < max_retries - 1:
                    wait_time = 2 ** attempt
                    print(f"CLI call failed (attempt {attempt + 1}/{max_retries}): {e}")
                    print(f"Retrying in {wait_time} seconds...")
                    time.sleep(wait_time)
                else:
                    print(f"CLI call failed after {max_retries} attempts: {e}")

        raise last_exception

    def _split_messages(self, messages: List[Dict[str, str]]):
        """
        Split messages into system prompt and user prompt.
        Uses claude CLI's --system-prompt for native semantic separation.
        """
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
