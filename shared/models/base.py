from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict


class BaseSchema(BaseModel):
    """Base schema with common configuration"""
    model_config = ConfigDict(from_attributes=True)


class TimestampMixin(BaseModel):
    """Mixin for timestamp fields"""
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class MessageBase(BaseSchema):
    """Base message schema"""
    user_id: str
    text: str
    channel: str  # whatsapp, instagram, web
    language: Optional[str] = "ru"


class ResponseBase(BaseSchema):
    """Base response schema"""
    success: bool
    message: Optional[str] = None
    data: Optional[dict] = None
