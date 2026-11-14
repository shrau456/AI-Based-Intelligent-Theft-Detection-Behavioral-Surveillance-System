import os
import requests
import base64
import cv2

SUPABASE_URL = os.getenv("SUPABASE_URL")

def save_detection(
    user_id: str,
    label: str,
    confidence_score: float,
    source_type: str,
    frame,
    video_timestamp: None
):

    try:
        _, buffer = cv2.imencode('.jpg', frame)

        response = requests.post(
            f"{SUPABASE_URL}/functions/v1/save-detection",
            json={
                "user_id": user_id,
                "label": label,
                "confidence_score": confidence_score,
                "source_type": source_type,
                "snapshot_base64": base64.b64encode(buffer).decode(),
                "video_timestamp": video_timestamp
            }
        )

        print("✅ Detection sent to Edge Function")
        return response.json()

    except Exception as e:
        print("❌ Edge Function Error:", e)