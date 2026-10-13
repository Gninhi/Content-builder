# Contributing to ContentOps Harness

Thank you for contributing to ContentOps Harness. As a governed agentic editorial operating system handling multi-tenant workflows and social publishing, all contributions must uphold strict security, quality, and architecture standards.

## Code of Conduct

All contributors are expected to maintain a professional, respectful, and collaborative environment.

## Security First Guidelines

1. **Never Commit Secrets**:
   - Never commit API keys (`NVIDIA_API_KEY`, `GOOGLE_API_KEY`, `TAVILY_API_KEY`), tokens, private certificates, or `.env` files.
   - All tests must use synthetic mock credentials or test doubles.
   - Run `pre-commit run --all-files` before pushing any branch.

2. **Data Isolation & Multi-Tenancy**:
   - Every database query, repository call, and LangGraph workflow state MUST explicitly enforce `workspace_id` tenant scoping.

3. **Safe Outbound Calls**:
   - All external HTTP calls must route through validated connectors with SSRF protection (`validate_target_url_security`).

## Development Workflow

1. **Clone & Set Up Environment**:
   ```bash
   git clone https://github.com/Gninhi/Content-builder.git
   cd Content-builder
   python -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   pre-commit install
   ```

2. **Frontend Setup**:
   ```bash
   cd apps/web
   npm ci
   npm run build
   ```

3. **Running Quality Checks Locally**:
   ```bash
   # Backend linting & tests
   ruff check .
   mypy .
   pytest tests/unit tests/security tests/integration
   
   # Frontend tests
   cd apps/web && npm run test
   ```

## Pull Request Process

- Open PRs against `main`.
- Ensure all CI workflow checks pass (Lint, Tests, Coverage >= 85%, Security Audit, Frontend Build).
- Every PR must address an issue or feature specification with unit/integration tests included.
