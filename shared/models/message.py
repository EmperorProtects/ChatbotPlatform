from enum import Enum
from typing import Optional
from pydantic import BaseModel


class ChannelType(str, Enum):
    WHATSAPP = "whatsapp"
    INSTAGRAM = "instagram"
    WEB = "web"


class MessageType(str, Enum):
    TEXT = "text"
    IMAGE = "image"
    DOCUMENT = "document"


class IncomingMessage(BaseModel):
    """Incoming message from any channel"""
    message_id: str
    user_id: str
    channel: ChannelType
    message_type: MessageType
    text: Optional[str] = None
    media_url: Optional[str] = None
    timestamp: int


class OutgoingMessage(BaseModel):
    """Outgoing message to any channel"""
    user_id: str
    channel: ChannelType
    text: str
    media_url: Optional[str] = None
