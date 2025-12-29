from logging.config import fileConfig
from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config

from alembic import context

# Import your models and database config
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.config import DATABASE_URL
from app.database import async_engine
from sqlmodel import SQLModel

# Import all models so Alembic can detect them
from app.apps.cms.models import PageContent
from app.apps.authentication.models import User
from app.apps.product.models import Motorcycles, MotorcycleBrand, Discounts, StaticQuotes
from app.apps.quote.models import Banco, FinancingOption
# Import other models as needed

# this is the Alembic Config object
config = context.config

# Override sqlalchemy.url with your database URL
# Use sync URL for Alembic (remove asyncpg)
sync_database_url = DATABASE_URL.replace("postgresql+asyncpg://", "postgresql://")
config.set_main_option("sqlalchemy.url", sync_database_url)

# Interpret the config file for Python logging
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Add your model's MetaData object here for 'autogenerate' support
target_metadata = SQLModel.metadata

def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode."""
    # Create a sync engine for Alembic
    from sqlalchemy import create_engine
    sync_url = DATABASE_URL.replace("postgresql+asyncpg://", "postgresql://")
    connectable = create_engine(sync_url, poolclass=pool.NullPool)

    with connectable.connect() as connection:
        context.configure(
            connection=connection, 
            target_metadata=target_metadata
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()