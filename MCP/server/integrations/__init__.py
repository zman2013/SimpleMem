"""External integrations for SimpleMem"""

from .openrouter import OpenRouterClient, OpenRouterClientManager
from .ollama import OllamaClient, OllamaClientManager
from .cli_llm import CLIClient, CLIClientManager

__all__ = [
    "OpenRouterClient",
    "OpenRouterClientManager",
    "OllamaClient",
    "OllamaClientManager",
    "CLIClient",
    "CLIClientManager",
]
