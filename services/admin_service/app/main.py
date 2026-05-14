from fastapi import FastAPI, HTTPException, Depends
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
import httpx
import os
from datetime import datetime

app = FastAPI(title="Admin Service", version="1.0.0", description="Administrative interface for chatbot platform")

# Service URLs
KNOWLEDGE_SERVICE_URL = os.getenv("KNOWLEDGE_SERVICE_URL", "http://knowledge_service:8006")
AI_SERVICE_URL = os.getenv("AI_SERVICE_URL", "http://ai_service:8005")
BOT_SERVICE_URL = os.getenv("BOT_SERVICE_URL", "http://bot_service:8002")
AUTH_SERVICE_URL = os.getenv("AUTH_SERVICE_URL", "http://auth_service:8001")


# Models
class KnowledgeItem(BaseModel):
    title: str
    content: str
    brief_id: str
    language: Optional[str] = "ru"
    metadata: Optional[Dict[str, Any]] = None


class BriefConfig(BaseModel):
    brief_id: str
    name: str
    description: str
    language: str = "ru"
    active: bool = True


class SystemStats(BaseModel):
    services_status: Dict[str, str]
    knowledge_base_stats: Dict[str, Any]
    conversation_stats: Dict[str, Any]

@app.get("/")
async def root():
    return {
        "message": "Admin Service", 
        "version": "1.0.0",
        "description": "Administrative interface for chatbot platform",
        "endpoints": [
            "/health", 
            "/stats", 
            "/knowledge", 
            "/briefs",
            "/services/status"
        ]
    }
@app.get("/health")
async def health_check():
    return {"status": "healthy", "timestamp": datetime.utcnow().isoformat()}

@app.get("/stats")
async def get_system_stats():
    """Get system-wide statistics"""
    stats = {
        "services_status": {},
        "knowledge_base_stats": {},
        "timestamp": datetime.utcnow().isoformat()
    }
    
    # Check service statuses
    services = {
        "knowledge_service": KNOWLEDGE_SERVICE_URL,
        "ai_service": AI_SERVICE_URL,
        "bot_service": BOT_SERVICE_URL,
        "auth_service": AUTH_SERVICE_URL
    }
    
    async with httpx.AsyncClient(timeout=5.0) as client:
        for service_name, service_url in services.items():
            try:
                response = await client.get(f"{service_url}/health")
                if response.status_code == 200:
                    stats["services_status"][service_name] = "healthy"
                else:
                    stats["services_status"][service_name] = f"unhealthy ({response.status_code})"
            except Exception as e:
                stats["services_status"][service_name] = f"error ({str(e)[:50]})"
    
    # Get knowledge base stats
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(f"{KNOWLEDGE_SERVICE_URL}/stats")
            if response.status_code == 200:
                stats["knowledge_base_stats"] = response.json()
            else:
                stats["knowledge_base_stats"] = {"error": "Could not fetch stats"}
    except Exception as e:
        stats["knowledge_base_stats"] = {"error": str(e)}
    
    return stats


@app.get("/services/status")
async def get_services_status():
    """Get detailed status of all services"""
    services = {
        "knowledge_service": KNOWLEDGE_SERVICE_URL,
        "ai_service": AI_SERVICE_URL,
        "bot_service": BOT_SERVICE_URL,
        "auth_service": AUTH_SERVICE_URL
    }
    
    status_details = {}
    
    async with httpx.AsyncClient(timeout=10.0) as client:
        for service_name, service_url in services.items():
            try:
                # Get health status
                health_response = await client.get(f"{service_url}/health")
                
                # Get root info
                root_response = await client.get(f"{service_url}/")
                
                status_details[service_name] = {
                    "url": service_url,
                    "status": "healthy" if health_response.status_code == 200 else "unhealthy",
                    "health_data": health_response.json() if health_response.status_code == 200 else None,
                    "info": root_response.json() if root_response.status_code == 200 else None,
                    "last_checked": datetime.utcnow().isoformat()
                }
            except Exception as e:
                status_details[service_name] = {
                    "url": service_url,
                    "status": "error",
                    "error": str(e),
                    "last_checked": datetime.utcnow().isoformat()
                }
    
    return status_details


@app.post("/knowledge")
async def add_knowledge_item(item: KnowledgeItem):
    """Add knowledge item via admin interface"""
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{KNOWLEDGE_SERVICE_URL}/add",
                json={
                    "title": item.title,
                    "content": item.content,
                    "brief_id": item.brief_id,
                    "language": item.language,
                    "metadata": item.metadata or {}
                }
            )
            
            if response.status_code == 200:
                return {"status": "success", "data": response.json()}
            else:
                raise HTTPException(status_code=response.status_code, detail=response.text)
                
    except httpx.HTTPError as e:
        raise HTTPException(status_code=503, detail=f"Knowledge service unavailable: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to add knowledge: {str(e)}")


@app.get("/knowledge")
async def list_knowledge_items(brief_id: Optional[str] = None, limit: int = 50):
    """List knowledge items"""
    try:
        params = {"limit": limit}
        if brief_id:
            params["brief_id"] = brief_id
            
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(
                f"{KNOWLEDGE_SERVICE_URL}/list",
                params=params
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                raise HTTPException(status_code=response.status_code, detail=response.text)
                
    except httpx.HTTPError as e:
        raise HTTPException(status_code=503, detail=f"Knowledge service unavailable: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list knowledge: {str(e)}")
