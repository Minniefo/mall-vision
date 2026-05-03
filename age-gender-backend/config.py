# config.py

# Face embedding
EMBEDDING_SIZE = 512
SIMILARITY_THRESHOLD = 0.75   # tune later

# Phase 2 – identity memory update control
QUALITY_UPDATE_THRESHOLD = 0.75   # Q_MIN
BASE_EMBED_UPDATE_ALPHA = 0.3     # initial learning rate

# Phase 3 – temporal decay
TEMPORAL_DECAY_TAU_DAYS = 30.0   # τ (30 days ≈ strong but forgiving)
MIN_TEMPORAL_WEIGHT = 0.5       # floor to avoid zeroing similarity (increased for demo)

# Phase 3.5 – Mass-mode Near-Zone ROI gating
MASS_NEAR_ZONE_ENABLED = True

# Phase 4 – decision thresholds
#THRESHOLD_RETURNING = 0.78   # confident match
#THRESHOLD_PROBABLE  = 0.65   # weak match (needs more evidence)
THRESHOLD_RETURNING = 0.70      # lowered to improve identification in varied lighting
THRESHOLD_PROBABLE  = 0.62

# Safety controls
AMBIGUITY_MARGIN = 0.03      
STALE_MAX_DAYS = 120         

# Polygon points in pixel coordinates (x, y) clockwise order
MASS_NEAR_ZONE_POLYGON = [(300, 400), (980, 400), (1250, 720), (50, 720)]

# Mass-mode identity policy
MASS_EXTRACT_EMBEDDINGS = True          # only for near zone
MASS_ALLOW_ID_MATCHING = True           # analytics-only, conservative
MASS_SIMILARITY_THRESHOLD = 0.85        # stricter than individual threshold

CURRENT_METHOD = "proposed"
# options: "cosine", "quality", "temporal", "proposed"


# MongoDB
MONGO_URI = "mongodb+srv://it22109712_db_user:etuOhoikqkNqrEgD@cluster0.f3wzpxd.mongodb.net/?appName=Cluster0"

DB_NAME = "mallvision"
COLLECTION_NAME = "visitors"
