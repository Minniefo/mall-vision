import cv2
import numpy as np
import os


MODEL_PATH = "utils/opencv_face_detector_uint8.pb"
CONFIG_PATH = "utils/opencv_face_detector.pbtxt"

# --------- Load TF model correctly ----------
if not os.path.exists(MODEL_PATH):
    print(" Model file missing:", MODEL_PATH)

if not os.path.exists(CONFIG_PATH):
    print(" Config file missing:", CONFIG_PATH)

net = cv2.dnn.readNetFromTensorflow(MODEL_PATH, CONFIG_PATH)


def detect_faces(frame):
    h, w = frame.shape[:2]

    blob = cv2.dnn.blobFromImage(frame, 1.0, (300, 300),
                                 (104.0, 177.0, 123.0), False, False)

    net.setInput(blob)
    detections = net.forward()

    boxes = []
    for i in range(detections.shape[2]):
        confidence = detections[0,0,i,2]
        if confidence < 0.6:
            continue

        box = detections[0,0,i,3:7] * np.array([w, h, w, h])
        x1, y1, x2, y2 = box.astype("int")

        x1 = max(0, x1)
        y1 = max(0, y1)
        x2 = min(w, x2)
        y2 = min(h, y2)

        boxes.append((x1, y1, x2, y2))

    return boxes
