# cohub Product Specification

`cohub` is a local coordination protocol and CLI tool for multi-agent command-line workflows. It helps users run Claude Code, Codex, and other CLI agents against the same project without losing context between sessions.

## Design Principles

1. **Externalized State**: project state is stored in Markdown and YAML files on disk.
2. **Protocol Before Tooling**: the `.cohub/` directory is the stable contract; CLI integrations are adapters.
3. **Adapter Isolation**: changes in CLI launch flags should only require adapter changes.
4. **Personal Workflow First**: concurrency warnings are lightweight and informative rather than restrictive.
5. **Git-Native Snapshots**: version history uses normal Git commits and tags.

## Core Mechanisms

| Need | Mechanism |
|---|---|
| Long-context continuity | `handoff.md` summaries are injected into the next session. |
| Multiple CLI agents | Adapters integrate different CLI tools behind a common interface. |
| Cross-session handoff | `handoff.md` and `state.md` provide durable project context. |
| Multiple active windows | `active.md` records session heartbeats. |
| Version checkpoints | `cohub snap` wraps Git commits and `snap-NNN` tags. |
| Reusable instructions | `~/.cohub/skills/` Markdown files are selected by tags. |

## Directory Structure

```text
~/.cohub/
  skills/
  adapters/
  config.yaml

project/
  .cohub/
    handoff.md
    state.md
    active.md
    snapshots.md
    reviews/
    meta.yaml
```

## Project Files

### `handoff.md`

Stores the latest session handoff summary. The intended sections are:

- Current task
- Completed work
- Blockers
- Decisions
- Suggested next steps

### `state.md`

Stores durable project status that should survive across sessions:

- Goal
- Current progress
- Important conventions
- Recent changes

### `active.md`

Stores lightweight active-session records:

```text
[session_id] cli | PID pid | started_at | current_work | heartbeat timestamp
```

### `snapshots.md`

Stores semantic snapshot history:

```text
- [timestamp] message (tag: snap-001)
```

### `meta.yaml`

Stores project metadata:

```yaml
project_name: example
tags: [python, research]
languages: [python]
goal: Local workflow coordination
skills:
  force: []
```

## Command Specification

### `cohub init`

- Creates `.cohub/` in the current project.
- Creates all required state files.
- Collects project metadata interactively.
- Offers Git initialization when the project is not already a Git repository.

### `cohub start <cli>`

- Reads `handoff.md`, `state.md`, and matching skills.
- Builds a context prompt.
- Loads the selected adapter.
- Registers the session in `active.md`.
- Starts a heartbeat thread.
- Launches the target CLI.
- Removes the session record on exit.
- Generates a handoff summary when possible.

### `cohub status`

- Reads `active.md`.
- Displays active sessions.
- Marks stale sessions based on heartbeat age.

### `cohub handoff`

- Finds the latest transcript through the selected adapter.
- Attempts an automatic summary.
- Falls back to manual input if no transcript or API key is available.

### `cohub snap "<message>"`

- Runs `git add -A`.
- Commits with the provided message.
- Creates a sequential `snap-NNN` tag.
- Appends the snapshot to `snapshots.md`.

### `cohub rewind`

- Lists snapshots.
- Lets the user inspect or restore a selected snapshot.

### `cohub skill`

- Lists, saves, edits, and force-enables reusable skills.
- Uses YAML front matter for tag matching.

### `cohub review`

- Planned review workflow.
- Current implementation is a placeholder.

## Adapter Interface

Adapters expose:

```python
NAME = "claude"
INJECTION_METHOD = "system_prompt_flag"

def build_command(system_prompt: str, project_dir: str) -> list[str]: ...
def find_latest_transcript(project_dir: str) -> Path | None: ...
def parse_transcript(path: Path) -> list[dict] | None: ...
```

## Summarization

The summarizer uses Anthropic when `ANTHROPIC_API_KEY` is configured. If automatic summarization fails, the tool asks the user for a short manual handoff note.

## MVP Scope

Included:

- Project initialization
- Claude adapter
- Active session tracking
- Handoff generation
- Git snapshots
- Skill loading and selection
- Unit tests for the main paths

Deferred:

- Complete Codex transcript support
- Real review workflow
- Automatic skill extraction
- Real-time current-task updates from transcripts
- Strict multi-process file locking

## Testing

```powershell
pytest tests/
```

The current tests cover:

- Adapter loading and parsing
- Project state file creation
- Active-session handling
- Skill front-matter parsing
- Git wrapper behavior
- Summarization fallback
