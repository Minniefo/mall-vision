import pandas as pd
from db import ads_collection

csv_path = "data/clean_ads_dataset.csv"

df = pd.read_csv(csv_path)

ads = df.to_dict(orient="records")

ads_collection.insert_many(ads)

print(f"Inserted {len(ads)} advertisements into MongoDB.")