from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]
REPOSITORY_ROOT = BACKEND_ROOT.parent


def test_container_and_render_contract() -> None:
    dockerfile = (BACKEND_ROOT / "Dockerfile").read_text(encoding="utf-8")
    dockerignore = (BACKEND_ROOT / ".dockerignore").read_text(encoding="utf-8")
    render = (REPOSITORY_ROOT / "render.yaml").read_text(encoding="utf-8")

    assert "USER bovista" in dockerfile
    assert 'CMD ["python", "-m", "scripts.start"]' in dockerfile
    assert ".env" in dockerignore
    assert ".venv/" in dockerignore
    assert "healthCheckPath: /health" in render
    assert (
        "preDeployCommand: alembic upgrade head && python -m scripts.configure_database_roles"
        in render
    )
    assert "dockerContext: ./backend" in render
    assert "type: worker" in render
    assert "dockerCommand: python -m scripts.start_worker" in render
    assert "MIGRATION_DATABASE_URL" in render
    assert "value: bovista_runtime" in render
    assert "value: bovista_worker" in render


def test_local_compose_includes_postgis_and_redis() -> None:
    compose = (BACKEND_ROOT / "docker-compose.yml").read_text(encoding="utf-8")

    assert "postgis/postgis:" in compose
    assert "redis:" in compose
    assert "healthcheck:" in compose
    assert "BOVISTA_TEST_DATABASE_URL" in compose


def test_environment_example_documents_render_runtime_inputs() -> None:
    environment = (BACKEND_ROOT / ".env.example").read_text(encoding="utf-8")

    for key in (
        "PORT",
        "DATABASE_URL",
        "REDIS_URL",
        "CORS_ORIGINS",
        "JWT_SIGNING_KEY",
        "OTP_DELIVERY_URL",
        "OTP_DELIVERY_TOKEN",
        "MFA_ENCRYPTION_KEY",
        "WORKER_USER_ID",
        "EVENT_DELIVERY_URL",
        "EVENT_DELIVERY_TOKEN",
    ):
        assert f"{key}=" in environment
