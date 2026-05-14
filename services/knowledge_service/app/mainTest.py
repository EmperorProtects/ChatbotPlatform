from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Optional, List
import httpx
import os

app = FastAPI(title="Knowledge Service", version="1.0.0")

CHROMA_URL = os.getenv("CHROMA_URL", "http://chroma:8000")
OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://ollama:11434")
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "nomic-embed-text")


class SearchRequest(BaseModel):
    query: str
    language: Optional[str] = "ru"
    top_k: Optional[int] = 5


class SearchResponse(BaseModel):
    context: str
    sources: List[dict]


class AddKnowledgeRequest(BaseModel):
    text: str
    metadata: dict
    brief_id: Optional[int] = None


@app.get("/")
async def root():
    return {"message": "Knowledge Service", "version": "1.0.0"}


@app.get("/health")
async def health():
    return {"status": "healthy"}


@app.post("/search", response_model=SearchResponse)
async def search_knowledge(request: SearchRequest):
    """Search knowledge base using semantic search"""
    
    try:
        # Generate embedding for query
        async with httpx.AsyncClient(timeout=30.0) as client:
            embed_response = await client.post(
                f"{OLLAMA_HOST}/api/embeddings",
                json={
                    "model": EMBEDDING_MODEL,
                    "prompt": request.query
                }
            )
            query_embedding = embed_response.json().get("embedding", [])
        
        # TODO: Search in ChromaDB
        # For now, return mock data
        context = "Это пример контекста из базы знаний."
        sources = [{"text": "Пример источника", "score": 0.95}]
        
        return SearchResponse(
            context=context,
            sources=sources
        )
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Search failed: {str(e)}")


@app.post("/add")
async def add_knowledge(request: AddKnowledgeRequest):
    """Add knowledge to the database"""
    
    try:
        # Generate embedding
        async with httpx.AsyncClient(timeout=30.0) as client:
            embed_response = await client.post(
                f"{OLLAMA_HOST}/api/embeddings",
                json={
                    "model": EMBEDDING_MODEL,
                    "prompt": request.text
                }
            )
            embedding = embed_response.json().get("embedding", [])
        
        # TODO: Store in ChromaDB
        
        return {"status": "success", "message": "Knowledge added"}
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to add knowledge: {str(e)}")
