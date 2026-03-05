You are working in /root/codexchat.

  Follow these files strictly:
  - docs/RULES.md
  - docs/builderLOOP.md
  - docs/INDEX.md
  - docs/codexchatmvp.md
  - docs/TODO/frontendTODO.md
  - docs/TODO/backendTODO.md
  - docs/TODO/dbTODO.md

  Execution requirements for this run:
  1) Select exactly one next unchecked task using
  builderLOOP priority/order.
  2) Because I explicitly want frontend-first now, select
  from docs/TODO/frontendTODO.md.
  3) Pick the next unchecked frontend task
  4) Announce the selected task with file path + exact
  checklist line.
  5) Ask me exactly 3 short questions before implementing.
  6) Implement only that task (and minimal required sub-
  work).
  7) Validate your changes (lint/typecheck/build if
  available).
  8) Update the TODO checkbox to complete with date note.
  9) Commit with a clear message.
  10) Push to origin master.
  11) Rebuild/restart containers.
  12) Run smoke checks (web reachable on active dev host).
  13) Report results: files changed, commit hash, deploy
  status, smoke status.
  14) Stop.

  Important context for this VPS:
  - Current active dev host is todo.flounderboard.com
  routed to codexchat_front.
  - Existing Traefik network is n8n_default; do not create
  a new network.
  - This domain routing is temporary and documented in
  docs/codexchatmvp.md.
  - README.md should not be changed for VPS-specific
  temporary domain notes.

  Hard constraints:
  - Do not start a second task in the same run.
  - If blocked, stop and report exact blocker.
  - If push/deploy/smoke fails, do not mark task complete.
  - Keep changes tightly scoped to the selected task.