"""
CLI LLM integration for chat completion via CLI command
and local SentenceTransformer for embeddings.
"""

import asyncio
import json
import re
import shutil
from typing import List, Dict, Any, Optional


class CLIClient:
    """
    CLI-based LLM client.
    - chat_completion: calls a CLI command (e.g. claude-opus) via subprocess
    - embedding: uses local SentenceTransformer model
    """

    def __init__(
        self,
        cli_command: str = "claude-opus",
        cli_timeout: int = 300,
        local_embedding_model: str = "Qwen/Qwen3-Embedding-0.6B",
    ):
        self.cli_command = cli_command
        self.cli_timeout = cli_timeout
        self.local_embedding_model = local_embedding_model
        self._embedding_model = None

    def _get_embedding_model(self):
        """Lazy-load the SentenceTransformer model"""
        if self._embedding_model is None:
            from sentence_transformers import SentenceTransformer
            print(f"Loading embedding model: {self.local_embedding_model}")
            self._embedding_model = SentenceTransformer(self.local_embedding_model)
            print(f"Embedding model loaded, dimension: {self._embedding_model.get_sentence_embedding_dimension()}")
        return self._embedding_model

    async def close(self):
        """Release resources"""
        if self._embedding_model is not None:
            del self._embedding_model
            self._embedding_model = None

    async def chat_completion(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.1,
        max_tokens: Optional[int] = None,
        response_format: Optional[Dict] = None,
        stream: bool = False,
    ) -> str:
        """
        Call LLM via CLI command.

        The CLI command receives the user prompt on stdin.
        System messages are passed via --system-prompt flag.
        Includes retry mechanism for transient failures.

        Args:
            messages: List of message dicts with 'role' and 'content'
            temperature: Sampling temperature (ignored by CLI)
            max_tokens: Maximum tokens (ignored by CLI)
            response_format: Optional response format hint
            stream: Whether to stream (ignored by CLI)

        Returns:
            Generated text content
        """
        # Separate system messages and user/assistant messages
        system_parts = []
        prompt_parts = []
        for msg in messages:
            role = msg.get("role", "")
            content = msg.get("content", "")
            if role == "system":
                system_parts.append(content)
            elif role == "assistant":
                prompt_parts.append(f"Assistant: {content}")
            else:
                prompt_parts.append(content)

        # If response_format requests JSON, inject instruction into system prompt
        if response_format and response_format.get("type") == "json_object":
            system_parts.append(
                "IMPORTANT: You MUST respond with valid JSON only. "
                "No markdown, no code fences, no explanation outside the JSON object."
            )

        system_prompt = "\n".join(system_parts) if system_parts else ""
        user_prompt = "\n".join(prompt_parts)

        # Build command
        cmd = [self.cli_command]
        if system_prompt:
            cmd.extend(["--system-prompt", system_prompt])

        # Retry mechanism
        max_retries = 3
        last_error = None
        for attempt in range(max_retries):
            try:
                proc = await asyncio.create_subprocess_exec(
                    *cmd,
                    stdin=asyncio.subprocess.PIPE,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                )
                stdout, stderr = await asyncio.wait_for(
                    proc.communicate(input=user_prompt.encode("utf-8")),
                    timeout=self.cli_timeout,
                )

                if proc.returncode != 0:
                    error_msg = stderr.decode("utf-8", errors="replace").strip()
                    last_error = f"CLI command failed (exit {proc.returncode}): {error_msg}"
                    if attempt < max_retries - 1:
                        await asyncio.sleep(1 * (attempt + 1))
                        continue
                    raise RuntimeError(last_error)

                return stdout.decode("utf-8", errors="replace").strip()

            except asyncio.TimeoutError:
                last_error = f"CLI command timed out after {self.cli_timeout}s"
                if attempt < max_retries - 1:
                    await asyncio.sleep(1 * (attempt + 1))
                    continue
                raise RuntimeError(last_error)

            except FileNotFoundError:
                raise RuntimeError(
                    f"CLI command not found: {self.cli_command}. "
                    "Make sure it is installed and in PATH."
                )

        raise RuntimeError(last_error)

    async def create_embedding(
        self,
        texts: List[str],
    ) -> List[List[float]]:
        """
        Create embeddings using local SentenceTransformer model.
        Uses asyncio.to_thread to avoid blocking the event loop.

        Args:
            texts: List of texts to embed

        Returns:
            List of embedding vectors
        """
        def _encode():
            model = self._get_embedding_model()
            embeddings = model.encode(texts, normalize_embeddings=True)
            return [emb.tolist() for emb in embeddings]

        return await asyncio.to_thread(_encode)

    async def create_single_embedding(self, text: str) -> List[float]:
        """Create embedding for a single text"""
        embeddings = await self.create_embedding([text])
        return embeddings[0]

    async def verify_api_key(self) -> tuple[bool, Optional[str]]:
        """
        Verify that the CLI command exists in PATH.

        Returns:
            Tuple of (is_valid, error_message)
        """
        if shutil.which(self.cli_command):
            return True, None
        return False, f"CLI command not found: {self.cli_command}"

    def extract_json(self, text: str) -> Any:
        """
        Extract JSON from LLM response text with robust parsing

        Args:
            text: Raw text that may contain JSON

        Returns:
            Parsed JSON object
        """
        if not text:
            return None

        # Strategy 1: Direct JSON parsing
        try:
            return json.loads(text.strip())
        except json.JSONDecodeError:
            pass

        # Strategy 2: Extract from ```json ``` blocks
        json_block_pattern = r"```json\s*([\s\S]*?)\s*```"
        matches = re.findall(json_block_pattern, text, re.IGNORECASE)
        if matches:
            try:
                return json.loads(matches[0].strip())
            except json.JSONDecodeError:
                pass

        # Strategy 3: Extract from generic ``` ``` blocks
        generic_block_pattern = r"```\s*([\s\S]*?)\s*```"
        matches = re.findall(generic_block_pattern, text)
        if matches:
            for match in matches:
                try:
                    return json.loads(match.strip())
                except json.JSONDecodeError:
                    continue

        # Strategy 4: Find balanced JSON object/array
        start_obj = text.find("{")
        start_arr = text.find("[")

        if start_obj == -1 and start_arr == -1:
            return None

        if start_arr == -1 or (start_obj != -1 and start_obj < start_arr):
            json_str = self._extract_balanced_braces(text[start_obj:], "{", "}")
        else:
            json_str = self._extract_balanced_braces(text[start_arr:], "[", "]")

        if json_str:
            try:
                return json.loads(json_str)
            except json.JSONDecodeError:
                pass

        # Strategy 5: Clean and retry
        cleaned = self._clean_json_string(text)
        try:
            return json.loads(cleaned)
        except json.JSONDecodeError:
            pass

        return None

    def _extract_balanced_braces(self, text: str, open_char: str, close_char: str) -> Optional[str]:
        """Extract a balanced brace-enclosed string"""
        if not text or text[0] != open_char:
            return None

        count = 0
        in_string = False
        escape_next = False

        for i, char in enumerate(text):
            if escape_next:
                escape_next = False
                continue

            if char == "\\":
                escape_next = True
                continue

            if char == '"' and not escape_next:
                in_string = not in_string
                continue

            if in_string:
                continue

            if char == open_char:
                count += 1
            elif char == close_char:
                count -= 1
                if count == 0:
                    return text[: i + 1]

        return None

    def _clean_json_string(self, text: str) -> str:
        """Clean common JSON issues from LLM output"""
        prefixes = [
            "Here's the JSON:",
            "Here is the JSON:",
            "JSON output:",
            "Output:",
            "Result:",
        ]
        cleaned = text.strip()
        for prefix in prefixes:
            if cleaned.lower().startswith(prefix.lower()):
                cleaned = cleaned[len(prefix):].strip()

        # Remove trailing commas before } or ]
        cleaned = re.sub(r",\s*([\}\]])", r"\1", cleaned)

        # Remove single-line comments
        cleaned = re.sub(r"//.*$", "", cleaned, flags=re.MULTILINE)

        return cleaned


class CLIClientManager:
    """
    Manages CLI client instance (singleton).
    Since CLI doesn't use API keys, this is similar to OllamaClientManager.
    """

    def __init__(
        self,
        cli_command: str = "claude-opus",
        cli_timeout: int = 300,
        local_embedding_model: str = "Qwen/Qwen3-Embedding-0.6B",
    ):
        self.cli_command = cli_command
        self.cli_timeout = cli_timeout
        self.local_embedding_model = local_embedding_model
        self._client: Optional[CLIClient] = None

    def get_client(self, api_key: str = None) -> CLIClient:
        """
        Get or create a CLI client

        Args:
            api_key: Ignored for CLI (kept for interface compatibility)

        Returns:
            CLIClient instance
        """
        if self._client is None:
            self._client = CLIClient(
                cli_command=self.cli_command,
                cli_timeout=self.cli_timeout,
                local_embedding_model=self.local_embedding_model,
            )

        return self._client

    async def close_all(self):
        """Close all client connections"""
        if self._client:
            await self._client.close()
            self._client = None

    async def remove_client(self, api_key: str = None):
        """Remove and close the client (kept for interface compatibility)"""
        await self.close_all()
