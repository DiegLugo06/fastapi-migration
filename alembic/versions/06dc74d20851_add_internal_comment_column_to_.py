"""Add internal_comment column to solicitudes table

Revision ID: 06dc74d20851
Revises: 68e1ec95cb9a
Create Date: 2025-07-24 15:53:55.095859

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '06dc74d20851'
down_revision = '68e1ec95cb9a'
branch_labels = None
depends_on = None


def upgrade():
    # Add internal_comment column to solicitudes table
    op.add_column('solicitudes', sa.Column('internal_comment', sa.Text(), nullable=True))


def downgrade():
    # Remove internal_comment column from solicitudes table
    op.drop_column('solicitudes', 'internal_comment')
