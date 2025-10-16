"""
Generic Search Entities Tool

Provides search functionality for any entity type using the elasticsearch search library.
Supports all 11 entity types: Impact, Urgency, Priority, Status, Category, Source,
Location, Department, UserGroup, User, Vendor.
"""

import logging
from typing import Dict, Any

from elasticsearch_search_lib import SearchClient

logger = logging.getLogger(__name__)

# Global search client instance
_search_client = None


def get_search_client() -> SearchClient:
    """Get or create search client instance."""
    global _search_client
    if _search_client is None:
        _search_client = SearchClient(tenant_id="apolo")
    return _search_client


async def search_entities(entity_type: str, query: str) -> Dict[str, Any]:
    """
    Search for entities of any type using a unified approach.

    This function can search across all supported entity types using
    the same unified query builder and search handler.

    Args:
        entity_type: Type of entity to search (user, impact, urgency, priority, 
                    status, category, source, location, department, usergroup, vendor)
        query: Search query string

    Returns:
        Dictionary containing:
        - success: Boolean indicating if search was successful
        - entity_type: The entity type that was searched
        - query: The search query used
        - total_hits: Total number of matching entities
        - returned_count: Number of entities returned in this response
        - entities: List of entity objects with their fields and scores
        - error: Error message (only present if success is False)

    Examples:
        Search for impacts:
        >>> search_entities("impact", "High")

        Search for users:
        >>> search_entities("user", "John Doe")

        Search for locations:
        >>> search_entities("location", "Building A")

        Search for vendors:
        >>> search_entities("vendor", "Microsoft")
    """
    try:
        # Validate inputs
        if not entity_type or not entity_type.strip():
            return {
                "success": False,
                "error": "Entity type parameter is required and cannot be empty",
                "entity_type": entity_type,
                "query": query,
                "total_hits": 0,
                "returned_count": 0,
                "entities": []
            }

        if not query or not query.strip():
            return {
                "success": False,
                "error": "Query parameter is required and cannot be empty",
                "entity_type": entity_type,
                "query": query,
                "total_hits": 0,
                "returned_count": 0,
                "entities": []
            }

        entity_type = entity_type.strip().lower()
        query = query.strip()

        logger.info(f"search_entities tool called: entity_type='{entity_type}', query='{query}'")

        # Get search client
        client = get_search_client()

        # Check if entity type is supported
        if not client.is_entity_supported(entity_type):
            available_types = client.get_supported_entities()
            return {
                "success": False,
                "error": f"Unsupported entity type '{entity_type}'. Available types: {', '.join(available_types)}",
                "entity_type": entity_type,
                "query": query,
                "total_hits": 0,
                "returned_count": 0,
                "entities": []
            }

        # Execute search with default limit of 10
        search_response = await client.search(
            entity_type=entity_type,
            query=query,
            limit=10  # Default limit for entity searches
        )

        # Convert results to generic format
        if search_response.success:
            entities = []
            for result in search_response.items:
                entity = {
                    "data": result.data,
                    "score": result.score,
                    "index": result.index,
                    "id": result.id
                }
                entities.append(entity)

            results = {
                "success": True,
                "entity_type": entity_type,
                "query": query,
                "total_hits": search_response.total_hits,
                "returned_count": len(entities),
                "entities": entities,
                "index_name": search_response.index_name
            }
        else:
            results = {
                "success": False,
                "error": search_response.error or 'Search failed',
                "entity_type": entity_type,
                "query": query,
                "total_hits": 0,
                "returned_count": 0,
                "entities": []
            }

        logger.info(
            f"search_entities completed: entity_type='{entity_type}', "
            f"success={results.get('success')}, hits={results.get('total_hits')}, "
            f"returned={results.get('returned_count')}"
        )

        return results

    except ValueError as e:
        logger.error(f"Validation error in search_entities: {e}")
        return {
            "success": False,
            "error": str(e),
            "entity_type": entity_type,
            "query": query,
            "total_hits": 0,
            "returned_count": 0,
            "entities": []
        }

    except Exception as e:
        logger.error(f"Unexpected error in search_entities tool: {e}", exc_info=True)
        return {
            "success": False,
            "error": f"Search failed: {str(e)}",
            "entity_type": entity_type,
            "query": query,
            "total_hits": 0,
            "returned_count": 0,
            "entities": []
        }


async def get_supported_entity_types() -> Dict[str, Any]:
    """
    Get list of all supported entity types.

    Returns:
        Dictionary containing:
        - success: Boolean indicating if operation was successful
        - entity_types: List of supported entity type names
        - count: Number of supported entity types
        - error: Error message (only present if success is False)
    """
    try:
        client = get_search_client()
        entity_types = client.get_supported_entities()

        return {
            "success": True,
            "entity_types": entity_types,
            "count": len(entity_types)
        }

    except Exception as e:
        logger.error(f"Failed to get supported entity types: {e}")
        return {
            "success": False,
            "error": str(e),
            "entity_types": [],
            "count": 0
        }


async def get_entity_fields(entity_type: str) -> Dict[str, Any]:
    """
    Get enabled fields for a specific entity type.

    Args:
        entity_type: Type of entity to get fields for

    Returns:
        Dictionary containing:
        - success: Boolean indicating if operation was successful
        - entity_type: The entity type requested
        - fields: List of field configurations
        - count: Number of enabled fields
        - error: Error message (only present if success is False)
    """
    try:
        if not entity_type or not entity_type.strip():
            return {
                "success": False,
                "error": "Entity type parameter is required",
                "entity_type": entity_type,
                "fields": [],
                "count": 0
            }

        entity_type = entity_type.strip().lower()
        client = get_search_client()

        if not client.is_entity_supported(entity_type):
            available_types = client.get_supported_entities()
            return {
                "success": False,
                "error": f"Unsupported entity type '{entity_type}'. Available types: {', '.join(available_types)}",
                "entity_type": entity_type,
                "fields": [],
                "count": 0
            }

        field_configs = client.get_entity_fields(entity_type)

        # Convert FieldConfig objects to dictionaries
        fields = [field.to_dict() for field in field_configs]

        return {
            "success": True,
            "entity_type": entity_type,
            "fields": fields,
            "count": len(fields)
        }

    except Exception as e:
        logger.error(f"Failed to get entity fields for '{entity_type}': {e}")
        return {
            "success": False,
            "error": str(e),
            "entity_type": entity_type,
            "fields": [],
            "count": 0
        }
