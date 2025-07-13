from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from pymongo import MongoClient
from datetime import datetime, timezone
import os
import uuid
from typing import List, Optional

app = FastAPI(title="NeoView Glucose Monitor API")

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# MongoDB connection
MONGO_URL = os.environ.get('MONGO_URL', 'mongodb://localhost:27017/')
client = MongoClient(MONGO_URL)
db = client.neoview_db
glucose_collection = db.glucose_readings

class GlucoseReading(BaseModel):
    glucose_value: float
    timestamp: Optional[str] = None
    device_id: Optional[str] = "ESP32_001"

class GlucoseResponse(BaseModel):
    id: str
    glucose_value: float
    category: str
    timestamp: str
    device_id: str
    color: str

def categorize_glucose(value: float) -> tuple[str, str]:
    """Categorize glucose value and return category and color"""
    if value < 70:
        return "Hipoglicemia", "#ef4444"  # red
    elif 70 <= value <= 140:
        return "Normal", "#22c55e"  # green
    elif 141 <= value <= 199:
        return "Atenção", "#f59e0b"  # yellow/orange
    else:  # >= 200
        return "Alerta", "#dc2626"  # dark red

@app.get("/")
async def root():
    return {"message": "NeoView Glucose Monitor API is running"}

@app.post("/api/glucose", response_model=GlucoseResponse)
async def save_glucose_reading(reading: GlucoseReading):
    """Save a new glucose reading from ESP32"""
    try:
        # Generate unique ID
        reading_id = str(uuid.uuid4())
        
        # Use provided timestamp or current time
        if reading.timestamp:
            timestamp = reading.timestamp
        else:
            timestamp = datetime.now(timezone.utc).isoformat()
        
        # Categorize glucose value
        category, color = categorize_glucose(reading.glucose_value)
        
        # Prepare document for MongoDB
        glucose_doc = {
            "id": reading_id,
            "glucose_value": reading.glucose_value,
            "category": category,
            "color": color,
            "timestamp": timestamp,
            "device_id": reading.device_id,
            "created_at": datetime.now(timezone.utc)
        }
        
        # Insert into MongoDB
        glucose_collection.insert_one(glucose_doc)
        
        # Return response
        return GlucoseResponse(
            id=reading_id,
            glucose_value=reading.glucose_value,
            category=category,
            color=color,
            timestamp=timestamp,
            device_id=reading.device_id
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error saving glucose reading: {str(e)}")

@app.get("/api/glucose/latest", response_model=Optional[GlucoseResponse])
async def get_latest_glucose():
    """Get the most recent glucose reading"""
    try:
        latest = glucose_collection.find_one(
            sort=[("created_at", -1)]
        )
        
        if not latest:
            return None
            
        return GlucoseResponse(
            id=latest["id"],
            glucose_value=latest["glucose_value"],
            category=latest["category"],
            color=latest["color"],
            timestamp=latest["timestamp"],
            device_id=latest["device_id"]
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching latest reading: {str(e)}")

@app.get("/api/glucose/history", response_model=List[GlucoseResponse])
async def get_glucose_history(limit: int = 50):
    """Get glucose reading history"""
    try:
        readings = list(glucose_collection.find(
            sort=[("created_at", -1)],
            limit=limit
        ))
        
        history = []
        for reading in readings:
            history.append(GlucoseResponse(
                id=reading["id"],
                glucose_value=reading["glucose_value"],
                category=reading["category"],
                color=reading["color"],
                timestamp=reading["timestamp"],
                device_id=reading["device_id"]
            ))
            
        return history
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching history: {str(e)}")

@app.get("/api/glucose/stats")
async def get_glucose_stats():
    """Get glucose statistics"""
    try:
        total_readings = glucose_collection.count_documents({})
        
        # Get category counts
        pipeline = [
            {"$group": {"_id": "$category", "count": {"$sum": 1}}}
        ]
        category_stats = list(glucose_collection.aggregate(pipeline))
        
        # Get average glucose
        avg_pipeline = [
            {"$group": {"_id": None, "avg_glucose": {"$avg": "$glucose_value"}}}
        ]
        avg_result = list(glucose_collection.aggregate(avg_pipeline))
        avg_glucose = avg_result[0]["avg_glucose"] if avg_result else 0
        
        return {
            "total_readings": total_readings,
            "average_glucose": round(avg_glucose, 1),
            "category_distribution": {stat["_id"]: stat["count"] for stat in category_stats}
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching stats: {str(e)}")

@app.delete("/api/glucose/clear")
async def clear_all_readings():
    """Clear all glucose readings (for testing)"""
    try:
        result = glucose_collection.delete_many({})
        return {"message": f"Deleted {result.deleted_count} readings"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error clearing readings: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)