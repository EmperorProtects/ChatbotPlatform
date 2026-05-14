from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
import httpx
import os
import json
import redis
import logging
from datetime import datetime
import asyncpg
import uuid

app = FastAPI(title="Bot Service", version="1.0.0")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("auth_service")

AI_SERVICE_URL = os.getenv("AI_SERVICE_URL", "http://ai_service:8005")
KNOWLEDGE_SERVICE_URL = os.getenv("KNOWLEDGE_SERVICE_URL", "http://knowledge_service:8006")
REDIS_URL = os.getenv("REDIS_URL", "redis://redis:6379/1")
POSTGRES_USER = os.getenv("POSTGRES_USER", "chatbot_user")
POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD", "chatbot_pass_2024")


# DATABASE_URL =f"postgresql://chatbot_user:chatbot_pass_2024@postgres_userdata:5432/userdata_db"
DATABASE_URL =f"postgresql://{POSTGRES_USER}:{POSTGRES_PASSWORD}@postgres_userdata:5432/userdata_db"

TOP_K_CONTEXT = 10 


# Initialize Redis connection
try:
    redis_client = redis.from_url(REDIS_URL, decode_responses=True)
except Exception:
    redis_client = None


class IncomingMessage(BaseModel):
    user_id: int 
    brief_id: int          
    text: str
    channel: str
    language: Optional[str] = "ru"


class BotResponse(BaseModel):
    user_id: int 
    text: Optional[str]
    channel: str = "whatsapp"

class CreateConversationRequest(BaseModel):
    user_id: int
    channel: Optional[str] = "whatsapp"

class CreateConversationResponse(BaseModel):
    conversation_id: uuid.UUID
    user_id: int
    status: str
    channel: str

async def init_db():
    """Initialize database connection pool"""
    global db_pool
    try:
        db_pool = await asyncpg.create_pool(
            DATABASE_URL,
            min_size=1,
            max_size=10,
            server_settings={
                'application_name': 'bot_service',
            }
        )
        logger.info("Database connection pool created successfully")
        
        # Test the connection
        async with db_pool.acquire() as connection:
            result = await connection.fetchval("SELECT 1")
            logger.info(f"Database connection test: {result}")
            
    except Exception as e:
        logger.error(f"Failed to create message_database pool: {e}")
        raise e


async def close_db():
    """Close database connection pool"""
    global db_pool
    if db_pool:
        await db_pool.close()
        logger.info("Database connection pool closed")


async def set_conversation_status(user_id: int, status: str, ttl_days: int = 7):
    # if redis_client:
    #     redis_client.setex(
    #         f"{BOT_STATUS_PREFIX}{user_id}",
    #         86400,
    #         status
    #     )
    if db_pool:
        try:
            async with db_pool.acquire() as connection:
                await connection.execute(
                    """
                    UPDATE conversations
                    SET status = $2, updated_at = NOW()
                    WHERE user_id = $1
                    """,
                    user_id,
                    status,
                )
                return {"status": "success", "message": f"Status updated to {status}"}
        except Exception as e:
            logger.error(f"Failed to set bot status for user {user_id}: {e}")
            return {status: "error", "message": "Failed to update status"}
    else:
        logger.warning("No database connection available to set bot status")
        return {status: "error", "message": "Database unavailable"}

async def get_conversation_status(user_id: str) -> str:
    # if redis_client:
    #     status = redis_client.get(f"{BOT_STATUS_PREFIX}{user_id}")
    #     if ststatus is not None:
    #     return status or "active"
    if db_pool:
        try:
            async with db_pool.acquire() as connection:
                query = """ SELECT status FROM conversations WHERE user_id = $1 """
                row = await connection.fetchrow(query, user_id)
                if row:
                    return row["status"] or "disabled"
        except Exception as e:
            logger.error(f"Failed to get bot status for user {user_id}: {e}")
    else:
        return "disabled"

async def save_conversation_message(user_id: int, sender_type: str, message: str,) -> Optional[str]:
    """Save conversation message to Redis"""

    if redis_client:
        message_id = str(uuid.uuid4())
        entry = {
            "id": message_id,
            "sender_type": sender_type,
            "message": message,
            "timestamp": datetime.utcnow().isoformat(),
        }
        redis_client.setex(f"id:{message_id}", 86400, json.dumps(entry))
        redis_client.lpush(f"conversation:{user_id}", message_id)
        redis_client.expire(f"conversation:{user_id}", 86400)
    if db_pool:
        try:
            async with db_pool.acquire() as connection:
                query = """SELECT id FROM conversations WHERE user_id = $1 ORDER BY updated_at DESC LIMIT 1"""
                row = await connection.fetchrow(query, user_id)
                if row:
                    conversation_id = row["id"]
                await connection.execute(
                    """
                    INSERT INTO messages (id, conversation_id, sender_type, message)
                    VALUES ($1, $2, $3, $4)
                    """,
                    str(uuid.uuid4()),
                    conversation_id,
                    sender_type,
                    message,
                )
        except Exception as e:
            logger.error(f"Failed to save conversation message for user {user_id}: {e}")

    logger.info(f"Saved message for user {user_id}: {sender_type} - {message[:50]}...")


async def get_conversation_history(user_id: int, limit: int = 50) -> List[Dict[str, Any]]:
    if redis_client:
        try:
            message_ids = redis_client.lrange(f"conversation:{user_id}", 0, limit - 1)
            messages = []
            if message_ids:
                messages = []
                for mid in message_ids:
                    raw = redis_client.get(f"id:{mid}")
                    if raw:
                        messages.append(json.loads(raw))
                    messages = sorted(messages, key=lambda x: x["timestamp"], reverse=False)
            return messages
        except Exception:
            pass
    if db_pool:
        try:
            async with db_pool.acquire() as connection:
                query = """
                    SELECT id, sender_type, message, created_at
                    FROM messages
                    WHERE conversation_id = (
                        SELECT id FROM conversations WHERE user_id = $1 ORDER BY updated_at DESC LIMIT 1
                    )
                    ORDER BY created_at DESC
                    LIMIT $2
                """
                rows = await connection.fetch(query, user_id, limit)
     
                messages = [{ "id": str(row["id"]),"sender_type": row["sender_type"], "message": row["message"], "timestamp": row["created_at"].isoformat()} for row in rows]
                if redis_client:
                    for message in messages:
                        redis_client.setex(f"id:{message['id']}", 86400, json.dumps(message))
                        redis_client.rpush(f"conversation:{user_id}", message["id"])
                return messages
        except Exception as e:
            logger.error(f"Failed to get conversation history for user {user_id}: {e}")

async def get_all_conversations_query(limit: int = 100) -> List[Dict[str, Any]]:
    if not db_pool:
        return []
    try:
        async with db_pool.acquire() as connection:
            query = """ SELECT id, user_id, channel, status, created_at, updated_at FROM conversations ORDER BY updated_at DESC LIMIT $1 """
            conversations = await connection.fetch(query, limit)
            result = []

            for conv in conversations:
                query = """ SELECT id, sender_type, message, created_at FROM messages WHERE conversation_id = $1 ORDER BY created_at DESC LIMIT 10 """
                rows = await connection.fetch(query, conv["id"])
                messages = [{ "id": str(msg["id"]),"sender_type": msg["sender_type"], "message": msg["message"], "timestamp": msg["created_at"].isoformat()} for msg in rows]

                logger.info(f"Fetched {len(messages)} messages for conversation {conv['id']}")

                result.append({
                    "conversation_id": str(conv["id"]),
                    "user_id": conv["user_id"],
                    "channel": conv["channel"],
                    "status": conv["status"],
                    "created_at": conv["created_at"].isoformat(),
                    "updated_at": conv["updated_at"].isoformat(),
                    "messages": messages
                })

                if redis_client:
                    for message in messages:
                        redis_client.setex(f"id:{message['id']}", 86400, json.dumps(message))
                        redis_client.rpush(f"conversation:{conv['id']}", message["id"])
            return result
    except Exception as e:
        logger.error(f"Failed to get all conversations: {e}")


async def fetch_knowledge_context(user_id: str, brief_id: int, text: str, language: str) -> str:
    """
    ✅ Главное: передаём user_id, чтобы knowledge_service подтянул user_collection.
    """
    payload = {
        "query": text,
        "language": language,
        "brief_id": brief_id,
        "user_id": user_id,   # ✅ добавили
        "top_k": TOP_K_CONTEXT,
    }

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            r = await client.post(f"{KNOWLEDGE_SERVICE_URL}/search", json=payload)
            if r.status_code != 200:
                return ""
            data = r.json()
            return data.get("context", "") or "", data.get("conversation_history", "")
    except Exception:
        return ""

async def fetch_system_prompt(brief_id: int = 1) -> str:
    payload = {
        "brief_id": brief_id,
        "metadata_filters":{
            "type":"system_prompt"
        }
    }
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            r = await client.post(
                f"{KNOWLEDGE_SERVICE_URL}/search/by_metadata",
                json=payload
            )
            if r.status_code == 200:
                data = r.json()
                results = data.get("results", [])
                system_prompt = results[0]["text"] if results else ""

                return system_prompt
    except Exception as e:
        logger.error(f"Failed to fetch system prompt for brief_id {brief_id}: {e}")
        system_prompt = None


async def save_user_memory(user_id: str, brief_id: int, message: str, response: str, channel: str = "whatsapp") -> None:
    """
    Опционально: сохраняем “память” пользователя в user_collection.
    Это НЕ вся переписка, а короткий факт/сводка.
    Пока делаем простой вариант: последние 1-2 фразы.
    """
    # Слишком длинное хранить не надо
    memory_text = f"[{channel}] User said: {message}\nBot replied: {response}"
    if len(memory_text) > 800:
        memory_text = memory_text[:800] + "..."

    payload = {
        "user_id": user_id,
        "brief_id": brief_id,
        "category": "history",
        "title": "Conversation snippet",
        "text": memory_text,
        "metadata": {"source": "bot_service"},
    }

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            await client.post(f"{KNOWLEDGE_SERVICE_URL}/add/user", json=payload)
    except Exception:
        # намеренно молчим, чтобы бот не падал
        pass

@app.on_event("startup")
async def startup_event():
    await init_db()

@app.on_event("shutdown")
async def shutdown_event():
    await close_db()


@app.get("/")
async def root():
    return {"message": "Bot Service", "version": "1.0.0"}


@app.get("/health")
async def health():
    redis_status = "connected" if redis_client else "disconnected"
    return {
        "status": "healthy",
        "redis": redis_status,
        "services": {"ai_service": AI_SERVICE_URL, "knowledge_service": KNOWLEDGE_SERVICE_URL},
    }


@app.post("/incoming", response_model=BotResponse)
async def handle_incoming_message(message: IncomingMessage):
    if not message.text.strip():
        raise HTTPException(status_code=400, detail="Message text cannot be empty")

    if len(message.text) > 2000:
        raise HTTPException(status_code=400, detail="Message text is too long (max 2000 characters)")


    if not db_pool:
        raise HTTPException(status_code=503, detail="Database unavailable")
        
    try:
        async with db_pool.acquire() as connection:
            row = await connection.fetchrow(
                """
                SELECT id, status FROM conversations 
                WHERE user_id = $1 
                ORDER BY updated_at DESC 
                LIMIT 1
                """,
                message.user_id,
            )
    except Exception as e:
        logger.error(f"Failed to fetch conversation for user {message.user_id}: {e}")
        raise HTTPException(status_code=500, detail="Database error")

    if not row:
        try:
            async with db_pool.acquire() as connection:
                row = await connection.fetchrow(
                    """
                    INSERT INTO conversations (id, user_id, channel, status)
                    VALUES ($1, $2, $3, 'enabled')
                    RETURNING id, status
                    """,
                    str(uuid.uuid4()),
                    message.user_id,
                    message.channel,
                )
        except Exception as e:
            logger.error(f"Failed to create conversation for user {message.user_id}: {e}")
            raise HTTPException(status_code=500, detail="Failed to create conversation")

    if await get_conversation_status(message.user_id) == "disabled":
        return BotResponse(
            user_id=message.user_id,
            text=None,
            # channel=message.channel
            channel="whatsapp"
        )

    # 1) knowledge context (business + user memory)
    context, conversation_history = await fetch_knowledge_context(
        user_id=message.user_id,
        brief_id=message.brief_id,
        text=message.text,
        language=message.language or "ru",
    )

    system_prompt = await fetch_system_prompt(message.brief_id)

    # 2) AI response
    bot_text = "Sorry, I couldn't generate a response."
    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            r = await client.post(
                f"{AI_SERVICE_URL}/generate",
                json={
                    "user_message": message.text,
                    "context": context,
                    "conversation_history": conversation_history,
                    "language": message.language,
                    "user_id": message.user_id,
                    "brief_id": message.brief_id,  # полезно для AI тоже
                    "system_prompt": system_prompt,
                },
            )
            if r.status_code == 200:
                logger.info(f"AI service response for user {message.user_id}: {r.text[:100]}...")
                bot_text = (r.json().get("response") or bot_text)

            else:
                bot_text = "Sorry, I'm having trouble processing your request right now."
    except Exception:
        bot_text = "Sorry, I'm experiencing technical difficulties. Please try again later."

    try:
        await save_conversation_message(message.user_id, "user", message.text)
        await save_conversation_message(message.user_id, "bot", bot_text)
    except Exception:
        pass

    await save_user_memory(message.user_id, message.brief_id, message.text, bot_text, message.channel)

    return BotResponse(user_id=message.user_id, text=bot_text, channel="whatsapp")


@app.get("/conversation/{user_id}")
async def get_conversation_history_endpoint(user_id: str, limit: Optional[int] = 50):
    messages = await get_conversation_history(user_id, limit or 50)
    return {"user_id": user_id, "messages": messages, "count": len(messages)}

@app.get("/conversation")
async def get_all_conversations(limit: Optional[int] = 100):
    conversations = await get_all_conversations_query(limit or 100)
    return {"conversations": conversations, "count": len(conversations)}

@app.post("/conversation/create", response_model=CreateConversationResponse)
async def create_conversation(request: CreateConversationRequest):
    if not db_pool:
        raise HTTPException(status_code=503, detail="Database unavailable")
    
    try:
        async with db_pool.acquire() as connection:
            row = await connection.fetchrow(
                """
                INSERT INTO conversations (user_id, channel, status)
                VALUES ($1, $2, 'enabled')
                RETURNING id, user_id, status, channel
                """,
                request.user_id,
                request.channel,
            )
            return CreateConversationResponse(
                conversation_id=row["id"],
                user_id=row["user_id"],
                status=row["status"],
                channel=row["channel"],
            )
    except Exception as e:
        logger.error(f"Failed to create conversation for user {request.user_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to create conversation")


@app.post("/conversation/disable/{user_id}")
async def disable_conversation(user_id: int):
    r =await set_conversation_status(user_id, "disabled")
    return {"status": r.get("status", "error"), "message": r.get("message", "")}

@app.post("/conversation/enable/{user_id}")
async def enable_conversation(user_id: int):
    r = await set_conversation_status(user_id, "enabled")
    return {"status": r.get("status", "error"), "message": r.get("message", "")}
