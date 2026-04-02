#db.py
from pymongo import MongoClient
from config import MONGO_URI, DB_NAME, COLLECTION_NAME
from datetime import datetime
import certifi

# -------------------------------
# MongoDB connection
# -------------------------------
#client = MongoClient(MONGO_URI)
client = MongoClient(
    MONGO_URI,
    tlsCAFile=certifi.where()
)
db = client[DB_NAME]

visitors_collection = db[COLLECTION_NAME]
perception_collection = db["perception_events"]
identity_events = db["identity_events"]
engagement_logs = db["engagement_logs"]
anomaly_events = db["anomaly_events"]
ads_collection = db["ads_catalog"]

# ===================================================
# LEGACY: Individual Age-Gender (keep if already used)
# ===================================================
def upsert_age_gender_event(
    session_id,
    person_id,
    age_group,
    gender,
    confidence
):
    """
    Legacy helper for individual age-gender updates.
    Prefer insert_perception_event() for new code.
    """
    perception_collection.update_one(
        {
            "session_id": session_id,
            "person_id": person_id,
            "model": "age_gender"
        },
        {
            "$set": {
                "model": "age_gender",
                "timestamp": datetime.utcnow(),

                "age_group": age_group,
                "gender": gender,
                "emotion": None,
                "behaviour": None,

                "confidence": {
                    "age_gender": confidence,
                    "emotion": None,
                    "behaviour": None
                },

                "channel": "advertisement",
                "window_seconds": None,
                "source": "kiosk_01"
            }
        },
        upsert=True
    )


# ===================================================
# NEW: Unified perception event insert (RECOMMENDED)
# ===================================================
def insert_perception_event(
    model,
    session_id,
    person_id,
    age_group=None,
    gender=None,
    emotion=None,
    behaviour=None,
    confidence_age_gender=None,
    confidence_emotion=None,
    confidence_behaviour=None,
    channel="advertisement",
    window_seconds=None,
    source="kiosk_01"
):
    """
    Insert a single perception event.
    Used by age-gender, emotion, behaviour models.
    Works for individual AND crowd.
    """

    perception_collection.insert_one({
        "model": model,
        "session_id": session_id,
        "person_id": person_id,
        "timestamp": datetime.utcnow(),

        "age_group": age_group,
        "gender": gender,
        "emotion": emotion,
        "behaviour": behaviour,

        "confidence": {
            "age_gender": confidence_age_gender,
            "emotion": confidence_emotion,
            "behaviour": confidence_behaviour
        },

        "channel": channel,
        "window_seconds": window_seconds,
        "source": source
    })


# ===================================================
# Convenience wrapper: Mass audience age-gender
# ===================================================
def insert_mass_age_gender_event(
    session_id,
    age_group,
    gender,
    window_seconds,
    source="kiosk_01",
    channel="advertisement"
):
    """
    Insert smoothed mass-audience age-gender perception.
    """

    insert_perception_event(
        model="age_gender",
        session_id=session_id,
        person_id="crowd",

        age_group=age_group,
        gender=gender,
        emotion=None,
        behaviour=None,

        confidence_age_gender="aggregate_majority",
        confidence_emotion=None,
        confidence_behaviour=None,

        channel=channel,
        window_seconds=window_seconds,
        source=source
    )

# ===================================================
# NEW: Mass audience window event (age + gender + emotion + ad)
# ===================================================
def insert_mass_window_event(
    session_id,
    age_group,
    gender,
    emotion,
    ad_id=None,
    window_seconds=None,
    source="kiosk_01",
    is_security_alert=False,
    alert_reason=None,
    emotion_confidence=None,
    total_people = 0,
    engaged_people=0,
    engagement_percentage=0.0,
    ad_source=None
):
    """
    Insert ONE committed mass-audience decision per smoothing window.
    Includes security alert flag if triggered.
    """

    perception_collection.insert_one({
        "model": "mass_window",
        "session_id": session_id,
        "person_id": "crowd",
        "timestamp": datetime.utcnow(),

        "age_group": age_group,
        "gender": gender,
        "emotion": emotion,

        "ad_id": ad_id,
        "ad_source": ad_source,

        "window_seconds": window_seconds,
        "source": source,

        # 🔥 Security fields
        "is_security_alert": is_security_alert,
        "alert_reason": alert_reason,
        "emotion_confidence": emotion_confidence,

        "total_people": total_people,
        "engaged_people": engaged_people,
        "engagement_percentage": engagement_percentage,

        # Optional classification channel
        "channel": "security" if is_security_alert else "advertisement"
    })

# ===================================================
# Indexes (IMPORTANT)
# ===================================================
def ensure_indexes():
    """
    Create NON-UNIQUE indexes suitable for event data.
    """

    # -------------------------------
    # Identity memory (visitors)
    # -------------------------------
    visitors_collection.create_index("last_seen")
    visitors_collection.create_index("visit_count")

    # -------------------------------
    # Perception events (age, gender, emotion, etc.)
    # -------------------------------
    perception_collection.create_index([
        ("session_id", 1),
        ("person_id", 1),
        ("model", 1),
        ("timestamp", -1)
    ])

    # -------------------------------
    # Identity analytics (Phase 5)
    # -------------------------------
    identity_events.create_index("visitor_id")
    identity_events.create_index("decision")
    identity_events.create_index("timestamp")
    identity_events.create_index("camera_id")
    identity_events.create_index([("camera_id", 1), ("timestamp", -1)])

