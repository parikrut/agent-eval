# Usage Guide

## Installation

### Prerequisites

- **Python 3.11+** — check with `python3 --version`
- **Git** — LocalDuck runs inside git repositories
- **One of:** GitHub Copilot (via `gh` CLI) or an API key from a supported provider

### Install with pip

```sh
pip install localduck
```

### Install with uv (recommended)

```sh
uv tool install localduck
```

### Install from source

```sh
git clone https://github.com/YOUR_USERNAME/localduck.git
cd localduck
uv sync
uv run localduck --help
```

---

## Setup

Run the interactive setup wizard inside any git repository:

```sh
localduck setup
```

The wizard will:

1. **Detect GitHub Copilot** — if you have `gh` CLI authenticated, it offers to use it automatically
2. **Pick a provider** (if not using Copilot) — OpenAI, Anthropic, xAI, Gemini, DeepSeek, or Mistral
3. **Enter your API key** — stored locally in `.localduckrc`
4. **Choose checks** — toggle which categories to scan for (security, code quality, etc.)
5. **Set blocking behavior** — block commits on critical issues, warnings, all issues, or never
6. **Install the pre-commit hook** — so every `git commit` triggers a scan automatically

### Copilot Mode

If you have the GitHub CLI installed and authenticated:

```sh
gh auth login   # one-time setup
localduck setup # will auto-detect Copilot
```

No API key needed — LocalDuck uses your existing GitHub token via the GitHub Models API.

### Manual Mode

If you don't have Copilot or prefer a different provider:

```sh
localduck setup
# → Select "Manual" when prompted
# → Pick your provider (e.g., Anthropic)
# → Enter your API key
# → Choose a model
```

Supported providers and models:

| Provider      | Models                                           |
| ------------- | ------------------------------------------------ |
| OpenAI        | gpt-4o, gpt-4o-mini, o1, o3-mini                 |
| Anthropic     | claude-sonnet-4, claude-opus-4, claude-3-5-haiku |
| xAI           | grok-3, grok-3-mini                              |
| Google Gemini | gemini-2.0-flash, gemini-2.0-pro, gemini-1.5-pro |
| DeepSeek      | deepseek-chat, deepseek-reasoner                 |
| Mistral       | mistral-large, codestral                         |

---

## Scanning

### Automatic (pre-commit hook)

After setup, every `git commit` automatically scans your staged changes:

```sh
git add .
git commit -m "feat: add auth module"
# LocalDuck scans staged diff before the commit goes through
```

If issues are found above your configured severity threshold, the commit is blocked:

```
🦆 LocalDuck scanning...

  ✗ Security           1 critical
      └─ auth.py:42             Hardcoded API key detected
  ✔ Code Quality       Passed
  ✔ Documentation      Passed

🚫 Commit blocked. See report in .localduck/reports
```

To bypass the scan for a single commit:

```sh
git commit --no-verify -m "wip: quick fix"
```

### Manual scan

Scan staged changes without committing:

```sh
localduck scan
```

Scan all tracked files (not just staged):

```sh
localduck scan --all
```

---

## Reports

After every scan, a report is generated in `.localduck/reports/`.

Open the latest report in your browser:

```sh
localduck report
```

Reports are available in **HTML** (default) or **Markdown** — set with `reportFormat` in `.localduckrc`.

---

## Cache Management

LocalDuck caches review results locally using ChromaDB. When you scan a diff that's semantically similar to one already reviewed, the cached result is returned instantly — no LLM call needed.

The cache lives at `~/.localduck/cache/` and is shared across all repositories.

```sh
# View cache statistics
localduck cache stats

# Clear all cached results
localduck cache clear
```

---

## Configuration

The setup wizard generates `.localduckrc` in your project root. You can edit it manually at any time.

### Full config reference

```json
{
  "agent": "copilot",
  "provider": null,
  "model": null,
  "apiKey": null,
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

### Config fields

| Field            | Type                                               | Default                | Description                                |
| ---------------- | -------------------------------------------------- | ---------------------- | ------------------------------------------ |
| `agent`          | `"copilot"` \| `"manual"`                          | `"copilot"`            | AI mode                                    |
| `provider`       | string \| null                                     | null                   | Provider ID (manual mode only)             |
| `model`          | string \| null                                     | null                   | Model name (auto-selected if null)         |
| `apiKey`         | string \| null                                     | null                   | API key (manual mode only)                 |
| `blockOn`        | `"critical"` \| `"warning"` \| `"all"` \| `"none"` | `"critical"`           | When to block commits                      |
| `tokenBudget`    | integer                                            | 50000                  | Max tokens per scan (0 = unlimited)        |
| `cacheThreshold` | float                                              | 0.92                   | Cosine similarity threshold for cache hits |
| `maxConcurrent`  | integer                                            | 3                      | Max concurrent LLM calls                   |
| `checks`         | object                                             | see above              | Toggle individual check categories         |
| `reportFormat`   | `"html"` \| `"markdown"`                           | `"html"`               | Report output format                       |
| `reportDir`      | string                                             | `".localduck/reports"` | Where reports are saved                    |

### Environment variables

API keys can also be set via environment variables instead of storing them in `.localduckrc`:

| Provider      | Environment Variable |
| ------------- | -------------------- |
| OpenAI        | `OPENAI_API_KEY`     |
| Anthropic     | `ANTHROPIC_API_KEY`  |
| xAI           | `XAI_API_KEY`        |
| Google Gemini | `GEMINI_API_KEY`     |
| DeepSeek      | `DEEPSEEK_API_KEY`   |
| Mistral       | `MISTRAL_API_KEY`    |
| Copilot       | `GITHUB_TOKEN`       |

### .gitignore

If you're using manual mode with an API key in `.localduckrc`, add it to `.gitignore`:

```
.localduckrc
.localduck/
```

---

## Commands Reference

| Command                 | Description                                        |
| ----------------------- | -------------------------------------------------- |
| `localduck setup`       | Interactive setup wizard + install pre-commit hook |
| `localduck uninstall`   | Remove hook and config                             |
| `localduck scan`        | Scan staged changes                                |
| `localduck scan --all`  | Scan all tracked files                             |
| `localduck report`      | Open the latest report in the browser              |
| `localduck cache stats` | Show cache hit rate and entry count                |
| `localduck cache clear` | Wipe all cached review results                     |
| `localduck version`     | Show installed version                             |
| `localduck --help`      | Show all available commands                        |

---

## Uninstall

Remove the pre-commit hook and config from the current repo:

```sh
localduck uninstall
```

To fully remove LocalDuck:

```sh
pip uninstall localduck
# or
uv tool uninstall localduck

# Optionally remove the global cache
rm -rf ~/.localduck
```
