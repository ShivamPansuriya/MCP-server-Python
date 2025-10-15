"""
Elasticsearch Client Wrapper

Manages connection to Elasticsearch cluster with configuration from environment variables.
Follows the same connection pattern as itsm-main-service.
"""

import logging
import os
from typing import Optional
from elasticsearch import Elasticsearch, exceptions as es_exceptions

logger = logging.getLogger(__name__)


class ElasticsearchClientWrapper:
    """
    Wrapper for Elasticsearch client with connection management.
    
    Connects to Elasticsearch cluster using environment-based configuration
    matching the pattern used in itsm-main-service.
    """
    
    def __init__(
        self,
        es_host: Optional[str] = None,
        es_port: int = 9200,
        timeout: int = 30,
        max_retries: int = 3
    ):
        """
        Initialize Elasticsearch client wrapper.
        
        Args:
            es_host: Elasticsearch host (defaults to ES_HOST env var or 'localhost')
            es_port: Elasticsearch port (default: 9200)
            timeout: Request timeout in seconds (default: 30)
            max_retries: Maximum number of connection retries (default: 3)
        """
        # Get host from parameter, environment variable, or default
        self.es_host = es_host or os.getenv("ES_HOST", "localhost")
        self.es_port = es_port
        self.timeout = timeout
        self.max_retries = max_retries
        
        # Build connection URL
        self.es_url = f"http://{self.es_host}:{self.es_port}"
        
        # Client instance (lazy initialization)
        self._client: Optional[Elasticsearch] = None
        self._connected = False
        
        logger.info(f"ElasticsearchClientWrapper initialized with URL: {self.es_url}")
    
    def connect(self) -> bool:
        """
        Establish connection to Elasticsearch cluster.
        
        Returns:
            True if connection successful, False otherwise
        """
        if self._connected and self._client is not None:
            return True
        
        try:
            logger.info(f"Connecting to Elasticsearch at {self.es_url}...")
            
            # Create Elasticsearch client
            self._client = Elasticsearch(
                [self.es_url],
                request_timeout=self.timeout,
                max_retries=self.max_retries,
                retry_on_timeout=True
            )
            
            # Test connection with ping
            if self._client.ping():
                self._connected = True
                logger.info(f"Successfully connected to Elasticsearch at {self.es_url}")
                
                # Log cluster info
                try:
                    info = self._client.info()
                    logger.info(
                        f"Elasticsearch cluster: {info.get('cluster_name', 'unknown')}, "
                        f"version: {info.get('version', {}).get('number', 'unknown')}"
                    )
                except Exception as e:
                    logger.warning(f"Could not retrieve cluster info: {e}")
                
                return True
            else:
                logger.error(f"Failed to ping Elasticsearch at {self.es_url}")
                self._connected = False
                return False
                
        except es_exceptions.ConnectionError as e:
            logger.error(f"Connection error to Elasticsearch at {self.es_url}: {e}")
            self._connected = False
            return False
            
        except Exception as e:
            logger.error(f"Unexpected error connecting to Elasticsearch: {e}", exc_info=True)
            self._connected = False
            return False
    
    def get_client(self) -> Optional[Elasticsearch]:
        """
        Get Elasticsearch client instance.
        
        Automatically connects if not already connected.
        
        Returns:
            Elasticsearch client instance or None if connection failed
        """
        if not self._connected:
            if not self.connect():
                return None
        
        return self._client
    
    def is_connected(self) -> bool:
        """
        Check if client is connected to Elasticsearch.
        
        Returns:
            True if connected, False otherwise
        """
        if not self._connected or self._client is None:
            return False
        
        try:
            return self._client.ping()
        except Exception as e:
            logger.warning(f"Connection check failed: {e}")
            self._connected = False
            return False
    
    def close(self):
        """Close Elasticsearch connection."""
        if self._client is not None:
            try:
                self._client.close()
                logger.info("Elasticsearch connection closed")
            except Exception as e:
                logger.warning(f"Error closing Elasticsearch connection: {e}")
            finally:
                self._client = None
                self._connected = False
    
    def __enter__(self):
        """Context manager entry."""
        self.connect()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()
    
    def __del__(self):
        """Destructor to ensure connection is closed."""
        self.close()


# Singleton instance for easy access
_es_client_wrapper: Optional[ElasticsearchClientWrapper] = None


def get_elasticsearch_client(
    es_host: Optional[str] = None,
    es_port: int = 9200
) -> ElasticsearchClientWrapper:
    """
    Get singleton Elasticsearch client wrapper instance.
    
    Args:
        es_host: Elasticsearch host (only used on first call)
        es_port: Elasticsearch port (only used on first call)
        
    Returns:
        ElasticsearchClientWrapper instance
    """
    global _es_client_wrapper
    if _es_client_wrapper is None:
        _es_client_wrapper = ElasticsearchClientWrapper(
            es_host=es_host,
            es_port=es_port
        )
    return _es_client_wrapper


def reset_elasticsearch_client():
    """Reset singleton instance (useful for testing)."""
    global _es_client_wrapper
    if _es_client_wrapper is not None:
        _es_client_wrapper.close()
        _es_client_wrapper = None

