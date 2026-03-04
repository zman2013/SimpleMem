# Suggested Commands

## Setup
```bash
# Install dependencies
pip install -r requirements.txt

# (Optional) GPU dependencies
pip install -r requirements-gpu.txt

# Create config
cp config.py.example config.py
# Edit config.py with your API key and settings
```

## Run
```bash
# Run main system test
python main.py

# Run LoComo10 benchmark
python test_locomo10.py

# Run VectorStore tests
python tests/test_vector_store.py
```

## MCP Server
```bash
# Install MCP server dependencies
pip install -r MCP/requirements.txt

# Start MCP server
python MCP/run.py --host 0.0.0.0 --port 8000

# Register a user
python MCP/register.py
```

## Docker
```bash
# Build and run with Docker Compose
cp .env.example .env
# Edit .env with your settings
docker compose --env-file .env up -d

# Or build manually
docker build -t simplemem .
```

## Git
```bash
git status
git log --oneline -10
git diff
```

## Utilities (Linux)
```bash
ls, cd, grep, find, cat, head, tail
```
