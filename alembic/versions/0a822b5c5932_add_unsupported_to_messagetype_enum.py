"""Add UNSUPPORTED to MessageType enum

Revision ID: 0a822b5c5932
Revises: 2db04f919bf2
Create Date: 2025-10-02 09:56:37.343075

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '0a822b5c5932'
down_revision = '2db04f919bf2'
branch_labels = None
depends_on = None


def upgrade():
    # Add UNSUPPORTED to the messagetype enum
    op.execute("ALTER TYPE messagetype ADD VALUE 'UNSUPPORTED'")


def downgrade():
    # Note: PostgreSQL doesn't support removing enum values directly
    # This would require recreating the enum type, which is complex
    # For now, we'll leave this as a comment indicating the limitation
    pass
