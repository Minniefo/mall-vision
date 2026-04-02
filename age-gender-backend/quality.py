# quality.py
import cv2
import numpy as np

# -------------------------------
# Blur score (Laplacian variance)
# -------------------------------
def blur_score(face_img):
    gray = cv2.cvtColor(face_img, cv2.COLOR_BGR2GRAY)
    return cv2.Laplacian(gray, cv2.CV_64F).var()


# -------------------------------
# Illumination score
# -------------------------------
def illumination_score(face_img):
    gray = cv2.cvtColor(face_img, cv2.COLOR_BGR2GRAY)
    mean_intensity = np.mean(gray)

    # Ideal mid-range lighting
    ideal = 127.0
    deviation = abs(mean_intensity - ideal)

    # Normalize to [0,1]
    return max(0.0, 1.0 - deviation / ideal)


# -------------------------------
# Face size score (relative)
# -------------------------------
def face_size_score(face_bbox, frame_shape):
    _, _, w, h = face_bbox
    frame_h, frame_w = frame_shape[:2]

    face_area = w * h
    frame_area = frame_h * frame_w

    ratio = face_area / frame_area

    # Small faces get penalized
    return min(1.0, ratio / 0.05)  # 5% of frame ≈ good size

def compute_quality_score(face_img, face_bbox, frame_shape):
    b = blur_score(face_img)
    i = illumination_score(face_img)
    s = face_size_score(face_bbox, frame_shape)

    # Normalize blur score (empirical threshold)
    blur_norm = min(1.0, b / 150.0)

    # Weighted combination
    quality = (
        0.4 * blur_norm +
        0.3 * i +
        0.3 * s
    )

    return float(np.clip(quality, 0.0, 1.0))

