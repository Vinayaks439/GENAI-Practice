"""
Rate Limiter
Token bucket and sliding window rate limiting for AI operations.
"""
import time
import threading
from typing import Optional
from dataclasses import dataclass, field
from collections import defaultdict
from enum import Enum


class RateLimitStrategy(Enum):
    """Rate limiting strategies."""
    TOKEN_BUCKET = "token_bucket"
    SLIDING_WINDOW = "sliding_window"
    FIXED_WINDOW = "fixed_window"


@dataclass
class RateLimitResult:
    """Result of a rate limit check."""
    allowed: bool
    remaining: int
    reset_time: float
    retry_after: Optional[float] = None
    limit: int = 0
    window: int = 0


class TokenBucket:
    """Token bucket rate limiter implementation."""
    
    def __init__(
        self,
        capacity: int,
        refill_rate: float,
        refill_amount: int = 1
    ):
        """
        Initialize token bucket.
        
        Args:
            capacity: Maximum tokens in bucket
            refill_rate: Seconds between refills
            refill_amount: Tokens added per refill
        """
        self.capacity = capacity
        self.refill_rate = refill_rate
        self.refill_amount = refill_amount
        
        self.tokens = capacity
        self.last_refill = time.time()
        self.lock = threading.Lock()
    
    def _refill(self):
        """Refill tokens based on elapsed time."""
        now = time.time()
        elapsed = now - self.last_refill
        
        refills = int(elapsed / self.refill_rate)
        if refills > 0:
            self.tokens = min(self.capacity, self.tokens + refills * self.refill_amount)
            self.last_refill = now
    
    def consume(self, tokens: int = 1) -> RateLimitResult:
        """
        Attempt to consume tokens.
        
        Args:
            tokens: Number of tokens to consume
            
        Returns:
            RateLimitResult indicating if request is allowed
        """
        with self.lock:
            self._refill()
            
            if self.tokens >= tokens:
                self.tokens -= tokens
                return RateLimitResult(
                    allowed=True,
                    remaining=self.tokens,
                    reset_time=self.last_refill + self.refill_rate,
                    limit=self.capacity,
                    window=int(self.refill_rate)
                )
            else:
                # Calculate retry time
                tokens_needed = tokens - self.tokens
                refills_needed = (tokens_needed + self.refill_amount - 1) // self.refill_amount
                retry_after = refills_needed * self.refill_rate
                
                return RateLimitResult(
                    allowed=False,
                    remaining=self.tokens,
                    reset_time=self.last_refill + self.refill_rate,
                    retry_after=retry_after,
                    limit=self.capacity,
                    window=int(self.refill_rate)
                )


class SlidingWindowCounter:
    """Sliding window rate limiter implementation."""
    
    def __init__(self, limit: int, window_seconds: int):
        """
        Initialize sliding window counter.
        
        Args:
            limit: Maximum requests per window
            window_seconds: Window size in seconds
        """
        self.limit = limit
        self.window = window_seconds
        
        self.current_count = 0
        self.previous_count = 0
        self.window_start = time.time()
        self.lock = threading.Lock()
    
    def _get_weighted_count(self) -> float:
        """Get weighted request count using sliding window."""
        now = time.time()
        elapsed = now - self.window_start
        
        # Reset if we've passed the window
        if elapsed >= self.window:
            windows_passed = int(elapsed / self.window)
            self.window_start += windows_passed * self.window
            elapsed = now - self.window_start
            
            if windows_passed >= 2:
                self.previous_count = 0
                self.current_count = 0
            else:
                self.previous_count = self.current_count
                self.current_count = 0
        
        # Calculate weighted count
        weight = (self.window - elapsed) / self.window
        return self.previous_count * weight + self.current_count
    
    def consume(self) -> RateLimitResult:
        """
        Attempt to consume a request slot.
        
        Returns:
            RateLimitResult indicating if request is allowed
        """
        with self.lock:
            weighted_count = self._get_weighted_count()
            
            if weighted_count < self.limit:
                self.current_count += 1
                remaining = max(0, int(self.limit - weighted_count - 1))
                
                return RateLimitResult(
                    allowed=True,
                    remaining=remaining,
                    reset_time=self.window_start + self.window,
                    limit=self.limit,
                    window=self.window
                )
            else:
                # Calculate when a slot will be available
                elapsed = time.time() - self.window_start
                retry_after = self.window - elapsed
                
                return RateLimitResult(
                    allowed=False,
                    remaining=0,
                    reset_time=self.window_start + self.window,
                    retry_after=retry_after,
                    limit=self.limit,
                    window=self.window
                )


class RateLimiter:
    """
    Multi-key rate limiter with configurable strategies.
    
    Supports:
    - Per-user rate limiting
    - Per-IP rate limiting
    - Per-endpoint rate limiting
    - Multiple time windows (per-minute, per-hour, per-day)
    """
    
    def __init__(
        self,
        strategy: RateLimitStrategy = RateLimitStrategy.SLIDING_WINDOW,
        default_limit: int = 60,
        default_window: int = 60
    ):
        """
        Initialize the rate limiter.
        
        Args:
            strategy: Rate limiting strategy to use
            default_limit: Default requests per window
            default_window: Default window in seconds
        """
        self.strategy = strategy
        self.default_limit = default_limit
        self.default_window = default_window
        
        # Per-key limiters
        self._limiters: dict[str, TokenBucket | SlidingWindowCounter] = {}
        self._lock = threading.Lock()
        
        # Custom limits per key pattern
        self._custom_limits: dict[str, tuple[int, int]] = {}
    
    def set_limit(self, key_pattern: str, limit: int, window: int):
        """
        Set custom limit for a key pattern.
        
        Args:
            key_pattern: Key pattern (e.g., "user:*", "ip:*")
            limit: Requests per window
            window: Window in seconds
        """
        self._custom_limits[key_pattern] = (limit, window)
    
    def _get_or_create_limiter(self, key: str) -> TokenBucket | SlidingWindowCounter:
        """Get or create a limiter for a key."""
        with self._lock:
            if key not in self._limiters:
                # Check for custom limits
                limit, window = self.default_limit, self.default_window
                for pattern, (l, w) in self._custom_limits.items():
                    if key.startswith(pattern.replace("*", "")):
                        limit, window = l, w
                        break
                
                # Create limiter based on strategy
                if self.strategy == RateLimitStrategy.TOKEN_BUCKET:
                    self._limiters[key] = TokenBucket(
                        capacity=limit,
                        refill_rate=window / limit,
                        refill_amount=1
                    )
                else:
                    self._limiters[key] = SlidingWindowCounter(
                        limit=limit,
                        window_seconds=window
                    )
            
            return self._limiters[key]
    
    def check(self, key: str, cost: int = 1) -> RateLimitResult:
        """
        Check if a request is allowed.
        
        Args:
            key: Rate limit key (e.g., "user:123", "ip:1.2.3.4")
            cost: Request cost (default 1)
            
        Returns:
            RateLimitResult
        """
        limiter = self._get_or_create_limiter(key)
        
        if isinstance(limiter, TokenBucket):
            return limiter.consume(cost)
        else:
            # Sliding window doesn't support variable cost
            return limiter.consume()
    
    def is_allowed(self, key: str, cost: int = 1) -> bool:
        """Quick check if request is allowed."""
        return self.check(key, cost).allowed
    
    def reset(self, key: str):
        """Reset rate limit for a key."""
        with self._lock:
            if key in self._limiters:
                del self._limiters[key]


# Convenience functions
def create_per_user_limiter(
    requests_per_minute: int = 60,
    requests_per_hour: int = 1000
) -> RateLimiter:
    """Create a rate limiter for per-user limiting."""
    limiter = RateLimiter(
        strategy=RateLimitStrategy.SLIDING_WINDOW,
        default_limit=requests_per_minute,
        default_window=60
    )
    limiter.set_limit("user:*", requests_per_minute, 60)
    return limiter


def create_api_rate_limiter(
    requests_per_second: int = 10,
    requests_per_minute: int = 100
) -> RateLimiter:
    """Create a rate limiter for API endpoints."""
    return RateLimiter(
        strategy=RateLimitStrategy.TOKEN_BUCKET,
        default_limit=requests_per_second,
        default_window=1
    )
