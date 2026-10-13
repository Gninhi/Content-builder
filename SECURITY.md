# Security Policy

## Supported Versions

Security updates and critical vulnerability patches are applied to the following versions of ContentOps Harness:

| Version | Supported          |
| ------- | ------------------ |
| 1.0.x   | :white_check_mark: |
| < 1.0   | :x:                |

## Reporting a Vulnerability

We take the security of ContentOps Harness seriously. If you discover a security vulnerability, please do NOT create a public GitHub issue.

Instead, please report vulnerabilities privately:

1. **GitHub Private Vulnerability Reporting (Preferred)**:
   Navigate to the repository's **Security** tab and click **Report a vulnerability** to submit an advisory draft.

2. **Email Security Contact**:
   Send an encrypted or confidential report to `security@contentops.local` with the following details:
   - Type of issue (e.g., SSRF, Prompt Injection, Insecure Deserialization, Secret Exposure, Auth bypass)
   - Step-by-step reproduction instructions or Proof of Concept (PoC)
   - Impact assessment on tenant isolation and data confidentiality

## Response Timeline

- **Initial Acknowledgment**: Within 48 hours.
- **Triage & Assessment**: Within 5 business days.
- **Remediation & Patch**: Target within 14 calendar days for critical/high vulnerabilities.
- **Responsible Disclosure**: Public disclosure occurs only after an advisory and mitigation patch have been released.

## Security Practices

ContentOps Harness enforces defense-in-depth principles:
- Zero secrets committed to the repository (enforced via Gitleaks pre-commit hooks and CI detection).
- Fail-closed OAuth token vault using authenticated AES-GCM-256 with key-id rotation.
- Tenant isolation enforced on all database queries and LangGraph state checkpoints.
- SSRF prevention on all outbound HTTP collectors and model endpoint resolvers.
- Mandatory Human-in-the-Loop (HITL) gate before any social publishing action.
