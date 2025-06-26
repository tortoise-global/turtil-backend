from logging.config import fileConfig
from sqlalchemy import pool
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.engine import Connection
from alembic import context
import asyncio
import sys
import os

# Add the project root to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# Import our application configuration and models
from app.config import settings
from app.models.base import UUIDBaseModel

# Import all models to ensure they're registered with SQLAlchemy
from app.models.staff import Staff
from app.models.college import College
from app.models.department import Department
from app.models.session import UserSession
from app.models.email_otp import CmsEmailOTP
from app.models.permission import CMSStaffPermission, CMSModules, CMSRoles
# Import new academic program models
from app.models.term import Term
from app.models.graduation import Graduation
from app.models.degree import Degree
from app.models.branch import Branch
from app.models.subject import Subject
from app.models.section import Section
from app.models.section_subject import SectionSubject

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Interpret the config file for Python logging.
# This line sets up loggers basically.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)


# URL encode the database URL to handle special characters
import urllib.parse
encoded_url = settings.database_url.replace('%', '%%')  # Escape % for configparser
config.set_main_option("sqlalchemy.url", encoded_url)

# add your model's MetaData object here
# for 'autogenerate' support
target_metadata = UUIDBaseModel.metadata

# other values from the config, defined by the needs of env.py,
# can be acquired:
# my_important_option = config.get_main_option("my_important_option")
# ... etc.


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.

    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well.  By skipping the Engine creation
    we don't even need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the
    script output.

    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    context.configure(connection=connection, target_metadata=target_metadata)

    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    """Run migrations in 'online' mode with asyncpg."""
    connectable = create_async_engine(
        settings.database_url,
        poolclass=pool.NullPool,
    )

    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)

    await connectable.dispose()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode."""
    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
