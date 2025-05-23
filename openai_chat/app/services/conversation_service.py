import json
import redis
from typing import list, Optional
from datetime import datetime, timedelta
from app.config import settings
from app.models.chat import ChatMessage, ConversationHistory
from app.utils.exceptions import ConversationServiceError
import uuid

class ConversationService: 
    def __init__(self):
        self.redis_client = redis.from_url(settings.redis_url, decode_responses=True)
        self.conversation_ttl = 86400 * 7

    def _get_conversation_key(self, conversation_id: str) -> str:
        return f"conversation:{conversation_id}"
    
    async def save_message(
            self,
            conversation_id: str,
            message: ChatMessage
    ) -> None:
        """save message to chat history"""
        try:
            key = self._get_conversation_key(conversation_id)

            existing_data = self.redis_client.get(key)
            if existing_data:
                conversation_data = json.loads(existing_data)
                messages = conversation_data.get("messages", [])
            else:
                messages = []
                conversation_data = {
                    "conversation_id": conversation_id,
                    "created_at": datetime.now().isoformat(),
                    "messages": []
                }

            message_dict = {
                "role": message.role,
                "content": message.content,
                "timestamp": message.timestamp.isoformat() if message.timestamp else datetime.now().isoformat()
            }

            messages.append(message_dict)

            conversation_data["messages"] = messages
            conversation_data["updated_at"] = datetime.now().isoformat()

            self.redis_client.setex(
                key,
                self.conversation_ttl,
                json.dumps(conversation_data)
            )

        except Exception as e:
            raise ConversationServiceError(f"Failed to save message: {str(e)}")
        
    async def get_conversation_history(
            self,
            conversation_id: str,
            limit: int = 50
    ) -> Optional[ConversationHistory]:
        try:
            key = self._get_conversation_key(conversation_id)
            data = self.redis_client.get(key)

            if not data:
                return None
            
            conversation_data = json.loads(data)

            messages = []
            for msg_data in conversation_data.get("messages", [])[-limit]:
                messages.append(ChatMessage(
                    role=msg_data["role"],
                    content=msg_data["content"],
                    timestamp=datetime.fromisoformat(msg_data["timestamp"])
                ))

            return ConversationHistory(
                conversation_id=conversation_data["conversation_id"],
                messages=messages,
                created_at=datetime.fromisoformat(conversation_data["created_at"]),
                updated_at=datetime.fromisoformat(conversation_data["updated_at"])
            )
        
        except Exception as e:
            raise ConversationServiceError(f"Failed to retrive conversation: {str(e)}")
        
    async def delete_conversation(self, conversation_id: str) -> bool:
        try:
            key = self._get_conversation_key(conversation_id)
            return bool(self.redis_client.delete(key))
        except Exception as e:
            raise ConversationServiceError(f"Failed to delete conversation: {str(e)}")
        
    async def list_user_conversations(self, user_id: str) -> list[str]:
        """All conversationID for a user"""
        try:
            pattern = f"conversation:*"
            keys = self.redis_client.keys(pattern)
            return [key.split(":")[-1] for key in keys]
        except Exception as e:
            raise ConversationServiceError(f"Failed to list conversations:{str(e)}")