# app/mongo_crud.py (новий файл)
from .mongo_db import activity_log_collection
from .schemas import ActivityLogBase # Або повний шлях до схеми
from typing import List
from bson import ObjectId # Для роботи з ObjectId, якщо потрібно

async def add_activity_log(log_data: ActivityLogBase) -> dict:
    log_dict = log_data.model_dump(by_alias=True)
    result = await activity_log_collection.insert_one(log_dict)
    # Повертаємо вставлений документ (можливо, з _id)
    # find_one поверне None, якщо нічого не знайдено
    created_log = await activity_log_collection.find_one({"_id": result.inserted_id})
    return created_log

async def get_activity_logs(limit: int = 100) -> List[dict]:
    logs = await activity_log_collection.find().sort("timestamp", -1).limit(limit).to_list(length=limit)
    return logs