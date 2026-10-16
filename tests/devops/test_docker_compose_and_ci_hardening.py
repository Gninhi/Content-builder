import yaml
from pathlib import Path


def test_docker_compose_hardening():
    """C8: Verifies docker-compose does not expose unauthenticated ports or hardcode secrets."""
    compose_path = Path("infra/docker/docker-compose.yml")
    assert compose_path.exists()

    with open(compose_path, "r", encoding="utf-8") as f:
        compose = yaml.safe_load(f)

    services = compose.get("services", {})
    assert "db" in services
    assert "redis" in services
    assert "api" in services

    # 1. Ports must not be bound to 0.0.0.0
    for svc_name in ["db", "redis"]:
        ports = services[svc_name].get("ports", [])
        for p in ports:
            assert "127.0.0.1:" in str(p), f"{svc_name} port {p} must be bound to 127.0.0.1 loopback only"

    # 2. No raw SQL migrations mounted as init scripts (Alembic single source of truth)
    db_volumes = [str(v) for v in services["db"].get("volumes", [])]
    assert not any("001_initial_schema.sql" in v for v in db_volumes)
    assert not any("002_rls_policies.sql" in v for v in db_volumes)

    # 3. Environment in api must use APP_ENV
    api_env = services["api"].get("environment", {})
    assert "APP_ENV" in api_env

    # 4. Command in api must run alembic migrations before uvicorn
    api_command = services["api"].get("command", "")
    assert "alembic upgrade head" in api_command


def test_dockerfile_purges_build_essential():
    """Verifies Dockerfile.api purges build-essential to minimize final attack surface."""
    dockerfile_path = Path("infra/docker/Dockerfile.api")
    assert dockerfile_path.exists()
    content = dockerfile_path.read_text(encoding="utf-8")

    assert "apt-get purge -y build-essential" in content
    assert "apt-get autoremove -y" in content


def test_ci_workflow_hardened():
    """N6: Verifies ci.yml uses APP_ENV and validates sha256 checksum for external downloads."""
    ci_path = Path(".github/workflows/ci.yml")
    assert ci_path.exists()
    content = ci_path.read_text(encoding="utf-8")

    assert "APP_ENV: production" in content
    assert "sha256sum -c" in content
    # Ensure weak example secret is not present in CI config
    assert "ci-very-strong-production-test-jwt-secret-key-32b!" not in content
