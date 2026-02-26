# 🦆 LocalDuck

> **Local AI-Powered Code Quality & Security Scanner — like Black Duck, but for your machine.**

---

## Overview

LocalDuck is an open-source Python CLI tool that acts as an AI-powered quality gate inside your Git repo. It installs as a pre-commit hook and reviews your staged diff before every commit — catching security vulnerabilities, code smells, and quality issues using the AI provider you already have access to.

No SaaS account. No cloud pipeline. No data leaving your machine beyond the diff sent to your chosen AI model.

---

## The Problem

AI coding assistants help you write code faster. None of them stop bad code from being committed.

- **Linters** catch syntax, not logic or security intent.
- **Code review** is async, slow, and skipped under pressure.
- **Black Duck / Veracode** are powerful but expensive, cloud-dependent, and built for enterprise contracts.

**LocalDuck fills the gap:** a zero-infrastructure AI quality gate that runs the moment you type `git commit`.

---

## How It Works

**Install once:**

```sh
pip install localduck
# or with uv (recommended):
uv tool install localduck

localduck setup
```

The setup wizard detects your AI configuration, lets you pick which checks matter for your project, and installs a pre-commit Git hook. From that point on, every `git commit` automatically scans your staged diff.

**At commit time, the pipeline runs:**

1. **Collect** — `git diff --staged` is extracted; lockfiles, images, fonts, and sourcemaps are filtered out
2. **Embed** — each file diff is embedded locally using `sentence-transformers` (free, no API call, milliseconds per file)
3. **Cache check** — ChromaDB is queried for semantically similar diffs already reviewed; cache hits return instantly with zero LLM calls
4. **Deduplicate** — near-identical diffs within the current batch (boilerplate, generated code) are grouped; only one representative is reviewed
5. **Review** — remaining unique diffs are batched to fit the model's context window and sent to the LLM asynchronously via LiteLLM
6. **Store & report** — results are written back to ChromaDB for future cache hits, and an HTML or Markdown report is generated

```
🦆 LocalDuck scanning staged changes...

  ✔ Code Quality       Passed
  ✔ Documentation      Passed
  ✗ Security           2 issues found
      └─ auth.py:42    Hardcoded API key detected
      └─ db.py:18      Potential SQL injection risk
  ✗ Code Smell         1 issue found
      └─ utils.py:87   Function exceeds 80 lines

🚫 Commit blocked. See report: .localduck/reports/report-2026-02-25.html
```

After the first full scan, the expected cache hit rate is **60–80%** for typical projects — meaning most commits make only a handful of LLM calls regardless of how many files changed.

---

## AI Integration

LocalDuck routes all LLM calls through **LiteLLM**, giving you a single interface across all providers. Two modes are supported:

### GitHub Copilot

Auto-detected if you have the `gh` CLI authenticated. Uses the GitHub Models API — no separate API key needed.

```sh
gh auth login   # one-time setup
```

LocalDuck detects your `gh` token automatically and uses `gpt-4o` via the GitHub Models endpoint. No extra config required.

### Manual — API Key

Choose any provider during `localduck setup`:

| Provider | Models |
|---|---|
| OpenAI | gpt-4o, gpt-4o-mini, o1, o3-mini |
| Anthropic | claude-sonnet-4, claude-opus-4, claude-3-5-haiku |
| xAI | grok-3, grok-3-mini |
| Google Gemini | gemini-2.0-flash, gemini-2.0-pro, gemini-1.5-pro |
| DeepSeek | deepseek-chat, deepseek-reasoner |
| Mistral | mistral-large, codestral |

Your API key is stored in `.localduckrc` (add to `.gitignore` if sharing the repo). Keys can also be set via environment variables.

---

## Checks

| Check | What It Catches |
|---|---|
| **Code Quality** | Style, complexity, dead code, duplication |
| **Security** | Injection risks, hardcoded secrets, insecure functions |
| **Code Smell** | Large functions, deep nesting, magic numbers |
| **License & Compliance** | Dependency license detection and compatibility |
| **Documentation** | Missing docstrings, undocumented public APIs |
| **Test Coverage** | Missing tests, test anti-patterns |
| **Performance** | N+1 queries, memory leaks, inefficient loops |
| **Accessibility** | Missing ARIA, non-semantic HTML, missing alt text |
| **AI/LLM-Specific** | Prompt injection risks, sensitive data in prompts |

All checks are toggleable — enable only what matters for your stack.

---

## Plan

### Architecture

```
git diff --staged
       │
       ▼
  [ filter ]  ──── skip lockfiles / images / fonts / sourcemaps
       │
       ▼
  [ embed ]   ──── sentence-transformers (all-MiniLM-L6-v2), local, free
       │
       ▼
  [ cache ]   ──── ChromaDB similarity query (cosine distance threshold)
       │                  │
       │            cache hit? ──► return stored result immediately
       │
       ▼
  [ dedup ]   ──── group near-identical diffs in current batch
       │
       ▼
  [ batch ]   ──── pack unique diffs into context-window-sized prompts
       │
       ▼
  [ review ]  ──── LiteLLM async calls (with retry + backoff)
       │
       ▼
  [ store ]   ──── write embeddings + results back to ChromaDB
       │
       ▼
  [ report ]  ──── HTML / Markdown report, block or pass commit
```

### Rate Limit Resilience

- Configurable concurrency limit (`maxConcurrent` in config)
- Parses `Retry-After` headers and applies jittered exponential backoff via `tenacity`
- Automatic provider rotation: if the primary provider returns 429 repeatedly, LocalDuck falls back to the next configured provider
- A single provider's rate limit never fails the commit

### Token Budget Enforcement

Set a hard cap on tokens per commit (`tokenBudget` in config). LocalDuck:

1. Ranks files by risk surface — security-sensitive paths (`auth`, `db`, `crypto`, `env`) are reviewed first
2. Stops batching when the budget is reached
3. Reports which files were skipped and why

### Embedding Cache

The ChromaDB collection lives at `~/.localduck/cache/` and persists across repos and commits. A diff is a cache hit when cosine similarity exceeds the configurable `cacheThreshold` (default `0.92`). Cache entries store the full review result and the original review timestamp.

---

## Configuration (`.localduckrc`)

Generated by `localduck setup`. Edit anytime.

```json
{
  "agent": "copilot",
  "blockOn": "critical",
  "tokenBudget": 50000,
  "cacheThreshold": 0.92,
  "maxConcurrent": 3,
  "checks": {
    "codeQuality": true,
    "security": true,
    "codeSmell": true,
    "license": false,
    "documentation": true,
    "testCoverage": false,
    "performance": false,
    "accessibility": false,
    "llmSpecific": false
  },
  "reportFormat": "html",
  "reportDir": ".localduck/reports"
}
```

For manual providers:

```json
{
  "agent": "manual",
  "provider": "anthropic",
  "model": "claude-sonnet-4-20250514",
  "apiKey": "sk-ant-...",
  "blockOn": "critical",
  "tokenBudget": 80000
}
```

**`blockOn` options:** `"critical"` · `"warning"` · `"all"` · `"none"`

---

## Commands

```sh
localduck setup               # interactive setup + install pre-commit hook
localduck uninstall           # remove hook and config

localduck scan                # manual scan of staged changes
localduck scan --all          # scan all tracked files
localduck report              # open the latest report
localduck cache clear         # wipe the local embedding cache
localduck cache stats         # show cache hit rate and entry count
```

---

## Project Structure

```
your-project/
├── .localduck/
│   └── reports/              # generated HTML / Markdown reports
├── .localduckrc              # config (add to .gitignore if using an API key)
└── .git/hooks/
    └── pre-commit            # installed by LocalDuck
```

Global cache (shared across all repos):

```
~/.localduck/
└── cache/                    # ChromaDB persistent collection
```

Source layout:

```
src/localduck/
├── agents/
│   ├── base.py               # abstract adapter, prompt building, chunking
│   ├── copilot.py            # GitHub Models API adapter
│   ├── manual.py             # LiteLLM multi-provider adapter
│   ├── detect.py             # Copilot auto-detection via gh CLI
│   └── __init__.py           # adapter factory
├── scanner/
│   ├── embedder.py           # sentence-transformers embedding
│   ├── cache.py              # ChromaDB read/write
│   ├── dedup.py              # batch deduplication
│   └── pipeline.py           # full scan pipeline (filter → embed → cache → review)
├── cli/
│   ├── setup.py              # interactive setup wizard (questionary)
│   └── uninstall.py          # clean removal
├── hooks/
│   └── install.py            # pre-commit hook installer
├── reports/
│   └── generate.py           # HTML + Markdown report generator (Jinja2)
├── runner.py                 # scan orchestrator (asyncio + tenacity)
├── git.py                    # git diff utilities
├── config.py                 # config loader + defaults
├── types.py                  # dataclasses / TypedDicts
└── cli.py                    # Typer CLI entrypoint
```

---

## Tech Stack

| Layer | Technology |
|---|---|
| Language | Python 3.11+ |
| Package manager | `uv` |
| CLI framework | Typer + Rich |
| Interactive setup | questionary |
| LLM gateway | LiteLLM — all providers, one interface |
| Local vector DB | ChromaDB — embedded, no server required |
| Embeddings | sentence-transformers (`all-MiniLM-L6-v2`) — local, free |
| Async runtime | asyncio |
| Retry / backoff | tenacity |
| HTTP client | httpx |
| Report templates | Jinja2 |
| Git integration | subprocess (`git diff --staged`) |

---

## Why LocalDuck?

- Runs entirely on your machine — no SaaS, no cloud pipeline
- Works with AI providers you already pay for
- Only the staged diff is ever sent to the AI — nothing else leaves your machine
- Blocking is opt-in and configurable by severity
- Local embedding cache means repeated patterns cost nothing after the first scan
- Open-source — extend it, fork it, contribute to it

---

## Contributing

Good first contributions:

- Add a new check category to the prompt templates
- Improve the HTML report template
- Add tests for the scanner pipeline
- Implement a new LiteLLM provider preset

Open an issue or submit a PR to get started.
