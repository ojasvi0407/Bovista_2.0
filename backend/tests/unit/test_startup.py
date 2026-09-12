import pytest

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
