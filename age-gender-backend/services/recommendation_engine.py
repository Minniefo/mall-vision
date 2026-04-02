# services/recommendation_engine.py

import os
import pandas as pd
from typing import Dict, Optional, List
from datetime import datetime
from pytz import timezone
from services.mappings import AGE_MAP
from db import ads_collection

class AdRecommendationEngine:

    def __init__(self, ads_database_path: str = "data/Classification model dataset.csv"):
        self.ads_database_path = ads_database_path
        self.ads_df = None
        self.is_loaded = False

    # --------------------------------------------------
    # Load Ads Dataset
    # --------------------------------------------------

    def load_ads_database(self) -> bool:

        ads = list(ads_collection.find({}, {"_id": 0}))

        if not ads:
            print("[ERROR] No ads found in MongoDB")
            return False

        self.ads_df = pd.DataFrame(ads)

        required_cols = [
            "pid",
            "ad_title",
            "target_age_group",
            "target_gender",
            "target_mood",
            "ad_type",      
            "media_url"
        ]

        missing = [c for c in required_cols if c not in self.ads_df.columns]
        if missing:
            print(f"[ERROR] Missing required columns: {missing}")
            return False

        for col in ["target_age_group", "target_gender", "target_mood"]:
            self.ads_df[col] = self.ads_df[col].astype(str).str.lower()

        for col in ["ad_type"]:
            self.ads_df[col] = self.ads_df[col].astype(str).str.lower()    

        self.is_loaded = True

        print(f"[INFO] Loaded {len(self.ads_df)} ads from MongoDB")

        return True

    # --------------------------------------------------
    # Age Mapping
    # --------------------------------------------------
    def map_age(self, live_age: str) -> str:
        return AGE_MAP.get(live_age, live_age).lower()

    # --------------------------------------------------
    # Emotion → Desired Ad Mood
    # --------------------------------------------------
    def decide_target_mood(self, emotion: Optional[str]) -> Optional[str]:

        if emotion is None:
            return "neutral"

        emotion = emotion.lower()

        colombo = timezone("Asia/Colombo")
        hour = datetime.now(colombo).hour
        is_night = hour >= 19 or hour < 6

        # Security block
        if emotion == "suspicious":
            return None

        if emotion == "fear" and is_night:
            return None

        # Emotional redirection
        if emotion == "happy":
            return "happy"
        
        if emotion == "sad":
            return "happy"
        
        if emotion == "angry":
            return "neutral"

        if emotion == "fear" and not is_night:
            return "happy"

        return "neutral"

    # --------------------------------------------------
    # Weighted Scoring (No Weather)
    # --------------------------------------------------
    def calculate_score(
        self,
        target_age,
        target_gender,
        target_mood,
        ad_row
    ) -> float:

        score = 0.0

        # Weights
        w_age = 0.45
        w_gender = 0.35
        w_mood = 0.20

        if target_age == ad_row["target_age_group"]:
            score += w_age

        if target_gender == ad_row["target_gender"]:
            score += w_gender

        if target_mood == ad_row["target_mood"]:
            score += w_mood

        return score

    # --------------------------------------------------
    # Main Recommendation
    # --------------------------------------------------
    def recommend(
        self,
        age: str,
        gender: str,
        mode: str = "mass",
        emotion: Optional[str] = None,
        engagement_pct: Optional[float] = None
    ) -> Dict:

        if not self.is_loaded:
            if not self.load_ads_database():
                return {"action": "error"}

        mapped_age = self.map_age(age)
        gender = gender.lower()

        # Individual mode ignores emotion
        if mode == "individual":
            target_mood = "neutral"
        else:
            target_mood = self.decide_target_mood(emotion)

        # Security case
        if target_mood is None:
            return {
                "action": "alert",
                "reason": emotion
            }

        # Score all ads
        self.ads_df["score"] = self.ads_df.apply(
            lambda row: self.calculate_score(
                mapped_age,
                gender,
                target_mood,
                row
            ),
            axis=1
        )

        max_score = self.ads_df["score"].max()
        best_ads = self.ads_df[self.ads_df["score"] == max_score]

        if best_ads.empty:
            return {"action": "no_match"}

        #best_ad = best_ads.sample(n=1).iloc[0]
        # Prefer video if engagement is high
        if engagement_pct is not None and engagement_pct > 50:
            video_ads = best_ads[best_ads["ad_type"] == "video"]
            
            if not video_ads.empty:
                best_ad = video_ads.sample(n=1).iloc[0]
            else:
                best_ad = best_ads.sample(n=1).iloc[0]
        else:
            best_ad = best_ads.sample(n=1).iloc[0]

        # Engagement hint (optional)
        engagement_strategy = None
        if mode == "mass" and engagement_pct is not None:
            if engagement_pct < 30:
                engagement_strategy = "refresh_more"
            else:
                engagement_strategy = "stable"

        return {
            "action": "recommend",
            "pid": best_ad["pid"],
            "ad_title": best_ad["ad_title"],
            "ad_type": best_ad["ad_type"],       
             "media_url": best_ad["media_url"],    
            "match_score": float(best_ad["score"]),
            "target_age_group": best_ad["target_age_group"],
            "target_gender": best_ad["target_gender"],
            "target_mood": best_ad["target_mood"],
            "engagement_strategy": engagement_strategy
        }