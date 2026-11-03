import json
import yaml
from pathlib import Path


def test_ci_workflow_has_binary_checksum_verification_and_sast():
    """Verifies that .github/workflows/ci.yml includes checksum validation and Bandit SAST."""
    ci_path = Path(".github/workflows/ci.yml")
    assert ci_path.exists(), "CI workflow .github/workflows/ci.yml must exist"

    content = ci_path.read_text(encoding="utf-8")
    parsed = yaml.safe_load(content)

    # 1. Verify Gitleaks checksum validation
    assert "sha256sum" in content, "CI workflow must verify SHA256 checksum on downloaded binaries"

    # 2. Verify Bandit SAST step
    security_steps = parsed["jobs"]["security-audit"]["steps"]
    step_names = [s.get("name", "") for s in security_steps]
    assert any("bandit" in name.lower() or "sast" in name.lower() for name in step_names), (
        f"Bandit SAST step must be present in security-audit job, found: {step_names}"
    )


def test_ci_workflow_parameterizes_test_secrets():
    """Verifies that sensitive test keys in CI are parameterized with secrets fallback."""
    ci_path = Path(".github/workflows/ci.yml")
    content = ci_path.read_text(encoding="utf-8")

    assert "secrets.CI_JWT_SECRET_KEY" in content, "JWT_SECRET_KEY in CI must support secrets.CI_JWT_SECRET_KEY override"
    assert "secrets.CI_SECRET_VAULT_KEY" in content, "SECRET_VAULT_KEY in CI must support secrets.CI_SECRET_VAULT_KEY override"


def test_package_versions_reconciled():
    """Verifies that backend, API and frontend declare consistent version 2.0.0."""
    pyproject_path = Path("pyproject.toml")
    pyproject_content = pyproject_path.read_text(encoding="utf-8")
    assert 'version = "2.0.0"' in pyproject_content, "pyproject.toml version must be 2.0.0"

    web_pkg_path = Path("apps/web/package.json")
    web_pkg_data = json.loads(web_pkg_path.read_text(encoding="utf-8"))
    assert web_pkg_data["version"] == "2.0.0", "apps/web/package.json version must be 2.0.0"

    api_main_path = Path("apps/api/main.py")
    api_main_content = api_main_path.read_text(encoding="utf-8")
    assert 'version="2.0.0"' in api_main_content, "FastAPI app in apps/api/main.py version must be 2.0.0"


def test_documentation_metrics_and_security_policy():
    """Verifies that README.md and SECURITY.md reflect current hardened state and metrics."""
    readme_path = Path("README.md")
    readme = readme_path.read_text(encoding="utf-8")
    # Verified test count exceeds 370 tests
    assert "370" in readme or "378" in readme, "README.md must accurately document backend test count (>= 370 tests)"

    security_path = Path("SECURITY.md")
    security = security_path.read_text(encoding="utf-8")
    assert "2.0" in security, "SECURITY.md supported versions table must include 2.0.x"
