"""
Centralized environment resolution for ContentOps Harness.
Enforces fail-closed configuration: canonical variable is APP_ENV.
Legacy alias variables (ENVIRONMENT, ENV) are accepted with deprecation warnings.
If unspecified, defaults to 'production' (fail-closed).
"""

import os
import warnings
from typing import Literal

AppEnvType = Literal["production", "prod", "staging", "development", "dev", "local", "test", "testing"]


def get_app_env() -> str:
    """
    Returns the canonical application environment name:
    'production', 'staging', 'development', 'test', etc.
    Priority: APP_ENV > ENVIRONMENT > ENV.
    Default: 'production' (fail-closed).
    """
    app_env = os.getenv("APP_ENV")
    if app_env is not None and app_env.strip():
        return app_env.strip().lower()

    environment = os.getenv("ENVIRONMENT")
    if environment is not None and environment.strip():
        warnings.warn(
            "ENVIRONMENT is deprecated and will be removed in a future release. Use APP_ENV instead.",
            DeprecationWarning,
            stacklevel=2,
        )
        return environment.strip().lower()

    env = os.getenv("ENV")
    if env is not None and env.strip():
        warnings.warn(
            "ENV is deprecated and will be removed in a future release. Use APP_ENV instead.",
            DeprecationWarning,
            stacklevel=2,
        )
        return env.strip().lower()

    return "production"


def is_production() -> bool:
    """Returns True if the application environment is production."""
    return get_app_env() in ("production", "prod")


def is_dev_or_test() -> bool:
    """Returns True if the application environment is dev, local or test."""
    return get_app_env() in ("dev", "development", "local", "test", "testing")


def is_test() -> bool:
    """Returns True if the application environment is test or testing."""
    return get_app_env() in ("test", "testing")
