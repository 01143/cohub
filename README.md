# cohub

Local workflow coordination for multiple CLI agents, including Claude Code and Codex. `cohub` lets different CLI agents share project state through a plain `.cohub/` directory so that sessions can hand off work, keep lightweight status, reuse skills, and preserve snapshot history.

## Why cohub

- File-based coordination: no daemon and no database.
- Adapter-based CLI integration: CLI-specific launch flags stay isolated from core project state.
- Cross-platform design: works on Windows, macOS, and Linux; currently tested on Windows 11 with PowerShell.
- Personal workflow first: designed for practical multi-window agent work without heavyweight orchestration.

## Maintainer Workflows

`cohub` is built for maintainers who work across multiple terminal sessions, editors, and coding agents:

- Resume work with an explicit handoff instead of reconstructing context from memory.
- Keep active agent sessions visible through a lightweight status board.
- Create semantic Git snapshots before risky changes.
- Reuse project-specific skills without copying prompts between tools.
- Keep coordination state local and auditable in plain Markdown and YAML files.

## Installation

```powershell
pip install -e .
```

After installation, the `cohub` command is available. Automatic handoff summaries use Anthropic when `ANTHROPIC_API_KEY` is set:

```powershell
$env:ANTHROPIC_API_KEY = "YOUR_ANTHROPIC_API_KEY"
```

If no key is configured, `cohub` still works and falls back to a short manual handoff note.

## Quick Start

```powershell
# 1. Initialize cohub in any project
cd D:\my-project
cohub init

# 2. Start a supported CLI with project context injected
cohub start claude

# 3. Check active sessions
cohub status

# 4. Save a semantic snapshot
cohub snap "finish first milestone"

# 5. Review snapshot history
cohub rewind

# 6. Resume later with the previous handoff context
cohub start claude
```

## Commands

| Command | Purpose |
|---|---|
| `cohub init` | Initialize `.cohub/` in the current project. |
| `cohub start <cli>` | Start a CLI with handoff, state, and matching skills injected. |
| `cohub status` | Show active sessions and stale session markers. |
| `cohub handoff [--cli claude]` | Regenerate or manually write the handoff summary. |
| `cohub snap "<message>"` | Run `git add`, commit, and create a `snap-NNN` tag. |
| `cohub rewind` | Browse snapshot history and optionally restore a snapshot. |
| `cohub skill {list|save|edit|use}` | Manage reusable local skills. |
| `cohub review --with <cli>` | Placeholder for future review workflow. |

## Skills

Skills are Markdown files stored in `~/.cohub/skills/<name>.md` with YAML front matter:

```markdown
---
name: python-cleanup
tags: [python, refactor]
when: Use when cleaning or refactoring Python code
---

# Python Cleanup

- Keep changes small and testable.
- Prefer existing project style.
```

During `cohub start`, project tags in `.cohub/meta.yaml` are matched against skill tags. Matching skills are injected into the CLI context. A skill can also be forced for a project:

```powershell
cohub skill use python-cleanup
```

## Adapter Protocol

Custom adapters can be placed in `~/.cohub/adapters/<name>.py`. An adapter should expose:

```python
NAME = "claude"
INJECTION_METHOD = "system_prompt_flag"

def build_command(system_prompt: str, project_dir: str) -> list[str]: ...
def find_latest_transcript(project_dir: str) -> Path | None: ...
def parse_transcript(path: Path) -> list[dict] | None: ...
```

Built-in adapters:

- `claude`: launches `claude --append-system-prompt "<text>"` and reads transcripts from `~/.claude/projects/`.
- `codex`: placeholder adapter for future full support.

## Directory Layout

```text
project/
  .cohub/
    handoff.md       previous session handoff summary
    state.md         manually maintained project state
    active.md        active session board with heartbeats
    snapshots.md     snapshot index
    reviews/         future review records
    meta.yaml        project metadata and skill tags

~/.cohub/
  skills/<name>.md   reusable personal skills
  adapters/<name>.py custom adapter overrides
```

## Current Limitations

- `cohub review` is a planned workflow, not a complete implementation.
- The Codex adapter is still a placeholder.
- Automatic skill extraction from sessions is not implemented.
- Active-session status is intentionally lightweight and does not use strict file locking.

## Contributing

Issues and pull requests are welcome. Useful areas include additional CLI adapters, safer snapshot workflows, cross-platform testing, and better maintainer automation around handoff summaries, review notes, and release preparation.

See [CONTRIBUTING.md](CONTRIBUTING.md) for local setup and contribution guidelines.

## Tests

```powershell
pytest tests/
```

The test suite covers project state handling, skill loading, summarization fallback, Git wrappers, and Claude/Codex adapter behavior.
