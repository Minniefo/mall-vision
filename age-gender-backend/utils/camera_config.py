import cv2

# Laptop webcam
CAMERA_SOURCE = 0

# UGREEN USB HD Camera
# CAMERA_SOURCE = 1



def get_camera():
    """Returns an opened cv2.VideoCapture object using the chosen source."""
    cap = cv2.VideoCapture(CAMERA_SOURCE)
    if not cap.isOpened():
        raise RuntimeError(f" Failed to open camera source: {CAMERA_SOURCE}")
    return cap
