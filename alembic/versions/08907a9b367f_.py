from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '08907a9b367f'
down_revision = '7f372f689034'
branch_labels = None
depends_on = None


def upgrade():
    # Ensure that the column is properly converted before altering the type
    op.execute("ALTER TABLE clientes ALTER COLUMN id_expiration_date TYPE DATE USING id_expiration_date::DATE")


def downgrade():
    # Convert back to VARCHAR explicitly
    op.execute("ALTER TABLE clientes ALTER COLUMN id_expiration_date TYPE VARCHAR USING id_expiration_date::TEXT")
