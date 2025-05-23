from fastapi import HTTPException, Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt
from passlib.context import CryptContext
from datetime import datetime, timedelta
from typing import Optional
import uuid
from app.config import settings
from app.models.chat import User

security = HTTPBearer()
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

fake_users_db = {}

class AuthService:
    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        return pwd_context.verify(plain_password, hashed_password)
    
    def get_password_hash(self, password: str) -> str:
        return pwd_context.hash(password)
    
    def create_access_token(self, data: dict, expires_delta: Optional[timedelta] = None):
        to_encode = data.copy()
        if expires_delta:
            expire = datetime.now() + expires_delta
        else:
            expire = datetime.now() + timedelta(minutes=15)
        to_encode.update({"exp": expire})
        encoded_jwt = jwt.encode(to_encode, settings.secret_key, algorithm=ALGORITHM)
        return encoded_jwt
    
    def verify_token(self, token: str) -> dict:
        try:
            payload = jwt.decode(token, settings.secret_key, algorithms=[ALGORITHM])
            username: str = payload.get("sub")
            if username is None:
                raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Could not validate credentials")
            return payload
        except JWTError:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Could not validate credentials")
            
    def create_user(self, username: str, password: str) -> User:
        if username in fake_users_db:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Username already registered")
        
        user_id = str(uuid.uuid4())
        hashed_password = self.get_password_hash(password)
        user_data = {
            "id": user_id,
            "username": username,
            "hashed_password": hashed_password,
            "created_at": datetime.now()
        }
        fake_users_db[username] = user_data

        return User(
            id=user_id,
            username=username,
            created_at=user_data["created_at"]
        )
    
    def authenticate_user(self, username: str, passowrd: str) -> Optional[dict]:
        user = fake_users_db.get(username)
        if not user:
            return None
        if not self.verify_password(passowrd, user["hashed_password"]):
            return None
        return user
    
auth_service = AuthService()

async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """dependency to get current authed user"""
    try:
        payload = auth_service.verify_token(credentials.credentials)
        username = payload.get("sub")
        user = fake_users_db.get(username)
        if user is None:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Could not validate credentials")
        return user
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Could not validate credentials")
    
def create_default_user():
    if "testuser" not in fake_users_db:
        auth_service.create_user("testuser", "testpass123")

create_default_user()