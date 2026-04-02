# model_loader.py

import tensorflow as tf
from tensorflow.keras.layers import Layer

# -----------------------------
# DropBlock2D (custom layer used in your age/gender model)
# -----------------------------
class DropBlock2D(Layer):
    def __init__(self, drop_prob=0.1, block_size=5, **kwargs):
        super().__init__(**kwargs)
        self.drop_prob = drop_prob
        self.block_size = block_size

    def call(self, x, training=False):
        return x   # disabled in inference


# -----------------------------
# Load Age/Gender Model
# -----------------------------
age_gender_model = tf.keras.models.load_model(
    "model_v3_safeAttention_fewshotMixed.keras",
    custom_objects={"DropBlock2D": DropBlock2D}
)

age_map = ["1-12", "13-19", "20-35", "36+"]

# ====================================================
# Load Emotion Model (Mass Mode Only)
# ====================================================
from utils.build_model import build_emotion_model

emotion_model = build_emotion_model()
emotion_model.load_weights("final_emotion_cnn_v3_calibrated.weights.h5")

emotion_labels = ["angry", "sad", "happy", "neutral", "fear", "suspicious"]

print("Emotion Model Loaded (Mass Mode)")


# -----------------------------
# Load ArcFace Embedding Model (InsightFace)
# -----------------------------
embedding_model = None

def get_embedding_model():
    global embedding_model
    if embedding_model is not None:
        return embedding_model

    from insightface.model_zoo import get_model
    m = get_model("arcface_r100_v1")
    if m is None:
        raise RuntimeError("ArcFace model could not be loaded (get_model returned None)")

    # ⚠️ prepare arguments depend on insightface version (see note below)
    m.prepare(ctx_id=0)
    embedding_model = m
    return embedding_model

print("Embedding Model Loaded: ArcFace r100")
print("Age/Gender Model Loaded")

# -----------------------------
# Load Engagement Models (PyTorch) - Lazy
# -----------------------------
engagement_service = None

def get_engagement_service():
    global engagement_service
    if engagement_service is not None:
        return engagement_service

    # Import inside to avoid torch loading unless needed
    from engagement_service import EngagementService

    # ✅ safest with TensorFlow running: CPU
    engagement_service = EngagementService(
        yolo_path="weights/yolov8n.pt",
        head_path="weights/head_orientation_cnn.pt",
        use_zones=False,
        device="cpu"
    )
    print("Engagement Service Loaded (Mass Mode)")
    return engagement_service
