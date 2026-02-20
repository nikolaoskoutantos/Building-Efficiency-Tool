import time
from fastapi import Request, HTTPException
from collections import defaultdict
import threading

# Simple in-memory rate limiter (per IP)
class RateLimiter:
    def __init__(self, max_requests: int, window_seconds: int):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.requests = defaultdict(list)
        self.lock = threading.Lock()

    def is_allowed(self, key: str) -> bool:
        now = time.time()
        with self.lock:
            reqs = self.requests[key]
            # Remove old requests
            self.requests[key] = [t for t in reqs if now - t < self.window_seconds]
            if len(self.requests[key]) >= self.max_requests:
                return False
            self.requests[key].append(now)
            return True

rate_limiter = RateLimiter(max_requests=5, window_seconds=60)  # 5 requests per minute per IP

def rate_limit_dependency(request: Request):
    ip = request.client.host
    if not rate_limiter.is_allowed(ip):
        raise HTTPException(status_code=429, detail="Too many requests. Please try again later.")
