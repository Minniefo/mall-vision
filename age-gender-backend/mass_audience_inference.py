#mass_audience_inference.py
import cv2
import numpy as np
import tensorflow as tf
from mtcnn import MTCNN
from tensorflow.keras import layers
from collections import Counter
import os
import random
import time
import uuid
from db import insert_mass_window_event, insert_perception_event
from system_state import current_mode, Mode
from mass_state import current_mass_ad
import base64
from datetime import datetime
from roi import is_in_near_zone
from config import (
    MASS_NEAR_ZONE_ENABLED,
    MASS_NEAR_ZONE_POLYGON
)
from model_loader import emotion_model
from datetime import datetime
from pytz import timezone
from model_loader import get_engagement_service
#from services.recommendation_engine import AdRecommendationEngine
#from services.novelty_ad_engine import NoveltyAdEngine
from services.yolo_detector import YOLOObjectDetector
import services.engine_loader as engine_loader

# ===============================
# Custom DropBlock Layer
# ===============================
class DropBlock2D(layers.Layer):
    def __init__(self, drop_prob=0.1, block_size=5, **kwargs):
        super().__init__(**kwargs)
        self.drop_prob = drop_prob
        self.block_size = block_size

    def call(self, x, training=False):
        # DropBlock disabled during inference
        return x


# ===============================
# Config
# ===============================
MODEL_PATH = "./model_v3_safeAttention_fewshotMixed.keras"
IMG_SIZE = 128
EMO_IMG_SIZE = 160
AD_BASE = "./Advertisements"

SMOOTH_WINDOW = 10     # seconds (dominance smoothing window)

MIN_FRAMES_FOR_DECISION = 10

AGE_LABELS = ["1-12", "13-19", "20-35", "36+"]
GENDER_LABELS = ["male", "female"]
EMOTION_LABELS = ["angry", "sad", "happy", "neutral", "fear", "suspicious"]

last_frame_log_time = 0
FRAME_LOG_INTERVAL = 10  # seconds

ENGAGEMENT_INTERVAL = 0.2   # seconds (5 FPS)
last_engagement_time = 0
DEBUG_ENGAGEMENT = True

#emotion model globals
dominant_emotion_buffer = []
consecutive_counter = 0
last_emotion = None
last_alert_state = False

#NOVELTY_ENGAGEMENT_THRESHOLD = 30
NOVELTY_ENGAGEMENT_THRESHOLD = 101
NOVELTY_SCAN_INTERVAL = 10   # seconds
last_novelty_scan_time = 0

SUSPICIOUS_ALERT_THRESHOLD = 0.70
FEAR_ALERT_THRESHOLD = 0.60

#engagement globals
dominant_engagement_buffer = []
engagement_service = None
latest_eng_stats = {
    "total_people": 0,
    "engaged_people": 0,
    "engagement_percentage": 0.0
}

SYSTEM_START_TIME = time.time()
STARTUP_WARMUP_SECONDS = 3

# ===============================
# Debug Controls
# ===============================

DEBUG_SYSTEM = True
DEBUG_FACE_DETECTION = False
DEBUG_EMOTION = False
DEBUG_ENGAGEMENT = True
DEBUG_NOVELTY = True
DEBUG_OBJECT = False
DEBUG_DATABASE = False

# ===============================
# Load Model & Detector
# ===============================
print("[INFO] Loading model...")
model = tf.keras.models.load_model(
    MODEL_PATH,
    custom_objects={"DropBlock2D": DropBlock2D},
    compile=False
)

detector = MTCNN()
print("[INFO] Model & MTCNN loaded")


yolo_detector = YOLOObjectDetector("yolov8n.pt")
yolo_loaded = yolo_detector.is_loaded

#NOVELTY_ENABLED = novelty_loaded and yolo_loaded
NOVELTY_ENABLED = True
DEBUG_OBJECT_RECOMMENDATION = True

current_ad_pid = None


# ===============================
# Advertisement Utilities
# ===============================

def gamma_correct(img, gamma=1.2):
    inv = 1.0 / gamma
    table = np.array(
        [(i / 255.0) ** inv * 255 for i in range(256)]
    ).astype("uint8")
    return cv2.LUT(img, table)


# ===============================
# Face Preprocessing (EMOTION MODEL)
# ===============================

def preprocess_face_size(img, box, size, pad_ratio=0.25):
    x, y, w, h = box
    H, W = img.shape[:2]

    pad_w = int(w * pad_ratio)
    pad_h = int(h * pad_ratio)

    x1 = max(0, x - pad_w)
    y1 = max(0, y - pad_h)
    x2 = min(W, x + w + pad_w)
    y2 = min(H, y + h + pad_h)

    face = img[y1:y2, x1:x2]
    if face.size == 0:
        return None

    face = cv2.resize(face, (size, size))
    face = face.astype("float32") / 255.0
    return face

#Emotion Preprocessing with CLAHE and Gamma Correction

def preprocess_face_for_emotion(frame_rgb, bbox, margin=0.25):
    x, y, w, h = bbox
    H, W = frame_rgb.shape[:2]

    # Expand bounding box (training-style)
    x1 = max(0, int(x - margin * w))
    y1 = max(0, int(y - margin * h))
    x2 = min(W, int(x + w + margin * w))
    y2 = min(H, int(y + h + margin * h))

    face = frame_rgb[y1:y2, x1:x2]
    if face.size == 0:
        return None

    # ===== Training Pipeline =====
    lab = cv2.cvtColor(face, cv2.COLOR_RGB2LAB)
    L, A, B = cv2.split(lab)

    mean_lum = np.mean(L)

    clip = 2.5 if mean_lum < 90 else 1.2
    clahe = cv2.createCLAHE(clipLimit=clip, tileGridSize=(8, 8))
    L = clahe.apply(L)

    lab = cv2.merge((L, A, B))
    face = cv2.cvtColor(lab, cv2.COLOR_LAB2RGB)

    if mean_lum < 80:
        face = gamma_correct(face, gamma=1.3)

    face = cv2.fastNlMeansDenoisingColored(
        face, None, 7, 7, 5, 11
    )

    face = cv2.resize(face, (160, 160))
    face = face.astype("float32") / 255.0

    return face    


# ===============================
# Webcam Loop
# ===============================
#cap = cv2.VideoCapture(0)

current_ad = None
current_ad_age = None
current_ad_gender = None

dominant_age_buffer = []
dominant_gender_buffer = []
window_start_time = time.time()
session_id = str(uuid.uuid4())
window_committed = False

#print("[INFO] System started. Press 'q' to quit.")
def test_object_recommendation(frame, final_age, final_gender, target_mood, primary_pid):

    print("\n========== OBJECT RECOMMENDATION TEST ==========")

    '''detections = yolo_detector.get_all_detections(frame)

    if DEBUG_OBJECT:
        print("[YOLO DETECTIONS]", detections)

    if not detections:
        print("[TEST RESULT] No objects detected")
        return None

    detected_object = detections[0]["object"]
    print("[TEST OBJECT]", detected_object)

    print("[NOVELTY DEBUG] Engine object:", engine_loader.novelty_engine)

    print(
        "[NOVELTY DEBUG] Engine loaded:",
        False if engine_loader.novelty_engine is None else engine_loader.novelty_engine.is_loaded
    )

    print(
        "[NOVELTY DEBUG] Ads loaded:",
        0 if engine_loader.novelty_engine is None or engine_loader.novelty_engine.ads_df is None
        else len(engine_loader.novelty_engine.ads_df)
    )

    novelty_ad = engine_loader.novelty_engine.get_object_novelty_ad(
        detected_object=detected_object,
        age=final_age,
        gender=final_gender,
        mood=target_mood,
        avoid_pid=primary_pid,
        debug=True
    )

    print("[NOVELTY RESULT]", novelty_ad)
    print("===============================================\n")

    return novelty_ad'''

    detections = yolo_detector.get_all_detections(frame)

    if DEBUG_OBJECT:
        print("[YOLO DETECTIONS]", detections)

    if not detections:
        print("[TEST RESULT] No objects detected")
        return None

    objects = [d["object"] for d in detections]

    print("[DETECTED OBJECTS]", objects)

    print("[NOVELTY DEBUG] Engine object:", engine_loader.novelty_engine)

    print(
        "[NOVELTY DEBUG] Engine loaded:",
        False if engine_loader.novelty_engine is None else engine_loader.novelty_engine.is_loaded
    )

    print(
        "[NOVELTY DEBUG] Ads loaded:",
        0 if engine_loader.novelty_engine is None or engine_loader.novelty_engine.ads_df is None
        else len(engine_loader.novelty_engine.ads_df)
    )

    best_novelty = None
    best_score = 0

    for obj in objects:

        print("[TEST OBJECT]", obj)

        novelty_ad = engine_loader.novelty_engine.get_object_novelty_ad(
            detected_object=obj,
            age=final_age,
            gender=final_gender,
            mood=target_mood,
            avoid_pid=primary_pid,
            debug=True
        )

        if novelty_ad and novelty_ad.get("similarity_score", 0) > best_score:
            best_score = novelty_ad["similarity_score"]
            best_novelty = novelty_ad
            best_novelty["detected_object"] = obj

    print("[BEST NOVELTY RESULT]", best_novelty)
    print("===============================================\n")

    return best_novelty
# ===============================
# MAIN ENTRY POINT
# ===============================
def run_mass_inference(frame):

    # -------------------------------
    # STARTUP WARMUP
    # -------------------------------
    if time.time() - SYSTEM_START_TIME < STARTUP_WARMUP_SECONDS:
        if DEBUG_SYSTEM:
            print("[SYSTEM] Warmup phase — skipping inference")
        return
    """
    Run ONE step of mass-audience inference.
    Called repeatedly from main.py camera loop.
    """

    global current_ad, current_ad_age, current_ad_gender
    global dominant_age_buffer, dominant_gender_buffer
    global window_start_time, window_committed
    global dominant_emotion_buffer
    global last_frame_log_time
    global consecutive_counter, last_emotion, last_alert_state
    global dominant_engagement_buffer
    global latest_eng_stats
    global engagement_service
    global current_ad_pid
    global last_novelty_scan_time

    if engagement_service is None:
        engagement_service = get_engagement_service()

    # -------------------------------
    # MODE GATE
    # -------------------------------
    if current_mode != Mode.MASS:
        dominant_age_buffer.clear()
        dominant_gender_buffer.clear()
        dominant_emotion_buffer.clear()
        dominant_engagement_buffer.clear()
        window_start_time = time.time()
        window_committed = False
        return

    rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    detections = detector.detect_faces(rgb)

    faces_ag = []   # 128x128 for age/gender
    faces_em = []   # 160x160 for emotion
    for d in detections:
        bbox = d["box"]

        # -------------------------------
        # Phase 3.5 – Near-zone gating
        # -------------------------------
        if MASS_NEAR_ZONE_ENABLED:
            in_near_zone = is_in_near_zone(bbox, MASS_NEAR_ZONE_POLYGON)

            # 🔍 DEBUG LOG (Phase 3.5 validation)
            if DEBUG_FACE_DETECTION:
                print("[ROI]", "NEAR" if in_near_zone else "FAR", "bbox:", bbox)

            if not in_near_zone:
                continue   # FAR person → ignore completely

        face_ag = preprocess_face_size(rgb, bbox, IMG_SIZE)       # 128
        face_em = preprocess_face_for_emotion(rgb, bbox)   # 160 with CLAHE+Gamma

        if face_ag is not None and face_em is not None:
            faces_ag.append(face_ag)
            faces_em.append(face_em)

    # -------------------------------
    # Per-frame inference
    # -------------------------------
    if not faces_ag:
        print("[MASS] No faces detected")

        # Reset smoothing buffers to avoid stale decisions
        dominant_age_buffer.clear()
        dominant_gender_buffer.clear()
        dominant_emotion_buffer.clear()
        dominant_engagement_buffer.clear()

        consecutive_counter = 0
        last_emotion = None
        return
    
    batch_ag = np.stack(faces_ag, axis=0)
    batch_em = np.stack(faces_em, axis=0)
    gender_preds, age_preds = model.predict(batch_ag, verbose=0)
    emotion_preds = emotion_model.predict(batch_em, verbose=0)

    age_votes = []
    gender_votes = []
    #emotion_votes = []

    for i in range(len(faces_ag)):
        age_votes.append(AGE_LABELS[np.argmax(age_preds[i])])
        gender_votes.append(GENDER_LABELS[np.argmax(gender_preds[i])])
        #emotion_index = np.argmax(emotion_preds[i])
        #emotion_label = EMOTION_LABELS[emotion_index]
        #emotion_conf = float(np.max(emotion_preds[i]))

        #print(f"[EMOTION] Face {i} → {emotion_label} ({emotion_conf:.2f})")'''
    
    # Compute mean probability across all detected faces
    #avg_frame_probs = np.mean(emotion_preds, axis=0)

    #frame_emotion_index = int(np.argmax(avg_frame_probs))


    person_emotions = []
    person_confidences = []

    for probs in emotion_preds:
        idx = np.argmax(probs)
        person_emotions.append(idx)
        person_confidences.append(probs[idx])

    frame_emotion_index = Counter(person_emotions).most_common(1)[0][0]
    frame_emotion = EMOTION_LABELS[frame_emotion_index]

    # confidence = average confidence of people voting for this emotion
    selected_conf = [
        person_confidences[i]
        for i in range(len(person_emotions))
        if person_emotions[i] == frame_emotion_index
    ]

    frame_emotion_conf = float(np.mean(selected_conf))

    avg_frame_probs = np.mean(emotion_preds, axis=0)

    suspicious_idx = EMOTION_LABELS.index("suspicious")
    avg_frame_probs[suspicious_idx] *= 0.6

    if np.sum(avg_frame_probs) > 0:
        avg_frame_probs = avg_frame_probs / np.sum(avg_frame_probs)

    dominant_emotion_buffer.append(avg_frame_probs)

    #emotion_votes.append(emotion_label)

    dominant_age_buffer.append(
        Counter(age_votes).most_common(1)[0][0]
    )
    dominant_gender_buffer.append(
        Counter(gender_votes).most_common(1)[0][0]
    )

    '''dominant_emotion_buffer.append(
        Counter(emotion_votes).most_common(1)[0][0]
    )'''

    global last_frame_log_time

    now = time.time()

    if now - last_frame_log_time >= FRAME_LOG_INTERVAL:

        # Take dominant of THIS FRAME only
        frame_age = Counter(age_votes).most_common(1)[0][0]
        frame_gender = Counter(gender_votes).most_common(1)[0][0]
        #frame_emotion = Counter(emotion_votes).most_common(1)[0][0]

        insert_perception_event(
            model="mass_frame_sample",
            session_id=session_id,
            person_id="crowd",
            age_group=frame_age,
            gender=frame_gender,
            emotion=frame_emotion,
            confidence_age_gender="frame_majority",
            confidence_emotion=f"avg_prob={frame_emotion_conf:.2f}",
            window_seconds=None,
            source="kiosk_01",
            channel="advertisement"
        )

        last_frame_log_time = now

    if DEBUG_EMOTION:
        print("[EMOTION BUFFER SIZE]", len(dominant_emotion_buffer))

    # -------------------------------
    # Engagement inference (MASS only)
    # -------------------------------
    global last_engagement_time

    now = time.time()
    should_run_engagement = len(faces_ag) > 0

    if should_run_engagement and (now - last_engagement_time) >= ENGAGEMENT_INTERVAL:
        try:
            eng_stats = engagement_service.process_frame(frame)

            latest_eng_stats["total_people"] = eng_stats.get("total_people", 0)
            latest_eng_stats["engaged_people"] = eng_stats.get("engaged_people", 0)
            latest_eng_stats["engagement_percentage"] = eng_stats.get("engagement_percentage", 0.0)

            engagement_pct = latest_eng_stats["engagement_percentage"]
            dominant_engagement_buffer.append(engagement_pct)

            last_engagement_time = now

            if DEBUG_ENGAGEMENT:
                print(
                    f"[ENG DEBUG] Total={eng_stats.get('total_people')} | "
                    f"Engaged={eng_stats.get('engaged_people')} | "
                    f"Pct={engagement_pct:.1f}%"
                )

        except Exception as e:
            print("[ENGAGEMENT] Failed:", e)
            dominant_engagement_buffer.append(0.0)
    else:
        # Maintain stability in smoothing
        if dominant_engagement_buffer:
            dominant_engagement_buffer.append(dominant_engagement_buffer[-1])
        else:
            dominant_engagement_buffer.append(0.0)

    # -------------------------------
    # Smoothing & Decision
    # -------------------------------
    now = time.time()

    if not window_committed:
        early = len(dominant_age_buffer) >= MIN_FRAMES_FOR_DECISION
        timed = (now - window_start_time) >= SMOOTH_WINDOW

        if early or timed:
            if dominant_age_buffer and dominant_emotion_buffer:
                final_age = Counter(dominant_age_buffer).most_common(1)[0][0]
                final_gender = Counter(dominant_gender_buffer).most_common(1)[0][0]
                #final_emotion = Counter(dominant_emotion_buffer).most_common(1)[0][0]
                #Temporal probability smoothing

                if dominant_emotion_buffer:
                    avg_window_probs = np.mean(dominant_emotion_buffer, axis=0)
                else:
                    avg_window_probs = np.zeros(len(EMOTION_LABELS))
                suspicious_idx = EMOTION_LABELS.index("suspicious")
                avg_window_probs[suspicious_idx] *= 0.6
                if np.sum(avg_window_probs) > 0:
                    avg_window_probs = avg_window_probs / np.sum(avg_window_probs)


                final_emotion_index = np.argmax(avg_window_probs)
                final_emotion = EMOTION_LABELS[final_emotion_index]
                emotion_confidence = float(np.max(avg_window_probs))

                print("[SMOOTHED EMOTION PROBS]", avg_window_probs)
                print("[FINAL EMOTION]", final_emotion, "confidence:", emotion_confidence)
                total_people = latest_eng_stats["total_people"]
                engaged_people = latest_eng_stats["engaged_people"]
                #final_engagement = latest_eng_stats["engagement_percentage"]
                if dominant_engagement_buffer:
                    final_engagement = np.mean(dominant_engagement_buffer)
                else:
                    final_engagement = latest_eng_stats["engagement_percentage"]
                #TEMP TEST MODE
                #final_engagement = 10
                
                if DEBUG_ENGAGEMENT:
                    print(
                        f"[ENG WINDOW] Avg Engagement={final_engagement:.2f}% | "
                        f"Samples={len(dominant_engagement_buffer)}"
                    )
                current_mass_ad["engagement_pct"] = final_engagement

                colombo = timezone("Asia/Colombo")
                current_hour = datetime.now(colombo).hour

                is_night = current_hour >= 19 or current_hour < 6

                '''# 🔥 DEBUG MODE
                TEST_FORCE_FEAR = True
                TEST_FORCE_NIGHT = True

                if TEST_FORCE_FEAR:
                    final_emotion = "fear"
                    emotion_confidence = 0.95   # ensure threshold passes

                if TEST_FORCE_NIGHT:
                    is_night = True

                print(f"[EMOTION FINAL] Dominant emotion for window: {final_emotion}")'''

                trigger_condition = False

                if final_emotion == "suspicious" and emotion_confidence >= SUSPICIOUS_ALERT_THRESHOLD:
                    trigger_condition = True

                elif final_emotion == "fear" and is_night and emotion_confidence >= FEAR_ALERT_THRESHOLD:
                    trigger_condition = True

                # Consecutive tracking
                if trigger_condition:
                    if last_emotion == final_emotion:
                        consecutive_counter += 1
                    else:
                        consecutive_counter = 1
                else:
                    consecutive_counter = 0

                last_emotion = final_emotion

                alert_triggered = consecutive_counter >= 2

                print("[ALERT DEBUG]",
                "trigger_condition=", trigger_condition,
                "consecutive_counter=", consecutive_counter,
                "alert_triggered=", alert_triggered)

                # Engagement bucket (simple)
                if final_engagement < 30:
                    force_change = True   # low engagement → refresh more
                else:
                    force_change = False  # medium/high → keep stable

                '''recommendation = ad_engine.recommend(
                    age=final_age,
                    gender=final_gender,
                    mode="mass",
                    emotion=final_emotion,
                    engagement_pct=final_engagement
                )'''

                if trigger_condition:
                    recommendation = {"action": "alert"}
                else:
                    recommendation = engine_loader.ad_engine.recommend(
                        age=final_age,
                        gender=final_gender,
                        mode="mass",
                        emotion=final_emotion,
                        engagement_pct=final_engagement
                )
                
                selected_pid = None
                selected_source = "primary"
                current_mass_ad["ad_source"] = "primary"
                current_mass_ad["detected_object"] = None
                ad_base64 = None

                # -------------------------
                # SECURITY CHECK
                # -------------------------
                if recommendation["action"] == "alert":
                    alert_triggered = True
                    current_ad = None
                    current_ad_pid = None

                # -------------------------
                # PRIMARY RECOMMENDATION
                # -------------------------
                elif recommendation["action"] == "recommend":

                    primary_pid = recommendation["pid"]
                    selected_pid = primary_pid

                    print("[PRIMARY]", primary_pid)

                    current_time = time.time()

                    if DEBUG_NOVELTY:
                        print("----- NOVELTY CHECK -----")
                        print("Engagement:", final_engagement)
                        print("Novelty Enabled:", NOVELTY_ENABLED)
                        print("Time Since Last Scan:", current_time - last_novelty_scan_time)
                        print("--------------------------")

                    # -------------------------
                    # SAFE NOVELTY CHECK
                    # -------------------------

                    if DEBUG_ENGAGEMENT:
                        print(
                            f"[ENGAGEMENT CHECK] "
                            f"Engagement={final_engagement:.1f}% | "
                            f"Threshold={NOVELTY_ENGAGEMENT_THRESHOLD} | "
                            f"BelowThreshold={final_engagement < NOVELTY_ENGAGEMENT_THRESHOLD}"
                        )

                    if (
                        NOVELTY_ENABLED
                        and final_engagement < NOVELTY_ENGAGEMENT_THRESHOLD
                        and (current_time - last_novelty_scan_time) > NOVELTY_SCAN_INTERVAL
                    ):
                        last_novelty_scan_time = current_time
                        try:
                            print("[NOVELTY] Attempting contextual scan")

                            if DEBUG_OBJECT_RECOMMENDATION:

                                novelty_ad = test_object_recommendation(
                                    frame,
                                    final_age,
                                    final_gender,
                                    recommendation["target_mood"],
                                    primary_pid
                                )

                                if novelty_ad and novelty_ad.get("pid"):
                                    selected_pid = novelty_ad["pid"]
                                    selected_source = "novelty"

                                    current_mass_ad["ad_source"] = "novelty"
                                    current_mass_ad["detected_object"] = novelty_ad.get("detected_object")

                                    print("[NOVELTY SUCCESS]")

                            else:

                                detections = yolo_detector.get_all_detections(frame)

                                if detections:
                                    detected_object = detections[0]["object"]

                                    novelty_ad = engine_loader.novelty_engine.get_object_novelty_ad(
                                        detected_object=detected_object,
                                        #age=final_age,
                                        #gender=final_gender,
                                        #mood=recommendation["target_mood"],
                                        avoid_pid=primary_pid
                                    )

                                if novelty_ad and novelty_ad.get("pid"):
                                    selected_pid = novelty_ad["pid"]
                                    selected_source = "novelty"
                                    print("[NOVELTY SUCCESS]")
                                    print("Detected Object:", detected_object)
                                    print("Primary PID:", primary_pid)
                                    print("Novelty PID:", selected_pid)

                        except Exception as e:
                            print("[NOVELTY ERROR]", e)
                            selected_pid = primary_pid
                            selected_source = "primary"

                    # -------------------------
                    # LOAD SELECTED AD
                    # -------------------------
                    if selected_pid != current_ad_pid:

                        ad_path = None
                        for ext in [".jpg", ".png", ".jpeg", ".webp"]:
                            path = os.path.join(AD_BASE, selected_pid + ext)
                            if os.path.exists(path):
                                ad_path = path
                                break

                        if ad_path:
                            current_ad = cv2.imread(ad_path)
                            current_ad_pid = selected_pid
                        else:
                            current_ad = None
                            current_ad_pid = None

                    if current_ad is not None:
                        _, buffer = cv2.imencode(".jpg", current_ad)
                        ad_base64 = (
                            "data:image/jpeg;base64,"
                            + base64.b64encode(buffer).decode()
                        )

                else:
                    current_ad = None
                    current_ad_pid = None

                if DEBUG_SYSTEM:
                    print(f"[AD SELECTED] {selected_pid} | Source: {selected_source}")
                    
                current_mass_ad["emotion"] = final_emotion
                current_mass_ad["age_group"] = final_age
                current_mass_ad["gender"] = final_gender
                current_mass_ad["ad_image_base64"] = ad_base64
                current_mass_ad["updated_at"] = datetime.utcnow()

                if DEBUG_SYSTEM:
                    print(f"[STATE] Age:{final_age} Gender:{final_gender} "
                        f"Emotion:{final_emotion} Engagement:{round(final_engagement,1)}%")

                insert_mass_window_event(
                    session_id=session_id,
                    age_group=final_age,
                    gender=final_gender,
                    emotion=final_emotion,
                    ad_id=selected_pid if recommendation["action"] == "recommend" else None,
                    window_seconds=SMOOTH_WINDOW,
                    source="kiosk_01",
                    is_security_alert=alert_triggered,
                    alert_reason=final_emotion if alert_triggered else None,
                    total_people=total_people,
                    engaged_people=engaged_people,
                    engagement_percentage=final_engagement,
                    ad_source=selected_source,
                    emotion_confidence=emotion_confidence
                )

                print("[MASS] Crowd event committed")

                window_committed = True

    if (now - window_start_time) >= SMOOTH_WINDOW:
        dominant_age_buffer.clear()
        dominant_gender_buffer.clear()
        dominant_emotion_buffer.clear()
        dominant_engagement_buffer.clear()
        window_start_time = now
        window_committed = False

print("[INFO] Program closed.")
