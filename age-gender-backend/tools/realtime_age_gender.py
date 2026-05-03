import cv2
import numpy as np
import tensorflow as tf
from mtcnn import MTCNN

# Load Model (with DropBlock2D)

from tensorflow.keras.layers import Layer

class DropBlock2D(Layer):
    def __init__(self, drop_prob=0.1, block_size=5, **kwargs):
        super().__init__(**kwargs)
        self.drop_prob = drop_prob
        self.block_size = block_size

    def call(self, x, training=False):
        return x  # inference mode (no dropout)

model = tf.keras.models.load_model(
    "model_v2_fewshot.keras",
    custom_objects={"DropBlock2D": DropBlock2D}
)

age_map = ["1-12", "13-19", "20-35", "36+"]

# ================================
# Initialize MTCNN face detector
# ================================
detector = MTCNN()

# ================================
# Start webcam
# ================================
cap = cv2.VideoCapture(0)  # 0 = default webcam

while True:
    ret, frame = cap.read()
    if not ret:
        break

    rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    faces = detector.detect_faces(rgb)

    for face in faces:
        x, y, w, h = face["box"]

        # Crop face
        x, y = max(x, 0), max(y, 0)
        face_img = frame[y:y+h, x:x+w]

        if face_img.size == 0:
            continue

        face_resized = cv2.resize(face_img, (128, 128))
        face_resized = face_resized.astype("float32") / 255.0
        face_resized = np.expand_dims(face_resized, axis=0)

        # Predict
        gender_pred, age_pred = model.predict(face_resized, verbose=0)

        gender = "Female" if gender_pred[0][0] > 0.5 else "Male"
        age_group = age_map[np.argmax(age_pred)]

        # Draw box + text
        cv2.rectangle(frame, (x, y), (x+w, y+h), (0,255,0), 2)
        cv2.putText(frame, f"{age_group}, {gender}",
                    (x, y-10), cv2.FONT_HERSHEY_SIMPLEX,
                    0.7, (255,255,255), 2)

    cv2.imshow("Age & Gender Detection", frame)

    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()
