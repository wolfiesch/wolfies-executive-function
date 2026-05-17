"""
HTTP security controls for the planner API.

The app is local-first, but the public Vercel entrypoint exposes personal
planner mutation routes. In deployed runtimes, require an app API key before
allowing writes.
"""

from __future__ import annotations

import hmac
import os
from typing import Iterable

from fastapi import FastAPI, Request
from starlette.responses import JSONResponse


MUTATING_METHODS = {"POST", "PUT", "PATCH", "DELETE"}
LOCAL_ENV_NAMES = {"dev", "development", "local", "test", "testing"}
DEPLOYED_ENV_NAMES = {"production", "prod", "preview", "staging", "stage"}
API_KEY_ENV_VARS = (
    "LIFE_PLANNER_API_KEY",
    "APP_API_KEY",
    "API_KEY",
)


def _first_configured_env(names: Iterable[str]) -> str | None:
    for name in names:
        value = os.getenv(name)
        if value:
            return value
    return None


def _runtime_name() -> str:
    return (
        os.getenv("LIFE_PLANNER_ENV")
        or os.getenv("APP_ENV")
        or os.getenv("ENVIRONMENT")
        or os.getenv("FASTAPI_ENV")
        or os.getenv("VERCEL_ENV")
        or os.getenv("NODE_ENV")
        or os.getenv("PYTHON_ENV")
        or os.getenv("ENV")
        or ""
    ).strip().lower()


def is_local_or_test_runtime() -> bool:
    """Return True when it is reasonable to keep local dev writes usable."""
    runtime = _runtime_name()

    if runtime in DEPLOYED_ENV_NAMES:
        return False

    # Vercel and DATABASE_URL are deployment signals in this repo's API entrypoint.
    if os.getenv("VERCEL") or os.getenv("DATABASE_URL"):
        return False
    if runtime in LOCAL_ENV_NAMES:
        return True
    if os.getenv("PYTEST_CURRENT_TEST"):
        return True

    return False


def _configured_api_key() -> str | None:
    return _first_configured_env(API_KEY_ENV_VARS)


def _request_api_key(request: Request) -> str | None:
    api_key = request.headers.get("x-api-key")
    if api_key:
        return api_key

    auth_header = request.headers.get("authorization", "")
    parts = auth_header.split()
    if len(parts) == 2 and parts[0].lower() == "bearer":
        return parts[1]

    return None


def _is_authorized_mutation(request: Request, api_key: str | None) -> bool:
    request_key = _request_api_key(request)
    if not api_key or not request_key:
        return False

    return hmac.compare_digest(request_key, api_key)


def install_mutation_auth_middleware(app: FastAPI) -> None:
    """
    Require auth for mutation requests outside local/test runtimes.

    Read-only endpoints remain public so health checks and local inspection keep
    working. In deployed runtimes, missing auth configuration returns 503 so a
    production deployment fails closed instead of silently accepting writes.
    """

    @app.middleware("http")
    async def require_auth_for_deployed_mutations(request: Request, call_next):
        if request.method.upper() not in MUTATING_METHODS:
            return await call_next(request)

        if is_local_or_test_runtime():
            return await call_next(request)

        api_key = _configured_api_key()
        if not api_key:
            return JSONResponse(
                status_code=503,
                content={
                    "detail": (
                        "Mutation authentication is not configured. "
                        "Set LIFE_PLANNER_API_KEY."
                    )
                },
            )

        if not _is_authorized_mutation(request, api_key):
            return JSONResponse(
                status_code=401,
                content={"detail": "Valid API key is required."},
                headers={"WWW-Authenticate": "Bearer"},
            )

        return await call_next(request)
