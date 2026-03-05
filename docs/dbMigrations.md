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
