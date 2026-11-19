from logging.config import fileConfig

from alembic import context

from app import models  # noqa: F401  (modeller Base.metadata'ya kaydolsun diye)
from app.core.database import Base, engine
from app.models.base import UTCDateTime

config = context.config

# Uygulama içinden çalıştırılırken ini dosyası verilmez; uygulamanın log ayarları korunur.
if config.config_file_name is not None:
    fileConfig(config.config_file_name, disable_existing_loggers=False)

target_metadata = Base.metadata


def render_item(type_, obj, _autogen_context):
    # Migration dosyaları uygulama koduna bağımlı olmasın; UTCDateTime düz DateTime olarak yazılır.
    if type_ == "type" and isinstance(obj, UTCDateTime):
        return "sa.DateTime()"
    return False


def run_migrations_offline() -> None:
    context.configure(
        url=str(engine.url),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        render_as_batch=True,
        render_item=render_item,
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    with engine.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            # SQLite ALTER TABLE desteği sınırlı; batch modu tabloyu kopyalayarak değiştirir.
            render_as_batch=True,
            render_item=render_item,
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
