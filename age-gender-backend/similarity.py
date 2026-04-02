# similarity.py

import numpy as np
import math
from sklearn.metrics.pairwise import cosine_similarity
from datetime import datetime

from db import visitors_collection
from utils import l2_normalize   # <-- from utils.py
from config import CURRENT_METHOD

from config import (
    SIMILARITY_THRESHOLD,
    QUALITY_UPDATE_THRESHOLD,
    BASE_EMBED_UPDATE_ALPHA,
    TEMPORAL_DECAY_TAU_DAYS,
    MIN_TEMPORAL_WEIGHT,
    THRESHOLD_PROBABLE,
    THRESHOLD_RETURNING,
    AMBIGUITY_MARGIN,
    STALE_MAX_DAYS
)

# --------------------------------
# Core cosine similarity (Phase 0)
# --------------------------------
def compute_cosine_similarity(emb1: np.ndarray, emb2: np.ndarray) -> float:
    emb1 = l2_normalize(emb1)
    emb2 = l2_normalize(emb2)

    return cosine_similarity(
        emb1.reshape(1, -1),
        emb2.reshape(1, -1)
    )[0][0]


# --------------------------------
# Identity matching with quality weighting (Phase 1) ; later integrated with phase 3
# --------------------------------
def find_match_with_decision(new_embedding: np.ndarray, quality_score: float):
    """
    Phase 4:
    - Evaluate all stored identities
    - Choose best match
    - Apply 3-level decision logic: new / probable / returning
    - Add ambiguity + stale safety controls
    Returns a dict with decision + visitor (if any) + scores.
    """

    new_embedding = l2_normalize(new_embedding)

    best = None
    second_best = None

    for visitor in visitors_collection.find({}, {"embedding":1,"last_seen":1,"visit_count":1}):
        stored_embedding = np.array(visitor["embedding"], dtype=np.float32)

        base_similarity = compute_cosine_similarity(new_embedding, stored_embedding)
        time_weight = temporal_weight(visitor["last_seen"])  # from Phase 3

        
        #effective_similarity = base_similarity * quality_score * time_weight
        if CURRENT_METHOD == "cosine":
            effective_similarity = base_similarity

        elif CURRENT_METHOD == "quality":
            effective_similarity = base_similarity * quality_score

        elif CURRENT_METHOD == "temporal":
            effective_similarity = base_similarity * time_weight

        else:  # proposed
            #effective_similarity = base_similarity * quality_score * time_weight
            confidence = 0.6 * quality_score + 0.4 * time_weight
            effective_similarity = base_similarity * confidence

        debug_info = {
            "cosine": float(base_similarity),
            "quality": float(quality_score),
            "temporal": float(time_weight),
            "final": float(effective_similarity)
        }    


        # Track top-1 and top-2
        if best is None or effective_similarity > best["score"]:
            second_best = best
            best = {"visitor": visitor, "score": float(effective_similarity)}
        elif second_best is None or effective_similarity > second_best["score"]:
            second_best = {"visitor": visitor, "score": float(effective_similarity)}

    # No candidates in DB
    if best is None:
        return {"decision": "new", "visitor": None, "score": 0.0, "reason": "empty_db"}

    # -------------------------------
    # Safety control 1: stale identity cap
    # -------------------------------
    days_since = (datetime.utcnow() - best["visitor"]["last_seen"]).days
    if days_since > STALE_MAX_DAYS:
        # Even if similarity is high, treat as probable (avoid false positives)
        if best["score"] >= THRESHOLD_RETURNING:
            return {
                "decision": "probable",
                "visitor": best["visitor"],
                "score": best["score"],
                "reason": f"stale_identity_{days_since}d"
            }

    # -------------------------------
    # Safety control 2: ambiguity check
    # -------------------------------
    if second_best is not None:
        if (best["score"] - second_best["score"]) < AMBIGUITY_MARGIN:
            # Too close → ambiguous, do not claim returning
            if best["score"] >= THRESHOLD_PROBABLE:
                return {
                    "decision": "probable",
                    "visitor": best["visitor"],
                    "score": best["score"],
                    "reason": "ambiguous_top2"
                }

    # -------------------------------
    # 3-level decision logic
    # -------------------------------
    if best["score"] >= THRESHOLD_RETURNING:
        #return {"decision": "returning", "visitor": best["visitor"], "score": best["score"], "reason": "confident"}
        return {
            "decision": "returning",
            "visitor": best["visitor"],
            "score": best["score"],
            "reason": "confident",
            "debug": debug_info
        }
    elif best["score"] >= THRESHOLD_PROBABLE:
        #return {"decision": "probable", "visitor": best["visitor"], "score": best["score"], "reason": "weak_match"}
        return {
            "decision": "probable",
            "visitor": best["visitor"],
            "score": best["score"],
            "reason": "weak_match",
            "debug": debug_info
        }
    else:
        #return {"decision": "new", "visitor": None, "score": best["score"], "reason": "below_probable"}
        return {
            "decision": "new",
            "visitor": None,
            "score": best["score"],
            "reason": "below_probable",
            "debug": debug_info
        }



# --------------------------------
# Update visitor stats
# --------------------------------
def update_visitor(visitor,
                   new_embedding: np.ndarray,
                   quality_score: float,
                   mode: str):
    """
    Phase 2:
    - Always update visit metadata
    - Update embedding ONLY if:
        - individual mode
        - quality_score >= QUALITY_UPDATE_THRESHOLD
    """

    visitors_collection.update_one(
        {"_id": visitor["_id"]},
        {
            "$inc": {"visit_count": 1},
            "$set": {"last_seen": datetime.utcnow()}
        }
    )

    # Phase 2: selective embedding update
    if (
        mode == "individual" and
        quality_score >= QUALITY_UPDATE_THRESHOLD
    ):
        old_emb = l2_normalize(
            np.array(visitor["embedding"], dtype=np.float32)
        )
        new_emb = l2_normalize(new_embedding)

        visit_count = visitor["visit_count"] + 1

        updated_emb = update_embedding(
            old_emb=old_emb,
            new_emb=new_emb,
            visit_count=visit_count
        )

        visitors_collection.update_one(
            {"_id": visitor["_id"]},
            {"$set": {"embedding": updated_emb.tolist()}}
        )



# --------------------------------
# Create new visitor
# --------------------------------
def create_visitor(embedding, age_group, gender):
    embedding = l2_normalize(embedding)

    visitors_collection.insert_one({
        "embedding": embedding.tolist(),
        "first_seen": datetime.utcnow(),
        "last_seen": datetime.utcnow(),
        "visit_count": 1,
        "age_group": age_group,
        "gender": gender
    })

# --------------------------------
# Adaptive embedding update (Phase 2)
# --------------------------------
def update_embedding(old_emb: np.ndarray,
                     new_emb: np.ndarray,
                     visit_count: int) -> np.ndarray:
    """
    Adaptive exponential moving average update.
    Learning rate decreases as visit count increases.
    """

    # Adaptive alpha (decays with visits)
    alpha = BASE_EMBED_UPDATE_ALPHA / (1 + np.log(visit_count + 1))

    updated = alpha * new_emb + (1 - alpha) * old_emb
    return l2_normalize(updated)


def temporal_weight(last_seen: datetime) -> float:
    """
    Compute temporal decay weight based on days since last_seen.
    """
    delta_days = (datetime.utcnow() - last_seen).days
    weight = math.exp(-delta_days / TEMPORAL_DECAY_TAU_DAYS)
    return max(MIN_TEMPORAL_WEIGHT, weight)