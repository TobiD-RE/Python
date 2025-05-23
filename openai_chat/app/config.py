import os
from typing import Optional
from pydantic_settings import BaseSettings
from dotenv import load_dotenv

load_dotenv()

class Settings(BaseSettings):
    openai_api_key: str
    secret_key: str
    redis_url: str = "redis://localhost:6379"
    rate_limit_per_minute: int = 10
    debug: bool = False

    class Config:
        env_file = ".env"


settings = Settings()