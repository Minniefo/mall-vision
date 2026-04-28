#engagement_service.py
import time
import cv2
import torch
import numpy as np
from collections import defaultdict, deque
from ultralytics import YOLO

from model.head_orientation_cnn import HeadOrientationCNN
from utils.sort import Sort
from db import engagement_logs
from datetime import datetime

try:
    from enhancements import ZoneEngine, zone_adjust_engagement
    ZONE_SUPPORT = True
except Exception:
    ZONE_SUPPORT = False


class EngagementService:
    """
    Engagement inference for MASS audience.
    - Loads YOLO + HeadOrientation model ONCE
    - Tracks people with SORT
    - Computes engagement using looking frames + dwell frames
    - Returns aggregated engagement percent
    """

    def __init__(
        self,
        yolo_path="weights/yolov8n.pt",
        head_path="weights/head_orientation_cnn.pt",
        conf_th=0.35,
        max_age=20,
        min_hits=3,
        iou_th=0.3,
        fps_assumed=5,
        engage_time=1.5,
        use_zones=False,
        zones_path="zones_cctv.json",
        device=None
    ):
        self.conf_th = conf_th

        self.fps_assumed = fps_assumed
        self.min_look_frames = int(fps_assumed * engage_time)

        self.device = device or ("cuda" if torch.cuda.is_available() else "cpu")

        # 1) Load detection model ONCE
        self.detector = YOLO(yolo_path)

        # 2) Load head model ONCE
        self.head_model = HeadOrientationCNN().to(self.device)
        self.head_model.load_state_dict(torch.load(head_path, map_location=self.device))
        self.head_model.eval()

        # 3) Tracker
        self.tracker = Sort(max_age=max_age, min_hits=min_hits, iou_threshold=iou_th)

        # 4) State per track
        self.motion_history = defaultdict(lambda: deque(maxlen=5))
        self.state = {}  # tid -> dict

        # 5) Optional zones
        self.use_zones = bool(use_zones and ZONE_SUPPORT)
        self.zone_engine = ZoneEngine(zones_path) if self.use_zones else None

        self.engagement_history = deque(maxlen=20)

        self.last_ts = time.time()

    # -------------------------
    # helpers
    # -------------------------
    @staticmethod
    def _crop_head(frame, bbox):
        x1, y1, x2, y2 = bbox
        h = y2 - y1
        head_y2 = y1 + int(0.4 * h)
        head = frame[y1:head_y2, x1:x2]
        if head.size == 0:
            return None
        return cv2.resize(head, (64, 64))

    def _infer_head_orientation(self, head_crop):
        t = torch.tensor(head_crop / 255.0).permute(2, 0, 1).unsqueeze(0).float().to(self.device)
        with torch.no_grad():
            out = self.head_model(t)
        return "looking_at_kiosk" if out.argmax().item() == 1 else "looking_away"

    # -------------------------
    # main API
    # -------------------------
    def process_frame(self, frame):
        """
        Input: BGR frame (OpenCV)
        Output: dict with aggregated engagement stats for MASS audience
        """

        # --- detect persons
        results = self.detector(frame, conf=self.conf_th, iou=0.5, classes=[0], verbose=False)[0]
        detections = []

        for b in results.boxes:
            x1, y1, x2, y2 = map(int, b.xyxy[0])

            # same size filters you used
            if (x2 - x1) < 40 or (y2 - y1) < 60:
                continue

            detections.append([x1, y1, x2, y2, float(b.conf)])

        dets_np = np.array(detections) if detections else np.empty((0, 5))
        tracks = self.tracker.update(dets_np)

        # --- update engagement state
        active_ids = set()
        engaged_count = 0
        total = 0

        now = time.time()
        dt = max(now - self.last_ts, 1e-6)
        fps = 1.0 / dt
        self.last_ts = now

        for tr in tracks:
            x1, y1, x2, y2, tid = map(int, tr[:5])
            active_ids.add(tid)

            if tid not in self.state:
                self.state[tid] = {
                    "looking_frames": 0,
                    "total_frames": 0,
                    "engaged": False,
                    "engagement_score": 0.0,
                    "zone": "unknown",

                    "first_seen": now,
                    "last_seen": now,

                    "motion_sum": 0.0,
                    "motion_count": 0,
                    "avg_speed": 0.0,
                }

            cx, cy = (x1 + x2) // 2, (y1 + y2) // 2

            self.motion_history[tid].append((cx, cy))

            motion = 0.0
            if len(self.motion_history[tid]) >= 2:
                xa, ya = self.motion_history[tid][-2]
                xb, yb = self.motion_history[tid][-1]
                motion = float(np.hypot(xb - xa, yb - ya))

            self.state[tid]["motion_sum"] += motion
            self.state[tid]["motion_count"] += 1
            self.state[tid]["avg_speed"] = (
                self.state[tid]["motion_sum"] /
                max(1, self.state[tid]["motion_count"])
            )
            self.state[tid]["last_seen"] = now

            # zone 
            zone = "unknown"
            if self.use_zones and self.zone_engine is not None:
                zone = self.zone_engine.get_zone(cx, cy)

            o = "NO_HEAD"
            head = self._crop_head(frame, (x1, y1, x2, y2))
            if head is not None:
                o = self._infer_head_orientation(head)
                self.state[tid]["total_frames"] += 1
                if o == "looking_at_kiosk":
                    self.state[tid]["looking_frames"] += 1

            print(f"[HEAD DEBUG] Track {tid} → {o}")        

            # base engagement (your original rule)
            ratio = self.state[tid]["looking_frames"] / max(1, self.state[tid]["total_frames"])

            dwell_time = now - self.state[tid]["first_seen"]

            base_engaged = (
                self.state[tid]["total_frames"] > 10
                and ratio > 0.6
                and dwell_time > 2.0
            )

            # zone adjustment
            final_engaged = base_engaged
            if self.use_zones and ZONE_SUPPORT:
                final_engaged = zone_adjust_engagement(
                    base_engaged, zone, self.state[tid]["total_frames"]
                )


            score = self.state[tid]["engagement_score"]

            if o == "looking_at_kiosk":
                score += 0.15
            else:
                score -= 0.08

            score = max(0.0, min(1.0, score))
            self.state[tid]["engagement_score"] = score

            final_engaged = score > 0.5    

            self.state[tid]["engaged"] = final_engaged
            self.state[tid]["zone"] = zone

            engagement_logs.update_one(
                {"track_id": tid},
                {"$set": {
                    "track_id": tid,
                    "active": True,
                    "mode" : "mass",
                    "first_seen": datetime.utcfromtimestamp(self.state[tid]["first_seen"]),
                    "last_seen": datetime.utcfromtimestamp(self.state[tid]["last_seen"]),
                    "total_dwell": float(now - self.state[tid]["first_seen"]),
                    "avg_speed": float(self.state[tid]["avg_speed"]),
                    "looking_ratio": float(
                        self.state[tid]["looking_frames"] /
                        max(1, self.state[tid]["total_frames"])
                    ),
                    "engaged": bool(final_engaged),
                    "zone": zone
                }},
                upsert=True
            )

            total += 1
            if final_engaged:
                engaged_count += 1

        # --- cleanup stale tracks
        # For now: keep state; you can add "last_seen" logic later

        raw_pct = (engaged_count / total) * 100.0 if total > 0 else 0.0

        self.engagement_history.append(raw_pct)

        if len(self.engagement_history) > 0:
            engagement_pct = sum(self.engagement_history) / len(self.engagement_history)
        else:
            engagement_pct = raw_pct

        stale_ids = set(self.state.keys()) - active_ids

        for sid in stale_ids:
            s = self.state[sid]

            engagement_logs.update_one(
                {"track_id": sid},
                {"$set": {
                    "track_id": sid,
                    "active": False,
                    "first_seen": datetime.utcfromtimestamp(s["first_seen"]),
                    "last_seen": datetime.utcfromtimestamp(s["last_seen"]),
                    "total_dwell": float(s["last_seen"] - s["first_seen"]),
                    "avg_speed": float(s["avg_speed"]),
                    "looking_ratio": float(
                        s["looking_frames"] /
                        max(1, s["total_frames"])
                    ),
                    "engaged": bool(s["engaged"]),
                    "zone": s["zone"],
                }},
                upsert=True
            )

            del self.state[sid]
            if sid in self.motion_history:
                del self.motion_history[sid]

        return {
            "total_people": total,
            "engaged_people": engaged_count,
            "engagement_percentage": float(engagement_pct),
            "fps": float(fps),
        }