from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]


def test_frontend_container_serves_spa_and_proxies_api() -> None:
    dockerfile = (ROOT / "Dockerfile.frontend").read_text()
    nginx = (ROOT / "deploy" / "nginx.conf").read_text()

    assert "pnpm install --frozen-lockfile" in dockerfile
    assert "pnpm build" in dockerfile
    assert "listen 8080" in nginx
    assert "try_files $uri $uri/ /index.html" in nginx
    assert "proxy_pass http://api:10000" in nginx


def test_root_compose_exposes_only_frontend_and_orders_startup() -> None:
    compose = yaml.safe_load((ROOT / "docker-compose.yml").read_text())
    services = compose["services"]

    assert set(services) == {"database", "redis", "migrate", "api", "worker", "frontend"}
    assert services["frontend"]["ports"] == ["0.0.0.0:8080:8080"]
    assert all("ports" not in services[name] for name in ("api", "database", "redis"))
    assert services["api"]["depends_on"]["migrate"]["condition"] == (
        "service_completed_successfully"
    )
    assert services["worker"]["depends_on"]["migrate"]["condition"] == (
        "service_completed_successfully"
    )
    assert services["frontend"]["depends_on"]["api"]["condition"] == "service_healthy"
    assert set(compose["volumes"]) == {"bovista-postgres", "bovista-redis"}
