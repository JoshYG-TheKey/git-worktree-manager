"""Caching layer for Git operations to improve performance."""

import time
from typing import Any, Dict, Optional, Callable, TypeVar, Generic
from dataclasses import dataclass, field
from threading import Lock
import hashlib
import json

T = TypeVar('T')


@dataclass
class CacheEntry(Generic[T]):
    """Represents a cached entry with expiration."""
    value: T
    timestamp: float
    ttl: float  # Time to live in seconds
    
    def is_expired(self) -> bool:
        """Check if the cache entry has expired."""
        return time.time() - self.timestamp > self.ttl


class GitOperationsCache:
    """Thread-safe cache for Git operations with TTL support."""
    
    def __init__(self, default_ttl: float = 300.0):  # 5 minutes default
        """Initialize the cache.
        
        Args:
            default_ttl: Default time-to-live for cache entries in seconds
        """
        self.default_ttl = default_ttl
        self._cache: Dict[str, CacheEntry] = {}
        self._lock = Lock()
        self._stats = {
            'hits': 0,
            'misses': 0,
            'evictions': 0
        }
    
    def get(self, key: str) -> Optional[Any]:
        """Get a value from the cache.
        
        Args:
            key: Cache key
            
        Returns:
            Cached value if found and not expired, None otherwise
        """
        with self._lock:
            entry = self._cache.get(key)
            if entry is None:
                self._stats['misses'] += 1
                return None
            
            if entry.is_expired():
                del self._cache[key]
                self._stats['evictions'] += 1
                self._stats['misses'] += 1
                return None
            
            self._stats['hits'] += 1
            return entry.value
    
    def set(self, key: str, value: Any, ttl: Optional[float] = None) -> None:
        """Set a value in the cache.
        
        Args:
            key: Cache key
            value: Value to cache
            ttl: Time-to-live in seconds (uses default if None)
        """
        effective_ttl = ttl if ttl is not None else self.default_ttl
        
        with self._lock:
            self._cache[key] = CacheEntry(
                value=value,
                timestamp=time.time(),
                ttl=effective_ttl
            )
    
    def invalidate(self, key: str) -> bool:
        """Invalidate a specific cache entry.
        
        Args:
            key: Cache key to invalidate
            
        Returns:
            True if key was found and removed, False otherwise
        """
        with self._lock:
            if key in self._cache:
                del self._cache[key]
                return True
            return False
    
    def invalidate_pattern(self, pattern: str) -> int:
        """Invalidate all cache entries matching a pattern.
        
        Args:
            pattern: Pattern to match against keys (simple substring match)
            
        Returns:
            Number of entries invalidated
        """
        with self._lock:
            keys_to_remove = [key for key in self._cache.keys() if pattern in key]
            for key in keys_to_remove:
                del self._cache[key]
            return len(keys_to_remove)
    
    def clear(self) -> None:
        """Clear all cache entries."""
        with self._lock:
            self._cache.clear()
            self._stats = {'hits': 0, 'misses': 0, 'evictions': 0}
    
    def cleanup_expired(self) -> int:
        """Remove all expired entries from the cache.
        
        Returns:
            Number of entries removed
        """
        with self._lock:
            current_time = time.time()
            expired_keys = [
                key for key, entry in self._cache.items()
                if current_time - entry.timestamp > entry.ttl
            ]
            
            for key in expired_keys:
                del self._cache[key]
            
            self._stats['evictions'] += len(expired_keys)
            return len(expired_keys)
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics.
        
        Returns:
            Dictionary with cache statistics
        """
        with self._lock:
            total_requests = self._stats['hits'] + self._stats['misses']
            hit_rate = self._stats['hits'] / total_requests if total_requests > 0 else 0.0
            
            return {
                'hits': self._stats['hits'],
                'misses': self._stats['misses'],
                'evictions': self._stats['evictions'],
                'hit_rate': hit_rate,
                'cache_size': len(self._cache),
                'total_requests': total_requests
            }
    
    def cached_call(self, key: str, func: Callable[[], T], ttl: Optional[float] = None) -> T:
        """Execute a function and cache its result.
        
        Args:
            key: Cache key
            func: Function to execute if not cached
            ttl: Time-to-live for the cached result
            
        Returns:
            Cached or computed result
        """
        # Try to get from cache first
        cached_result = self.get(key)
        if cached_result is not None:
            return cached_result
        
        # Execute function and cache result
        result = func()
        self.set(key, result, ttl)
        return result


def create_cache_key(*args, **kwargs) -> str:
    """Create a consistent cache key from arguments.
    
    Args:
        *args: Positional arguments
        **kwargs: Keyword arguments
        
    Returns:
        SHA256 hash of the serialized arguments
    """
    # Create a consistent representation of the arguments
    key_data = {
        'args': args,
        'kwargs': sorted(kwargs.items()) if kwargs else {}
    }
    
    # Serialize to JSON and hash
    key_str = json.dumps(key_data, sort_keys=True, default=str)
    return hashlib.sha256(key_str.encode()).hexdigest()


class CacheConfig:
    """Configuration for different cache types."""
    
    # Cache TTL values in seconds
    BRANCHES_TTL = 60.0  # 1 minute - branches don't change often
    COMMIT_INFO_TTL = 3600.0  # 1 hour - commit info is immutable
    CURRENT_BRANCH_TTL = 30.0  # 30 seconds - current branch can change frequently
    WORKTREE_LIST_TTL = 30.0  # 30 seconds - worktree list can change
    DIFF_SUMMARY_TTL = 300.0  # 5 minutes - diff summaries can change with commits
    
    # Maximum cache sizes
    MAX_COMMIT_INFO_ENTRIES = 1000
    MAX_DIFF_SUMMARY_ENTRIES = 500