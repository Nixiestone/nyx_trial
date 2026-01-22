"""
Advanced Rate Limiter for API and Command Throttling
Uses sliding window algorithm for accurate rate limiting

Author: BLESSING OMOREGIE
Location: src/security/rate_limiter.py
"""

import time
from collections import defaultdict, deque
from typing import Dict, Tuple, Optional
from threading import Lock


class SlidingWindowRateLimiter:
    """
    Sliding window rate limiter.
    More accurate than fixed window, prevents burst attacks.
    """
    
    def __init__(self, max_calls: int = 10, time_window: int = 60):
        """
        Initialize rate limiter.
        
        Args:
            max_calls: Maximum calls allowed in time window
            time_window: Time window in seconds
        """
        self.max_calls = max_calls
        self.time_window = time_window
        self.calls: Dict[int, deque] = defaultdict(deque)
        self.lock = Lock()
    
    def is_allowed(self, user_id: int) -> Tuple[bool, Optional[str]]:
        """
        Check if user is allowed to make a call.
        
        Args:
            user_id: User identifier
            
        Returns:
            Tuple of (is_allowed, error_message)
        """
        with self.lock:
            current_time = time.time()
            
            # Get user's call history
            user_calls = self.calls[user_id]
            
            # Remove calls outside time window
            while user_calls and current_time - user_calls[0] >= self.time_window:
                user_calls.popleft()
            
            # Check if limit exceeded
            if len(user_calls) >= self.max_calls:
                # Calculate time until next allowed call
                oldest_call = user_calls[0]
                wait_time = int(self.time_window - (current_time - oldest_call))
                
                return False, f"Rate limit exceeded. Try again in {wait_time} seconds."
            
            # Allow call and record it
            user_calls.append(current_time)
            
            # Calculate remaining calls
            remaining = self.max_calls - len(user_calls)
            
            return True, None
    
    def get_remaining_calls(self, user_id: int) -> int:
        """Get number of remaining calls for user."""
        with self.lock:
            current_time = time.time()
            user_calls = self.calls[user_id]
            
            # Clean old calls
            while user_calls and current_time - user_calls[0] >= self.time_window:
                user_calls.popleft()
            
            return max(0, self.max_calls - len(user_calls))
    
    def reset_user(self, user_id: int):
        """Reset rate limit for a specific user."""
        with self.lock:
            if user_id in self.calls:
                self.calls[user_id].clear()
    
    def cleanup_old_users(self, inactive_threshold: int = 3600):
        """
        Remove users who haven't made calls recently.
        
        Args:
            inactive_threshold: Seconds of inactivity before cleanup
        """
        with self.lock:
            current_time = time.time()
            users_to_remove = []
            
            for user_id, user_calls in self.calls.items():
                if not user_calls or current_time - user_calls[-1] > inactive_threshold:
                    users_to_remove.append(user_id)
            
            for user_id in users_to_remove:
                del self.calls[user_id]


class TokenBucketRateLimiter:
    """
    Token bucket rate limiter.
    Allows bursts while maintaining average rate.
    """
    
    def __init__(self, rate: float = 1.0, capacity: int = 10):
        """
        Initialize token bucket.
        
        Args:
            rate: Tokens added per second
            capacity: Maximum tokens in bucket
        """
        self.rate = rate
        self.capacity = capacity
        self.buckets: Dict[int, Dict] = defaultdict(lambda: {
            'tokens': capacity,
            'last_update': time.time()
        })
        self.lock = Lock()
    
    def is_allowed(self, user_id: int, tokens_required: int = 1) -> Tuple[bool, Optional[str]]:
        """
        Check if user has enough tokens.
        
        Args:
            user_id: User identifier
            tokens_required: Tokens needed for this operation
            
        Returns:
            Tuple of (is_allowed, error_message)
        """
        with self.lock:
            bucket = self.buckets[user_id]
            current_time = time.time()
            
            # Add tokens based on time elapsed
            time_elapsed = current_time - bucket['last_update']
            tokens_to_add = time_elapsed * self.rate
            bucket['tokens'] = min(self.capacity, bucket['tokens'] + tokens_to_add)
            bucket['last_update'] = current_time
            
            # Check if enough tokens
            if bucket['tokens'] >= tokens_required:
                bucket['tokens'] -= tokens_required
                return True, None
            else:
                wait_time = int((tokens_required - bucket['tokens']) / self.rate)
                return False, f"Rate limit exceeded. Try again in {wait_time} seconds."
    
    def get_available_tokens(self, user_id: int) -> float:
        """Get number of available tokens for user."""
        with self.lock:
            bucket = self.buckets[user_id]
            current_time = time.time()
            
            time_elapsed = current_time - bucket['last_update']
            tokens_to_add = time_elapsed * self.rate
            available = min(self.capacity, bucket['tokens'] + tokens_to_add)
            
            return available


# Global rate limiters for different operations
COMMAND_RATE_LIMITER = SlidingWindowRateLimiter(max_calls=20, time_window=60)
API_RATE_LIMITER = SlidingWindowRateLimiter(max_calls=100, time_window=60)
ADMIN_RATE_LIMITER = SlidingWindowRateLimiter(max_calls=50, time_window=60)


def rate_limit_command(user_id: int) -> Tuple[bool, Optional[str]]:
    """Check command rate limit."""
    return COMMAND_RATE_LIMITER.is_allowed(user_id)


def rate_limit_api(user_id: int) -> Tuple[bool, Optional[str]]:
    """Check API rate limit."""
    return API_RATE_LIMITER.is_allowed(user_id)


def rate_limit_admin(user_id: int) -> Tuple[bool, Optional[str]]:
    """Check admin rate limit."""
    return ADMIN_RATE_LIMITER.is_allowed(user_id)


if __name__ == "__main__":
    # Test rate limiters
    print("Testing Rate Limiters...")
    
    limiter = SlidingWindowRateLimiter(max_calls=5, time_window=10)
    
    # Test user 1
    for i in range(7):
        allowed, msg = limiter.is_allowed(1)
        print(f"Call {i+1}: {'✓' if allowed else '✗'} {msg or ''}")
        time.sleep(0.5)
    
    print("\nWaiting 5 seconds...")
    time.sleep(5)
    
    # Should have some calls available now
    allowed, msg = limiter.is_allowed(1)
    print(f"After wait: {'✓' if allowed else '✗'} {msg or ''}")
    
    print("\nRate limiter test complete!")