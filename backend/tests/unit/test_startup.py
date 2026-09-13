import pytest

from scripts.database_url import ensure_database_url
from scripts.start import server_config


def test_server_config_uses_render_port() -> None:
    assert server_config({"PORT": "12000"}) == {
        "app": "app.main:app",
        "host": "0.0.0.0",  # noqa: S104 - required for Render port detection
        "port": 12000,
    }


def test_server_config_rejects_invalid_port() -> None:
    with pytest.raises(ValueError, match="PORT"):
        server_config({"PORT": "not-a-port"})


def test_component_database_url_is_encoded_for_runtime_role() -> None:
    environment = {
        "DATABASE_HOST": "private-db",
        "DATABASE_PORT": "5432",
        "DATABASE_NAME": "bovista",
        "DATABASE_USER": "bovista_runtime",
        "DATABASE_PASSWORD": "space and/slash",
    }
    assert ensure_database_url(environment) == (
        "postgresql+asyncpg://bovista_runtime:space%20and%2Fslash" "@private-db:5432/bovista"
    )
