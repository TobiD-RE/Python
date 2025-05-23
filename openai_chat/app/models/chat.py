from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from datetime import datetime

class ChatMessage(BaseModel):
    role: str
    content: str
    timestamp: Optional[datetime] = None

class ChatRequest(BaseModel):
    message: str
    conversation_id: Optional[str] = None
    system_prompt: Optional[str] = None
    max_tokens: Optional[int] = 1000
    temperature: Optional[float] = 0.7

class ChatResponse(BaseModel):
    message: str
    conversation_id: str
    usage: Optional[Dict[str, Any]] = None
    model: str

class ConversationHistory(BaseModel):
    conversation_id: str
    messages: List[ChatMessage]
    created_at: datetime
    updated_at: datetime

class UserCreate(BaseModel):
    username: str
    password: str

class User(BaseModel):
    id: str
    username: str
    created_at: datetime

class Token(BaseModel):
    access_token: str
    token_type: str