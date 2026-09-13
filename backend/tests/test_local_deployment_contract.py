import base64
import os
import shutil
import subprocess
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
INITIALIZER = ROOT / "scripts" / "initialize-local-docker.ps1"
POWERSHELL = (
    Path(os.environ["SystemRoot"]) / "System32" / "WindowsPowerShell" / "v1.0" / "powershell.exe"
)


def _copied_initializer(tmp_path: Path) -> Path:
    assert INITIALIZER.exists(), "The local Docker initializer must exist."
    scripts = tmp_path / "scripts"
    scripts.mkdir()
    destination = scripts / INITIALIZER.name
    shutil.copy2(INITIALIZER, destination)
    return destination


def _run_initializer(script: Path, *arguments: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(  # noqa: S603 - fixed executable and test-controlled arguments
        [
            str(POWERSHELL),
            "-NoProfile",
            "-ExecutionPolicy",
            "Bypass",
            "-File",
            str(script),
            *arguments,
        ],
        cwd=script.parent.parent,
        capture_output=True,
        text=True,
        check=False,
    )


def _environment_values(path: Path) -> dict[str, str]:
    return dict(
        line.split("=", 1)
        for line in path.read_text(encoding="utf-8-sig").splitlines()
        if line and not line.startswith("#")
    )


def test_frontend_container_serves_spa_and_proxies_api() -> None:
    dockerfile = (ROOT / "Dockerfile.frontend").read_text()
    nginx = (ROOT / "deploy" / "nginx.conf").read_text()

    assert "pnpm install --frozen-lockfile" in dockerfile
    assert "pnpm build" in dockerfile
    assert "listen 8080" in nginx
    assert "try_files $uri $uri/ /index.html" in nginx
    assert "resolver 127.0.0.11" in nginx
    assert "set $api_upstream http://api:10000" in nginx
    assert "proxy_pass $api_upstream" in nginx


def test_root_compose_exposes_only_frontend_and_orders_startup() -> None:
    compose = yaml.safe_load((ROOT / "docker-compose.yml").read_text())
    services = compose["services"]

    assert set(services) == {"database", "redis", "migrate", "api", "worker", "frontend"}
    assert services["frontend"]["ports"] == ["0.0.0.0:8080:8080"]
    assert all("ports" not in services[name] for name in ("api", "database", "redis"))
    assert "-h 127.0.0.1" in " ".join(services["database"]["healthcheck"]["test"])
    assert services["api"]["depends_on"]["migrate"]["condition"] == (
        "service_completed_successfully"
    )
    assert services["worker"]["depends_on"]["migrate"]["condition"] == (
        "service_completed_successfully"
    )
    worker_healthcheck = " ".join(services["worker"]["healthcheck"]["test"])
    assert "scripts.start_worker" in worker_healthcheck
    assert "/health" not in worker_healthcheck
    migration_command = " ".join(services["migrate"]["command"])
    assert "python -m scripts.provision_local_worker" in migration_command
    assert services["migrate"]["environment"]["WORKER_USER_ID"] == (
        services["worker"]["environment"]["WORKER_USER_ID"]
    )
    assert services["frontend"]["depends_on"]["api"]["condition"] == "service_healthy"
    assert set(compose["volumes"]) == {"bovista-postgres", "bovista-redis"}


def test_initializer_generates_distinct_secrets_and_fernet_key(tmp_path: Path) -> None:
    script = _copied_initializer(tmp_path)

    result = _run_initializer(script)

    assert result.returncode == 0, result.stderr
    values = _environment_values(tmp_path / ".env.local-docker")
    secret_names = {
        "POSTGRES_PASSWORD",
        "DATABASE_PASSWORD",
        "WORKER_DATABASE_PASSWORD",
        "AUDIT_HMAC_KEY",
        "JWT_SIGNING_KEY",
        "REFRESH_TOKEN_PEPPER",
        "OTP_HMAC_KEY",
        "MFA_ENCRYPTION_KEY",
        "EVENT_DELIVERY_TOKEN",
    }
    assert secret_names <= values.keys()
    assert len({values[name] for name in secret_names}) == len(secret_names)
    assert all(len(values[name]) >= 43 for name in secret_names)
    assert len(base64.urlsafe_b64decode(values["MFA_ENCRYPTION_KEY"])) == 32


def test_initializer_refuses_to_overwrite_existing_environment(tmp_path: Path) -> None:
    script = _copied_initializer(tmp_path)
    target = tmp_path / ".env.local-docker"
    target.write_text("existing-content", encoding="utf-8")

    result = _run_initializer(script)

    assert result.returncode != 0
    assert target.read_text(encoding="utf-8") == "existing-content"


def test_initializer_force_replaces_existing_environment(tmp_path: Path) -> None:
    script = _copied_initializer(tmp_path)
    target = tmp_path / ".env.local-docker"
    target.write_text("existing-content", encoding="utf-8")

    result = _run_initializer(script, "-Force")

    assert result.returncode == 0, result.stderr
    assert target.read_text(encoding="utf-8-sig") != "existing-content"


def test_local_secrets_and_runbook_are_documented() -> None:
    ignored = (ROOT / ".gitignore").read_text()
    readme = (ROOT / "backend" / "README.md").read_text()

    assert ".env.local-docker" in ignored.splitlines()
    assert "docker compose --env-file .env.local-docker up --build -d" in readme
    assert "docker compose --env-file .env.local-docker logs api" in readme
    assert "New-NetFirewallRule" in readme
    assert "pg_dump" in readme


def test_database_invariant_verifier_includes_release_history_triggers() -> None:
    verifier = (ROOT / "backend" / "scripts" / "verify_db_invariants.py").read_text()

    assert "laboratory_result_history" in verifier
    assert "laboratory_transition_history" in verifier
    assert "case_transition_history" in verifier
