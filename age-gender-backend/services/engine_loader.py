#engine_loader.py
from services.recommendation_engine import AdRecommendationEngine
from services.novelty_ad_engine import NoveltyAdEngine

ad_engine = None
novelty_engine = None


'''def init_engines():
    global ad_engine, novelty_engine

    if ad_engine is None:
        ad_engine = AdRecommendationEngine()
        ad_engine.load_ads_database()

    if novelty_engine is None:
        novelty_engine = NoveltyAdEngine()
        novelty_engine.load_and_precompute()

    print("[ENGINE LOADER] Engines initialized")'''

def init_engines():
    global ad_engine, novelty_engine

    if ad_engine is None:
        ad_engine = AdRecommendationEngine()
        ad_engine.load_ads_database()

    if novelty_engine is None:
        novelty_engine = NoveltyAdEngine()
        success = novelty_engine.load_and_precompute()

        if success:
            print("✅ Novelty engine loaded successfully")
        else:
            print("❌ Novelty engine FAILED to load")

    print("[ENGINE LOADER] Engines initialized")