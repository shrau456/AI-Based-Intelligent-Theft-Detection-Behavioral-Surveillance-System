import cv2
import asyncio
from websocket.upload_ws import send_progress #type: ignore
from services.frame_processor import process_frame
import base64

def format_timestamp(seconds):
    mins = int(seconds // 60)
    secs = int(seconds % 60)

    return f"{mins:02}:{secs:02}"

async def process_video(video_path, user_id, source_type):

    cap = cv2.VideoCapture(video_path)

    fps = cap.get(cv2.CAP_PROP_FPS)
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    frame_count = 0

    await send_progress(user_id, {
        "status": "processing",
        "progress": 0
    })

    while cap.isOpened():

        ret, frame = cap.read()

        if not ret:
            break

        # calculating timestamp
        seconds = frame_count / fps
        video_timestamp = format_timestamp(seconds)
        frame_base64 = None

        if frame_count % 2 == 0:
           annotated, _ = process_frame(frame, user_id, source_type, video_timestamp)

           #convert frame to base64
           _, buffer = cv2.imencode(".jpg", annotated)
           frame_base64 = base64.b64encode(buffer).decode()

        frame_count += 1

        progress = int((frame_count / total_frames) * 100)

        await send_progress(user_id, {
            "status": "processing",
            "progress": progress,
            "frame": frame_base64
        })

    cap.release()

    await send_progress(user_id, {
        "status": "completed"
    })

    print("✅ Video Processing Completed")