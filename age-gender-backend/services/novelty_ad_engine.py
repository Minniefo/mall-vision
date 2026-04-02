#novelty_ad_engine.py
import pandas as pd
import numpy as np
from typing import Dict, Optional, List, Tuple
import warnings
import os
from db import ads_collection
from services.mappings import AGE_MAP

warnings.filterwarnings('ignore')

# Suppress Hugging Face warnings
os.environ['HF_HUB_DISABLE_SYMLINKS_WARNING'] = '1'
os.environ['TRANSFORMERS_VERBOSITY'] = 'error'

try:
    from sentence_transformers import SentenceTransformer
    from sklearn.metrics.pairwise import cosine_similarity
    import logging
    logging.getLogger('sentence_transformers').setLevel(logging.ERROR)
    DEPENDENCIES_AVAILABLE = True
except ImportError:
    DEPENDENCIES_AVAILABLE = False


class NoveltyAdEngine:
    def __init__(self, ads_database_path: str = "Classification model dataset.csv"):
        self.ads_database_path = ads_database_path
        self.ads_df = None
        self.ad_embeddings = None
        self.model = None
        self.is_loaded = False
        self.last_shown_ad_pid = None
        
    def load_and_precompute(self) -> bool:
        if not DEPENDENCIES_AVAILABLE:
            return False
        
        try:
            ads = list(ads_collection.find({}, {"_id": 0}))
            if not ads:
                print("[ERROR] No ads found in MongoDB")
                return False
            
            self.ads_df = pd.DataFrame(ads).reset_index(drop=True)

            required_cols = ["pid", "ad_title"]

            missing_cols = [col for col in required_cols if col not in self.ads_df.columns]
            if missing_cols:
                print("[ERROR] Missing columns:", missing_cols)
                return False

            ad_texts = self._prepare_ad_texts()

            self.model = SentenceTransformer('all-MiniLM-L6-v2', device='cpu')

            self.ad_embeddings = self.model.encode(
                ad_texts,
                batch_size=32,
                show_progress_bar=False,
                convert_to_numpy=True
            )

            self.is_loaded = True

            print(f"[NOVELTY] Loaded {len(self.ads_df)} ads from MongoDB")

            return True

        except Exception as e:
            print(f"Error initializing novelty engine: {str(e)}")
            return False
    
    def _prepare_ad_texts(self) -> List[str]:
        ad_texts = []
        for idx, row in self.ads_df.iterrows():
            text_parts = [str(row['ad_title'])]
            
            if 'ad_description' in row.index and pd.notna(row['ad_description']):
                text_parts.append(str(row['ad_description']))
            
            if 'tags' in row.index and pd.notna(row['tags']):
                text_parts.append(str(row['tags']))
            
            ad_texts.append(' '.join(text_parts))
        
        return ad_texts
    
    def build_object_context(self, detected_object):

        context_map = {
            "cup": "coffee cup beverage cafe",
            "bottle": "drink beverage water soda",
            "laptop": "electronics laptop computer technology",
            "cell phone": "smartphone mobile electronics",
            "backpack": "travel bag backpack luggage",
            "handbag": "fashion handbag accessories",
            "book": "book reading bookstore education",
            "pizza": "pizza fast food restaurant",
            "burger": "burger fast food restaurant",
            "chair": "furniture home living",
            "tv": "television smart tv electronics entertainment screen"        }

        return context_map.get(detected_object.lower(), detected_object)
    
    def get_object_novelty_ad(
        self,
        detected_object: str,
        age: str,
        gender: str,
        mood: str,
        avoid_pid: Optional[str] = None,
        debug: bool = False
    ) -> Optional[Dict]:
        
        print("[NOVELTY DEBUG] Engine loaded:", self.is_loaded)
        print("[NOVELTY DEBUG] Ads loaded:", len(self.ads_df) if self.ads_df is not None else 0)

        if not self.is_loaded:
            return None

        if not detected_object or detected_object.strip() == "":
            return None

        try:
            # Normalize inputs
            age = AGE_MAP.get(age, age).lower()
            gender = gender.lower()
            mood = mood.lower()

            # 🔵 Step 1: Demographic filtering FIRST
            # Level 1: age + gender
            '''filtered_df = self.ads_df[
                (self.ads_df["target_age_group"].str.lower() == age) &
                (self.ads_df["target_gender"].str.lower() == gender)
            ]'''
            filtered_df = self.ads_df

            # Level 2: age only
            if filtered_df.empty:
                if debug:
                    print("[NOVELTY] Relaxing filter → age only")

                filtered_df = self.ads_df[
                    self.ads_df["target_age_group"].str.lower() == age
                ]

            # Level 3: gender only
            if filtered_df.empty:
                if debug:
                    print("[NOVELTY] Relaxing filter → gender only")

                filtered_df = self.ads_df[
                    self.ads_df["target_gender"].str.lower() == gender
                ]

            # Level 4: fallback to all ads
            if filtered_df.empty:
                if debug:
                    print("[NOVELTY] Relaxing filter → all ads")

                filtered_df = self.ads_df

            # 🔵 Step 2: Compute embeddings only for filtered ads
            indices = filtered_df.index.tolist()
            filtered_embeddings = self.ad_embeddings[indices]

            context_text = self.build_object_context(detected_object)

            object_embedding = self.model.encode(
                [context_text],
                convert_to_numpy=True
            )

            similarities = cosine_similarity(object_embedding, filtered_embeddings)[0]

            sorted_indices = np.argsort(similarities)[::-1]

            for i in sorted_indices:
                real_index = indices[i]
                candidate_pid = self.ads_df.loc[real_index]["pid"]

                if avoid_pid and candidate_pid == avoid_pid:
                    continue

                if self.last_shown_ad_pid and candidate_pid == self.last_shown_ad_pid:
                    continue

                selected_ad = self.ads_df.loc[real_index].to_dict()
                selected_ad["similarity_score"] = float(similarities[i])
                selected_ad["detected_object"] = detected_object

                self.last_shown_ad_pid = candidate_pid

                if debug:
                    print("[NOVELTY] Selected:", candidate_pid)

                return selected_ad
            
            # -----------------------------
            # Fallback if all candidates skipped
            # -----------------------------
            best_index = indices[sorted_indices[0]]

            selected_ad = self.ads_df.loc[best_index].to_dict()
            selected_ad["similarity_score"] = float(similarities[sorted_indices[0]])
            selected_ad["detected_object"] = detected_object

            if debug:
                print("[NOVELTY] Fallback selection:", selected_ad["pid"])

            return selected_ad
            

        except Exception as e:
            print(f"Error finding novelty ad: {str(e)}")
            return None
    
    def get_top_n_similar_ads(
        self,
        detected_object: str,
        n: int = 5,
        avoid_pid: Optional[str] = None
    ) -> List[Dict]:
        if not self.is_loaded:
            return []
        
        if not detected_object:
            return []
        
        try:
            object_embedding = self.model.encode([detected_object], convert_to_numpy=True)
            similarities = cosine_similarity(object_embedding, self.ad_embeddings)[0]
            sorted_indices = np.argsort(similarities)[::-1]
            
            results = []
            for idx in sorted_indices:
                candidate_pid = self.ads_df.iloc[idx]['pid']
                
                if avoid_pid and candidate_pid == avoid_pid:
                    continue
                
                ad_dict = self.ads_df.iloc[idx].to_dict()
                ad_dict['similarity_score'] = float(similarities[idx])
                ad_dict['detected_object'] = detected_object
                results.append(ad_dict)
                
                if len(results) >= n:
                    break
            
            return results
            
        except Exception as e:
            print(f"Error getting top ads: {str(e)}")
            return []
    
    def get_stats(self) -> Optional[Dict]:
        if not self.is_loaded:
            return None
        
        return {
            'total_ads': len(self.ads_df),
            'embedding_dimensions': self.ad_embeddings.shape[1],
            'model_name': 'all-MiniLM-L6-v2',
            'memory_usage_mb': self.ad_embeddings.nbytes / 1024 / 1024,
            'last_shown_ad': self.last_shown_ad_pid
        }


if __name__ == "__main__":
    print("This module is designed to be imported by main.py")
