"""Import SQLAlchemy models here so Alembic autogenerate can discover metadata."""

from app.db.base import Base

__all__ = ["Base"]
