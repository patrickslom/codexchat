# Heartbeat Wizard Plan

## Goal
Build a guided Heartbeat Wizard that helps users safely create, test, and run scheduled Codex automations backed by one markdown file per heartbeat.

## Product Outcomes
- Reduce setup errors by replacing free-form heartbeat creation with step-by-step flow.
- Make heartbeats easier to understand, audit, and maintain.
- Keep risky execution modes explicit and gated.

## Wizard Flow (MVP)
1. **Goal & Template**
- User chooses a purpose (monitoring, summary, follow-up, custom).
- Optional starter template pre-fills markdown.

2. **Conversation Target**
- Select existing conversation or create dedicated heartbeat conversation.
- Show where output messages will appear.

3. **Schedule**
- Presets: every `5`, `10`, `15`, `30`, `60` minutes.
- Advanced: custom cron expression.
- Display timezone and next run preview.

4. **Instruction File (Markdown)**
- Create one file per heartbeat.
- Default path: `WORKSPACE_PATH/heartbeats/{heartbeat_id}.md`.
- In-app markdown editor with basic lint/validation.

5. **Safety & Runtime Controls**
- Execution mode (safe / yolo).
- Max runtime, retry count, overlap policy (`skip` or `queue`).
- Enabled toggle.

6. **Review & Test**
- Final summary of config.
- “Run test now” button before activation.

## Data Model (MVP)
### `heartbeat_jobs`
- `id` (uuid)
- `user_id` (fk)
- `conversation_id` (fk)
- `name`
- `description`
- `schedule_type` (`interval` or `cron`)
- `interval_minutes` (nullable)
- `cron_expr` (nullable)
- `timezone`
- `instruction_md_path`
- `instruction_md_sha256`
- `mode` (`safe`/`yolo`)
- `max_runtime_seconds`
- `retry_limit`
- `overlap_policy` (`skip`/`queue`)
- `is_enabled`
- `next_run_at`
- `last_run_at`
- `created_at`, `updated_at`

### `heartbeat_runs`
- `id` (uuid)
- `heartbeat_job_id` (fk)
- `status` (`queued`/`running`/`succeeded`/`failed`/`canceled`)
- `started_at`, `finished_at`
- `error_message` (nullable)
- `codex_request_id` (nullable)
- `output_message_id` (nullable)
- `instruction_snapshot_md`
- `instruction_snapshot_sha256`
- `created_at`

## File Strategy
- Each heartbeat owns one markdown file.
- File changes update `instruction_md_sha256`.
- At runtime, snapshot markdown content into `heartbeat_runs` for auditability.
- Soft validation on save; strict validation on run.

## Backend API (Proposed)
- `POST /api/heartbeats` create heartbeat via wizard payload.
- `GET /api/heartbeats` list current user heartbeats.
- `GET /api/heartbeats/:id` heartbeat detail.
- `PATCH /api/heartbeats/:id` update config.
- `POST /api/heartbeats/:id/test-run` trigger immediate test run.
- `POST /api/heartbeats/:id/enable` enable heartbeat.
- `POST /api/heartbeats/:id/disable` disable heartbeat.
- `GET /api/heartbeats/:id/runs` run history.
- `GET /api/heartbeats/:id/instruction` read markdown.
- `PUT /api/heartbeats/:id/instruction` update markdown.

## Worker/Scheduler Behavior
- Poll due jobs every short interval (e.g., 10s).
- Acquire per-job distributed lock before execution.
- Enforce overlap policy:
  - `skip`: do not start if prior run active.
  - `queue`: enqueue single pending run.
- Write run lifecycle events for observability.
- Recompute `next_run_at` after each run attempt.

## UI Components (Frontend)
- `HeartbeatWizardModal` (stepper container)
- `GoalStep`, `TargetStep`, `ScheduleStep`, `InstructionStep`, `SafetyStep`, `ReviewStep`
- `HeartbeatEditor` (markdown editor)
- `HeartbeatRunHistoryTable`
- `HeartbeatStatusBadge` + next run countdown

## Validation Rules
- Require conversation target.
- Require valid schedule (interval or cron).
- Require non-empty markdown.
- Cap file size and line count.
- Block enabling if validation fails.

## Security & Safety
- Keep heartbeat execution within existing workspace constraints.
- Clearly label yolo mode as destructive risk.
- Add admin-configurable caps (max jobs/user, max run duration, max retries).
- Log all test runs and production runs.

## Rollout Plan
1. Ship backend tables + minimal APIs.
2. Ship wizard UI without cron advanced mode (interval presets first).
3. Add test-run and run history.
4. Add cron + timezone preview.
5. Add templates and variables.

## Open Questions
- Should markdown files live in user-scoped directories?
- Should heartbeat runs post into existing thread or a dedicated child thread?
- What retention policy should apply to run snapshots?
- Should queued overlap permit multiple pending runs or max one?

## Success Metrics
- % of heartbeats created via wizard vs legacy flow.
- Heartbeat creation completion rate.
- Failed run rate before/after wizard launch.
- Time from “new heartbeat” to first successful run.
