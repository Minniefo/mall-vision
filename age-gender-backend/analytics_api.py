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

import pytz
from datetime import datetime, timedelta
from fastapi import Query

SL_TZ = pytz.timezone("Asia/Colombo")

def get_utc_range(from_date: str = None, to_date: str = None):
    query = {}

    if from_date:
        local_from = SL_TZ.localize(datetime.fromisoformat(from_date))
        utc_from = local_from.astimezone(pytz.utc)
        query["$gte"] = utc_from

    if to_date:
        # include full day properly
        local_to = SL_TZ.localize(datetime.fromisoformat(to_date)) + timedelta(days=1)
        utc_to = local_to.astimezone(pytz.utc)
        query["$lt"] = utc_to

    return query

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
def hourly_trend(
    from_date: str = Query(None, alias="from"),
    to_date: str = Query(None, alias="to")
):

    match_stage = {}

    date_filter = get_utc_range(from_date, to_date)
    if date_filter:
        match_stage["timestamp"] = date_filter

    pipeline = [
        {"$match": match_stage} if match_stage else {"$match": {}},
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
def new_vs_returning(
    from_date: str = Query(None, alias="from"),
    to_date: str = Query(None, alias="to")
):
    match_stage = {}

    date_filter = get_utc_range(from_date, to_date)
    if date_filter:
        match_stage["last_seen"] = date_filter

    pipeline = [
        {"$match": match_stage} if match_stage else {"$match": {}},
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
def returning_by_age(
    from_date: str = Query(None, alias="from"),
    to_date: str = Query(None, alias="to")
):

    match_stage = {}

    date_filter = get_utc_range(from_date, to_date)
    if date_filter:
        match_stage["last_seen"] = date_filter

    pipeline = [
        {"$match": match_stage} if match_stage else {"$match": {}},
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
def get_security_alerts(
    from_date: str = Query(None, alias="from"),
    to_date: str = Query(None, alias="to")
):

    query = {"is_security_alert": True}

    date_filter = get_utc_range(from_date, to_date)

    if date_filter:
        query["timestamp"] = date_filter
    else:
        # fallback → last 30 seconds
        now = datetime.utcnow()
        query["timestamp"] = {
            "$gte": now - timedelta(seconds=30)
        }

    alerts = list(
        perception_collection.find(query).sort("timestamp", -1)
    )

    return [
        {
            "_id": str(a["_id"]),
            "alert_reason": a.get("alert_reason") or a.get("emotion"),
            "timestamp": a["timestamp"].isoformat() + "Z"
        }
        for a in alerts
    ]


@router.get("/summary-stats")
def summary_stats(
    from_date: str = Query(None, alias="from"),
    to_date: str = Query(None, alias="to")
):

    query = {}

    date_filter = get_utc_range(from_date, to_date)
    if date_filter:
        query["last_seen"] = date_filter   # 👈 KEY LINE

    total_visitors = visitors_collection.count_documents(query)

    returning_visitors = visitors_collection.count_documents({
        **query,
        "visit_count": {"$gt": 1}
    })

    new_visitors = visitors_collection.count_documents({
        **query,
        "visit_count": {"$lte": 1}
    })

    total_detections = perception_collection.count_documents({})

    returning_rate = (
        (returning_visitors / total_visitors) * 100
        if total_visitors > 0 else 0
    )

    return {
        "total_detections": total_detections,
        "total_visitors": total_visitors,
        "returning": returning_visitors,
        "new": new_visitors,
        "returning_rate": round(returning_rate, 2)
    }