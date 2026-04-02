from pymongo import MongoClient, ASCENDING
from pymongo.errors import PyMongoError
from datetime import datetime


class MongoEmotionRouter:
    """
    Routes aggregated 10-second emotion outputs into MongoDB.

    - Keeps existing collections unchanged
    - Adds standardized output for multi-model integration
    """

    def __init__(
        self,
        mongo_uri="mongodb://localhost:27017",
        db_name="emotion_system",
        ads_collection="advertisement_emotions",
        security_collection="security_events",
        integration_collection="detections_raw",
        source_id="kiosk_01"
    ):
        self.client = MongoClient(mongo_uri)
        self.db = self.client[db_name]

        self.ads_col = self.db[ads_collection]
        self.sec_col = self.db[security_collection]
        self.int_col = self.db[integration_collection]

        self.source_id = source_id
        self._ensure_indexes()

    
    # Index creation (idempotent)
    
    def _ensure_indexes(self):
        # Advertisement queries
        self.ads_col.create_index([("timestamp", ASCENDING)])
        self.ads_col.create_index([("dominant_emotion", ASCENDING)])

        # Security workflows
        self.sec_col.create_index([("timestamp", ASCENDING)])
        self.sec_col.create_index([("trigger_emotion", ASCENDING)])
        self.sec_col.create_index([("handled", ASCENDING)])

        # Integration / fusion queries
        self.int_col.create_index([("timestamp", ASCENDING)])
        self.int_col.create_index([("session_id", ASCENDING)])
        self.int_col.create_index([("person_id", ASCENDING)])
        self.int_col.create_index([("model", ASCENDING)])

    
    # Routing logic (single entry point)
    
    def route(
        self,
        aggregated_payload: dict,
        session_id: str,
        person_id: str = "crowd"
    ):
        """
        Routes ONE aggregated 10-second payload into MongoDB.

        This method:
        1) Writes to existing collections (ads / security)
        2) ALSO writes standardized integration output

        aggregated_payload must contain:
        - dominant_emotion
        - counts
        - window_seconds
        - timestamp (optional)
        """

        dominant = aggregated_payload["dominant_emotion"]

        timestamp = aggregated_payload.get(
            "timestamp",
            datetime.utcnow()
        )

        base_doc = {
            "timestamp": timestamp,
            "window_seconds": aggregated_payload["window_seconds"],
            "emotion_counts": aggregated_payload["counts"],
            "source": self.source_id
        }

        try:
            
            # SECURITY EVENT 
            
            if dominant in ["fear", "suspicious"]:
                sec_doc = {
                    **base_doc,
                    "trigger_emotion": dominant,
                    "severity": "high",
                    "status": "triggered",
                    "handled": False
                }
                self.sec_col.insert_one(sec_doc)

            
            # ADVERTISEMENT EMOTION 
            
            else:
                ads_doc = {
                    **base_doc,
                    "dominant_emotion": dominant,
                    "confidence": "aggregate_majority"
                }
                self.ads_col.insert_one(ads_doc)

            
            # INTEGRATION OUTPUT 
            
            integration_doc = {
                "model": "emotion",

                "session_id": session_id,
                "person_id": person_id,
                "timestamp": timestamp,

                "age_group": None,
                "gender": None,
                "emotion": dominant,
                "behaviour": None,

                "confidence": {
                    "age_gender": None,
                    "emotion": "aggregate_majority",
                    "behaviour": None
                },

                "channel": (
                    "security"
                    if dominant in ["fear", "suspicious"]
                    else "advertisement"
                ),

                "window_seconds": aggregated_payload["window_seconds"],
                "source": self.source_id
            }

            self.int_col.insert_one(integration_doc)

        except PyMongoError as e:
            # Never crash real-time system
            print("[MongoRouter] MongoDB write failed:", str(e))
