import json
import os
from datetime import datetime

OUTPUT_FILE = "emotion_output.txt"

def write_emotion_output(emotion: str, security_alert: bool):
    data = {
        "emotion": emotion,
        "security_alert": security_alert,
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }

    tmp_file = OUTPUT_FILE + ".tmp"

    with open(tmp_file, "w") as f:
        json.dump(data, f, indent=4)

    os.replace(tmp_file, OUTPUT_FILE)
