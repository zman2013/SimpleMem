# Task Completion Checklist

When completing a task, ensure the following:

## Code Quality
- [ ] Code follows existing naming conventions (snake_case functions, PascalCase classes)
- [ ] Type hints are used consistently with Optional/List/Dict
- [ ] Docstrings are added for new public methods/classes
- [ ] No hardcoded API keys or secrets

## Testing
- [ ] Run `python tests/test_vector_store.py` if database/vector store was modified
- [ ] Run `python main.py` for a quick smoke test if core pipeline was changed
- [ ] Run `python test_locomo10.py` for comprehensive evaluation if retrieval logic changed

## Configuration
- [ ] New config values added to `config.py.example` (never to `config.py`)
- [ ] New env vars added to `.env.example`
- [ ] Constructor parameters follow `Optional[T] = None` pattern with config fallback

## Notes
- No formal linting/formatting tools configured (no black, ruff, flake8, mypy in requirements)
- No pytest framework; tests are run as standalone scripts
- `config.py` and `.env` are gitignored; only example files are committed
