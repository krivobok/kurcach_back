from __future__ import annotations


def test_openapi_spec_contains_all_main_groups(client):
    response = client.get("/api/openapi.json")
    spec = response.get_json()

    assert response.status_code == 200
    assert spec["openapi"] == "3.0.3"
    assert "/api/auth/register" in spec["paths"]
    assert "/api/rooms" in spec["paths"]
    assert "/api/games/{game_id}/moves" in spec["paths"]
    assert "/api/games/{game_id}/analysis" in spec["paths"]
    assert "/api/stats/achievements" in spec["paths"]
    assert "/api/users/{user_id}/games" in spec["paths"]
    assert "/api/matchmaking" in spec["paths"]
    assert "/api/admin/users/{user_id}/status" in spec["paths"]
    assert "/api/admin/rooms/{room_id}" in spec["paths"]
    assert "bearerAuth" in spec["components"]["securitySchemes"]
    assert len(spec["x-websocket-events"]) >= 10


def test_swagger_page_and_postman_exports(client):
    swagger = client.get("/swagger")
    collection = client.get("/api/postman.json")
    environment = client.get("/api/postman-environment.json")

    assert swagger.status_code == 200
    assert "Документация запросов" in swagger.get_data(as_text=True)
    assert collection.status_code == 200
    assert collection.get_json()["info"]["name"] == "Крестики-нолики: серверные запросы"
    assert environment.status_code == 200
    assert environment.get_json()["values"][0]["key"] == "base_url"
    assert not any("export" in key and "using" in key for key in environment.get_json())
