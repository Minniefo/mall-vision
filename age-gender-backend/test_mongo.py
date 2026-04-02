from pymongo import MongoClient
from config import MONGO_URI

print("Testing MongoDB connection...")
print("URI:", MONGO_URI)

client = MongoClient(
    MONGO_URI,
    serverSelectionTimeoutMS=5000
)

try:
    client.admin.command("ping")
    print("✅ MongoDB authentication SUCCESSFUL")
except Exception as e:
    print("❌ MongoDB authentication FAILED")
    print(e)
