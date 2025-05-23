from fastapi import APIRouter, HTTPException, Depends, status
from typing import Optional, List
from datetime import datetime
import uuid
from app.models.chat import ChatRequest, ChatResponse, ChatMessage, ConversationHistory
from app.services.openai_service import OpenAIService
from app.services.conversation_service import ConversationService
from app.middleware.auth import get_current_user
from app.middleware.rate_limit import rate_limit
from app.utils.exceptions import OpenAIServiceError, ConversationServiceError

router = APIRouter(prefix="/chat", tags=["chat"])

openai_service = OpenAIService()
conversation_service = ConversationService()

@router.post("/", response_model=ChatResponse)
@rate_limit
async def chat(
    request: ChatRequest,
    current_user: dict = Depends(get_current_user)
):
    """send message and get ai response"""
    try:
        conversation_id = request.conversation_id or str(uuid.uuid4())

        history = await conversation_service.get_conversation_history(conversation_id)
        messages = history.messages if history else []

        if request.system_prompt and (not messages or messages[0].role != "system"):
            system_message = ChatMessage(
                role="system",
                content=request.system_prompt,
                timestamp=datetime.now()
            )
            messages.insert(0, system_message)
            await conversation_service.save_message(conversation_id, system_message)

        user_message = ChatMessage(
            role="user",
            content=request.message,
            timestamp=datetime.now()
        )
        messages.append(user_message)
        await conversation_service.save_message(conversation_id, user_message)

        response = await openai_service.chat_completion(
            messages=messages,
            max_tokens=request.max_tokens,
            temperature=request.temperature,
            conversation_id=conversation_id
        )

        assistant_message = ChatMessage(
            role="assistant",
            content=response.message,
            timestamp=datetime.now()
        )
        await conversation_service.save_message(conversation_id, assistant_message)

        return response
    
    except OpenAIServiceError as e:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=f"OpenAI service error: {str(e)}")
    
    except ConversationServiceError as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Conversation service error: {str(e)}")
    
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Unecpected error: {str(e)}")
    
@router.get("/history/{conversation_id}", response_model=ConversationHistory)
async def get_conversation_history(
    conversation_id: str,
    limit: int = 50,
    current_user: dict = Depends(get_current_user)
):
    try:
        history = await conversation_service.get_conversation_history(conversation_id, limit)

        if not history:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Conversation not found")
        return history
    except ConversationServiceError as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to retrieve conversation: {str(e)}")
    
@router.delete("/history/{conversation_id}")
async def delete_conversation(conversation_id: str, current_user: dict = Depends(get_current_user)):
    try:
        deleted = await conversation_service.delete_conversation(conversation_id)

        if not deleted:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversation not found")
        
        return {"message": "Conversation deleted successfully"}
    
    except ConversationServiceError as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Dailed to delete conversation: {str(e)}")
    
@router.get("/conversations", response_model=List[str])
async def list_conversations(current_user: dict = Depends(get_current_user)):
    try:
        conversations = await conversation_service.list_user_conversations(current_user["id"])
        return conversations
    except ConversationServiceError as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to list conversations: {str(e)}")
    

@router.get("/health")
async def health_check():
    try:
        openai_status = await openai_service.validate_api_key()

        return {
            "status": "healthy" if openai_status else "degraded",
            "openai_api": "connected" if openai_status else "disconnected",
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "openai_api": str(e),
            "timestamp": datetime.now().isoformat()
        }