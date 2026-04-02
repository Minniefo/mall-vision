import time
from collections import Counter
from typing import List, Optional


class EmotionWindowAggregator:
    def __init__(self, window_seconds: int = 10):
        self.window_seconds = window_seconds
        self.reset()

    def reset(self):
        self.start_time = time.time()
        self.emotion_buffer: List[str] = []

    def add_frame_emotions(self, emotions: List[str]):
        if emotions:
            self.emotion_buffer.extend(emotions)

    def is_window_complete(self) -> bool:
        return (time.time() - self.start_time) >= self.window_seconds

    def aggregate(self) -> Optional[dict]:
        if not self.emotion_buffer:
            self.reset()
            return None

        counts = Counter(self.emotion_buffer)
        dominant_emotion = counts.most_common(1)[0][0]

        channel = (
            "security"
            if dominant_emotion in ["fear", "suspicious"]
            else "advertisement"
        )

        result = {
            "dominant_emotion": dominant_emotion,
            "channel": channel,
            "counts": dict(counts),
            "window_seconds": self.window_seconds
        }

        self.reset()
        return result
