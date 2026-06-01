# Security Policy

## Reporting a Vulnerability

Please open a GitHub issue if you find a security concern in `cohub`.

Do not include private credentials, API keys, personal data, or confidential project material in public reports. If a report needs sensitive details, state that in the issue and share only the minimum public context needed to reproduce the problem.

## Security Model

`cohub` is designed as a local-first coordination tool:

- Project state is stored in plain local files under `.cohub/`.
- Runtime state, logs, caches, and local project data should not be committed.
- Optional summarization depends on user-provided API keys through environment variables.
- If no API key is configured, the tool falls back to a manual handoff workflow.

## Supported Version

The current `main` branch is the supported development version.
