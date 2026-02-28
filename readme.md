> ⚠️ **Work in Progress** — This project is under active development. Expect bugs, breaking changes, and incomplete features.

# LocalDuck

An AI-powered pre-commit hook that reviews your staged code before it reaches your repo. It catches security issues, code smells, and quality problems at commit time — not in code review.

## Why install it

- **Catches issues early** — scans your diff before the commit goes through, not after
- **No new workflow** — works automatically on every `git commit`
- **Works with what you have** — uses GitHub Copilot (no API key needed) or any major LLM provider
- **Fast** — caches results locally so repeated or similar diffs don't cost extra LLM calls

## Requirements

- Python 3.11+
- Git
- GitHub Copilot (via `gh` CLI) **or** an API key from OpenAI, Anthropic, xAI, Gemini, DeepSeek, or Mistral

## Install

```sh
uv tool install localduck
```

or with pip:

```sh
pip install localduck
```

## Setup

Run the setup wizard inside any git repo:

```sh
localduck setup
```

This walks you through picking an AI provider, configuring which checks to run, and installing the pre-commit hook. That's it — every `git commit` will now trigger a scan automatically.

**Using GitHub Copilot?** Authenticate with `gh auth login` first and setup will detect it automatically. No API key required.

## Usage

After setup, scans happen automatically on commit. You can also run a manual scan at any time:

```sh
localduck scan
```

To bypass the hook for a single commit:

```sh
git commit --no-verify -m "your message"
```
