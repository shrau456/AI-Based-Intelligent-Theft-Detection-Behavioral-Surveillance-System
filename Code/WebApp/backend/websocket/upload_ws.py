from fastapi import WebSocket #type: ignore
import json

active_connections = {}


async def upload_websocket_endpoint(websocket: WebSocket):
    await websocket.accept()

    query_params = websocket.query_params
    user_id = query_params.get("user_id")

    active_connections[user_id] = websocket

    print(f"📹 Upload WebSocket Connected: {user_id}")

    try:
        while True:
            await websocket.receive_text()
    except:
        print("Upload websocket disconnected")
        del active_connections[user_id]


async def send_progress(user_id, message):

    websocket = active_connections.get(user_id)

    if websocket:
        await websocket.send_text(json.dumps(message))