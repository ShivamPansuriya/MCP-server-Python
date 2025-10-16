"""
Elasticsearch Search Library

A simple, configuration-driven Elasticsearch search library for ITSM entities.

Features:
- XML-based configuration with entity-level settings
- Support for 11 ITSM entity types
- Conditional query strategies (match_phrase vs fuzzy match)
- Type-safe data models
- Clean, intuitive API

Quick Start:
    >>> from elasticsearch_search_lib import SearchClient
    >>> 
    >>> # Create search client
    >>> client = SearchClient(tenant_id="apolo")
    >>> 
    >>> # Search for users
    >>> results = await client.search("user", "john doe", limit=10)
    >>> 
    >>> # Access results
    >>> for item in results.items:
    ...     print(item.data, item.score)

Example:
    >>> from elasticsearch_search_lib import SearchClient
    >>> 
    >>> client = SearchClient(tenant_id="apolo")
    >>> results = await client.search("impact", "High")
    >>> print(f"Found {results.total_hits} impacts")
"""

__version__ = "1.0.0"
__author__ = "ITSM Team"
__all__ = [
    # Main client
    "SearchClient",
    # Models
    "SearchResult",
    "SearchResponse",
    "FieldConfig",
    "EntityConfig",
    # Exceptions
    "SearchLibraryError",
    "ConfigurationError",
    "EntityNotFoundError",
    "SearchExecutionError",
    # Convenience functions
    "create_search_client",
    "get_supported_entities",
]

# Import main components
from elasticsearch_search_lib.client import SearchClient
from elasticsearch_search_lib.models import (
    SearchResult,
    SearchResponse,
    FieldConfig,
    EntityConfig,
)
from elasticsearch_search_lib.exceptions import (
    SearchLibraryError,
    ConfigurationError,
    EntityNotFoundError,
    SearchExecutionError,
)


def create_search_client(tenant_id: str, **kwargs) -> SearchClient:
    """
    Create a new SearchClient instance.
    
    Convenience function for creating a search client with common defaults.
    
    Args:
        tenant_id: Tenant identifier for index naming
        **kwargs: Additional arguments passed to SearchClient
        
    Returns:
        Configured SearchClient instance
        
    Example:
        >>> client = create_search_client("apolo")
        >>> results = await client.search("user", "john")
    """
    return SearchClient(tenant_id=tenant_id, **kwargs)


def get_supported_entities() -> list[str]:
    """
    Get list of all supported entity types.
    
    Returns:
        List of entity type names
        
    Example:
        >>> entities = get_supported_entities()
        >>> print(entities)
        ['impact', 'urgency', 'priority', 'status', ...]
    """
    from elasticsearch_search_lib.config.loader import ConfigLoader
    loader = ConfigLoader()
    return loader.get_supported_entities()

