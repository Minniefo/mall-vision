"""
evaluate_metrics.py

Computes Precision / Recall / F1 for returning-customer identification
from MongoDB collection: identity_events

Requirements:
- identity_events documents contain:
    - method: "cosine" | "quality" | "temporal" | "proposed"
    - decision: predicted label (e.g., "new", "returning", "returning_after_probable")
    - true_label: ground truth ("new" or "returning") for controlled experiments
"""

from pymongo import MongoClient
from datetime import datetime
from collections import defaultdict

from config import MONGO_URI, DB_NAME


# ----------------------------
# Helpers
# ----------------------------
VALID_METHODS = {"cosine", "quality", "temporal", "proposed"}
VALID_TRUE = {"new", "returning"}


def is_pred_returning(decision: str) -> bool:
    """
    Treat any decision that starts with 'returning' as predicted returning.
    Covers:
    - "returning"
    - "returning_after_probable"
    - "returning_after_probable_x"
    """
    if not decision:
        return False
    d = str(decision).lower().strip()
    return d.startswith("returning")


def safe_float(x, default=0.0) -> float:
    try:
        return float(x)
    except Exception:
        return default


def compute_metrics(tp: int, fp: int, fn: int):
    precision = tp / (tp + fp) if (tp + fp) else 0.0
    recall = tp / (tp + fn) if (tp + fn) else 0.0
    f1 = (2 * precision * recall / (precision + recall)) if (precision + recall) else 0.0
    return precision, recall, f1


def fmt(x: float) -> str:
    return f"{x:.3f}"


# ----------------------------
# Main
# ----------------------------
def main():
    client = MongoClient(MONGO_URI)
    db = client[DB_NAME]
    col = db["identity_events"]

    # OPTIONAL: add time window filter (set to None to ignore)
    START = None  # e.g., datetime(2026, 2, 1)
    END = None    # e.g., datetime(2026, 2, 2)

    query = {
        "method": {"$in": list(VALID_METHODS)},
        "true_label": {"$in": list(VALID_TRUE)},
        "decision": {"$exists": True}
    }

    if START or END:
        query["timestamp"] = {}
        if START:
            query["timestamp"]["$gte"] = START
        if END:
            query["timestamp"]["$lte"] = END

    # stats per method
    stats = defaultdict(lambda: {"TP": 0, "FP": 0, "FN": 0, "N": 0})

    # iterate events
    events = list(col.find(query, {"_id": 0, "method": 1, "decision": 1, "true_label": 1}))
    if not events:
        print("No eligible identity_events found for evaluation.")
        print("Check that identity_events contain: method, decision, true_label.")
        return

    for e in events:
        method = e.get("method")
        decision = e.get("decision", "")
        true_label = e.get("true_label", "")

        pred_returning = is_pred_returning(decision)
        true_returning = (true_label == "returning")

        stats[method]["N"] += 1

        if pred_returning and true_returning:
            stats[method]["TP"] += 1
        elif pred_returning and not true_returning:
            stats[method]["FP"] += 1
        elif (not pred_returning) and true_returning:
            stats[method]["FN"] += 1
        # else: TN (not needed for precision/recall)

    # print results
    print("\n=== Precision / Recall / F1 by Method ===")
    print(f"DB: {DB_NAME} | Collection: identity_events")
    print(f"Events evaluated: {len(events)}")

    header = f"{'Method':<10}  {'N':>5}  {'TP':>5}  {'FP':>5}  {'FN':>5}  {'Precision':>10}  {'Recall':>8}  {'F1':>8}"
    print("\n" + header)
    print("-" * len(header))

    for method in sorted(stats.keys()):
        tp = stats[method]["TP"]
        fp = stats[method]["FP"]
        fn = stats[method]["FN"]
        n = stats[method]["N"]

        precision, recall, f1 = compute_metrics(tp, fp, fn)

        print(f"{method:<10}  {n:>5}  {tp:>5}  {fp:>5}  {fn:>5}  {fmt(precision):>10}  {fmt(recall):>8}  {fmt(f1):>8}")

    print("\nNote:")
    print("- Predicted returning = decision starts with 'returning'.")
    print("- true_label is expected to be manually assigned during controlled tests.")


if __name__ == "__main__":
    main()
