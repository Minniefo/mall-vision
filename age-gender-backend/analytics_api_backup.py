# analytics_api.py

from fastapi import APIRouter
from datetime import datetime
from db import identity_events
from db import perception_collection
from db import visitors_collection
#from db import perception_events
from bson import ObjectId
from datetime import datetime, timedelta

router = APIRouter(prefix="/analytics", tags=["Analytics"])


# -------------------------------------------------
# Age & Gender Distribution
# -------------------------------------------------
@router.get("/age-gender-distribution")
def age_gender_distribution():

    pipeline = [
        {
            "$match": {
                "age_group": {"$ne": None},
                "gender": {"$ne": None}
            }
        },
        {
            "$group": {
                "_id": {
                    "age_group": "$age_group",
                    "gender": "$gender"
                },
                "count": {"$sum": 1}
            }
        }
    ]

    return list(perception_collection.aggregate(pipeline))


# -------------------------------------------------
# Hourly Trend
# -------------------------------------------------
@router.get("/hourly-trend")
def hourly_trend():

    pipeline = [
        {
            "$project": {
                "hour": {
                    "$hour": {
                        "date": "$timestamp",
                        "timezone": "Asia/Colombo"
                    }
                }
            }
        },
        {
            "$group": {
                "_id": "$hour",
                "count": {"$sum": 1}
            }
        },
        {"$sort": {"_id": 1}}
    ]

    return list(perception_collection.aggregate(pipeline))


# -------------------------------------------------
# New vs Returning
# -------------------------------------------------
@router.get("/new-vs-returning")
@router.get("/new-vs-returning")
def new_vs_returning():

    pipeline = [
        {
            "$project": {
                "type": {
                    "$cond": [
                        {"$gt": ["$visit_count", 1]},
                        "returning",
                        "new"
                    ]
                }
            }
        },
        {
            "$group": {
                "_id": "$type",
                "count": {"$sum": 1}
            }
        },
        {"$sort": {"_id": 1}}
    ]

    return list(visitors_collection.aggregate(pipeline))


# -------------------------------------------------
# Returning Customers by Age
# -------------------------------------------------
@router.get("/returning-by-age")
def returning_by_age():

    pipeline = [
        {
            "$project": {
                "age_group": 1,
                "type": {
                    "$cond": [
                        {"$gt": ["$visit_count", 1]},
                        "returning",
                        "new"
                    ]
                }
            }
        },
        {
            "$group": {
                "_id": {
                    "age_group": "$age_group",
                    "type": "$type"
                },
                "count": {"$sum": 1}
            }
        }
    ]

    return list(visitors_collection.aggregate(pipeline))



@router.get("/security-alerts")
def get_security_alerts():

    now = datetime.utcnow()
    window_start = now - timedelta(seconds=30)

    alerts = list(
        perception_collection.find({
            "is_security_alert": True,
            "timestamp": {"$gte": window_start}
        }).sort("timestamp", -1)
    )

    result = []

    for alert in alerts:
        result.append({
            "_id": str(alert["_id"]),
            "alert_reason": alert.get("alert_reason") or alert.get("emotion"),
            "timestamp": alert["timestamp"].isoformat() + "Z"
        })

    return result

