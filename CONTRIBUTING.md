# Contributing to cohub

Thank you for considering a contribution to `cohub`.

## Development Setup

```powershell
git clone https://github.com/01143/cohub.git
cd cohub
pip install -e .
pip install pytest
pytest tests/
```

## Contribution Areas

- CLI adapters for additional coding tools.
- Safer Git snapshot and rewind workflows.
- Maintainer automation for handoffs, review notes, and release preparation.
- Cross-platform testing on Windows, macOS, and Linux.
- Documentation improvements with concrete workflow examples.

## Pull Request Guidelines

- Keep changes focused and easy to review.
- Add or update tests for behavior changes.
- Avoid committing local `.cohub/` state, API keys, logs, caches, or generated runtime data.
- Document any new command, adapter protocol change, or user-visible workflow.

## Local Security

`cohub` is a local-first coordination tool. Contributions should preserve that model: project state should remain in local files unless a user explicitly chooses an integration that sends data elsewhere.
