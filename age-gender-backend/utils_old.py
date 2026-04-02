# backend/utils.py
import base64
import cv2
import numpy as np
import hashlib


# --------------------------------
# L2 normalize embedding (Phase 0 core utility)
# --------------------------------
def l2_normalize(embedding: np.ndarray) -> np.ndarray:
    norm = np.linalg.norm(embedding)
    if norm == 0:
        return embedding
    return embedding / norm


# --------------------------------
# Base64 → OpenCV image
# --------------------------------
def decode_base64_image(base64_str):
    try:
        header, data = base64_str.split(",", 1)
        img_bytes = base64.b64decode(data)
        img_array = np.frombuffer(img_bytes, np.uint8)
        return cv2.imdecode(img_array, cv2.IMREAD_COLOR)
    except:
        return None

# --------------------------------
# Stable hash for embeddings (privacy-safe & consistent)
# --------------------------------
def hash_embedding(embedding):
    # 1. Normalize vector (makes embedding scale-invariant)
    emb = l2_normalize(embedding)

    # Quantize to bins instead of rounding
    #  -1 to +1 range → grouped into 20 bins
    # This makes embeddings extremely stable.
    bins = np.linspace(-1, 1, 21)
    digitized = np.digitize(emb, bins)

    # 3. Convert to string
    emb_str = ",".join(map(str, digitized))

    # 4. Hash using SHA256 (non-reversible)
    return hashlib.sha256(emb_str.encode()).hexdigest()

# --------------------------------
# Crop face safely
# --------------------------------
def safe_crop(img, box):
    x, y, w, h = box
    x, y = max(0, x), max(0, y)
    return img[y:y+h, x:x+w]

