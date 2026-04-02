from datetime import datetime

current_mass_ad = {
    "age_group": None,
    "gender": None,
    "ad_image_base64": None,
    "updated_at": None,
    "emotion": None
}


current_security_alert = {
    "active": False,
    "type": None,          # "running" / "loitering" / "suspicious_idle_behavior"
    "track_id": None,
    "metric_value": None,
    "threshold": None,
    "updated_at": None,
}
