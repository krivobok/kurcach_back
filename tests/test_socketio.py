from __future__ import annotations

from app.extensions import socketio
from conftest import register


def test_socket_connect_user_join_and_room_subscribe(app, client):
    session = register(client, "socket_user")
    socket_client = socketio.test_client(app, flask_test_client=client)

    assert socket_client.is_connected()
    assert any(item["name"] == "connected" for item in socket_client.get_received())

    socket_client.emit("user.join", {"token": session["token"]})
    received = socket_client.get_received()
    assert any(item["name"] == "user.joined" for item in received)

    room_response = client.post(
        "/api/rooms",
        headers={"Authorization": f"Bearer {session['token']}"},
        json={"name": "Socket AI room", "mode": "ai"},
    )
    room_id = room_response.get_json()["data"]["id"]

    socket_client.emit("room.subscribe", {"room_id": room_id})
    received = socket_client.get_received()
    assert any(item["name"] == "room.snapshot" for item in received)

    socket_client.disconnect()
