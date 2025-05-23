from fastapi import FastAPI, HTTPException, Depends, status
from fastapi.security import HTTPBearer
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import uvicorn
from app.config import settings
from app.routers import chat
from app.middleware.auth import auth_service, create_default_user
from app.models.chat import UserCreate, Token, User
from datetime import timedelta

@asynccontextmanager
async def lifespan(app: FastAPI):
    print("Starting OpenAI chat API backend")
    print(f"Debug mode: {settings.debug}")

    create_default_user()
    print("Default test user created (username: testuser, password: tesetpass123)")

    yield

    print(" shutting down OpenAI Backend")

app = FastAPI(
    title="OpenAI Chat API Backend",
    description="A backend service for integrating with OpenAI's Chat API",
    version="1.0.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(chat.router)

@app.post("/auth/register", response_model=User)
async def register(user_data: UserCreate):
    try:
        user = auth_service.create_user(user_data.username, user_data.password)
        return user

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Registration failed: {str(e)}")
    
@app.post("/auth/login", response_model=Token)
async def login(user_data: UserCreate):
    """login and get access token"""
    user = auth_service.authenticate_user(user_data.username, user_data.password)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Incorrect username or password")
    
    access_token_expires = timedelta(minutes=30)
    access_token = auth_service.create_access_token(
        data={"sub": user["username"]}, expires_delta=access_token_expires
    )

    return {"access_token": access_token, "token_type": "bearer"}

@app.get("/")
async def root():
    return {
        "message": "OpenAI Chat API Backend",
        "version": "1.0.0",
        "status": "running",
        "endpoints": {
            "chat": "/chat/",
            "health": "/chat/health",
            "auth": {
                "register": "/auth/register",
                "login": "/auth/login"
            },
            "docs": "/docs"
        }
    }

@app.get("/health")
async def health():
    return {
        "status": "healty",
        "service": "openai-chat-backend",
        "version": "1.0.0"
    }

if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.debug
    )