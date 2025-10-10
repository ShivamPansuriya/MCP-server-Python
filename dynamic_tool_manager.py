"""
Dynamic Tool Manager for Per-User MCP Tool Generation

Manages the lifecycle of dynamically generated tools, including creation,
storage, retrieval, and cache invalidation on a per-user basis.
"""

import logging
from typing import Dict, Callable, Optional, List
from threading import Lock
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class DynamicToolManager:
    """
    Manages dynamic tool generation and caching for authenticated users.
    
    Stores tools in a two-level dictionary structure:
    {auth_token: {tool_name: callable_function}}
    
    Thread-safe for concurrent access from multiple users.
    """
    
    def __init__(self, cache_ttl_seconds: int = 300):
        """
        Initialize the Dynamic Tool Manager.
        
        Args:
            cache_ttl_seconds: Time-to-live for cached tools (default: 5 minutes)
        """
        self._tools: Dict[str, Dict[str, Callable]] = {}
        self._cache_timestamps: Dict[str, datetime] = {}
        self._lock = Lock()
        self.cache_ttl_seconds = cache_ttl_seconds
        logger.info(f"DynamicToolManager initialized with {cache_ttl_seconds}s cache TTL")
    
    def get_user_tools(self, auth_token: str) -> Dict[str, Callable]:
        """
        Retrieve cached tools for a specific user.
        
        Args:
            auth_token: User's authentication token
            
        Returns:
            Dictionary mapping tool names to callable functions.
            Returns empty dict if no tools cached or cache expired.
        """
        with self._lock:
            # Check if tools exist for this user
            if auth_token not in self._tools:
                logger.debug(f"No cached tools found for user token: {auth_token[:20]}...")
                return {}
            
            # Check if cache has expired
            if auth_token in self._cache_timestamps:
                cache_time = self._cache_timestamps[auth_token]
                expiry_time = cache_time + timedelta(seconds=self.cache_ttl_seconds)
                
                if datetime.now() > expiry_time:
                    logger.info(f"Cache expired for user token: {auth_token[:20]}...")
                    # Clear expired cache
                    del self._tools[auth_token]
                    del self._cache_timestamps[auth_token]
                    return {}
                else:
                    logger.debug(f"Returning {len(self._tools[auth_token])} cached tools for user")
            
            return self._tools[auth_token].copy()
    
    def store_user_tools(self, auth_token: str, tools: Dict[str, Callable]) -> None:
        """
        Store generated tools for a specific user.
        
        Args:
            auth_token: User's authentication token
            tools: Dictionary mapping tool names to callable functions
        """
        with self._lock:
            self._tools[auth_token] = tools
            self._cache_timestamps[auth_token] = datetime.now()
            logger.info(f"Stored {len(tools)} tools for user token: {auth_token[:20]}...")
    
    def clear_user_tools(self, auth_token: str) -> None:
        """
        Invalidate cached tools for a specific user.
        
        Args:
            auth_token: User's authentication token
        """
        with self._lock:
            if auth_token in self._tools:
                tool_count = len(self._tools[auth_token])
                del self._tools[auth_token]
                if auth_token in self._cache_timestamps:
                    del self._cache_timestamps[auth_token]
                logger.info(f"Cleared {tool_count} tools for user token: {auth_token[:20]}...")
            else:
                logger.debug(f"No tools to clear for user token: {auth_token[:20]}...")
    
    def clear_all_tools(self) -> None:
        """
        Clear all cached tools for all users.
        Useful for server restart or global cache invalidation.
        """
        with self._lock:
            total_users = len(self._tools)
            total_tools = sum(len(tools) for tools in self._tools.values())
            self._tools.clear()
            self._cache_timestamps.clear()
            logger.info(f"Cleared all cached tools ({total_tools} tools from {total_users} users)")
    
    def get_cache_stats(self) -> Dict[str, int]:
        """
        Get statistics about the current cache state.
        
        Returns:
            Dictionary with cache statistics
        """
        with self._lock:
            total_users = len(self._tools)
            total_tools = sum(len(tools) for tools in self._tools.values())
            
            return {
                "total_users": total_users,
                "total_tools": total_tools,
                "cache_ttl_seconds": self.cache_ttl_seconds
            }
    
    def has_cached_tools(self, auth_token: str) -> bool:
        """
        Check if valid cached tools exist for a user.
        
        Args:
            auth_token: User's authentication token
            
        Returns:
            True if valid cached tools exist, False otherwise
        """
        tools = self.get_user_tools(auth_token)
        return len(tools) > 0

