# privacy.py

import numpy as np
from config import EMBEDDING_SIZE

# Fixed random projection (system-wide)
np.random.seed(42)

R = np.linalg.qr(
    np.random.randn(EMBEDDING_SIZE, EMBEDDING_SIZE)
)[0]

def anonymize_embedding(embedding: np.ndarray) -> np.ndarray:
    """
    One-way privacy-safe transformation.
    Distance-preserving, irreversible.
    """
    projected = embedding @ R
    projected = projected / np.linalg.norm(projected)
    return projected.astype(np.float32)
