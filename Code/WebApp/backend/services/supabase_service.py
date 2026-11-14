
import os
import uuid
import cv2
import tempfile
from datetime import datetime
from supabase import create_client # type: ignore

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

def upload_detection(frame, user_id, person_id, score):
    try:
        timestamp = int(datetime.utcnow().timestamp())
        filename = f"{user_id}/{timestamp}_{uuid.uuid4().hex}.jpg"

        # Save temp image
        temp_path = tempfile.mktemp(suffix=".jpg")
        cv2.imwrite(temp_path, frame)

        # Upload to Supabase storage
        with open(temp_path, "rb") as f:
            supabase.storage.from_("snapshots").upload(
                filename,
                f,
                {"content-type": "image/jpeg"}
            )

        # Store in DB
        supabase.table("detections").insert({
            "user_id": user_id,
            "snapshot_url": filename,
            "label": "suspicious_behavior",
            "confidence_score": float(score),
            "source_type": "live_feed",
            "timestamp": datetime.utcnow().isoformat()
        }).execute()

        print("Detection saved to Supabase")

    except Exception as e:
        print("Supabase Error:", e)