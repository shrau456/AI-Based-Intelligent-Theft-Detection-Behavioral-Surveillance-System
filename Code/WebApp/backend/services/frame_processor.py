import cv2
import time
import pandas as pd
import numpy as np
import xgboost as xgb  # type: ignore

from core.model_loader import ModelLoader
#from services.supabase_service import upload_detection
from services.detection_service import save_detection

# ------------------ CONFIG ------------------
BAG_CLASSES = [24, 26]
HAND_KP = [9, 10]
WAIST_KP = 11

# Persistent tracking memory
person_memory = {}


# this line is moved from function below to here. because in function, we will be loading model for every frame, this will make our processing slow, so now we are just loading all models once.

def process_frame(frame, user_id, source_type, video_timestamp=None):
    pose_model, object_model, trolley_model, xgb_model = ModelLoader.get_models() 

    annotated = frame.copy()
    suspicious_events = []

    # ------------------ POSE TRACK ------------------
    pose_results = pose_model.track(
        frame,
        persist=True,
        tracker="bytetrack.yaml",
        verbose=False
    )

    if pose_results[0].boxes.id is None:
        return annotated, suspicious_events

    boxes = pose_results[0].boxes.xyxy
    ids = pose_results[0].boxes.id.tolist()
    confs = pose_results[0].boxes.conf.tolist()
    keypoints_all = pose_results[0].keypoints.xyn.tolist()

    # ------------------ OBJECT DETECTION ------------------
    obj_results = object_model(frame, verbose=False)

    object_boxes = []
    h, w, _ = frame.shape

    for r in obj_results:
        for box, cls in zip(r.boxes.xyxy, r.boxes.cls):
            x1, y1, x2, y2 = box.tolist()
            bw, bh = (x2 - x1) / w, (y2 - y1) / h

            if 0.02 < bw < 0.25 and 0.02 < bh < 0.25:
                object_boxes.append([x1/w, y1/h, x2/w, y2/h])

    # ----- this part was added on 8/3/26. no checking done for this part of the code was done so can be removed if required.----
    current_ids = set(ids)
    for stored_id in list(person_memory.keys()):
        if stored_id not in current_ids:
            del person_memory[stored_id]
    # this part handles when people leaves the frame.

    # ------------------ PERSON LOOP ------------------
    for i, box in enumerate(boxes):

        if confs[i] < 0.55:
            continue

        pid = int(ids[i])
        keypoints = keypoints_all[i]
        x1, y1, x2, y2 = map(int, box.tolist())

        if pid not in person_memory:
            person_memory[pid] = {
                "pickup": False,
                "concealed": False,
                "disappeared": False,
                "conceal_frames": 0,
                "has_stolen": False,
                "theft_completed": False,
                "high_score_frames": 0
            }

        mem = person_memory[pid]

        # ------------------ POSE SCORE ------------------
        data = {}
        for j in range(len(keypoints)):
            data[f"x{j}"] = keypoints[j][0]
            data[f"y{j}"] = keypoints[j][1]

        df = pd.DataFrame([data])
        f_pose = 1 - xgb_model.predict(xgb.DMatrix(df))[0]

        # ------------------ PICKUP (Persistent) ------------------
        object_near_hand = False

        for o in object_boxes:
            cx = (o[0] + o[2]) / 2
            cy = (o[1] + o[3]) / 2

            hx = (keypoints[9][0] + keypoints[10][0]) / 2
            hy = (keypoints[9][1] + keypoints[10][1]) / 2

            if abs(cx - hx) < 0.15 and abs(cy - hy) < 0.20:
                object_near_hand = True
                mem["pickup"] = True
                break

        f_pickup = 1 if mem["pickup"] else 0

        # ------------------ CONCEALMENT (Persistent) ------------------
        curr_hand_y = min(keypoints[9][1], keypoints[10][1])
        waist_y = keypoints[WAIST_KP][1]

        if abs(curr_hand_y - waist_y) < 0.05:
            mem["conceal_frames"] += 1

        if mem["conceal_frames"] > 5:
            mem["concealed"] = True

        f_concealment = 1 if mem["concealed"] else 0

        # ------------------ DISAPPEAR (Persistent) ------------------
        if mem["pickup"] and not object_near_hand:
            mem["disappeared"] = True

        f_disappearance = 1 if mem["disappeared"] else 0

        # ------------------ SUSPICION SCORE ------------------
        score = (
            0.25 * f_pickup +
            0.25 * f_concealment +
            0.35 * f_disappearance +
            0.15 * f_pose
        )

        # ------------------ TEMPORAL STABILITY ------------------
        print("-------------------------------------")
        print("person_id = ", pid)
        print("score =", score)
        print("pickup =", f_pickup)
        print("concealment =", f_concealment)
        print("disappearance =", f_disappearance)
        print("pose =", f_pose)

        if score >= 0.75:
            mem["high_score_frames"] += 1
        else:
            mem["high_score_frames"] = 0

        # ------------------ THEFT TRIGGER ------------------
        if mem["high_score_frames"] >= 6 and not mem["theft_completed"]:
            mem["has_stolen"] = True
            mem["theft_completed"] = True

            cv2.rectangle(annotated, (x1, y1), (x2, y2), (0, 0, 255), 3)
            cv2.putText(
                annotated,
                f"Suspicious | Score: {score:.2f}",
                (x1, y1 - 10),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.6,
                (0, 0, 255),
                2
            )

            # Save detection using Edge Function
            save_detection(
                user_id=user_id,
                label="suspicious_behavior",
                confidence_score=float(score),
                source_type=source_type,
                frame=annotated,
                video_timestamp=video_timestamp
            )

            suspicious_events.append({
                "person_id": pid,
                "score": float(score),
                "timestamp": time.time()
            })

        # ------------------ DRAW ------------------
        label = "Suspicious" if mem["has_stolen"] else "Normal"
        color = (0, 0, 255) if mem["has_stolen"] else (0, 255, 0)

        cv2.rectangle(annotated, (x1, y1), (x2, y2), color, 3)

        score_text = f"Score: {score:.2f}"
        cv2.putText(
            annotated,
            score_text,
            (x1, y1 - 10),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.6,
            color,
            2
        )

    return annotated, suspicious_events


