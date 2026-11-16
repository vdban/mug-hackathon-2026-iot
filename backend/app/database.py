import os
from pathlib import Path
from pymongo import MongoClient
from dotenv import load_dotenv

_ENV_PATH = Path(__file__).resolve().parents[2] / ".env"
load_dotenv(_ENV_PATH, override=True)

MONGODB_URI = os.getenv("MONGODB_URI", "mongodb://localhost:27017")
DB_NAME = os.getenv("MONGODB_DATABASE", "smart_aquarium_iot")

client = None
db = None

def get_database():
    global client, db
    if client is None:
        client = MongoClient(
            MONGODB_URI,
            serverSelectionTimeoutMS=2500,
            connectTimeoutMS=2500,
            socketTimeoutMS=3000,
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
