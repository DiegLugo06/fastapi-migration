"""Add reminders table

Revision ID: ccd333b5ce6f
Revises: cac8d7d79f11
Create Date: 2025-01-15 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'ccd333b5ce6f'
down_revision = 'cac8d7d79f11'
branch_labels = None
depends_on = None


def upgrade():
    # Create reminders table
    op.create_table('reminders',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('solicitud_id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('reminder_datetime', sa.DateTime(), nullable=False),
        sa.Column('message', sa.Text(), nullable=True),
        sa.Column('status', sa.String(length=20), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['solicitud_id'], ['solicitudes.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create index on reminder_datetime for efficient querying
    op.create_index(op.f('ix_reminders_reminder_datetime'), 'reminders', ['reminder_datetime'], unique=False)
    
    # Create index on status for filtering
    op.create_index(op.f('ix_reminders_status'), 'reminders', ['status'], unique=False)


def downgrade():
    # Drop indexes
    op.drop_index(op.f('ix_reminders_status'), table_name='reminders')
    op.drop_index(op.f('ix_reminders_reminder_datetime'), table_name='reminders')
    
    # Drop table
    op.drop_table('reminders') 