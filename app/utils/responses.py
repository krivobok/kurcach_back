from __future__ import annotations

from typing import Any

from flask import jsonify


def ok(data: Any = None, message: str | None = None, status: int = 200):
    payload: dict[str, Any] = {"ok": True}
    if data is not None:
        payload["data"] = data
    if message:
        payload["message"] = message
    return jsonify(payload), status


def error(message: str, status: int = 400, code: str = "bad_request", details: Any = None):
    payload: dict[str, Any] = {"ok": False, "error": {"code": code, "message": message}}
    if details is not None:
        payload["error"]["details"] = details
    return jsonify(payload), status
