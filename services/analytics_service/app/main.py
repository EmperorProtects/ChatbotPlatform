from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
import os
import redis
import json
from datetime import datetime, timedelta
from collections import defaultdict

app = FastAPI(title="Analytics Service", version="1.0.0", description="Analytics and metrics for chatbot platform")

# Configuration
REDIS_URL = os.getenv("REDIS_URL", "redis://redis:6379/4")

# Initialize Redis connection
try:
    redis_client = redis.from_url(REDIS_URL, decode_responses=True)
except Exception:
    redis_client = None


# Models
class AnalyticsEvent(BaseModel):
    event_type: str  # "message_received", "message_sent", "user_session", etc.
    user_id: str
    channel: str
    timestamp: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class AnalyticsQuery(BaseModel):
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    channel: Optional[str] = None
    event_type: Optional[str] = None

@app.get("/")
async def root():
    return {
        "message": "Analytics Service", 
        "version": "1.0.0",
        "description": "Analytics and metrics for chatbot platform",
        "endpoints": [
            "/health",
            "/metrics/overview",
            "/metrics/channels",
            "/metrics/users",
            "/events"
        ]
    }

@app.get("/health")
async def health_check():
    return {"status": "healthy", "redis_connected": redis_client is not None}


@app.post("/events")
async def track_event(event: AnalyticsEvent):
    """Track analytics event"""
    if not redis_client:
        raise HTTPException(status_code=503, detail="Analytics storage unavailable")
    
    try:
        # Add timestamp if not provided
        if not event.timestamp:
            event.timestamp = datetime.now(datetime.UTC).isoformat()
        
        # Create event record
        event_data = {
            "event_type": event.event_type,
            "user_id": event.user_id,
            "channel": event.channel,
            "timestamp": event.timestamp,
            "metadata": event.metadata or {}
        }
        
        # Store event
        event_key = f"analytics:event:{datetime.now(datetime.UTC).strftime('%Y%m%d')}:{event.event_type}"
        redis_client.lpush(event_key, json.dumps(event_data))
        redis_client.expire(event_key, 86400 * 30)  # 30 days
        
        # Update counters
        today = datetime.now(datetime.UTC).strftime('%Y-%m-%d')
        redis_client.hincrby(f"analytics:counters:{today}", f"{event.channel}:{event.event_type}", 1)
        redis_client.expire(f"analytics:counters:{today}", 86400 * 30)
        
        # Track unique users
        redis_client.sadd(f"analytics:users:{today}", event.user_id)
        redis_client.expire(f"analytics:users:{today}", 86400 * 30)
        
        return {"status": "success", "event_id": event_key}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to track event: {str(e)}")


@app.get("/metrics/overview")
async def get_overview_metrics(days: int = 7):
    """Get overview metrics for the last N days"""
    if not redis_client:
        raise HTTPException(status_code=503, detail="Analytics storage unavailable")
    
    try:
        metrics = {
            "total_messages": 0,
            "unique_users": 0,
            "channels": {},
            "daily_breakdown": []
        }
        
        # Get data for the last N days
        for i in range(days):
            date = (datetime.now(datetime.UTC) - timedelta(days=i)).strftime('%Y-%m-%d')
            
            # Get daily counters
            counters = redis_client.hgetall(f"analytics:counters:{date}")
            daily_messages = 0
            daily_channels = defaultdict(int)
            
            for key, count in counters.items():
                channel, event_type = key.split(':', 1)
                count = int(count)
                
                if event_type == "message_received":
                    daily_messages += count
                    daily_channels[channel] += count
                    metrics["total_messages"] += count
            
            # Get unique users for the day
            daily_users = redis_client.scard(f"analytics:users:{date}")
            
            metrics["daily_breakdown"].append({
                "date": date,
                "messages": daily_messages,
                "unique_users": daily_users,
                "channels": dict(daily_channels)
            })
            
            # Aggregate channel data
            for channel, count in daily_channels.items():
                if channel not in metrics["channels"]:
                    metrics["channels"][channel] = 0
                metrics["channels"][channel] += count
        
        # Calculate unique users across all days (approximate)
        all_users = set()
        for i in range(days):
            date = (datetime.now(datetime.UTC) - timedelta(days=i)).strftime('%Y-%m-%d')
            daily_users = redis_client.smembers(f"analytics:users:{date}")
            all_users.update(daily_users)
        
        metrics["unique_users"] = len(all_users)
        
        return metrics
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get metrics: {str(e)}")


@app.get("/metrics/channels")
async def get_channel_metrics():
    """Get metrics by channel"""
    if not redis_client:
        raise HTTPException(status_code=503, detail="Analytics storage unavailable")
    
    try:
        today = datetime.now(datetime.UTC).strftime('%Y-%m-%d')
        counters = redis_client.hgetall(f"analytics:counters:{today}")
        
        channel_metrics = defaultdict(lambda: {
            "messages_received": 0,
            "messages_sent": 0
        })
        
        for key, count in counters.items():
            channel, event_type = key.split(':', 1)
            count = int(count)
            
            if event_type in channel_metrics[channel]:
                channel_metrics[channel][event_type] = count
        
        return dict(channel_metrics)
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get channel metrics: {str(e)}")
