import cv2
import numpy as np
import tensorflow as tf
from mtcnn import MTCNN
import os
import random
import time


# ====================================================
# 1. Load Model (with DropBlock2D)
# ====================================================

from tensorflow.keras.layers import Layer

class DropBlock2D(Layer):
    def __init__(self, drop_prob=0.1, block_size=5, **kwargs):
        super().__init__(**kwargs)
        self.drop_prob = drop_prob
        self.block_size = block_size

    def call(self, x, training=False):
        # During inference dropout is OFF
        return x


model = tf.keras.models.load_model(
    "model_v3_safeAttention_fewshotMixed.keras",
    custom_objects={"DropBlock2D": DropBlock2D}
)

print("Model Loaded Successfully!")

age_map = ["1-12", "13-19", "20-35", "36+"]


# ====================================================
# 2. Advertisement Folder Mapping
# ====================================================

def get_ad_folder(age_label, gender_label):
    """
    Convert predicted age & gender to advertisement folder name.
    """
    if age_label in ["1-12", "13-19"]:
        gender_folder = "boy" if gender_label == "male" else "girl"
    else:
        gender_folder = "man" if gender_label == "male" else "woman"

    return age_label, gender_folder


def load_random_ad(age_label, gender_label):
    base_path = "Advertisements"   # <-- folder next to this script

    age_folder, gender_folder = get_ad_folder(age_label, gender_label)

    full_path = f"{base_path}/{age_folder}/{gender_folder}"

    if not os.path.isdir(full_path):
        print("⚠ No folder found:", full_path)
        return None

    files = os.listdir(full_path)
    if len(files) == 0:
        print("⚠ No ads inside:", full_path)
        return None

    chosen = random.choice(files)
    ad_path = os.path.join(full_path, chosen)

    ad_img = cv2.imread(ad_path)
    if ad_img is None:
        print("⚠ Error loading:", ad_path)
        return None

    return ad_img


# ====================================================
# 3. MTCNN Face Detector
# ====================================================

detector = MTCNN()
print("MTCNN Loaded!")


# ====================================================
# 4. Start Webcam + Advertisement Loop
# ====================================================

# Try opening the UGREEN USB webcam
cap = cv2.VideoCapture(0, cv2.CAP_AVFOUNDATION)

# Set 2K resolution (if supported)
cap.set(cv2.CAP_PROP_FRAME_WIDTH, 2560)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 1440)

last_ad_time = 0
ad_interval = 10      # seconds
current_ad = None

print("\nReal-Time System Started")
print("Press 'Q' to quit.\n")

while True:
    ret, frame = cap.read()
    if not ret:
        break

    rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    faces = detector.detect_faces(rgb)

    # If no face → don't update ad yet
    if len(faces) == 0:
        combined = frame if current_ad is None else np.hstack(
            (frame, cv2.resize(current_ad, (frame.shape[1], frame.shape[0])))
        )
        cv2.imshow("Age-Gender + Advertisement", combined)
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break
        continue

    # Use the largest face (most reliable)
    faces = sorted(faces, key=lambda f: f["box"][2] * f["box"][3], reverse=True)
    face = faces[0]

    x, y, w, h = face["box"]
    x, y = max(0, x), max(0, y)

    face_img = frame[y:y+h, x:x+w]

    if face_img.size == 0:
        continue

    # Preprocess face
    face_resized = cv2.resize(face_img, (128, 128))
    face_resized = face_resized.astype("float32") / 255.0
    face_resized = np.expand_dims(face_resized, axis=0)

    # Predict
    gender_pred, age_pred = model.predict(face_resized, verbose=0)

    # Decode gender (sigmoid)
    gender_value = gender_pred[0][0]
    gender_label = "female" if gender_value > 0.5 else "male"

    # Decode age (softmax)
    age_label = age_map[np.argmax(age_pred)]

    # Draw detection on frame
    cv2.rectangle(frame, (x, y), (x+w, y+h), (0,255,0), 2)
    cv2.putText(frame, f"{age_label}, {gender_label}",
                (x, y-10), cv2.FONT_HERSHEY_SIMPLEX,
                0.8, (255,255,255), 2)

    # Update advertisement every X seconds
    if time.time() - last_ad_time > ad_interval:
        current_ad = load_random_ad(age_label, gender_label)
        last_ad_time = time.time()

    # Combine webcam + advertisement
    if current_ad is None:
        combined = frame
    else:
        ad_resized = cv2.resize(current_ad, (frame.shape[1], frame.shape[0]))
        combined = np.hstack((frame, ad_resized))

    cv2.imshow("Age-Gender + Advertisement", combined)

    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()

print("\n Program closed.")
