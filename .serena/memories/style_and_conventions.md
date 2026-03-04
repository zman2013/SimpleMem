# Code Style and Conventions

## General
- **Language**: Python 3.11+
- **Encoding**: UTF-8
- **Naming**: snake_case for functions/variables, PascalCase for classes
- **Constants**: UPPER_SNAKE_CASE (defined in config.py)
- **Private methods**: Prefixed with `_` (e.g., `_parse_llm_response`)

## Type Hints
- Used throughout the codebase with `typing` module (List, Optional, Dict, etc.)
- Pydantic v2 models for data structures (`MemoryEntry`, `Dialogue`)
- Dataclasses used in cross-session module (`cross/types.py`)

## Docstrings
- Triple-quote docstrings on classes and public methods
- Format: Brief description + Args section with `- param: description`
- Module-level docstrings at the top of each file

## Code Organization
- Each module has a clear single responsibility
- `__init__.py` files are present but minimal
- Config values have sensible defaults with Optional overrides in constructors
- Heavy use of `Optional[T] = None` pattern with fallback to config defaults

## Imports
- Standard library first, then third-party, then local
- Relative imports not used; all imports are from package roots (e.g., `from core.memory_builder import MemoryBuilder`)

## Error Handling
- Print statements for logging (no structured logging framework in core)
- `logging` module used in cross-session module
- Try/except with fallback patterns in embedding initialization

## Patterns
- Builder/Pipeline pattern for memory processing
- Strategy pattern for retrieval (semantic, keyword, structured)
- Parallel processing with `concurrent.futures.ThreadPoolExecutor`
- JSON parsing from LLM responses with regex fallbacks
