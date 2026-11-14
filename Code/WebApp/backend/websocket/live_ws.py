from fastapi import WebSocket # type: ignore
import base64
import cv2
import numpy as np

from services.frame_processor import process_frame
from services.frame_processor import person_memory

async def live_websocket_endpoint(websocket: WebSocket): #type: ignore
    await websocket.accept()
    print("Live WebSocket Connected")

    try:
        while True:
            data = await websocket.receive_text()
            # extracting user_id from query params
            query_params = websocket.query_params
            user_id = query_params.get("user_id", "unknown")
            source_type = query_params.get("source_type")

            # Decode base64 image
            image_bytes = base64.b64decode(data.split(",")[1])
            np_arr = np.frombuffer(image_bytes, np.uint8)
            frame = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)

            # Process frame
            annotated_frame, events = process_frame(frame, user_id, source_type)

            # Encode processed frame
            _, buffer = cv2.imencode(".jpg", annotated_frame)
            encoded_frame = base64.b64encode(buffer).decode("utf-8")

            response = {
                "frame": f"data:image/jpeg;base64,{encoded_frame}",
                "events": events
            }

            await websocket.send_json(response)

    except Exception as e:
        print("WebSocket Error:", e)
    finally:
        person_memory.clear()
        await websocket.close()
        print("🔌 WebSocket Disconnected")