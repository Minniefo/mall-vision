import cv2
import numpy as np


def gamma_correct(img, gamma=1.2):
    """
    Apply gamma correction for shadow / low-light conditions
    """
    inv = 1.0 / gamma
    table = np.array(
        [(i / 255.0) ** inv * 255 for i in range(256)]
    ).astype("uint8")
    return cv2.LUT(img, table)


def preprocess_face(frame_rgb, box, margin=0.25):
    """
    Preprocess face to match training distribution while being
    robust to lighting, distance, and noise.

    Input:
        frame_rgb : RGB frame
        box       : MediaPipe relative bounding box
    Output:
        face      : (160,160,3) normalized face or None
    """

    h, w, _ = frame_rgb.shape

   
    # Convert relative bbox → pixel coords
    
    x1 = int(box.xmin * w)
    y1 = int(box.ymin * h)
    x2 = int((box.xmin + box.width) * w)
    y2 = int((box.ymin + box.height) * h)

    
    # Expand bounding box (training-style margin)
    
    bw, bh = x2 - x1, y2 - y1
    x1 = max(0, int(x1 - margin * bw))
    y1 = max(0, int(y1 - margin * bh))
    x2 = min(w, int(x2 + margin * bw))
    y2 = min(h, int(y2 + margin * bh))

    face = frame_rgb[y1:y2, x1:x2]

    if face.size == 0:
        return None

    
    # Convert to LAB for illumination handling
    
    lab = cv2.cvtColor(face, cv2.COLOR_RGB2LAB)
    L, A, B = cv2.split(lab)

    mean_lum = np.mean(L)

    
    # Adaptive CLAHE (lighting-aware)
    
    if mean_lum < 90:
        clip = 2.5   # low light
    else:
        clip = 1.2   # bright / normal light

    clahe = cv2.createCLAHE(clipLimit=clip, tileGridSize=(8, 8))
    L = clahe.apply(L)

    lab = cv2.merge((L, A, B))
    face = cv2.cvtColor(lab, cv2.COLOR_LAB2RGB)

    
    # Gamma correction for shadows
    
    if mean_lum < 80:
        face = gamma_correct(face, gamma=1.3)

    
    # Denoising (webcam grain removal)
    #
    face = cv2.fastNlMeansDenoisingColored(
        face,
        None,
        h=7,
        hColor=7,
        templateWindowSize=5,
        searchWindowSize=11
    )

    
    # Distance-aware upscaling
    
    if face.shape[0] < 96 or face.shape[1] < 96:
        face = cv2.resize(face, (160, 160), interpolation=cv2.INTER_CUBIC)
    else:
        face = cv2.resize(face, (160, 160))

    
    # Normalize to model input range
    
    face = face.astype("float32") / 255.0

    return face
