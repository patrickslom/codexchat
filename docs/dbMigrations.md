# DB Migrations Workflow

This project uses SQLAlchemy + Alembic for PostgreSQL schema management.

## Baseline
- Baseline revision: `20260305_01` in `codexchat_back/alembic/versions/20260305_01_baseline.py`
- Baseline is intentionally empty and establishes migration history before schema tables are added.

## Environment
- Required env var: `DATABASE_URL`
- Expected format: PostgreSQL SQLAlchemy URL (example: `postgresql+psycopg://codexchat:codexchat@codexchat_db:5432/codexchat`)
- Validation is enforced at backend startup and Alembic runtime.

## Common Commands
From `codexchat_back/`:

```bash
# create a new migration file
alembic revision -m "short_description"

# create migration from SQLAlchemy model changes
alembic revision --autogenerate -m "describe_change"

# apply migrations
alembic upgrade head

# rollback one step
alembic downgrade -1

# show current DB revision
alembic current

# show migration history
alembic history
```

## Versioning Conventions
- One logical concern per migration when possible.
- Message format: `<domain>: <action>` (example: `core: create users table`).
- Keep downgrade path available when safe.
- Do not edit applied migration files; add a follow-up revision instead.

## Review Checklist
- Migration applies cleanly on empty DB.
- Migration applies cleanly over prior revisions.
- Downgrade path is present and tested where safe.
- Added/changed indexes and constraints match TODO scope.

## Conversation locks + stale recovery
- Added table: `conversation_locks` (revision `20260305_06`).
- Columns:
  - `conversation_id` (unique FK to `conversations.id`, `ON DELETE CASCADE`)
  - `locked_by` (nullable FK to `users.id`, `ON DELETE SET NULL`)
  - `owner_token` (compare-and-release ownership token)
  - `locked_at`, `last_heartbeat_at`, `expires_at`
  - `stale_after_seconds` (per-lock stale TTL)
  - `metadata_json` (system/worker ownership details when `locked_by` is null)
  - `resource_type`, `resource_id` (normalized lock resource keys)
- Default TTL assumptions:
  - `stale_after_seconds` default is `120` seconds.
  - A lock is stale when `now() - last_heartbeat_at > stale_after_seconds`.
- Recovery procedure:
  - Acquire lock by writing `owner_token` and lock timestamps.
  - Lock owner updates `last_heartbeat_at` periodically while work is active.
  - Release/refresh operations must include `owner_token` match (compare-and-release).
  - If stale, a new owner can replace the row with a new `owner_token`.
- Required indexes:
  - `ix_conversation_locks_resource_type_resource_id` on (`resource_type`, `resource_id`)
  - `ix_conversation_locks_last_heartbeat_at` on `last_heartbeat_at`
  - `ix_conversation_locks_locked_by` on `locked_by`
- Backfill notes:
  - No backfill required for this initial lock table creation.
