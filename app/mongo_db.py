import os
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv

load_dotenv()

MONGO_DETAILS = os.getenv("MONGO_DETAILS", "mongodb://localhost:27017")
MONGO_DATABASE_NAME = os.getenv("MONGO_DATABASE_NAME", "mydatabase")

client = AsyncIOMotorClient(MONGO_DETAILS)
database = client[MONGO_DATABASE_NAME]

# Функція для отримання колекції
def get_collection(collection_name: str):
    return database[collection_name]

# Приклад: колекція для логів
activity_log_collection = get_collection("activity_logs")

async def close_mongo_connection():
    client.close()