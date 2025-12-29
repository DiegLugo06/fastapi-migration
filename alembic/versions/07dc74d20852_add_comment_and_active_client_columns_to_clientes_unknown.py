"""Add comment and active_client columns to clientes_unknown table

Revision ID: 07dc74d20852
Revises: 06dc74d20851
Create Date: 2025-08-06 13:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '07dc74d20852'
down_revision = '06dc74d20851'
branch_labels = None
depends_on = None


def upgrade():
    # Add comment column to clientes_unknown table
    op.add_column('clientes_unknown', sa.Column('comment', sa.Text(), nullable=True))
    
    # Add active_client column to clientes_unknown table
    op.add_column('clientes_unknown', sa.Column('active_client', sa.Boolean(), nullable=True, server_default='true'))


def downgrade():
    # Remove active_client column from clientes_unknown table
    op.drop_column('clientes_unknown', 'active_client')
    
    # Remove comment column from clientes_unknown table
    op.drop_column('clientes_unknown', 'comment') 