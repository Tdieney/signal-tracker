# Repository instructions for coding agents

These instructions apply to every AI/coding agent that reads, changes, tests, or generates files in this repository.

## Required reading

Before making changes:

1. Read `docs/README.md` and every document it marks as required, in order.
2. Read the latest entries in `DEVELOPER_LOG.md` so you do not repeat work or overwrite an unresolved decision.
3. Inspect the working tree and preserve changes you did not create.

## Mandatory developer log

Every task that changes code, documentation, configuration, workflows, tests, generated schemas, or repository assets MUST be recorded in the single root file `DEVELOPER_LOG.md`.

Logging workflow:

1. Before the first repository change, append a `STARTED` entry with a unique session ID, timestamp, agent identity if known, user request, scope, assumptions, planned files, and pre-existing working-tree changes.
2. Perform the work and verification.
3. Before the final response, append a second entry with the same session ID and status `COMPLETED`, `PAUSED`, or `BLOCKED`. Record the actual changes, decisions, files changed, commands/checks with results, safety/security/data impact, and remaining work.
4. Confirm the final log entry is saved before claiming completion.

Log rules:

- Append chronologically; never delete, reorder, rewrite, or reformat another session's entries.
- If an older entry is wrong, append a correction that references its session ID.
- Keep entries factual and concise. Record decisions and observable evidence, not private chain-of-thought.
- Never put secrets, credentials, private endpoints, confidential/raw provider data, personal data, or full sensitive command output in the log.
- Use ISO 8601 timestamps with an explicit UTC offset.
- Logging does not replace tests, documentation, or the final response.
- A task is not complete when its closing log entry is missing.

Use the templates at the top of `DEVELOPER_LOG.md` exactly enough to keep entries searchable and consistent.

## Scope and safety

- Follow the precedence rules in `docs/README.md`.
- Do not change signal formulas, public schema boundaries, security controls, or Phase 1 scope without explicit owner approval.
- Do not expose secrets or confidential data in frontend code, public files, logs, fixtures, build artifacts, or `VITE_*` variables.
- Do not delete or overwrite uncommitted work you did not create.
