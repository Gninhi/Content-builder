import os
from pathlib import Path
from dotenv import load_dotenv

# Load local environment without reading or logging values
load_dotenv(".env")

ENV_EXAMPLE_PATH = Path(".env.example")

REQUIRED_VARS = [
    # Core Application
    "ENV",
    "LOG_LEVEL",
    "LOG_FORMAT",
    "DATABASE_URL",
    "CHECKPOINTER_TYPE",
    # Security & Auth
    "JWT_SECRET_KEY",
    "JWT_ALGORITHM",
    "JWT_ISSUER",
    "JWT_AUDIENCE",
    "SECRET_VAULT_KEY",
    "CORS_ALLOWED_ORIGINS",
    # LLM & Observability
    "GOOGLE_API_KEY",
    "GEMINI_MODEL",
    "LANGFUSE_PUBLIC_KEY",
    "LANGFUSE_SECRET_KEY",
    "LANGFUSE_HOST",
    "TAVILY_API_KEY",
    # Platform / Governance
    "SOCIAL_SANDBOX_MODE",
    "LIVE_PUBLISHING_ENABLED",
    "LIVE_TESTS",
    "KILL_SWITCH_GLOBAL",
    "MAX_PUBLICATIONS_PER_HOUR",
    "REDIS_URL",
    "AI_TRANSPARENCY_MODE",
    # LinkedIn Connectors
    "LINKEDIN_CLIENT_ID",
    "LINKEDIN_CLIENT_SECRET",
    "LINKEDIN_ACCESS_TOKEN",
    "LINKEDIN_REDIRECT_URI",
    "LINKEDIN_API_VERSION",
    # X Connectors
    "X_API_KEY",
    "X_API_SECRET",
    "X_ACCESS_TOKEN",
    "X_CLIENT_ID",
    "X_CLIENT_SECRET",
    "X_REDIRECT_URI",
    "X_MONTHLY_PUBLICATION_LIMIT"
]


def run_diagnostics():
    print("=== DIAGNOSTIC DE CONFIGURATION DE L'ENVIRONNEMENT ===")
    print("Format : STRICTEMENT 'défini / non défini' (aucune valeur ni longueur exposée)\n")

    status_report = {}
    for var_name in REQUIRED_VARS:
        val = os.getenv(var_name)
        # Check presence and whether it is a placeholder or set
        if val is not None and val != "" and not val.startswith("your_") and not val.startswith("change-me"):
            status_report[var_name] = "défini"
        elif val is not None and val != "":
            status_report[var_name] = "défini (placeholder/dev)"
        else:
            status_report[var_name] = "non défini"

    # Print clean table
    for k, s in status_report.items():
        print(f"  {k:<32} : {s}")

    print("\nDiagnostic terminé sans fuite de secrets.")


if __name__ == "__main__":
    run_diagnostics()
