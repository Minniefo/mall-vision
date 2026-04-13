import cv2
import os
import numpy as np

# Load images
BASE_DIR = os.path.dirname(os.path.dirname(__file__))

FLOWER_PATH = os.path.join(BASE_DIR, "assets", "filters", "flower_crown.png")
GLASSES_PATH = os.path.join(BASE_DIR, "assets", "filters", "sunglasses.png")

flower_png = cv2.imread(FLOWER_PATH, cv2.IMREAD_UNCHANGED)
glasses_png = cv2.imread(GLASSES_PATH, cv2.IMREAD_UNCHANGED)

if flower_png is None:
    raise ValueError(f"Flower image not found at {FLOWER_PATH}")

if glasses_png is None:
    raise ValueError(f"Glasses image not found at {GLASSES_PATH}")


def overlay_png(background, overlay, x, y):
    bg_h, bg_w = background.shape[:2]
    ov_h, ov_w = overlay.shape[:2]

    if x >= bg_w or y >= bg_h:
        return background

    x1 = max(x, 0)
    y1 = max(y, 0)
    x2 = min(x + ov_w, bg_w)
    y2 = min(y + ov_h, bg_h)

    overlay_crop = overlay[0:(y2 - y1), 0:(x2 - x1)]

    if overlay_crop.shape[2] < 4:
        return background

    overlay_rgb = overlay_crop[:, :, :3]
    alpha = overlay_crop[:, :, 3] / 255.0
    alpha = alpha[:, :, np.newaxis]

    bg_crop = background[y1:y2, x1:x2]

    blended = (alpha * overlay_rgb + (1 - alpha) * bg_crop).astype(np.uint8)

    background[y1:y2, x1:x2] = blended

    return background


def apply_flower_crown(frame, face_box):
    x, y, w, h = face_box

    crown_width = int(w * 1.3)
    crown_height = int(crown_width * flower_png.shape[0] / flower_png.shape[1])

    crown = cv2.resize(flower_png, (crown_width, crown_height))

    crown_x = x - int((crown_width - w) / 2)
    crown_y = y - int(crown_height * 0.7)

    return overlay_png(frame, crown, crown_x, crown_y)


def apply_sunglasses(frame, face_box):
    x, y, w, h = face_box

    glasses_width = int(w * 1.1)
    glasses_height = int(glasses_width * glasses_png.shape[0] / glasses_png.shape[1])

    glasses = cv2.resize(glasses_png, (glasses_width, glasses_height))

    glasses_x = x - int((glasses_width - w) / 2)
    glasses_y = y + int(h * 0.25)

    return overlay_png(frame, glasses, glasses_x, glasses_y)