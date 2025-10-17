#!/usr/bin/env python3
"""
Configuration Management

Centralized configuration for the MCP server including:
- Environment variable handling
- Default values
- Configuration validation
"""

import os
import logging
from typing import Optional
from dataclasses import dataclass

logger = logging.getLogger(__name__)
# IMPORT AND LOAD .ENV
from dotenv import load_dotenv
load_dotenv()


@dataclass
class ServerConfig:
    """Main server configuration."""
    host: str = "127.0.0.1"
    port: int = 9092
    log_level: str = "INFO"


@dataclass
class APIConfig:
    """External API configuration."""
    form_schema_url: str = "http://127.0.0.1:8080/api/module/request/form"
    cache_ttl: int = 300  # 5 minutes


@dataclass
class ElasticsearchConfig:
    """Elasticsearch configuration."""
    tenant_id: str = "apolo"


@dataclass
class WebSocketConfig:
    """WebSocket client configuration."""
    server_url: str
    access_token: str
    client_id: str
    client_secret: str
    instance_id: str
    connection_timeout: int = 30  # seconds
    
    @classmethod
    def from_env(cls) -> 'WebSocketConfig':
        """Create configuration from environment variables."""
        return cls(
            server_url=os.getenv('MOTADATA_SERVER_URL', 'http://127.0.0.1:8080'),
            access_token=os.getenv('MOTADATA_ACCESS_TOKEN', 'notoken'),
            client_id=os.getenv('MOTADATA_CLIENT_ID', 'python-service'),
            client_secret=os.getenv('MOTADATA_CLIENT_SECRET', 'IZqQXkqA1tGLIBRpYs'),
            instance_id=os.getenv('MOTADATA_INSTANCE_ID', 'python-service-1'),
        )
    
    def validate(self) -> bool:
        """Validate configuration."""
        if not self.server_url:
            logger.error("MOTADATA_SERVER_URL is required")
            return False
        if not self.client_id or not self.client_secret:
            logger.error("MOTADATA_CLIENT_ID and MOTADATA_CLIENT_SECRET are required")
            return False
        return True


@dataclass
class AppConfig:
    """Application-wide configuration."""
    server: ServerConfig
    api: APIConfig
    elasticsearch: ElasticsearchConfig
    websocket: WebSocketConfig
    
    @classmethod
    def load(cls) -> 'AppConfig':
        """Load configuration from environment and defaults."""
        return cls(
            server=ServerConfig(),
            api=APIConfig(),
            elasticsearch=ElasticsearchConfig(),
            websocket=WebSocketConfig.from_env()
        )
    
    def validate(self) -> bool:
        """Validate all configuration."""
        return self.websocket.validate()


def setup_logging(level: str = "INFO") -> None:
    """
    Configure application logging.
    
    Args:
        level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
    """
    logging.basicConfig(
        level=getattr(logging, level.upper()),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

