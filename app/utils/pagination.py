from __future__ import annotations

from flask import request


def get_pagination(default_limit: int = 20, max_limit: int = 100) -> tuple[int, int]:
    try:
        limit = int(request.args.get("limit", default_limit))
        offset = int(request.args.get("offset", 0))
    except ValueError:
        return default_limit, 0
    limit = max(1, min(limit, max_limit))
    offset = max(0, offset)
    return limit, offset
