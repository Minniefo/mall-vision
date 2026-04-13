#main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import cv2
import numpy as np
import tensorflow as tf
from mtcnn import MTCNN
import base64
import os
import random
from db import upsert_age_gender_event
from db import ensure_indexes
from db import visitors_collection
from system_state import current_mode, current_session_id, Mode
import uuid
from mass_state import current_mass_ad
from mass_audience_inference import run_mass_inference
from db import identity_events
from analytics_api import router as analytics_router
from config import CURRENT_METHOD
from typing import Optional
from services.anomaly_service import AnomalyService
import threading
from fastapi import UploadFile, File, Form
from pathlib import Path
import pandas as pd
import shutil
from services.classifier import AdClassifier
from db import ads_collection

# 🔹 Returning customer imports
from face_embedder import FaceEmbedder
from privacy import anonymize_embedding
from similarity import find_match_with_decision, update_visitor, create_visitor


from bson.objectid import ObjectId
from datetime import datetime

from services.mappings import AGE_MAP
from db import anomaly_events
from quality import compute_quality_score
from datetime import datetime, timezone
import services.engine_loader as engine_loader
from services.filters import apply_flower_crown


classifier = AdClassifier("model")
classifier.load_model()


# ====================================================
# FastAPI App + CORS
# ====================================================
app = FastAPI()
from fastapi.staticfiles import StaticFiles

app.mount("/ads", StaticFiles(directory="Advertisements"), name="ads")
'''@app.on_event("startup")
def startup_event():
    ensure_indexes()
'''
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173"
    ],   # change to frontend URL later
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(analytics_router)

print("CORS Enabled!")

@app.get("/current_mass_ad")
def get_current_mass_ad():
    return {
        "age_group": current_mass_ad.get("age_group"),
        "gender": current_mass_ad.get("gender"),
        "ad_image": current_mass_ad.get("ad_image_base64"),
        "ad_type": current_mass_ad.get("ad_type"),          
        "media_url": current_mass_ad.get("media_url"), 
        "updated_at": current_mass_ad.get("updated_at"),
        "emotion": current_mass_ad.get("emotion"),
        "engagement_pct": current_mass_ad.get("engagement_pct"),
        "ad_source": current_mass_ad.get("ad_source"),
        "detected_object": current_mass_ad.get("detected_object")
    }



# ====================================================
# Load Age + Gender Model
# ====================================================
from tensorflow.keras.layers import Layer

class DropBlock2D(Layer):
    def __init__(self, drop_prob=0.1, block_size=5, **kwargs):
        super().__init__(**kwargs)
        self.drop_prob = drop_prob
        self.block_size = block_size

    def call(self, x, training=False):
        return x  # no dropout during inference


model = tf.keras.models.load_model(
    "model_v3_safeAttention_fewshotMixed.keras",
    custom_objects={"DropBlock2D": DropBlock2D}
)

print("Age + Gender Model Loaded!")

age_map = ["1-12", "13-19", "20-35", "36+"]


# ====================================================
# Advertisement Helpers
# ====================================================
def get_ad_folder(age_label, gender_label):
    if age_label in ["1-12", "13-19"]:
        gender_folder = "boy" if gender_label == "male" else "girl"
    else:
        gender_folder = "man" if gender_label == "male" else "woman"

    return age_label, gender_folder


def load_random_ad(age_label, gender_label):
    base_path = "Advertisements"

    age_folder, gender_folder = get_ad_folder(age_label, gender_label)
    full_path = f"{base_path}/{age_folder}/{gender_folder}"

    if not os.path.isdir(full_path):
        return None

    files = os.listdir(full_path)
    if not files:
        return None

    chosen = random.choice(files)
    ad_path = os.path.join(full_path, chosen)
    return cv2.imread(ad_path)

def select_largest_face(faces):
    """
    Select the largest face (closest to camera).
    faces: list of detected face dicts
    """
    if not faces:
        return None

    largest = None
    largest_area = 0

    for face in faces:
        x, y, w, h = face["box"]   # MTCNN format

        area = w * h

        if area > largest_area:
            largest_area = area
            largest = face

    return largest


# ====================================================
# Face Detector + Embedder
# ====================================================
detector = MTCNN()
embedder = FaceEmbedder()

print("MTCNN Loaded!")
print("Face Embedder Loaded!")


# ====================================================
# Helper: Base64 → OpenCV Image
# ====================================================
def decode_base64_image(base64_str):
    try:
        header, data = base64_str.split(",")
        img_bytes = base64.b64decode(data)
        img_array = np.frombuffer(img_bytes, np.uint8)
        return cv2.imdecode(img_array, cv2.IMREAD_COLOR)
    except:
        return None


# ====================================================
# Session Storage (Per Game)
# ====================================================
predictions = {
    "genders": [],
    "ages": []
}

'''session_state = {
    "visitor_type": "unknown",     # unknown | new | probable | returning
    "visit_count": 0,
    "identity_locked": False,      # ✅ prevents flicker
    "probable_hits": 0,            # counts repeated probable
    "matched_visitor_id": None ,    # store matched visitor id if any
    "returning_popup_shown": False
}'''

session_state = {
    "visitor_type": "unknown",
    "visit_count": 0,
    "identity_locked": False,

    # decision counters
    "probable_hits": 0,
    "new_hits": 0,

    # embedding buffer
    "embedding_buffer": [],

    "matched_visitor_id": None,
    "returning_popup_shown": False,
    "days_since_last_visit": None,
    "similarity_debug": None,
}



# ====================================================
# Request Model
# ====================================================
class FrameInput(BaseModel):
    image: str  # base64 screenshot
    preview: bool = False
    capture: bool = False
    session_id: Optional[str] = None
    

# ====================================================
# Identity Precheck Function (ADD HERE)
# ====================================================
def process_identity_precheck(img, faces):
    print("\n🧠 ===============================")
    print("🧠 [PRECHECK START]")
    print("🧠 Current visitor_type:", session_state["visitor_type"])
    print("🧠 identity_locked:", session_state["identity_locked"])

    if session_state["identity_locked"]:
        print("[PRECHECK] Skipped – already locked")
        return

    print("[PRECHECK] Processing identity...")

    faces = sorted(faces, key=lambda f: f["box"][2] * f["box"][3], reverse=True)
    x, y, w, h = faces[0]["box"]

    '''if w < 80 or h < 80:
        print("[PRECHECK] Face too small — skipping")
        return'''
    
    MIN_FACE_SIZE = 40

    if w < MIN_FACE_SIZE or h < MIN_FACE_SIZE:
        print(f"[PRECHECK] Too small ({w}x{h}) — skipping")
        return {"status": "face too small"}

    elif w < 60:
        print(f"[PRECHECK] Borderline face ({w}x{h}) — continuing")

    H, W = img.shape[:2]
    pad = int(0.25 * max(w, h))

    x1 = max(0, x - pad)
    y1 = max(0, y - pad)
    x2 = min(W, x + w + pad)
    y2 = min(H, y + h + pad)

    landmarks = faces[0]["keypoints"]

    face_img = img[y1:y2, x1:x2]

    if face_img.size == 0:
        return {"status": "empty face"}

    left_eye = landmarks["left_eye"]
    right_eye = landmarks["right_eye"]

    landmarks_adj = {
        "left_eye": (left_eye[0] - x1, left_eye[1] - y1),
        "right_eye": (right_eye[0] - x1, right_eye[1] - y1)
    }

    face_img = embedder.align_face(face_img, landmarks_adj)

    face_img = cv2.cvtColor(face_img, cv2.COLOR_BGR2YCrCb)
    face_img[:,:,0] = cv2.equalizeHist(face_img[:,:,0])
    face_img = cv2.cvtColor(face_img, cv2.COLOR_YCrCb2BGR)

    emb = embedder.get_embedding(cv2.cvtColor(face_img, cv2.COLOR_BGR2RGB))

    if emb is None:
        print("[PRECHECK] Embedding extraction FAILED")
        return
    
    print("🧠 ✅ Embedding extracted")

    quality_score = compute_quality_score(face_img, (x, y, w, h), img.shape)
    print(f"🧠 Quality score: {quality_score:.3f}")


    result = find_match_with_decision(
        emb,
        quality_score
    )

    decision = result["decision"]
    score = result["score"]
    debug_info = result.get("debug")
    session_state["similarity_debug"] = debug_info

    # Store embeddings for averaging
    session_state["embedding_buffer"].append(emb)

    # Keep only last 3
    if len(session_state["embedding_buffer"]) > 3:
        session_state["embedding_buffer"].pop(0)

    print(f"[PRECHECK] Decision={decision} | Score={score:.3f}")

    visitor = result.get("visitor")

    if decision == "returning":

        last_seen = visitor.get("last_seen")
        days_since = calculate_days_since(last_seen)

        session_state["visitor_type"] = "returning"
        session_state["new_hits"] = 0
        session_state["returning_popup_shown"] = False
        session_state["visit_count"] = visitor["visit_count"] + 1
        session_state["matched_visitor_id"] = str(visitor["_id"])
        session_state["identity_locked"] = True
        session_state["probable_hits"] = 0
        session_state["days_since_last_visit"] = days_since
        session_state["similarity_debug"] = debug_info

        print("[PRECHECK] RETURNING detected")
    
    elif decision == "probable":

        session_state["probable_hits"] += 1
        print(f"[PRECHECK] PROBABLE ({session_state['probable_hits']})")

        if session_state["probable_hits"] >= 3 and visitor is not None:

            last_seen = visitor.get("last_seen")
            days_since = calculate_days_since(last_seen)

            session_state["visitor_type"] = "returning"
            session_state["new_hits"] = 0
            session_state["visit_count"] = visitor["visit_count"] + 1
            session_state["matched_visitor_id"] = str(visitor["_id"])
            session_state["identity_locked"] = True
            session_state["returning_popup_shown"] = False
            session_state["days_since_last_visit"] = days_since
            session_state["similarity_debug"] = debug_info

            print("[PRECHECK] RETURNING confirmed after probable frames")
    

    elif decision == "new":

        session_state["new_hits"] += 1
        print(f"[PRECHECK] NEW ({session_state['new_hits']})")

        if session_state["new_hits"] >= 3:

            # Average embeddings
            embeddings = np.array(session_state["embedding_buffer"])
            avg_embedding = np.mean(embeddings, axis=0)

            session_state["visitor_type"] = "new"
            session_state["pending_new_embedding"] = avg_embedding
            session_state["identity_locked"] = True

            session_state["probable_hits"] = 0
            session_state["new_hits"] = 0
            session_state["matched_visitor_id"] = None

            print("[PRECHECK] NEW confirmed after multiple frames")

def calculate_days_since(last_seen):

    if last_seen is None:
        return None

    # Convert naive datetime to UTC-aware
    if last_seen.tzinfo is None:
        last_seen = last_seen.replace(tzinfo=timezone.utc)

    now = datetime.now(timezone.utc)

    diff = now - last_seen

    return diff.days      

@app.post("/start_game")
def start_game():

    global current_mode, current_session_id

    predictions["genders"].clear()
    predictions["ages"].clear()

    current_session_id = str(uuid.uuid4())
    current_mode = Mode.INDIVIDUAL

    # ----------------------------------------
    # CASE 1: Returning detected in MASS
    # ----------------------------------------
    if session_state["visitor_type"] == "returning":

        visitor_id = session_state["matched_visitor_id"]

        # 🔥 Commit visit only when game actually starts
        visitors_collection.update_one(
            {"_id": ObjectId(visitor_id)},
            {
                "$inc": {"visit_count": 1},
                "$set": {"last_seen": datetime.utcnow()}
            }
        )

        print(f"[DB] Visit count incremented for visitor {visitor_id}")

        session_state["returning_popup_shown"] = False

    # ----------------------------------------
    # CASE 2: New visitor
    # ----------------------------------------
    elif session_state["visitor_type"] == "new":
        session_state["visit_count"] = 1
        session_state["identity_locked"] = True
        session_state["returning_popup_shown"] = False

    # 🔥 FALLBACK: If identity not ready, treat as new
    if session_state["visitor_type"] == "unknown":
        print("[START_GAME] Identity not ready → treating as new")

        session_state["visitor_type"] = "new"
        session_state["visit_count"] = 1    

    return {
        "session_id": current_session_id,
        "visitor_type": session_state["visitor_type"],
        "visit_count": session_state["visit_count"],
        "days_since_last_visit": session_state.get("days_since_last_visit"),
        "similarity_debug": session_state.get("similarity_debug"),
        "mode": "individual"
    }

# ====================================================
# Get current session state (for real-time returning popup)
# ====================================================
@app.get("/session_state")
def get_session_state():
    return {
        "visitor_type": session_state["visitor_type"],
        "visit_count": session_state["visit_count"],
        "identity_locked": session_state["identity_locked"],
        "matched_visitor_id": session_state["matched_visitor_id"],
        "returning_popup_shown": session_state["returning_popup_shown"],
        "days_since_last_visit": session_state.get("days_since_last_visit"),
        "similarity_debug": session_state.get("similarity_debug")
    }

anomaly_service = AnomalyService()

@app.on_event("startup")
def startup_services():

    print("🚀 Initializing engines...")

    engine_loader.init_engines()

    print("✅ Engines ready")

    t = threading.Thread(target=anomaly_service.loop_forever, daemon=True)
    t.start()
    
# ====================================================
# Upload Frame (Age & Gender ONLY)
# ====================================================
@app.post("/upload_frame")
def upload_frame(data: FrameInput):
    
    print(f"[STATE] visitor_type={session_state['visitor_type']} locked={session_state['identity_locked']} popup_shown={session_state['returning_popup_shown']} matched_id={session_state['matched_visitor_id']} probable_hits={session_state['probable_hits']}")

    print(f"\n[UPLOAD_FRAME] Mode={current_mode} | Locked={session_state['identity_locked']}")

    img = decode_base64_image(data.image)
    if img is None:
        return {"error": "Invalid image"}

    rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
    faces = detector.detect_faces(rgb)

    if data.preview:
        if faces:
            x, y, w, h = faces[0]["box"]
            img = apply_flower_crown(img, (x, y, w, h))

        _, buffer = cv2.imencode('.jpg', img)
        img_base64 = base64.b64encode(buffer).decode('utf-8')

        return {"image": img_base64}
    
    if data.capture:
        print("[CAPTURE] Capturing image")

        if faces:
            x, y, w, h = faces[0]["box"]
            img = apply_flower_crown(img, (x, y, w, h))

        _, buffer = cv2.imencode('.jpg', img)
        img_base64 = base64.b64encode(buffer).decode('utf-8')

        return {
            "status": "captured",
            "image": img_base64
        }

    # -------------------------------------
    # MASS MODE (Idle Precheck + Crowd Ads)
    # -------------------------------------
    if current_mode == Mode.MASS and not data.preview and not data.capture:

        print("[MODE] MASS – Running mass inference")
        print("[MASS] visitor_type:", session_state["visitor_type"])
        print("[MASS] identity_locked:", session_state["identity_locked"])

        run_mass_inference(img)

        if faces:
            print(f"[MASS] Faces detected: {len(faces)}")

            if not session_state["identity_locked"]:
                print("[MASS] Running identity precheck")
            else:
                print("[MASS] Identity already locked – skipping precheck")

            target_face = select_largest_face(faces)

            if target_face is not None:
                process_identity_precheck(img, [target_face])
        else:
            print("[MASS] No faces detected")

        return {"status": "mass"}

    # -------------------------------------
    # INDIVIDUAL MODE (Full Game Logic)
    # -------------------------------------
    print("[MODE] INDIVIDUAL – Processing game frame")
    if data.session_id != current_session_id:
        return {"status": "ignored"}

    if not faces:
        return {"status": "no face"}

    faces = sorted(faces, key=lambda f: f["box"][2] * f["box"][3], reverse=True)
    x, y, w, h = faces[0]["box"]

    print(f"[DEBUG] Face size: {w}x{h}")
    print(f"[DEBUG] Frame size: {img.shape}")
    '''if w < 50 or h < 50:
        print("[PRECHECK] Face too small — skipping")
        #return'''
    MIN_FACE_SIZE = 40

    if w < MIN_FACE_SIZE or h < MIN_FACE_SIZE:
        print(f"[PRECHECK] Too small ({w}x{h}) — skipping")
        return {"status": "face too small"}

    elif w < 60:
        print(f"[PRECHECK] Borderline face ({w}x{h}) — continuing")
    
    H, W = img.shape[:2]

    pad = int(0.25 * max(w, h))
    x1 = max(0, x - pad)
    y1 = max(0, y - pad)
    x2 = min(W, x + w + pad)
    y2 = min(H, y + h + pad)

    landmarks = faces[0]["keypoints"]

    face_img = img[y1:y2, x1:x2]

    #img = apply_flower_crown(img, (x, y, w, h))

    if face_img.size == 0:
        return {"status": "empty face"}
    
    left_eye = landmarks["left_eye"]
    right_eye = landmarks["right_eye"]

    landmarks_adj = {
        "left_eye": (left_eye[0] - x1, left_eye[1] - y1),
        "right_eye": (right_eye[0] - x1, right_eye[1] - y1)
    }

    face_img = embedder.align_face(face_img, landmarks_adj)

    '''# ----------------------------------
    # PHASE 4 – Identity decision (once per session)
    # ----------------------------------
    print("[MODE] INDIVIDUAL – Processing game frame")
    if not session_state["identity_locked"]:

        face_img = cv2.cvtColor(face_img, cv2.COLOR_BGR2YCrCb)
        face_img[:,:,0] = cv2.equalizeHist(face_img[:,:,0])
        face_img = cv2.cvtColor(face_img, cv2.COLOR_YCrCb2BGR)
        
        emb = embedder.get_embedding(cv2.cvtColor(face_img, cv2.COLOR_BGR2RGB))

        if emb is None:
            print("[IDENTITY] Embedding extraction FAILED")
        else:
            print("[IDENTITY] Embedding extracted OK", emb.shape)

        if emb is not None:
            quality_score = compute_quality_score(face_img, (x, y, w, h), img.shape)
            result = find_match_with_decision(emb, quality_score)

            decision = result["decision"]
            score = result["score"]
            visitor = result.get("visitor")

            print(f"[IDENTITY] Decision={decision} | Score={score:.3f}")

            # ----------------------------
            # RETURNING
            # ----------------------------
            if decision == "returning":

                last_seen = visitor.get("last_seen")
                days_since = calculate_days_since(last_seen)

                session_state["visitor_type"] = "returning"
                session_state["returning_popup_shown"] = False
                session_state["visit_count"] = visitor["visit_count"] + 1
                session_state["matched_visitor_id"] = str(visitor["_id"])
                session_state["identity_locked"] = True
                session_state["probable_hits"] = 0
                session_state["new_hits"] = 0
                session_state["days_since_last_visit"] = days_since
                

                update_visitor(visitor, emb, quality_score, mode="individual")

                identity_events.insert_one({
                    "visitor_id": visitor["_id"],
                    "session_id": current_session_id,
                    "decision": "returning",
                    "method": CURRENT_METHOD,             # <--- add
                    "true_label": session_state.get("true_label", None),  # <--- add
                    "similarity_score": score,
                    "quality_score": quality_score,
                    "mode": "individual",
                    "camera_id": "kiosk_01",
                    "zone": "near",
                    "timestamp": datetime.utcnow()
                })

                print(f"[IDENTITY] LOCKED RETURNING id={visitor['_id']} score={score:.3f}")

            # ----------------------------
            # NEW
            # ----------------------------
            elif decision == "new":
                session_state["visitor_type"] = "new"
                session_state["visit_count"] = 1
                session_state["identity_locked"] = True
                session_state["pending_new_embedding"] = emb

                identity_events.insert_one({
                    "visitor_id": None,
                    "session_id": current_session_id,
                    "decision": "new",
                    "method": CURRENT_METHOD,             # <--- add
                    "true_label": session_state.get("true_label", None),  # <--- add
                    "similarity_score": score,
                    "quality_score": quality_score,
                    "mode": "individual",
                    "camera_id": "kiosk_01",
                    "zone": "near",
                    "timestamp": datetime.utcnow()
                })

                print(f"[IDENTITY] LOCKED NEW score={score:.3f}")

            # ----------------------------
            # PROBABLE
            # ----------------------------
            else:
                session_state["probable_hits"] += 1
                print(f"[IDENTITY] PROBABLE ({session_state['probable_hits']}) score={score:.3f}")

                if session_state["probable_hits"] >= 3 and visitor is not None:
                    last_seen = visitor.get("last_seen")
                    days_since = calculate_days_since(last_seen)
                    session_state["days_since_last_visit"] = days_since
                    session_state["visitor_type"] = "returning"
                    if visitor:
                        session_state["visit_count"] = visitor["visit_count"] + 1
                    session_state["matched_visitor_id"] = str(visitor["_id"])
                    session_state["identity_locked"] = True
                    session_state["days_since_last_visit"] = days_since

                    update_visitor(visitor, emb, quality_score, mode="individual")

                    identity_events.insert_one({
                        "visitor_id": visitor["_id"],
                        "session_id": current_session_id,
                        "decision": "returning_after_probable",
                        "similarity_score": score,
                        "quality_score": quality_score,
                        "mode": "individual",
                        "camera_id": "kiosk_01",
                        "zone": "near",
                        "timestamp": datetime.utcnow()
                    })'''

    face_resized = cv2.resize(face_img, (128, 128))
    face_resized = face_resized.astype("float32") / 255.0
    face_resized = np.expand_dims(face_resized, axis=0)

    gender_pred, age_pred = model.predict(face_resized, verbose=0)

    gender = "female" if gender_pred[0][0] > 0.5 else "male"
    age = age_map[np.argmax(age_pred)]

    predictions["genders"].append(gender)
    predictions["ages"].append(age)

    if data.preview or getattr(data, "capture", False):
        if faces:
            x, y, w, h = faces[0]["box"]
            img = apply_flower_crown(img, (x, y, w, h))

    _, buffer = cv2.imencode('.jpg', img)
    img_base64 = base64.b64encode(buffer).decode('utf-8')

    return {
        "status": "ok",
        "image": img_base64
    }

@app.post("/acknowledge_returning")
def acknowledge_returning():
    session_state["returning_popup_shown"] = True
    return {"status": "acknowledged"}

'''@app.post("/mass_frame")
def receive_mass_frame(data: FrameInput):
    img = decode_base64_image(data.image)
    if img is None:
        return {"status": "invalid image"}

    run_mass_inference(img)

    return {"status": "mass frame processed"}
'''
@app.post("/mass_frame")
def receive_mass_frame(data: FrameInput):
    img = decode_base64_image(data.image)
    if img is None:
        return {"status": "invalid image"}

    rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
    faces = detector.detect_faces(rgb)

    run_mass_inference(img)

    print("[MASS_FRAME] Faces:", len(faces))

    if faces:
        target_face = select_largest_face(faces)

        if target_face is not None:
            print("[MASS_FRAME] Running identity precheck")
            process_identity_precheck(img, [target_face])
    else:
        print("[MASS_FRAME] No faces detected")

    return {"status": "mass frame processed"}

# ====================================================
# Final Prediction + Ad
# ====================================================
@app.get("/final_prediction")
def final_prediction():
    print("\n[FINAL] Calculating final prediction")
    print(f"[FINAL] Visitor type before reset: {session_state['visitor_type']}")
    global current_mode, current_session_id

    if not predictions["ages"]:
        return {
            "age_group": None,
            "gender": None,
            "visitor_type": session_state["visitor_type"],
            "visit_count": session_state["visit_count"],
            "advertisement_image": None
        }

    final_gender = max(set(predictions["genders"]), key=predictions["genders"].count)
    final_age = max(set(predictions["ages"]), key=predictions["ages"].count)

    # If session locked as NEW, commit the new visitor now with final demographics
    if session_state["visitor_type"] == "new":
        emb = session_state.get("pending_new_embedding")
        if emb is not None:
            create_visitor(emb, final_age, final_gender)
            print("[IDENTITY] New visitor committed to DB")


    # ----------------------------------
    # Recommendation Engine (Individual Mode)
    # ----------------------------------

    # Map perception age to dataset age
    mapped_age = AGE_MAP.get(final_age, final_age)

    target_values = {
        "target_age_group": mapped_age,
        "target_gender": final_gender.lower(),   # ensure lowercase
        "target_mood": "neutral"                 # individual mode → neutral
    }

    print("[RECOMMENDATION INPUT]", target_values)

    best_ad = engine_loader.ad_engine.recommend(
        age=final_age,
        gender=final_gender.lower(),
        mode="individual"
    )

    ad_img = None
    ad_base64 = None

    if best_ad and best_ad.get("action") == "recommend":
        pid = best_ad.get("pid")

        print(f"[AD CONTROL] Loading image for PID: {pid}")

        #ad_img = load_ad_by_pid(pid)
        ad_img = None
        ad_base64 = None
        ad_type = None
        media_url = None

        if best_ad and best_ad.get("action") == "recommend":
            pid = best_ad.get("pid")

            # 🔥 GET FULL AD FROM DB
            ad_doc = ads_collection.find_one({"pid": pid})

            if ad_doc:
                ad_type = ad_doc.get("ad_type", "image")
                media_url = ad_doc.get("media_url")

                if ad_type == "image":
                    ad_img = load_ad_by_pid(pid)

                    if ad_img is not None:
                        _, buffer = cv2.imencode(".jpg", ad_img)
                        ad_base64 = "data:image/jpeg;base64," + base64.b64encode(buffer).decode()

    predictions["genders"].clear()
    predictions["ages"].clear()

    visitor_type = session_state["visitor_type"]
    visit_count = session_state["visit_count"]

    current_mode = Mode.MASS
    current_session_id = None

    session_state["identity_locked"] = False
    session_state["visitor_type"] = "unknown"
    session_state["visit_count"] = 0
    session_state["matched_visitor_id"] = None
    session_state["returning_popup_shown"] = False
    session_state["probable_hits"] = 0
    session_state["days_since_last_visit"] = None
    session_state.pop("pending_new_embedding", None)
    session_state["embedding_buffer"] = []
    session_state["new_hits"] = 0
    session_state["similarity_debug"] = None

    print("[MODE] Switched back to MASS")

    return {
        "age_group": final_age,
        "gender": final_gender,
        "visitor_type": visitor_type,
        "visit_count": visit_count,
        "ad_type": ad_type,             
        "media_url": media_url, 
        "advertisement_image": ad_base64
    }

def load_ad_by_pid(pid):
    base_path = "Advertisements"

    # Try common formats
    for ext in [".jpg", ".png", ".jpeg", ".webp"]:
        path = os.path.join(base_path, pid + ext)
        if os.path.exists(path):
            return cv2.imread(path)

    print(f"[AD ERROR] Image not found for PID: {pid}")
    return None

@app.post("/admin/add-ad")
async def add_ad(
    ad_title: str = Form(...),
    ad_description: str = Form(""),
    file: UploadFile = File(...)
):
    try:

        # Generate PID
        pid = uuid.uuid4().hex[:8].upper()

        # Classify ad
        prediction = classifier.predict(ad_title)
        if prediction is None:
            return {"success": False, "message": "Classification failed"}

        age = prediction["target_age_group"]
        gender = prediction["target_gender"].capitalize()
        mood = prediction["target_mood"].lower()
        weather = prediction.get("target_weather", "sunny").lower()

        if age == "65+":
            age = "65 plus"

        # Save image
        ad_folder = Path("Advertisements")
        ad_folder.mkdir(exist_ok=True)

        #image_path = ad_folder / f"{pid}.jpg"
        file_ext = file.filename.split(".")[-1].lower()

        file_path = ad_folder / f"{pid}.{file_ext}"

        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        # Auto-generate tags
        auto_tags = ad_title.lower().replace(" ", ", ")
        file_ext = file.filename.split(".")[-1].lower()

        if file_ext in ["mp4", "webm"]:
            ad_type = "video"
        else:
            ad_type = "image"

        new_row = {
            "pid": pid,
            "ad_title": ad_title,
            "ad_description": ad_description,
            "target_age_group": age,
            "target_gender": gender,
            "target_mood": mood,
            "target_weather": weather,
            "ad_type": ad_type,                        
            "media_url": f"/ads/{pid}.{file_ext}",
            "tags": auto_tags
        }

        # Insert into MongoDB
        ads_collection.insert_one(new_row)

        # Reload ads in recommendation engine
        engine_loader.ad_engine.load_ads_database()

        return {
            "success": True,
            "pid": pid,
            "classified_as": {
                "age": age,
                "gender": gender,
                "mood": mood,
                "weather": weather
            }
        }

    except Exception as e:
        return {"success": False, "message": str(e)}
    

# ====================================================
# Get Behaviour Anomaly Alerts
# ====================================================

from datetime import datetime, timedelta

@app.get("/analytics/anomaly-alerts")
def get_anomaly_alerts():

    now = datetime.utcnow()
    window_start = now - timedelta(seconds=30)

    events = list(
        anomaly_events.find({
            "timestamp": {"$gte": window_start}
        }).sort("timestamp", -1)
    )

    result = []

    for e in events:
        result.append({
            "track_id": e.get("track_id"),
            "anomaly_type": e.get("anomaly_type"),
            "metric_value": e.get("metric_value"),
            "timestamp": e["timestamp"].isoformat() + "Z"
        })

    return result