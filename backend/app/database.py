import os
from pymongo import MongoClient
from dotenv import load_dotenv

load_dotenv()

MONGODB_URI = os.getenv("MONGODB_URI", "mongodb://localhost:27017")
DB_NAME = os.getenv("MONGODB_DATABASE", "smart_fridge_iot")

client = None
db = None

def get_database():
    global client, db
    if client is None:
        client = MongoClient(
            MONGODB_URI,
            serverSelectionTimeoutMS=5000,
            maxPoolSize=50,
            retryWrites=True
        )
        db = client[DB_NAME]
    return db

def check_db_health():
    try:
        database = get_database()
        database.command("ping")
        return {"status": "connected", "database": DB_NAME}
    except Exception as e:
        return {"status": "error", "message": str(e)}
