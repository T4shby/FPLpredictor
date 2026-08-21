Revision ID: 0001_initial
Revises:
Create Date: 2026-08-21
"""

from alembic import op
import sqlalchemy as sa

revision = "0001_initial"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    from backend.app.db.models import Base

    Base.metadata.create_all(bind=bind)


def downgrade() -> None:
    bind = op.get_bind()
    from backend.app.db.models import Base

    Base.metadata.drop_all(bind=bind)
