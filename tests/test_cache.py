"""Tests for the caching layer."""

import pytest
import time
from unittest.mock import Mock, patch
from git_worktree_manager.cache import (
    GitOperationsCache,
    CacheEntry,
    CacheConfig,
    create_cache_key
)


class TestCacheEntry:
    """Test CacheEntry functionality."""

    def test_cache_entry_creation(self):
        """Test creating a cache entry."""
        entry = CacheEntry(value="test", timestamp=time.time(), ttl=60.0)
        assert entry.value == "test"
        assert entry.ttl == 60.0
        assert not entry.is_expired()

    def test_cache_entry_expiration(self):
        """Test cache entry expiration."""
        # Create an entry that's already expired
        old_timestamp = time.time() - 120  # 2 minutes ago
        entry = CacheEntry(value="test", timestamp=old_timestamp, ttl=60.0)
        assert entry.is_expired()

        # Create an entry that's not expired
        recent_timestamp = time.time() - 30  # 30 seconds ago
        entry = CacheEntry(value="test", timestamp=recent_timestamp, ttl=60.0)
        assert not entry.is_expired()


class TestGitOperationsCache:
    """Test GitOperationsCache functionality."""

    def test_cache_initialization(self):
        """Test cache initialization."""
        cache = GitOperationsCache(default_ttl=300.0)
        assert cache.default_ttl == 300.0
        assert cache._cache == {}
        
        stats = cache.get_stats()
        assert stats['hits'] == 0
        assert stats['misses'] == 0
        assert stats['cache_size'] == 0

    def test_cache_set_and_get(self):
        """Test setting and getting cache values."""
        cache = GitOperationsCache()
        
        # Test cache miss
        result = cache.get("test_key")
        assert result is None
        
        # Test cache set and hit
        cache.set("test_key", "test_value")
        result = cache.get("test_key")
        assert result == "test_value"
        
        # Check stats
        stats = cache.get_stats()
        assert stats['hits'] == 1
        assert stats['misses'] == 1
        assert stats['cache_size'] == 1

    def test_cache_ttl(self):
        """Test cache TTL functionality."""
        cache = GitOperationsCache(default_ttl=0.1)  # 100ms TTL
        
        cache.set("test_key", "test_value")
        assert cache.get("test_key") == "test_value"
        
        # Wait for expiration
        time.sleep(0.2)
        
        # Should be expired now
        result = cache.get("test_key")
        assert result is None
        
        # Check that expired entry was removed
        stats = cache.get_stats()
        assert stats['cache_size'] == 0
        assert stats['evictions'] == 1

    def test_cache_custom_ttl(self):
        """Test setting custom TTL for specific entries."""
        cache = GitOperationsCache(default_ttl=300.0)
        
        # Set with custom TTL
        cache.set("test_key", "test_value", ttl=0.1)
        assert cache.get("test_key") == "test_value"
        
        # Wait for expiration
        time.sleep(0.2)
        
        # Should be expired
        assert cache.get("test_key") is None

    def test_cache_invalidation(self):
        """Test cache invalidation."""
        cache = GitOperationsCache()
        
        cache.set("test_key", "test_value")
        assert cache.get("test_key") == "test_value"
        
        # Invalidate specific key
        result = cache.invalidate("test_key")
        assert result is True
        assert cache.get("test_key") is None
        
        # Try to invalidate non-existent key
        result = cache.invalidate("non_existent")
        assert result is False

    def test_cache_pattern_invalidation(self):
        """Test pattern-based cache invalidation."""
        cache = GitOperationsCache()
        
        cache.set("branches_repo1", ["main", "dev"])
        cache.set("branches_repo2", ["master", "feature"])
        cache.set("commit_info_abc123", {"hash": "abc123"})
        
        # Invalidate all branch-related entries
        count = cache.invalidate_pattern("branches")
        assert count == 2
        
        # Check that only branch entries were removed
        assert cache.get("branches_repo1") is None
        assert cache.get("branches_repo2") is None
        assert cache.get("commit_info_abc123") is not None

    def test_cache_clear(self):
        """Test clearing all cache entries."""
        cache = GitOperationsCache()
        
        cache.set("key1", "value1")
        cache.set("key2", "value2")
        
        assert cache.get_stats()['cache_size'] == 2
        
        cache.clear()
        
        stats = cache.get_stats()
        assert stats['cache_size'] == 0
        assert stats['hits'] == 0
        assert stats['misses'] == 0

    def test_cache_cleanup_expired(self):
        """Test cleanup of expired entries."""
        cache = GitOperationsCache()
        
        # Add some entries with different TTLs
        cache.set("key1", "value1", ttl=0.1)  # Will expire quickly
        cache.set("key2", "value2", ttl=300.0)  # Won't expire
        
        # Wait for first entry to expire
        time.sleep(0.2)
        
        # Cleanup expired entries
        removed_count = cache.cleanup_expired()
        assert removed_count == 1
        
        # Check that only non-expired entry remains
        assert cache.get("key1") is None
        assert cache.get("key2") == "value2"

    def test_cached_call(self):
        """Test the cached_call method."""
        cache = GitOperationsCache()
        mock_func = Mock(return_value="computed_value")
        
        # First call should execute function
        result1 = cache.cached_call("test_key", mock_func)
        assert result1 == "computed_value"
        assert mock_func.call_count == 1
        
        # Second call should use cache
        result2 = cache.cached_call("test_key", mock_func)
        assert result2 == "computed_value"
        assert mock_func.call_count == 1  # Function not called again
        
        # Check stats
        stats = cache.get_stats()
        assert stats['hits'] == 1
        assert stats['misses'] == 1

    def test_cache_thread_safety(self):
        """Test basic thread safety of cache operations."""
        import threading
        
        cache = GitOperationsCache()
        results = []
        
        def worker():
            for i in range(10):
                cache.set(f"key_{i}", f"value_{i}")
                result = cache.get(f"key_{i}")
                results.append(result)
        
        # Run multiple threads
        threads = [threading.Thread(target=worker) for _ in range(3)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()
        
        # All operations should have succeeded
        assert len(results) == 30
        assert all(result is not None for result in results)


class TestCreateCacheKey:
    """Test cache key creation."""

    def test_create_cache_key_basic(self):
        """Test basic cache key creation."""
        key1 = create_cache_key("branches", "/path/to/repo")
        key2 = create_cache_key("branches", "/path/to/repo")
        
        # Same arguments should produce same key
        assert key1 == key2
        assert isinstance(key1, str)
        assert len(key1) == 64  # SHA256 hex digest length

    def test_create_cache_key_different_args(self):
        """Test that different arguments produce different keys."""
        key1 = create_cache_key("branches", "/path/to/repo1")
        key2 = create_cache_key("branches", "/path/to/repo2")
        key3 = create_cache_key("commit_info", "/path/to/repo1")
        
        assert key1 != key2
        assert key1 != key3
        assert key2 != key3

    def test_create_cache_key_with_kwargs(self):
        """Test cache key creation with keyword arguments."""
        key1 = create_cache_key("diff", branch1="main", branch2="dev")
        key2 = create_cache_key("diff", branch1="main", branch2="dev")
        key3 = create_cache_key("diff", branch2="dev", branch1="main")  # Different order
        
        # Same kwargs should produce same key regardless of order
        assert key1 == key2 == key3

    def test_create_cache_key_mixed_args(self):
        """Test cache key creation with mixed positional and keyword arguments."""
        key1 = create_cache_key("operation", "repo_path", branch="main", commit="abc123")
        key2 = create_cache_key("operation", "repo_path", commit="abc123", branch="main")
        
        # Should be the same regardless of kwarg order
        assert key1 == key2


class TestCacheConfig:
    """Test cache configuration constants."""

    def test_cache_config_values(self):
        """Test that cache config has expected values."""
        assert CacheConfig.BRANCHES_TTL == 60.0
        assert CacheConfig.COMMIT_INFO_TTL == 3600.0
        assert CacheConfig.CURRENT_BRANCH_TTL == 30.0
        assert CacheConfig.WORKTREE_LIST_TTL == 30.0
        assert CacheConfig.DIFF_SUMMARY_TTL == 300.0
        
        assert CacheConfig.MAX_COMMIT_INFO_ENTRIES == 1000
        assert CacheConfig.MAX_DIFF_SUMMARY_ENTRIES == 500


class TestCacheIntegration:
    """Integration tests for cache functionality."""

    def test_cache_performance_simulation(self):
        """Test cache performance with simulated workload."""
        cache = GitOperationsCache()
        
        # Simulate repeated operations
        def expensive_operation(key):
            time.sleep(0.001)  # Simulate some work
            return f"result_for_{key}"
        
        # First round - cache misses
        start_time = time.time()
        for i in range(10):
            result = cache.cached_call(f"key_{i}", lambda k=i: expensive_operation(k))
            assert result == f"result_for_{i}"
        first_round_time = time.time() - start_time
        
        # Second round - cache hits
        start_time = time.time()
        for i in range(10):
            result = cache.cached_call(f"key_{i}", lambda k=i: expensive_operation(k))
            assert result == f"result_for_{i}"
        second_round_time = time.time() - start_time
        
        # Cache hits should be significantly faster
        assert second_round_time < first_round_time / 2
        
        # Check stats
        stats = cache.get_stats()
        assert stats['hits'] == 10
        assert stats['misses'] == 10
        assert stats['hit_rate'] == 0.5

    def test_cache_memory_usage(self):
        """Test cache memory usage and cleanup."""
        cache = GitOperationsCache()
        
        # Add many entries
        for i in range(100):
            cache.set(f"key_{i}", f"value_{i}" * 100)  # Larger values
        
        assert cache.get_stats()['cache_size'] == 100
        
        # Clear cache
        cache.clear()
        assert cache.get_stats()['cache_size'] == 0