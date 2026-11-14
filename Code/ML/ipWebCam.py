import cv2
import pandas as pd
from ultralytics import YOLO
import xgboost as xgb
import cvzone
import time
import os

# for performace
cv2.setNumThreads(4)

# Input
video_path = "http://10.172.145.215:8080/video"  # mobile IP camera
#video_path = "./test_videos/room3.mp4"

# loading models
pose_model = YOLO("./yolo_models/yolo11n-pose.pt")
object_model = YOLO("./yolo_models/yolo11n.pt")
trolley_model = YOLO("./yolo_models/best.pt")

xgb_model = xgb.Booster()
xgb_model.load_model("trained_model.json")

# Some configuration
BAG_CLASSES = [24, 26]
TROLLEY_CLASS = 2

HAND_KP = [9, 10]
WAIST_KP = 11

os.makedirs("./output_videos", exist_ok=True)

# defining per person memory
person_memory = {}

# Spatial Calculation functions 
def object_near_hand(obj, kps, tx=0.15, ty=0.20):
    hx = (kps[9][0] + kps[10][0]) / 2
    hy = (kps[9][1] + kps[10][1]) / 2
    cx = (obj[0] + obj[2]) / 2
    cy = (obj[1] + obj[3]) / 2
    return abs(cx - hx) < tx and abs(cy - hy) < ty

def hand_near_bag(bag, kps, t=0.12):
    hx = (kps[9][0] + kps[10][0]) / 2
    hy = (kps[9][1] + kps[10][1]) / 2
    cx = (bag[0] + bag[2]) / 2
    cy = (bag[1] + bag[3]) / 2
    return abs(cx - hx) < t and abs(cy - hy) < t

def inside_trolley(obj, trolleys):
    cx = (obj[0] + obj[2]) / 2
    cy = (obj[1] + obj[3]) / 2
    return any(t[0] < cx < t[2] and t[1] < cy < t[3] for t in trolleys)

def get_object_in_hand(objects, kps):
    for o in objects:
        if object_near_hand(o, kps):
            return o
    return None

def object_released(obj, kps):
    if obj is None:
        return True
    near_hand = object_near_hand(obj, kps)
    hand_y = min(kps[9][1], kps[10][1])
    waist_y = kps[WAIST_KP][1]
    near_waist = abs(hand_y - waist_y) < 0.08
    return (not near_hand) and (not near_waist)

# main function
def detect_shoplifting(video_path):

    cap = cv2.VideoCapture(video_path, cv2.CAP_FFMPEG)
    cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)

    fps = 15
    out = cv2.VideoWriter(
        "./output_videos/mobile_camera_output_input_is_given2.mp4",
        cv2.VideoWriter_fourcc(*"mp4v"),
        fps,
        (640, 480)
    )

    frame_count = 0
    FRAME_SKIP = 2

    while cap.isOpened():

        # If some old frames are there we need to drop them
        cap.grab()
        ok, frame = cap.retrieve()
        if not ok:
            break

        frame_count += 1
        if frame_count % FRAME_SKIP != 0:
            continue

        frame = cv2.resize(frame, (640, 480))
        annotated = frame.copy()

        pose_results = pose_model.track(
            frame,
            persist=True,
            tracker="bytetrack.yaml",
            stream=True,
            verbose=False
        )

        has_person = False

        for result in pose_results:

            if result.boxes.id is None:
                continue

            has_person = True

            boxes = result.boxes.xyxy
            ids = result.boxes.id.tolist()
            confs = result.boxes.conf.tolist()
            kps_all = result.keypoints.xyn.tolist()

        if not has_person:
            out.write(annotated)
            cv2.imshow("Shoplifting Detection", annotated)
            continue

        obj_boxes, bag_boxes, trolley_boxes = [], [], []
        h, w, _ = frame.shape

        for r in object_model(frame, verbose=False):
            for b, c in zip(r.boxes.xyxy, r.boxes.cls):
                x1, y1, x2, y2 = b.tolist()
                bw, bh = (x2-x1)/w, (y2-y1)/h
                if 0.02 < bw < 0.25 and 0.02 < bh < 0.25:
                    obj_boxes.append([x1/w, y1/h, x2/w, y2/h])
                if int(c.item()) in BAG_CLASSES:
                    bag_boxes.append([x1/w, y1/h, x2/w, y2/h])

        for r in trolley_model(frame, verbose=False):
            for b, c in zip(r.boxes.xyxy, r.boxes.cls):
                if int(c.item()) == TROLLEY_CLASS:
                    x1, y1, x2, y2 = b.tolist()
                    trolley_boxes.append([x1/w, y1/h, x2/w, y2/h])

        # Identify person in the frame
        for i, box in enumerate(boxes):
            if confs[i] < 0.65:
                continue

            pid = int(ids[i])
            kps = kps_all[i]
            x1, y1, x2, y2 = map(int, box.tolist())

            if pid not in person_memory:
                person_memory[pid] = {
                    "tracked_object": None,
                    "pickup_time": None,
                    "display_sus": False
                }

            mem = person_memory[pid]

            # Pose Extraction
            data = {}
            for j in range(len(kps)):
                data[f"x{j}"] = kps[j][0]
                data[f"y{j}"] = kps[j][1]
            f_pose = 1 - xgb_model.predict(
                xgb.DMatrix(pd.DataFrame([data]))
            )[0]

            # Associating object ownership
            current_object = get_object_in_hand(obj_boxes, kps)
            if current_object is not None:
                mem["tracked_object"] = current_object
                if mem["pickup_time"] is None:
                    mem["pickup_time"] = time.time()

            # Concealment
            hand_y = min(kps[9][1], kps[10][1])
            waist_y = kps[WAIST_KP][1]
            f_conceal = abs(hand_y - waist_y) < 0.05 or any(
                hand_near_bag(b, kps) for b in bag_boxes
            )

            # Disappearnce
            f_disp = False
            if mem["pickup_time"] and time.time() - mem["pickup_time"] > 1.2:
                if current_object is None:
                    f_disp = True

            if mem["tracked_object"] and f_conceal and f_disp:
                mem["display_sus"] = True

            # if object is realeased
            if mem["tracked_object"] and object_released(mem["tracked_object"], kps):
                mem["tracked_object"] = None
                mem["pickup_time"] = None
                mem["display_sus"] = False

            # Output
            label = "Suspicious" if mem["display_sus"] else "Normal"
            color = (0, 0, 255) if mem["display_sus"] else (0, 255, 0)

            cv2.rectangle(annotated, (x1, y1), (x2, y2), color, 2)
            cvzone.putTextRect(
                annotated, f"{label} | ID:{pid}",
                (x1, y1 - 10), scale=1, thickness=1
            )

            if mem["tracked_object"]:
                ox1, oy1, ox2, oy2 = mem["tracked_object"]
                ox1, oy1, ox2, oy2 = int(ox1*w), int(oy1*h), int(ox2*w), int(oy2*h)
                cv2.rectangle(annotated, (ox1, oy1), (ox2, oy2), (255, 0, 0), 2)
                cvzone.putTextRect(annotated, "Object", (ox1, oy1 - 5), scale=0.7)

        out.write(annotated)
        cv2.imshow("Shoplifting Detection", annotated)
        if cv2.waitKey(1) & 0xFF == ord("q"):
            break

    cap.release()
    out.release()
    cv2.destroyAllWindows()

detect_shoplifting(video_path)
