class EmotionSmoother:
    def __init__(self, max_len=5):
        self.max_len = max_len
        self.buffer = []

    def add_prediction(self, pred_class):
        """
        pred_class = integer class index 0–5
        Returns smoothed final class
        """
        self.buffer.append(pred_class)

        if len(self.buffer) > self.max_len:
            self.buffer.pop(0)

        # Majority vote
        return max(set(self.buffer), key=self.buffer.count)
