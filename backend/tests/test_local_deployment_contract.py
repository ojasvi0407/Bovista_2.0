from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def test_frontend_container_serves_spa_and_proxies_api() -> None:
    dockerfile = (ROOT / "Dockerfile.frontend").read_text()
    nginx = (ROOT / "deploy" / "nginx.conf").read_text()

    assert "pnpm install --frozen-lockfile" in dockerfile
    assert "pnpm build" in dockerfile
    assert "listen 8080" in nginx
    assert "try_files $uri $uri/ /index.html" in nginx
    assert "proxy_pass http://api:10000" in nginx
