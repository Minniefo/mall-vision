#anomaly_service.py
import time
from datetime import datetime, timedelta
from collections import defaultdict
from db import engagement_logs, anomaly_events
from config import MONGO_URI, DB_NAME
from mass_state import current_security_alert

class AnomalyService:
    def __init__(
        self,
        #scan_interval=1,
        #active_window=3,
        #alert_cooldown=60,
        #confirm_frames=30,
        #run_speed_th=50.0,
        #loiter_time_th=30.0,
        #look_ratio_th=0.9,

        #demo/testing params
        scan_interval = 1,
        active_window = 2,
        alert_cooldown = 10,
        confirm_frames = 5,
        run_speed_th = 15.0,
        loiter_time_th = 8.0,
        look_ratio_th = 0.7
       
    ):
        self.scan_interval = scan_interval
        self.active_window = active_window
        self.alert_cooldown = alert_cooldown
        self.confirm_frames = confirm_frames

        self.run_speed_th = run_speed_th
        self.loiter_time_th = loiter_time_th
        self.look_ratio_th = look_ratio_th

        self.recent_alerts = {}
        self.violation_counter = defaultdict(int)

        self.running = False

    def can_trigger(self, key):
        now = datetime.utcnow()
        last = self.recent_alerts.get(key)
        if last is None or (now - last).total_seconds() > max(self.alert_cooldown, 5):
            self.recent_alerts[key] = now
            return True
        return False

    def run_once(self):
        try:
            self.step()
        except Exception as e:
            print("❌ Anomaly error:", e)

    '''def log_anomaly(self, track_id, anomaly_type, metric, threshold):
        confirm_key = f"{track_id}_{anomaly_type}"
        self.violation_counter[confirm_key] += 1

        if self.violation_counter[confirm_key] < self.confirm_frames:
            return

        self.violation_counter[confirm_key] = 0    

        if not self.can_trigger(confirm_key):
            return

        doc = {
            "track_id": track_id,
            "anomaly_type": anomaly_type,
            "metric_value": metric,
            "threshold": threshold,
            "timestamp": datetime.utcnow()
        }

        # 🔥 HARD DEDUPE: prevent same anomaly spam
        existing = anomaly_events.find_one({
            "track_id": track_id,
            "anomaly_type": anomaly_type,
            "timestamp": {
                "$gte": datetime.utcnow() - timedelta(seconds=5)
            }
        })

        if existing:
            return

        anomaly_events.insert_one(doc)

        # Update shared state for frontend/backend use
        current_security_alert.update({
            "active": True,
            "type": anomaly_type,
            "track_id": track_id,
            "metric_value": metric,
            "threshold": threshold,
            "updated_at": doc["timestamp"]
        })

        print(f"🚨 ANOMALY ALERT | ID={track_id} | {anomaly_type} | {metric:.2f} > {threshold}")'''

    def log_anomaly(self, track_id, anomaly_type, metric, threshold):

        confirm_key = f"{track_id}_{anomaly_type}"
        self.violation_counter[confirm_key] += 1

        # -----------------------------
        # Frame confirmation logic
        # -----------------------------
        if self.violation_counter[confirm_key] < self.confirm_frames:
            return

        # -----------------------------
        # 🔥 HARD DEDUPE (FIRST)
        # -----------------------------
        existing = anomaly_events.find_one({
            "track_id": track_id,
            "anomaly_type": anomaly_type,
            "timestamp": {
                "$gte": datetime.utcnow() - timedelta(seconds=5)
            }
        })

        if existing:
            return

        # -----------------------------
        # 🔥 COOLDOWN CHECK
        # -----------------------------
        if not self.can_trigger(confirm_key):
            return

        # -----------------------------
        # Insert anomaly
        # -----------------------------
        doc = {
            "track_id": track_id,
            "anomaly_type": anomaly_type,
            "metric_value": metric,
            "threshold": threshold,
            "timestamp": datetime.utcnow()
        }

        anomaly_events.insert_one(doc)

        # -----------------------------
        # 🔥 RESET counter AFTER success
        # -----------------------------
        self.violation_counter[confirm_key] = 0

        # -----------------------------
        # Update shared state
        # -----------------------------
        current_security_alert.update({
            "active": True,
            "type": anomaly_type,
            "track_id": track_id,
            "metric_value": metric,
            "threshold": threshold,
            "updated_at": doc["timestamp"]
        })

        print(f"🚨 ANOMALY ALERT | ID={track_id} | {anomaly_type} | {metric:.2f} > {threshold}")    

    def detect_running(self, person):
        if person.get("avg_speed", 0) > self.run_speed_th:
            self.log_anomaly(person["track_id"], "running", person["avg_speed"], self.run_speed_th)

    def detect_loitering(self, person):
        if person.get("total_dwell", 0) > self.loiter_time_th:
            self.log_anomaly(person["track_id"], "loitering", person["total_dwell"], self.loiter_time_th)

    def detect_suspicious_idle(self, person):
        if person.get("total_dwell", 0) > self.loiter_time_th and \
            person.get("looking_ratio", 1.0) < self.look_ratio_th:
            self.log_anomaly(person["track_id"], "suspicious_idle_behavior", person["looking_ratio"], self.look_ratio_th)

    '''def step(self):
        now = datetime.utcnow()
        active_since = now - timedelta(seconds=min(self.active_window, 3))

        active_people = engagement_logs.find({
            "mode": "mass",
            "last_seen": {"$gte": active_since}
        })

        for person in active_people:
            # Safety: ensure track_id exists
            if "track_id" not in person:
                continue
            self.detect_running(person)
            self.detect_loitering(person)
            self.detect_suspicious_idle(person)

        # 🔥 CLEANUP: remove stale counters
        active_ids = {p["track_id"] for p in active_people if "track_id" in p}

        keys_to_delete = []

        for key in self.violation_counter:
            track_id = key.split("_")[0]
            if track_id not in active_ids:
                keys_to_delete.append(key)

        for key in keys_to_delete:
            del self.violation_counter[key]'''

    def step(self):
        now = datetime.utcnow()
        active_since = now - timedelta(seconds=min(self.active_window, 3))

        # 🔥 Convert cursor to list (IMPORTANT FIX)
        active_people = list(engagement_logs.find({
            "mode": "mass",
            "last_seen": {"$gte": active_since}
        }))

        # -----------------------------
        # Detection
        # -----------------------------
        for person in active_people:
            if "track_id" not in person:
                continue

            self.detect_running(person)
            self.detect_loitering(person)
            self.detect_suspicious_idle(person)

        # -----------------------------
        # 🔥 CLEANUP: remove stale counters
        # -----------------------------
        active_ids = {p["track_id"] for p in active_people if "track_id" in p}

        keys_to_delete = []

        for key in list(self.violation_counter.keys()):
            track_id = key.split("_")[0]

            if track_id not in active_ids:
                keys_to_delete.append(key)

        for key in keys_to_delete:
            del self.violation_counter[key]            

    def loop_forever(self):
        self.running = True
        print("🚨 Anomaly service started")
        while self.running:
            try:
                self.run_once()
                time.sleep(self.scan_interval)
            except Exception as e:
                print("❌ Anomaly error:", e)
                time.sleep(5)

    def stop(self):
        self.running = False