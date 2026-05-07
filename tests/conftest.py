from __future__ import annotations

import pytest

from app import create_app
from config import TestingConfig


class LocalTestingConfig(TestingConfig):
    DATABASE_PATH = ""


@pytest.fixture()
def app(tmp_path):
    class RuntimeConfig(LocalTestingConfig):
        DATABASE_PATH = str(tmp_path / "test.sqlite3")

    app = create_app(RuntimeConfig)
    yield app


@pytest.fixture()
def client(app):
    return app.test_client()


def register(client, username: str, password: str = "secret123") -> dict:
    response = client.post(
        "/api/auth/register",
        json={"username": username, "password": password, "display_name": username.title()},
    )
    assert response.status_code == 201, response.get_data(as_text=True)
    return response.get_json()["data"]


def auth_headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}
