"""
Rate Limiting Middleware for ContentOS

Implements token bucket rate limiting to prevent API abuse.
Configurable via environment variables.
"""
import time
import hashlib
from typing import Dict, Tuple, Optional
from collections import defaultdict
from dataclasses import dataclass
from fastapi import Request, HTTPException, status
from starlette.middleware.base import BaseHTTPMiddleware
import logging

logger = logging.getLogger(__name__)


@dataclass
class RateLimitConfig:
    """Rate limit configuration."""
    requests_per_minute: int = 60  # Default: 60 requests per minute
    burst_size: int = 10           # Allow bursts of up to 10 requests
    
    
class TokenBucket:
    """Token bucket for rate limiting."""
    
    def __init__(self, rate: float, capacity: int):
        """
        Initialize token bucket.
        
        Args:
            rate: Tokens per second
            capacity: Maximum tokens (burst capacity)
        """
        self.rate = rate
        self.capacity = capacity
        self.tokens = capacity
        self.last_update = time.time()
    
    def consume(self, tokens: int = 1) -> Tuple[bool, float]:
        """
        Attempt to consume tokens.
        
        Returns:
            Tuple of (success, wait_time_if_failed)
        """
        now = time.time()
        elapsed = now - self.last_update
        self.last_update = now
        
        # Add tokens based on elapsed time
        self.tokens = min(self.capacity, self.tokens + elapsed * self.rate)
        
        if self.tokens >= tokens:
            self.tokens -= tokens
            return True, 0
        
        # Calculate wait time
        wait_time = (tokens - self.tokens) / self.rate
        return False, wait_time


class RateLimiter:
    """In-memory rate limiter using token bucket algorithm."""
    
    def __init__(self, config: Optional[RateLimitConfig] = None):
        self.config = config or RateLimitConfig()
        self.buckets: Dict[str, TokenBucket] = {}
        self._cleanup_counter = 0
        self._cleanup_interval = 1000  # Cleanup every 1000 requests
        
    def _get_client_key(self, request: Request) -> str:
        """Get unique key for client (IP + optional user)."""
        # Get client IP
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            ip = forwarded.split(",")[0].strip()
        else:
            ip = request.client.host if request.client else "unknown"
        
        # Include Authorization header hash for authenticated requests
        auth = request.headers.get("Authorization", "")
        if auth:
            auth_hash = hashlib.md5(auth.encode()).hexdigest()[:8]
            return f"{ip}:{auth_hash}"
        
        return ip
    
    def _get_bucket(self, key: str) -> TokenBucket:
        """Get or create token bucket for key."""
        if key not in self.buckets:
            rate = self.config.requests_per_minute / 60.0  # Convert to per-second
            self.buckets[key] = TokenBucket(rate, self.config.burst_size)
        return self.buckets[key]
    
    def _cleanup_old_buckets(self):
        """Remove stale buckets to prevent memory growth."""
        self._cleanup_counter += 1
        if self._cleanup_counter >= self._cleanup_interval:
            self._cleanup_counter = 0
            now = time.time()
            stale_keys = [
                key for key, bucket in self.buckets.items()
                if now - bucket.last_update > 3600  # 1 hour stale
            ]
            for key in stale_keys:
                del self.buckets[key]
            if stale_keys:
                logger.debug(f"Cleaned up {len(stale_keys)} stale rate limit buckets")
    
    def check_rate_limit(self, request: Request) -> Tuple[bool, float, int]:
        """
        Check if request is within rate limit.
        
        Returns:
            Tuple of (allowed, wait_time, remaining_tokens)
        """
        self._cleanup_old_buckets()
        
        key = self._get_client_key(request)
        bucket = self._get_bucket(key)
        allowed, wait_time = bucket.consume()
        
        return allowed, wait_time, int(bucket.tokens)


class RateLimitMiddleware(BaseHTTPMiddleware):
    """FastAPI middleware for rate limiting."""
    
    # Paths exempt from rate limiting
    EXEMPT_PATHS = {
        "/health",
        "/docs",
        "/redoc", 
        "/openapi.json",
        "/",
    }
    
    def __init__(self, app, config: Optional[RateLimitConfig] = None):
        super().__init__(app)
        self.limiter = RateLimiter(config)
        self.config = config or RateLimitConfig()
        
    async def dispatch(self, request: Request, call_next):
        # Skip rate limiting for exempt paths
        if request.url.path in self.EXEMPT_PATHS:
            return await call_next(request)
        
        # Skip for static files
        if request.url.path.startswith("/uploads"):
            return await call_next(request)
        
        allowed, wait_time, remaining = self.limiter.check_rate_limit(request)
        
        if not allowed:
            logger.warning(f"Rate limit exceeded for {request.client.host if request.client else 'unknown'}")
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail={
                    "error": "rate_limit_exceeded",
                    "message": "Too many requests. Please slow down.",
                    "retry_after_seconds": round(wait_time, 2),
                },
                headers={
                    "Retry-After": str(int(wait_time) + 1),
                    "X-RateLimit-Limit": str(self.config.requests_per_minute),
                    "X-RateLimit-Remaining": "0",
                }
            )
        
        response = await call_next(request)
        
        # Add rate limit headers
        response.headers["X-RateLimit-Limit"] = str(self.config.requests_per_minute)
        response.headers["X-RateLimit-Remaining"] = str(remaining)
        
        return response


def create_rate_limiter(requests_per_minute: int = 60, burst_size: int = 10) -> RateLimitMiddleware:
    """Factory function to create rate limiter middleware."""
    config = RateLimitConfig(
        requests_per_minute=requests_per_minute,
        burst_size=burst_size,
    )
    return lambda app: RateLimitMiddleware(app, config)
