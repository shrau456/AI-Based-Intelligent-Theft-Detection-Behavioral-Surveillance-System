import os
import cv2
from ultralytics import YOLO
import pandas as pd

model = YOLO("yolo11s-pose.pt")

cap = cv2.VideoCapture('nm1.mp4')

frames = cap.get(cv2.CAP_PROP_FRAME_COUNT)
fps = cap.get(cv2.CAP_PROP_FPS)
seconds = round(frames / fps)

frame_total = 2000
i = 0
a = 0 

all_data = []

while cap.isOpened():
    cap.set(cv2.CAP_PROP_POS_MSEC, (i * ((seconds / frame_total) * 1000)))
    flag, frame = cap.read()

    if not flag:
        break

    pa = r'C:\Users\sprat\OneDrive\Desktop\BTech Project\Shoplifting\yolo-pose-shoplifting\yolopose\images'
    image_path = f'{pa}\img_{i}.jpg'
    cv2.imwrite(image_path, frame)

    results = model(frame, verbose=False)

    for r in results:
        bound_box = r.boxes.xyxy
        conf = r.boxes.conf.tolist()
        keypoints = r.keypoints.xyn.tolist()

        for index, box in enumerate(bound_box):
            if conf[index] > 0.75:
                x1, y1, x2, y2 = box.tolist()
                cropped_person = frame[int(y1):int(y2), int(x1):int(x2)]
                op = r'C:\Users\sprat\OneDrive\Desktop\BTech Project\Shoplifting\yolo-pose-shoplifting\yolopose\images1'
                output_path = f'{op}\person_nn_{a}.jpg'

                data = {'image_name': f'person_nn_{a}.jpg'}

                for j in range(len(keypoints[index])):
                    data[f'x{j}'] = keypoints[index][j][0]
                    data[f'y{j}'] = keypoints[index][j][1]

                all_data.append(data)
                cv2.imwrite(output_path, cropped_person)
                a += 1

    i += 1

print(f"Total frames processed: {i-1}, Total cropped images saved: {a-1}")
cap.release()
cv2.destroyAllWindows()

df = pd.DataFrame(all_data)

csv_file_path = r'C:\Users\sprat\OneDrive\Desktop\BTech Project\Shoplifting\yolo-pose-shoplifting\nkeypoint.csv'

if not os.path.isfile(csv_file_path):
    df.to_csv(csv_file_path, index=False) 
else:
    df.to_csv(csv_file_path, mode='a', header=False, index=False) 

print(f"Keypoint data saved to {csv_file_path}")
