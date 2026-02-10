# Contributing Guide

## Coding Standards

### Logging
We use `structlog` exclusively. **Do not use standard python logging f-strings.**

✅ **Correct:**
```python
logger.info("user_login", user_id="123", status="success")
```

❌ **Incorrect:**
```python
logger.info(f"User {user_id} logged in successfully")
```

### Async/Await
The entire bot is asynchronous. Ensure all I/O operations (API calls, DB access) are awaited to prevent blocking the event loop.

## Testing

We use `pytest` for testing.

### Running Tests
- **Run all tests:**
  ```bash
  uv run pytest tests/ -v
  ```
- **Run with coverage:**
  ```bash
  uv run pytest --cov=knowledge_finder_bot tests/
  ```

### Writing Tests
- Use `pytest-asyncio` for async tests.
- Mock external services (Azure, Graph API, nlm-proxy) using `unittest.mock` or `pytest-mock`.
- Place fixtures in `tests/conftest.py`.

## Git Workflow

1. **Branching:** Create feature branches from `main`.
   - Format: `feature/description` or `fix/issue-description`.
2. **Commits:** Use [Conventional Commits](https://www.conventionalcommits.org/).
   - `feat: add new command`
   - `fix: resolve crash on startup`
   - `docs: update setup guide`
3. **Pull Requests:** Open a PR to `main` and ensure CI checks pass.
