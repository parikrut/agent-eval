# Contributing to LocalDuck

Thanks for your interest in contributing! Here's everything you need to get started.

## Development Setup

```sh
# Clone the repo
git clone https://github.com/YOUR_USERNAME/localduck.git
cd localduck

# Install uv (if you don't have it)
curl -LsSf https://astral.sh/uv/install.sh | sh

# Create venv and install dependencies
uv sync --dev

# Verify everything works
uv run ruff check src/
uv run pytest
```

## Project Structure

```
src/localduck/
├── agents/           # LLM adapters (Copilot, LiteLLM multi-provider)
├── scanner/          # Core scan pipeline (filter, embed, cache, dedup, batch)
├── cli/              # Setup wizard and uninstall
├── hooks/            # Pre-commit hook installer
├── reports/          # HTML + Markdown report generation (Jinja2)
├── cli.py            # Typer CLI entrypoint
├── runner.py         # Async scan orchestrator
├── config.py         # Pydantic config model
├── git.py            # Git diff extraction
└── types.py          # Core data types
```

## Architecture Overview

```
CLI (Typer) → Runner → Pipeline
                          ├── filter (skip lockfiles, images, etc.)
                          ├── embed (sentence-transformers, local)
                          ├── cache check (ChromaDB cosine similarity)
                          ├── dedup (group near-identical diffs)
                          ├── batch (fit into context window)
                          ├── review (LLM call via adapter)
                          └── store (write results back to cache)
```

## Code Style

- **Formatter & linter**: `ruff` — run `uv run ruff check src/` and `uv run ruff format src/`
- **Type checking**: `pyright` strict mode — run `uv run pyright src/`
- **Imports**: sorted by `ruff` (isort rules enabled)
- **Line length**: 99 characters
- **Naming**: `snake_case` for functions/variables, `PascalCase` for classes, `UPPER_CASE` for constants

## Running Tests

```sh
uv run pytest -v
```

## Good First Contributions

1. **Add a new check category** — add the category to `types.py`, update `config.py`, update the system prompt in `agents/base.py`
2. **Improve the HTML report** — edit `reports/templates/report.html.j2`
3. **Add a new provider preset** — add to the `PROVIDER_MODELS` dict in `agents/manual.py`
4. **Write tests** — especially for `scanner/filter.py`, `scanner/batcher.py`, `config.py`

## PR Process

1. Fork the repo and create a branch from `main`
2. Make your changes
3. Ensure `ruff check`, `ruff format --check`, `pyright`, and `pytest` all pass
4. Submit a PR using the template
5. Wait for review

## Questions?

Open an issue — happy to help.
