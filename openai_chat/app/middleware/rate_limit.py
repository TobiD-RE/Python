import time
import redis
from functools import wraps
from fastapi import HTTPException, Request, status
from app.config import settings

redis_client = redis.from_url(settings.redis_url, decode_response=True)

class RateLimiter:
    def __init__(self, redis_client, max_requests: int = 10, window_minutes: int = 1):
        self.redis_client = redis_client
        self.max_requests = max_requests
        self.window_seconds = window_minutes * 60

    def is_allowed(self, identifier: str) -> tuple[bool, dict]:
        """check if request is allowed based on rate limit"""
        key = f"rate_limit:{identifier}"
        current_time = int(time.time())
        window_start = current_time - self.window_seconds

        pipe = self.redis_client.pipeline()

        pipe.zremrangebyscore(key, 0, window_start)

        pipe.zcard(key)

        pipe.zadd(key, {str(current_time): current_time})

        pipe.expire(key, self.window_seconds)

        results = pipe.execute()
        current_requests = results[1]

        if current_requests >= self.max_requests:
            return False, {
                "allowed": False,
                "limit": self.max_requests,
                "remaining": 0,
                "reset_time": window_start + self.window_seconds
            }
        
        return True, {
            "allowed": True,
            "limit": self.max_requests,
            "remaining": self.max_requests - current_requests - 1,
            "reset_time": window_start + self.window_seconds
        }
    
rate_limiter = RateLimiter(
    redis_client,
    max_requests=settings.rate_limit_per_minute,
    window_mintues=1
)

def rate_limit(func):
    @wraps(func)
    async def wrapper(*args, **kwargs):
        request = None
        for arg in args:
            if isinstance(arg, Request):
                request = arg
                break

        if not request:
            return await func(*args, **kwargs)
        
        client_ip = request.client.host
        identifier = f"ip:{client_ip}"

        is_allowed, rate_info = rate_limiter.is_allowed(identifier)

        if not is_allowed:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail={
                    "message": "Rate limit exceeded",
                    "limit": rate_info["limit"],
                    "rest_time": rate_info["rest_time"]
                }
            )
        
        response = await func(*args, **kwargs)

        return response
    
    return wrapper