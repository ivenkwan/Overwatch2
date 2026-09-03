# Hermes Agent + OpenCode CLI Integration: Quick-Start Technical Manual

## Overview

This manual is a step-by-step configuration checklist for integrating **Hermes Agent** (Nous Research's open-source AI orchestration framework) with the **OpenCode CLI** (a provider-agnostic coding agent). The integration uses the `hermes-opencode-plugin` to enable Hermes to delegate software engineering tasks into OpenCode's multi-agent harness — specifically the **oh-my-opencode (OMO)** orchestration layer featuring the Sisyphus agent.[^1][^2]

**Architecture summary:**[^2]

```
Hermes (brain, memory, planning, user-facing)
  ├── read_file, terminal, web_search    ← quick inline tasks
  ├── delegate_task                      ← basic Hermes subagent
  └── opencode                           ← OMO meta-subagent
        └── Sisyphus orchestrates:
              ├── Hephaestus  (deep autonomous implementation)
              ├── Oracle      (architecture decisions)
              ├── Librarian   (documentation research)
              ├── Explore     (codebase grep / search)
              └── ... all running in parallel
```

***

## Phase 1: Prerequisites Checklist

Before installing the plugin, confirm every prerequisite is satisfied.

### System Requirements

- [ ] **Node.js 18+** installed (Node 20+ recommended)[^3]
- [ ] **Python 3.10+** available on PATH (required for Hermes and plugin tests)[^4]
- [ ] **Git** installed — OpenCode benefits from a Git-initialised working directory[^5]
- [ ] **Bun** (recommended) or npm/pnpm/yarn for OpenCode plugin installation[^3]
- [ ] **macOS, Linux, or WSL** (Windows Subsystem for Linux)[^3]

### Required Tools — Not Yet Installed?

Install in this order:

```bash
# 1. Install Hermes Agent (Nous Research)
pip install hermes-agent

# 2. Install OpenCode CLI (official installer)
curl -fsSL https://opencode.ai/install | bash

# Alternatively via npm or Homebrew
npm i -g opencode-ai@latest
# brew install anomalyco/tap/opencode

# 3. Verify both CLIs are on PATH
hermes --version
opencode --version     # Must be ≥ 1.0.133 to avoid config bug
```

> **Important:** If `opencode` resolves to a non-default path (e.g., `~/.opencode/bin/opencode`), note the full path now — it will be needed when configuring the Hermes skill. Always verify with `which -a opencode`.[^5]

***

## Phase 2: Install the hermes-opencode-plugin

The plugin adds an `opencode` tool to Hermes's tool registry without modifying Hermes core.[^2]

### Step 1 — Clone Plugin into Hermes Plugins Directory

```bash
git clone https://github.com/zaycruz/hermes-opencode-plugin.git \
    ~/.hermes/plugins/opencode
```

### Step 2 — Install the Bundled Skill (Recommended)

The `SKILL.md` teaches Hermes *when* and *how* to use each OpenCode action, agent, and flag.[^1][^2]

```bash
mkdir -p ~/.hermes/skills/software-development/opencode-driven-development
cp ~/.hermes/plugins/opencode/SKILL.md \
   ~/.hermes/skills/software-development/opencode-driven-development/SKILL.md
```

### Step 3 — Restart Hermes

```bash
hermes chat   # or your usual entrypoint
```

The `opencode` tool auto-registers via `PluginContext.register_tool()` at startup. No core modifications are needed. Plugin-registered tools automatically bypass the toolset filter.[^2]

### Step 4 — Install oh-my-opencode (OMO)

OMO is the orchestration layer that provides Sisyphus and its sub-agents inside OpenCode.[^3]

```bash
# Recommended (bun)
bunx oh-my-opencode install

# Alternatives
npm install -g oh-my-opencode
pnpm add -g oh-my-opencode
```

The interactive installer asks which AI providers you have and generates `~/.config/opencode/oh-my-opencode.json` with optimal model assignments.[^6]

### Step 5 — Verify Plugin Registration

```bash
# Quick smoke test — Hermes should now have the opencode tool
hermes chat

# Inside Hermes, run:
opencode(action="status")
```

Expected output: `OpenCode CLI available` + version string. If the tool is not found, ensure `~/.hermes/plugins/opencode/plugin.yaml` exists and restart Hermes.[^2]

***

## Phase 3: Configure the API Provider

Both **Hermes** and **OpenCode** need their own provider credentials. They can share a provider or use different ones.

### 3A — Configure Hermes Provider

All API keys go in `~/.hermes/.env`. The recommended approach for China-accessible providers:[^7]

#### MiniMax (Global)

```bash
# ~/.hermes/.env
MINIMAX_API_KEY=your_key_here
```

```bash
hermes chat --provider minimax --model MiniMax-M2.7
```

Or permanently in `~/.hermes/config.yaml`:

```yaml
model:
  provider: "minimax"
  default: "MiniMax-M2.7"
```

#### MiniMax (OAuth — no API key needed)

```bash
hermes model
# → pick "MiniMax (OAuth)"
# → browser opens; sign in with your MiniMax account
# → credentials saved to ~/.hermes/auth.json
```

#### DeepSeek

```bash
# ~/.hermes/.env
DEEPSEEK_API_KEY=your_key_here
```

```yaml
# ~/.hermes/config.yaml
model:
  provider: "deepseek"
  default: "deepseek-chat"
```

#### Interactive Provider Setup (Recommended for New Installs)

```bash
hermes model
# Full wizard — add providers, run OAuth, enter API keys
```

> **Note:** `hermes model` (terminal) sets up providers; `/model` (inside a chat session) only switches between already-configured providers.[^7]

### 3B — Configure OpenCode Provider

OpenCode stores auth in `~/.local/share/opencode/auth.json`.[^8]

```bash
# Interactive login (works for most providers)
opencode auth login

# Verify at least one provider is active
opencode auth list
```

#### Set Provider via Environment Variables (Alternative)

```bash
# For MiniMax via OpenCode
export MINIMAX_API_KEY=your_key_here

# For DeepSeek
export DEEPSEEK_API_KEY=your_key_here

# For OpenRouter (covers many models including DeepSeek)
export OPENROUTER_API_KEY=your_key_here
```

#### Force a Specific Model in OpenCode

```bash
opencode run 'task description' --model minimax/MiniMax-M2.7
opencode run 'task description' --model deepseek/deepseek-chat
opencode run 'task description' --model openrouter/anthropic/claude-sonnet-4
```

Model names follow the format `provider/model-name`. Run `opencode models` to list all available models in your environment.[^6][^8]

### 3C — OMO Agent Model Configuration

Edit `~/.config/opencode/oh-my-opencode.json` to assign models per agent:[^6]

```json
{
  "$schema": "https://raw.githubusercontent.com/code-yeongyu/oh-my-opencode/master/assets/oh-my-opencode.schema.json",
  "agents": {
    "atlas": { "model": "anthropic/claude-sonnet-4-5", "variant": "max" },
    "librarian": { "model": "deepseek/deepseek-chat" },
    "explore": { "model": "minimax/MiniMax-M2.7" }
  },
  "categories": {
    "quick": { "model": "minimax/MiniMax-M2.7" },
    "unspecified-low": { "model": "deepseek/deepseek-chat" }
  }
}
```

Unspecified agents use an automatic provider fallback chain — you only need to override what you want to change.[^6]

***

## Phase 4: Configure the Iterative Two-Agent Loop

The integration creates a feedback loop where **Hermes adjusts and refines task instructions** for OpenCode, rather than issuing a single one-shot command.[^1][^2]

### How the Loop Works

```
User → Hermes (planner, memory, context)
         ↓  opencode(action="run", prompt="...", directory="...")
       OpenCode + OMO (Sisyphus orchestrates sub-agents)
         ↓  returns JSON: status, files_changed, tool_count, summary
       Hermes reviews result, updates memory, adjusts next prompt
         ↓
       Hermes issues follow-up opencode() call if task incomplete
         ↓
       Reports final outcome to user
```

### Plugin Actions Reference[^2]

| Action | Description | When to Use |
|--------|-------------|-------------|
| `run` | Fire-and-forget one-shot task | Bounded, non-interactive tasks |
| `session` | Send a message to an existing session | Multi-turn iterative work |
| `status` | Check if OpenCode CLI is available | Health check before dispatching |
| `stop` | Stop the OpenCode background server | Cleanup after long sessions |

### Agent Selection Reference[^2]

| Agent Flag | Best For |
|-----------|----------|
| *(default)* | Most tasks — Sisyphus auto-routes |
| `hephaestus` | Deep autonomous implementation |
| `prometheus` | Strategic planning before coding |
| `oracle` | Architecture decisions |
| `atlas` | Checklist-driven execution |

### Hermes Decision Framework for Tool Routing[^2]

| Task Complexity | Tool to Use |
|----------------|-------------|
| < 3 tool calls needed | Do it yourself (`read_file`, `terminal`) |
| Basic subtask | `delegate_task` (Hermes subagent) |
| Real software engineering | `opencode` (OMO meta-subagent) |

### Example: One-Shot Task Dispatch

Hermes internally calls:

```python
opencode(action="run", prompt="Add dark mode to the settings page", directory="/project")
```

OpenCode returns a structured JSON result. Hermes then:
1. Reviews `files_changed`, `tool_count`, and `summary`
2. Checks memory for project conventions
3. Issues a follow-up `opencode()` call with refined instructions if needed[^1][^2]

### Example: Multi-Turn Iterative Session

```python
# Hermes starts an interactive OpenCode session
terminal(command="opencode", workdir="~/project", background=True, pty=True)
# Returns a session_id

# Hermes submits the initial task
process(action="submit", session_id="<id>", data="Implement OAuth refresh flow and add tests")

# Hermes polls for progress
process(action="poll", session_id="<id>")
process(action="log", session_id="<id>")

# Hermes reviews output, then adjusts instructions based on result
process(action="submit", session_id="<id>", data="Now add error handling for token expiry")

# Hermes exits the session cleanly
process(action="write", session_id="<id>", data="\x03")  # Ctrl+C
```

> **Warning:** Never use `/exit` — it opens an agent selector dialog. Always exit with `Ctrl+C` (`\x03`) or `process(action="kill")`.[^1]

### Parallel Work Pattern (Isolation)

Use separate working directories to prevent session collisions:[^1]

```python
terminal(command="opencode run 'Fix issue #101 and commit'", workdir="/tmp/issue-101", background=True, pty=True)
terminal(command="opencode run 'Add parser regression tests'", workdir="/tmp/issue-102", background=True, pty=True)
process(action="list")
```

### pty Flag Reference[^1]

| Mode | pty Required? |
|------|--------------|
| `opencode run '...'` (one-shot) | ❌ Not needed |
| Interactive TUI (`opencode`) | ✅ Required |
| Background multi-turn session | ✅ Required |

***

## Phase 5: Verify Hermes Is Dispatching to OpenCode

Run these checks end-to-end to confirm the integration is working correctly.

### Check 1 — CLI Smoke Test (OpenCode Only)

```bash
opencode run 'Respond with exactly: OPENCODE_SMOKE_OK'
```

**Success criteria:**
- Output contains `OPENCODE_SMOKE_OK`
- Command exits without provider/model errors
- No auth errors displayed[^1]

### Check 2 — Plugin Status Check (via Hermes)

Inside Hermes chat:

```
opencode(action="status")
```

**Success criteria:** Returns `OpenCode CLI available` with a version number.[^2]

### Check 3 — Full Integration Smoke Test

Run the plugin's built-in test suite:[^2]

```bash
cd ~/.hermes/plugins/opencode

# Fast tests only (~10 seconds)
python -m pytest tests/test_opencode_smoke.py -v -k "status or missing_prompt or timeout" -n 0

# Full suite (~15 minutes)
python -m pytest tests/test_opencode_smoke.py -v -x -n 0
```

**Key tests and what they prove:**

| Test | What It Proves |
|------|----------------|
| `test_status_check` | CLI detection works |
| `test_missing_prompt_error` | Input validation and error handling |
| `test_create_single_file` | End-to-end file creation |
| `test_edit_existing_file` | Non-destructive editing |
| `test_multi_file_scaffold` | Package creation and test verification |
| `test_agent_selection_hephaestus` | Agent routing via `--agent` flag |
| `test_timeout_handling` | Graceful timeout degradation |
| `test_session_continuity` | Multi-turn session with incremental changes |

### Check 4 — JSON Event Stream Parsing

Verify Hermes receives structured results from OpenCode's JSON output mode:[^2]

```bash
opencode run 'Create hello.py that prints Hello World' --format json
```

Expected fields in the JSON event stream: `status`, `files_changed`, `tool_count`, `summary`. If parsing succeeds, Hermes can use these fields to decide whether to issue a follow-up task.

### Check 5 — Token Usage and Session Cost

```bash
opencode stats
opencode stats --days 7 --models minimax/MiniMax-M2.7
opencode session list
```

Use these commands to confirm OpenCode sessions are being logged and costs are trackable.[^1]

***

## Phase 6: Troubleshooting

### T1 — `command not found: opencode`

**Cause:** OpenCode binary not on PATH.[^8]

```bash
# Find the binary
which -a opencode
find ~/.opencode -name "opencode" -type f 2>/dev/null

# Add to PATH
echo 'export PATH="$HOME/.opencode/bin:$PATH"' >> ~/.bashrc
source ~/.bashrc

# Or fix npm global permissions (Linux)
mkdir ~/.npm-global
npm config set prefix '~/.npm-global'
echo 'export PATH=~/.npm-global/bin:$PATH' >> ~/.bashrc
source ~/.bashrc
npm install -g opencode-ai
```

If the binary resolves but behaviour differs between your terminal and Hermes, pin the explicit full path in the skill config:[^1]

```bash
terminal(command="$HOME/.opencode/bin/opencode run '...'", workdir="~/project")
```

### T2 — Authentication Error (401 / Invalid API Key)

```bash
# Check which credentials are stored
opencode auth list
cat ~/.local/share/opencode/auth.json

# Check environment variables
env | grep -i api_key

# Re-authenticate
opencode auth login

# For Hermes provider
hermes model   # Full wizard — re-enter key or re-run OAuth
```

**HTTP error reference:**[^8]

| Code | Meaning | Auto-Retry |
|------|---------|-----------|
| 401 | Invalid or expired API key | ❌ Manual fix required |
| 403 | No permission for this model | ❌ Manual fix required |
| 429 | Rate limit exceeded | ✅ Auto-retry with backoff |
| 503 | Provider overloaded | ✅ Auto-retry with backoff |

### T3 — `ProviderInitError` or `ProviderModelNotFoundError`

```bash
# Verify provider configuration
opencode auth list

# Clear storage and retry
rm -rf ~/.local/share/opencode

# Check correct model name format: provider/model-name
opencode models   # List all available models

# Correct examples
# anthropic/claude-sonnet-4-20250514
# deepseek/deepseek-chat
# minimax/MiniMax-M2.7
```

### T4 — Connection Timeout / ETIMEDOUT / ECONNREFUSED

```bash
# Test basic connectivity to provider
curl -v https://api.minimax.chat
curl -v https://api.deepseek.com

# Set HTTP proxy if behind corporate network
export HTTP_PROXY=http://proxy-host:port
export HTTPS_PROXY=http://proxy-host:port
export NO_PROXY=localhost,127.0.0.1

# For corporate certificates (Node.js)
export NODE_EXTRA_CA_CERTS=/path/to/corp-ca.pem

# For SSL errors (temporary workaround only)
export NODE_TLS_REJECT_UNAUTHORIZED=0
```

**VPN / corporate proxy patterns in HK enterprise environments:**[^8]

- If proxy requires NTLM auth, use `cntlm` as a local bridge
- Use split tunneling to exclude API endpoints from VPN routing
- Allowlist domains: API endpoint of your provider (e.g., `api.minimax.chat`, `api.deepseek.com`)

### T5 — OpenCode Appears Stuck or Unresponsive

```bash
# Check logs before killing
process(action="log", session_id="<id>")

# Enable debug logging for root cause
opencode --log-level DEBUG --print-logs

# View latest log files
ls -lt ~/.local/share/opencode/log/ | head
cat $(ls -t ~/.local/share/opencode/log/*.log | head -1)

# Clear cache and retry
rm -rf ~/.cache/opencode
opencode
```

### T6 — Context Overflow During Long Tasks

OpenCode automatically retries on rate limit (429) but NOT on context overflow:[^8]

```bash
# Inside OpenCode TUI
/compact     # Summarise middle conversation turns
/new         # Start a fresh session

# Switch to a model with larger context
opencode run 'task' --model openrouter/anthropic/claude-sonnet-4
```

Context overflow error messages by provider:[^8]

| Provider | Error Pattern |
|---------|--------------|
| Anthropic | `prompt is too long` |
| DeepSeek | `maximum context length is X tokens` |
| MiniMax | `context window exceeds limit` |
| OpenAI | `exceeds the context window` |

### T7 — Wrong Binary Selected (PATH Conflict)

```bash
# Check all opencode binaries on PATH
terminal(command="which -a opencode")
terminal(command="opencode --version")

# Pin explicit binary path to avoid mismatch
terminal(command="$HOME/.opencode/bin/opencode run '...'")
```

### T8 — Plugin Not Registering in Hermes

```bash
# Confirm file structure
ls ~/.hermes/plugins/opencode/
# Should show: plugin.yaml, __init__.py, opencode_tool.py, SKILL.md, tests/

# Check plugin manifest
cat ~/.hermes/plugins/opencode/plugin.yaml

# Restart Hermes with verbose output
hermes chat --debug
```

### T9 — `hermes-opencode-plugin` Update

```bash
cd ~/.hermes/plugins/opencode && git pull
# Hermes core stays untouched; hermes update won't break the plugin
```

***

## Quick Diagnostic Checklist

When something breaks, run through this sequence:[^8]

- [ ] `opencode --version` — confirm ≥ 1.0.133
- [ ] `opencode auth list` — is at least one provider active?
- [ ] `opencode run 'Respond with: OPENCODE_SMOKE_OK'` — end-to-end test
- [ ] `hermes --version` — Hermes is installed
- [ ] `opencode(action="status")` inside Hermes chat — plugin registered?
- [ ] `cat ~/.hermes/.env | grep API_KEY` — env vars present?
- [ ] `python -m pytest tests/test_opencode_smoke.py -v -k "status"` — plugin test passes?
- [ ] `opencode --log-level DEBUG --print-logs` — check for hidden errors
- [ ] Network: `curl -v <provider_api_endpoint>` — can you reach the provider?
- [ ] `opencode session list` — sessions are being created and logged?

***

## Configuration File Reference

| File | Purpose |
|------|---------|
| `~/.hermes/config.yaml` | Hermes provider, model, and behaviour settings |
| `~/.hermes/.env` | API keys for Hermes providers |
| `~/.hermes/auth.json` | OAuth credentials for Hermes |
| `~/.hermes/plugins/opencode/plugin.yaml` | Plugin manifest for auto-registration |
| `~/.hermes/skills/software-development/opencode-driven-development/SKILL.md` | Skill instructions for when/how Hermes uses OpenCode |
| `~/.config/opencode/opencode.json` | OpenCode global config (permissions, providers) |
| `~/.config/opencode/oh-my-opencode.json` | OMO agent model assignments |
| `~/.local/share/opencode/auth.json` | OpenCode provider credentials |
| `~/.local/share/opencode/log/` | OpenCode debug logs |
| `.opencode/oh-my-opencode.json` | Project-level OMO config (wins over global) |

---

## References

1. [Delegate coding to OpenCode CLI (features, PR review)](https://hermes-agent.nousresearch.com/docs/user-guide/skills/bundled/autonomous-ai-agents/autonomous-ai-agents-opencode) - Delegate coding to OpenCode CLI (features, PR review)

2. [zaycruz/hermes-opencode-plugin](https://github.com/zaycruz/hermes-opencode-plugin) - OpenCode integration plugin for Hermes Agent — dispatch coding tasks to OMO's multi-agent harness - ...

3. [OpenCode Tutorial - Getting Started with Oh My OpenCode](https://ohmyopencode.com/opencode-tutorial/) - OpenCode tutorial for developers: install OpenCode, configure Oh My OpenCode, and run your first AI ...

4. [Oh My OpenCode Quick Start & Best Practices](https://opencodeguide.com/en/oh-my-opencode-best-practices) - Learn how to quickly get started with Oh My OpenCode, configure multi-agent systems, and follow best...

5. [Hermes Agent 整合OpenCode CLI 的实战经验 - AtomGit开源社区](https://gitcode.csdn.net/69ecb1e054b52172bc700042.html) - Hermes Agent 是一个开源 AI 代理框架，核心优势在于多模型支持、工具调用和灵活的 Skill 机制。它擅长完成搜索信息、整理数据、调度任务等工作。OpenCode 是一个 provide...

6. [oh-my-opencode/docs/guide/overview.md at dev - GitHub](https://github.com/code-yeongyu/oh-my-opencode/blob/dev/docs/guide/overview.md) - The Best Agent Harness. Meet Sisyphus: The Batteries-Included Agent that codes like you. - code-yeon...

7. [AI Providers | Hermes Agent - nous research](https://hermes-agent.nousresearch.com/docs/integrations/providers) - This page covers setting up inference providers for Hermes Agent — from cloud APIs like OpenRouter a...

8. [Troubleshooting: Quickly Diagnose and Fix Common Issues](https://learnopencode.com/en/appendix/troubleshoot) - OpenCode 是终端 AI 编程助手，本教程从零基础到进阶，教你用 AI 写代码、改 Bug、自动化办公。支持智谱、DeepSeek 等国产模型，完全免费开源。

