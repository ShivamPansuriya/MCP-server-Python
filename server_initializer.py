#!/usr/bin/env python3
"""
Server Initialization Module

Handles all initialization logic for the MCP server components:
- Dynamic tool system
- Elasticsearch search library
- Hierarchy cache system
- WebSocket client for real-time updates
"""

import logging
import threading
from typing import Optional, Tuple

from config import AppConfig
from api_client import FormSchemaClient
from dynamic_tool_manager import DynamicToolManager
from dynamic_tool_middleware import DynamicToolMiddleware

logger = logging.getLogger(__name__)


class DynamicToolSystem:
    """Manages dynamic tool generation system."""
    
    def __init__(self, config: AppConfig):
        self.config = config
        self.schema_client: Optional[FormSchemaClient] = None
        self.tool_manager: Optional[DynamicToolManager] = None
        self.middleware: Optional[DynamicToolMiddleware] = None
    
    def initialize(self) -> DynamicToolMiddleware:
        """
        Initialize the dynamic tool system.
        
        Returns:
            DynamicToolMiddleware instance
        """
        logger.info("Initializing dynamic tool system...")
        
        self.schema_client = FormSchemaClient(
            api_url=self.config.api.form_schema_url,
            cache_ttl=self.config.api.cache_ttl,
            verbose=True
        )
        
        self.tool_manager = DynamicToolManager(
            cache_ttl_seconds=self.config.api.cache_ttl
        )
        
        self.middleware = DynamicToolMiddleware(
            schema_client=self.schema_client,
            tool_manager=self.tool_manager,
            tool_name="create_request",
            tool_description=(
                "Creates a new request with dynamically defined fields based on your permissions. "
                "The available fields are determined by the form schema API and may vary based on "
                "user permissions."
            )
        )
        
        logger.info("✅ Dynamic tool system initialized")
        return self.middleware


class SearchSystem:
    """Manages Elasticsearch search functionality."""
    
    def __init__(self, config: AppConfig):
        self.config = config
        self.search_client = None
    
    def initialize(self) -> Optional[object]:
        """
        Initialize the Elasticsearch search library.
        
        Returns:
            SearchClient instance or None if initialization fails
        """
        logger.info("Initializing Elasticsearch search library...")
        
        try:
            from elasticsearch_search_lib import SearchClient
            
            self.search_client = SearchClient(
                tenant_id=self.config.elasticsearch.tenant_id
            )
            
            entity_count = len(self.search_client.get_supported_entities())
            logger.info(f"✅ Search library initialized with {entity_count} entity types")
            
            return self.search_client
            
        except Exception as e:
            logger.error(f"Error initializing search library: {e}", exc_info=True)
            logger.warning("Search tools will be available but may fail at runtime")
            return None


class HierarchyCacheSystem:
    """Manages hierarchy cache for locations and departments."""
    
    def __init__(self, config: AppConfig):
        self.config = config
        self.cache_manager = None
    
    def initialize(self) -> Optional[object]:
        """
        Initialize the hierarchy cache system.
        
        Returns:
            HierarchyCacheManager instance or None if initialization fails
        """
        logger.info("Initializing hierarchy cache system...")
        
        try:
            from hierarchy_cache import initialize_hierarchy_caches
            
            self.cache_manager = initialize_hierarchy_caches(
                tenant_id=self.config.elasticsearch.tenant_id
            )
            
            if self.cache_manager and self.cache_manager.is_initialized():
                logger.info("✅ Hierarchy cache system initialized successfully")
            else:
                logger.warning("⚠️ Hierarchy cache system initialization incomplete")
                logger.warning("Server will continue but hierarchy features may be limited")
            
            return self.cache_manager
            
        except Exception as e:
            logger.error(f"Error initializing hierarchy cache system: {e}", exc_info=True)
            logger.warning("Server will continue without hierarchy caches")
            return None


class WebSocketSystem:
    """Manages WebSocket client for real-time cache updates."""
    
    def __init__(self, config: AppConfig, cache_manager):
        self.config = config
        self.cache_manager = cache_manager
        self.websocket_client = None
        self.websocket_thread = None
    
    def initialize(self) -> Tuple[Optional[object], Optional[threading.Thread]]:
        """
        Initialize and start the WebSocket client.
        
        Returns:
            Tuple of (websocket_client, websocket_thread)
            
        Raises:
            RuntimeError: If WebSocket connection fails during startup
        """
        logger.info("Initializing WebSocket client for hierarchy cache updates...")
        
        # Validate configuration
        if not self.config.websocket.validate():
            raise RuntimeError("Invalid WebSocket configuration")
        
        try:
            from websocket_client import HierarchyCacheWebSocketClient
            
            ws_config = self.config.websocket
            logger.info(
                f"WebSocket configuration: server={ws_config.server_url}, "
                f"instance={ws_config.instance_id}"
            )
            
            # Create WebSocket client
            self.websocket_client = HierarchyCacheWebSocketClient(
                cache_manager=self.cache_manager,
                access_token=ws_config.access_token,
                server_url=ws_config.server_url,
                client_id=ws_config.client_id,
                client_secret=ws_config.client_secret,
                instance_id=ws_config.instance_id
            )
            
            # Start WebSocket client in background thread
            self.websocket_thread = threading.Thread(
                target=self.websocket_client.connect,
                daemon=True,
                name="WebSocketClient"
            )
            self.websocket_thread.start()
            logger.info("WebSocket client thread started")
            
            # Wait for connection to be established (with timeout)
            logger.info(
                f"Waiting for WebSocket connection "
                f"(timeout: {ws_config.connection_timeout}s)..."
            )
            
            if self.websocket_client.connection_established.wait(
                timeout=ws_config.connection_timeout
            ):
                logger.info("✅ WebSocket client connected successfully")
            elif self.websocket_client.connection_failed.is_set():
                raise Exception("WebSocket connection failed during startup")
            else:
                raise Exception(
                    f"WebSocket connection timeout after {ws_config.connection_timeout} seconds"
                )
            
            return self.websocket_client, self.websocket_thread
            
        except Exception as e:
            logger.error(f"❌ Failed to initialize WebSocket client: {e}", exc_info=True)
            logger.error("Server startup aborted due to WebSocket connection failure")
            raise RuntimeError(f"WebSocket client initialization failed: {e}") from e


class ServerInitializer:
    """
    Main initializer that coordinates all server components.
    
    This class orchestrates the initialization of all server subsystems
    in the correct order and handles dependencies between them.
    """
    
    def __init__(self, config: AppConfig):
        self.config = config
        self.dynamic_tool_system = DynamicToolSystem(config)
        self.search_system = SearchSystem(config)
        self.hierarchy_cache_system = HierarchyCacheSystem(config)
        self.websocket_system = None  # Created after cache system
        
        # Component references
        self.middleware = None
        self.search_client = None
        self.cache_manager = None
        self.websocket_client = None
        self.websocket_thread = None
    
    def initialize_all(self) -> dict:
        """
        Initialize all server components.
        
        Returns:
            Dictionary containing all initialized components
            
        Raises:
            RuntimeError: If critical components fail to initialize
        """
        logger.info("=" * 60)
        logger.info("Starting MCP Server Initialization")
        logger.info("=" * 60)
        
        # 1. Initialize dynamic tool system (required)
        self.middleware = self.dynamic_tool_system.initialize()
        
        # 2. Initialize search system (optional)
        self.search_client = self.search_system.initialize()
        
        # 3. Initialize hierarchy cache system (required for WebSocket)
        self.cache_manager = self.hierarchy_cache_system.initialize()
        
        # 4. Initialize WebSocket system (required)
        self.websocket_system = WebSocketSystem(self.config, self.cache_manager)
        self.websocket_client, self.websocket_thread = self.websocket_system.initialize()
        
        logger.info("=" * 60)
        logger.info("✅ All server components initialized successfully")
        logger.info("=" * 60)
        
        return {
            'middleware': self.middleware,
            'search_client': self.search_client,
            'cache_manager': self.cache_manager,
            'websocket_client': self.websocket_client,
            'websocket_thread': self.websocket_thread,
        }


