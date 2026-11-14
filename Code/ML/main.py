
import cv2
import pandas as pd
from ultralytics import YOLO
import xgboost as xgb
import cvzone

# input video path
video_path = "./test_videos/c1.mp4"
# video_path = 0  # for laptop webcam testing

# for connecting cctv, or mobile ip camera, then only enable these two, else do not
# cv2.setNumThreads(4)
# video_path = "http://10.172.145.215:8080/video" 

# loading the required models
pose_model = YOLO("./yolo_models/yolo11n-pose.pt") 
object_model = YOLO("./yolo_models/yolo11n.pt")

# fine tuned trolly model
trolley_model = YOLO("./yolo_models/best.pt")

xgb_model = xgb.Booster()
xgb_model.load_model("trained_model.json")

# Some configs
BAG_CLASSES = [24, 26]
TROLLEY_CLASS = 2

# per person memory
person_memory = {}
evidence_log = []

HAND_KP = [9, 10]
WAIST_KP = 11

def object_near_hand_region(obj_box, keypoints, thresh_x=0.15, thresh_y=0.20):
    hx = (keypoints[9][0] + keypoints[10][0]) / 2
    hy = (keypoints[9][1] + keypoints[10][1]) / 2

    ox1, oy1, ox2, oy2 = obj_box
    cx, cy = (ox1 + ox2) / 2, (oy1 + oy2) / 2

    return abs(cx - hx) < thresh_x and abs(cy - hy) < thresh_y


def hand_near_bag(bag_box, keypoints, thresh=0.12):
    hx = (keypoints[9][0] + keypoints[10][0]) / 2
    hy = (keypoints[9][1] + keypoints[10][1]) / 2

    bx1, by1, bx2, by2 = bag_box
    cx, cy = (bx1 + bx2) / 2, (by1 + by2) / 2

    return abs(cx - hx) < thresh and abs(cy - hy) < thresh

def object_inside_trolley(obj_box, trolley_boxes):
    ox1, oy1, ox2, oy2 = obj_box
    cx, cy = (ox1 + ox2) / 2, (oy1 + oy2) / 2

    for tb in trolley_boxes:
        tx1, ty1, tx2, ty2 = tb
        if tx1 < cx < tx2 and ty1 < cy < ty2:
            return True
    return False

def detect_shoplifting(video_path):
    cap = cv2.VideoCapture(video_path)
    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    out = cv2.VideoWriter(
        "./output_videos/delete.mp4",
        fourcc,
        20.0, # fps 
        (1018, 600) # resizing the frame
    )

    frame_id = 0
    FRAME_SKIP = 1

    while cap.isOpened():
        success, frame = cap.read()
        if not success:
            break

        frame_id += 1
        if (frame_id % FRAME_SKIP != 0):
            continue
        frame = cv2.resize(frame, (1018, 600))

        # preson trackign
        pose_results = pose_model.track(
            frame,
            persist=True,
            tracker="bytetrack.yaml",
            verbose=False
        )

        annotated_frame = frame.copy()

        if pose_results[0].boxes.id is None:
            out.write(annotated_frame)
            cv2.imshow("Shoplifting Detection", annotated_frame)
            continue

        boxes = pose_results[0].boxes.xyxy
        track_ids = pose_results[0].boxes.id.tolist()
        confs = pose_results[0].boxes.conf.tolist()
        keypoints_all = pose_results[0].keypoints.xyn.tolist()

        obj_results = object_model(frame, verbose=False)

        object_boxes = []
        bag_boxes = []

        h, w, _ = frame.shape

        for r in obj_results:
            for box, cls in zip(r.boxes.xyxy, r.boxes.cls):
                x1, y1, x2, y2 = box.tolist()
                cls = int(cls.item())

                bw = (x2 - x1) / w
                bh = (y2 - y1) / h

                if 0.02 < bw < 0.25 and 0.02 < bh < 0.25:
                    object_boxes.append([x1 / w, y1 / h, x2 / w, y2 / h])

                if cls in BAG_CLASSES:
                    bag_boxes.append([x1 / w, y1 / h, x2 / w, y2 / h])

        trolley_results = trolley_model(frame, verbose=False)
        trolley_boxes = []

        for r in trolley_results:
            for box, cls in zip(r.boxes.xyxy, r.boxes.cls):

                if int(cls.item()) == TROLLEY_CLASS:
                    x1, y1, x2, y2 = box.tolist()
                    trolley_boxes.append([x1 / w, y1 / h, x2 / w, y2 / h])

        for i, box in enumerate(boxes):

            if confs[i] < 0.55:
                continue

            person_id = int(track_ids[i])
            keypoints = keypoints_all[i]
            x1, y1, x2, y2 = map(int, box.tolist())

            if person_id not in person_memory:
                person_memory[person_id] = {
                    "pickup": False,
                    "pickup_frame": None,
                    "conceal_frames": 0,
                    "bag_conceal_frames": 0,
                    "has_stolen": False,
                    "return_frames": 0
                }

            mem = person_memory[person_id]

            data = {}
            for j in range(len(keypoints)):
                data[f"x{j}"] = keypoints[j][0]
                data[f"y{j}"] = keypoints[j][1]

            df = pd.DataFrame(data, index=[0])
            normal_prob = xgb_model.predict(xgb.DMatrix(df))[0]
            f_pose = 1 - normal_prob

            f_pickup = 0
            for obj_box in object_boxes:

                if object_inside_trolley(obj_box, trolley_boxes):
                    continue

                if object_near_hand_region(obj_box, keypoints):
                    f_pickup = 1
                    mem["pickup"] = True
                    mem["pickup_frame"] = frame_id
                    break

            curr_hand_y = min(keypoints[9][1], keypoints[10][1])
            waist_y = keypoints[WAIST_KP][1]

            if abs(curr_hand_y - waist_y) < 0.05:
                mem["conceal_frames"] += 1
            else:
                mem["conceal_frames"] = 0

            bag_detected = False
            for bag in bag_boxes:
                if hand_near_bag(bag, keypoints):
                    bag_detected = True
                    break

            if bag_detected:
                mem["bag_conceal_frames"] += 1
            else:
                mem["bag_conceal_frames"] = 0

            body_conceal = mem["conceal_frames"] > 5
            bag_conceal = mem["bag_conceal_frames"] > 3

            f_concealment = 1 if (body_conceal or bag_conceal) else 0

            f_disappearance = 0

            if bag_conceal:
                f_disappearance = 1

            if f_disappearance == 0 and mem["pickup"] and mem["pickup_frame"] is not None:
                if frame_id - mem["pickup_frame"] > 25:
                    still_visible = False
                    for obj_box in object_boxes:

                        if object_inside_trolley(obj_box, trolley_boxes):
                            still_visible = True
                            break

                        if object_near_hand_region(obj_box, keypoints):
                            still_visible = True
                            break

                    if not still_visible:
                        f_disappearance = 1

            if f_pickup == 0 and f_concealment == 1:
                f_pickup = 1
                mem["pickup"] = True

            SuspicionScore = (
                0.30 * f_pickup +
                0.30 * f_concealment +
                0.25 * f_disappearance +
                0.15 * f_pose
            )
            if SuspicionScore > 0.75:
                mem["has_stolen"] = True

            object_back_in_hand = False
            for obj_box in object_boxes:
                if object_near_hand_region(obj_box, keypoints):
                    object_back_in_hand = True
                    break

            if mem["has_stolen"] and object_back_in_hand:
                mem["return_frames"] += 1
            else:
                mem["return_frames"] = 0

            if mem["return_frames"] > 10:
                mem["has_stolen"] = False
                mem["pickup"] = False
                mem["pickup_frame"] = None

            if mem["has_stolen"]:
                label = "Suspicious"
                color = (0, 0, 255)
            else:
                label = "Normal"
                color = (0, 255, 0)

            cv2.rectangle(annotated_frame, (x1, y1), (x2, y2), color, 2)

            cvzone.putTextRect(
                annotated_frame,
                f"{label} | ID:{person_id} | {SuspicionScore:.2f}",
                (x1, y1 - 10),
                scale=1,
                thickness=1
            )

            cvzone.putTextRect(
                annotated_frame,
                f"P:{f_pickup} C:{f_concealment} D:{f_disappearance}",
                (x1, y2 + 20),
                scale=0.8,
                thickness=1
            )

        out.write(annotated_frame)
        cv2.imshow("Shoplifting Detection", annotated_frame)

        if cv2.waitKey(1) & 0xFF == ord("q"):
            break

    cap.release()
    out.release()  # output video
    cv2.destroyAllWindows()

detect_shoplifting(video_path)
