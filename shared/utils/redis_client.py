import json
from typing import Optional, Any
import redis.asyncio as redis
from shared.utils.logger import get_logger

logger = get_logger(__name__)


class RedisClient:
    """Redis client wrapper"""
    
    def __init__(self, url: str):
        self.url = url
        self.client: Optional[redis.Redis] = None
    
    async def connect(self):
        """Connect to Redis"""
        self.client = await redis.from_url(self.url, encoding="utf-8", decode_responses=True)
        logger.info("Connected to Redis")
    
    async def disconnect(self):
        """Disconnect from Redis"""
        if self.client:
            await self.client.close()
            logger.info("Disconnected from Redis")
    
    async def get(self, key: str) -> Optional[Any]:
        """Get value from Redis"""
        value = await self.client.get(key)
        if value:
            try:
                return json.loads(value)
            except json.JSONDecodeError:
                return value
        return None
    
    async def set(self, key: str, value: Any, expire: Optional[int] = None):
        """Set value in Redis"""
        if isinstance(value, (dict, list)):
            value = json.dumps(value)
        await self.client.set(key, value, ex=expire)
    
    async def delete(self, key: str):
        """Delete key from Redis"""
        await self.client.delete(key)
