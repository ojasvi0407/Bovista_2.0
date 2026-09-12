from configparser import ConfigParser

from app.db.alembic_config import escape_configparser_value


def test_database_url_is_safe_for_alembic_configparser() -> None:
    database_url = "postgresql+asyncpg://user:password%21@localhost/database"
    parser = ConfigParser()
    parser.add_section("alembic")

    parser.set("alembic", "sqlalchemy.url", escape_configparser_value(database_url))

    assert parser.get("alembic", "sqlalchemy.url") == database_url
