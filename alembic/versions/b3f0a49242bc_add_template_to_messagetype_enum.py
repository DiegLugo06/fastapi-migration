"""Add TEMPLATE to messagetype enum

Revision ID: b3f0a49242bc
Revises: 0676acc91191
Create Date: 2025-07-11 14:34:04.205968

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'b3f0a49242bc'
down_revision = '0676acc91191'
branch_labels = None
depends_on = None


def upgrade():
    # Add TEMPLATE to the messagetype enum
    op.execute("ALTER TYPE messagetype ADD VALUE 'TEMPLATE'")


def downgrade():
    # Note: PostgreSQL doesn't support removing enum values directly
    # This would require recreating the enum type, which is complex
    # For now, we'll leave this as a comment indicating the limitation
    pass
