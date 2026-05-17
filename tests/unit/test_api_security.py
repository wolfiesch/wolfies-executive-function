import importlib
import sys
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.testclient import TestClient

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.security import install_mutation_auth_middleware


AUTH_ENV_VARS = [
    "LIFE_PLANNER_ENV",
    "APP_ENV",
    "ENVIRONMENT",
    "FASTAPI_ENV",
    "VERCEL_ENV",
    "NODE_ENV",
    "PYTHON_ENV",
    "ENV",
    "VERCEL",
    "DATABASE_URL",
    "LIFE_PLANNER_API_KEY",
    "APP_API_KEY",
    "API_KEY",
]


def _clear_auth_env(monkeypatch):
    for name in AUTH_ENV_VARS:
        monkeypatch.delenv(name, raising=False)


def _test_app() -> FastAPI:
    app = FastAPI()
    install_mutation_auth_middleware(app)

    @app.get("/tasks/")
    async def list_tasks():
        return {"tasks": []}

    @app.post("/tasks/")
    async def create_task():
        return {"created": True}

    return app


def _test_app_with_cors() -> FastAPI:
    app = _test_app()
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["https://frontend.example"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    return app


def test_local_dev_allows_mutations_without_api_key(monkeypatch):
    _clear_auth_env(monkeypatch)
    monkeypatch.setenv("APP_ENV", "development")

    response = TestClient(_test_app()).post("/tasks/")

    assert response.status_code == 200
    assert response.json() == {"created": True}


def test_deployed_runtime_keeps_read_only_routes_public(monkeypatch):
    _clear_auth_env(monkeypatch)
    monkeypatch.setenv("VERCEL_ENV", "production")

    response = TestClient(_test_app()).get("/tasks/")

    assert response.status_code == 200
    assert response.json() == {"tasks": []}


def test_deployed_runtime_fails_closed_without_auth_config(monkeypatch):
    _clear_auth_env(monkeypatch)
    monkeypatch.setenv("VERCEL_ENV", "production")

    response = TestClient(_test_app()).post("/tasks/")

    assert response.status_code == 503
    assert "Mutation authentication is not configured" in response.json()["detail"]


def test_deployed_auth_errors_keep_cors_headers(monkeypatch):
    _clear_auth_env(monkeypatch)
    monkeypatch.setenv("VERCEL_ENV", "production")

    response = TestClient(_test_app_with_cors()).post(
        "/tasks/",
        headers={"origin": "https://frontend.example"},
    )

    assert response.status_code == 503
    assert response.headers["access-control-allow-origin"] == "https://frontend.example"


def test_deployed_runtime_rejects_missing_or_wrong_api_key(monkeypatch):
    _clear_auth_env(monkeypatch)
    monkeypatch.setenv("VERCEL_ENV", "production")
    monkeypatch.setenv("LIFE_PLANNER_API_KEY", "correct-key")

    client = TestClient(_test_app())

    missing = client.post("/tasks/")
    wrong = client.post("/tasks/", headers={"x-api-key": "wrong-key"})

    assert missing.status_code == 401
    assert wrong.status_code == 401


def test_deployed_runtime_accepts_x_api_key(monkeypatch):
    _clear_auth_env(monkeypatch)
    monkeypatch.setenv("VERCEL_ENV", "production")
    monkeypatch.setenv("LIFE_PLANNER_API_KEY", "correct-key")

    response = TestClient(_test_app()).post(
        "/tasks/",
        headers={"x-api-key": "correct-key"},
    )

    assert response.status_code == 200
    assert response.json() == {"created": True}


def test_deployed_runtime_accepts_bearer_api_key(monkeypatch):
    _clear_auth_env(monkeypatch)
    monkeypatch.setenv("VERCEL_ENV", "production")
    monkeypatch.setenv("LIFE_PLANNER_API_KEY", "correct-key")

    response = TestClient(_test_app()).post(
        "/tasks/",
        headers={"authorization": "Bearer correct-key"},
    )

    assert response.status_code == 200
    assert response.json() == {"created": True}


def test_deployed_runtime_accepts_bearer_api_key_with_extra_spacing(monkeypatch):
    _clear_auth_env(monkeypatch)
    monkeypatch.setenv("VERCEL_ENV", "production")
    monkeypatch.setenv("LIFE_PLANNER_API_KEY", "correct-key")

    response = TestClient(_test_app()).post(
        "/tasks/",
        headers={"authorization": "Bearer   correct-key"},
    )

    assert response.status_code == 200
    assert response.json() == {"created": True}


def test_unknown_runtime_fails_closed_without_explicit_local_signal(monkeypatch):
    _clear_auth_env(monkeypatch)
    monkeypatch.delenv("PYTEST_CURRENT_TEST", raising=False)

    response = TestClient(_test_app()).post("/tasks/")

    assert response.status_code == 503
    assert "Mutation authentication is not configured" in response.json()["detail"]


def test_vercel_api_entrypoint_blocks_task_mutation_before_router(monkeypatch):
    _clear_auth_env(monkeypatch)
    monkeypatch.setenv("VERCEL_ENV", "production")

    api_index = importlib.import_module("api.index")
    response = TestClient(api_index.app).post("/tasks/", json={"title": "blocked"})

    assert response.status_code == 503
    assert "Mutation authentication is not configured" in response.json()["detail"]
