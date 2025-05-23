import asyncio
from typing import List, Dict, Any, Optional
from openai import AsyncOpenAI
from app.config import settings
from app.models.chat import ChatMessage, ChatResponse
from app.utils.exceptions import OpenAIServiceError
import uuid

class OpenAIService:
    def __init__(self):
        self.client = AsyncOpenAI(api_key=settings.openai_api_key)
        self.default_model = "gpt-3.5-turbo"
    
    async def chat_completion(
        self,
        messages: List[ChatMessage],
        model: str = None,
        max_tokens: int = 1000,
        temperature: float = 0.7,
        conversation_id: str = None
    ) -> ChatResponse:
        """send chat completion request to openai api"""
        try:
            openai_messages = [
                {"role": msg.role, "content": msg.content}
                for msg in messages
            ]

            response = await self.client.chat.completions.create(
                model=model or self.default_model,
                messages=openai_messages,
                max_tokens=max_tokens,
                temperature=temperature
            )

            assistant_message = response.choices[0].message.content

            return ChatResponse(
                message=assistant_message,
                conversation_id=conversation_id or str(uuid.uuid4()),
                usage=response.usage.model_dump() if response.usage else None,
                model=response.model
            )
        
        except Exception as e:
            raise OpenAIServiceError(f"OpenAI API error: {str(e)}")
        
    async def validate_api_key(self) -> bool:
        try:
            models = await self.client.models.list()
            return True
        except Exception:
            return False
