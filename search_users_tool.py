"""
Search Users MCP Tool

Simplified search functionality using the elasticsearch search library.
Now accepts only a query string as input parameter.
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


async def search_users(query: str) -> Dict[str, Any]:
    """
    Search for users using a simple query string.

    Simplified search function that accepts only a query string.
    All other parameters (limit, tenant_id, etc.) are handled internally
    through configuration and defaults.

    Args:
        query: Search query string (e.g., "ANUJKUMARJ28@GMAIL.COM", "John Doe", "9876543210")

    Returns:
        Dictionary containing:
        - success: Boolean indicating if search was successful
        - query: The search query used
        - total_hits: Total number of matching users
        - returned_count: Number of users returned in this response
        - users: List of user objects with fields:
            * id: User database ID
            * name: User's full name
            * email: User's email address
            * contact: Primary contact number
            * userlogonname: User's login name
            * contact2: Secondary contact number
            * usertype: User type (requester/technician)
            * score: Relevance score
        - error: Error message (only present if success is False)

    Examples:
        Search by email:
        >>> search_users("ANUJKUMARJ28@GMAIL.COM")

        Search by name:
        >>> search_users("John Doe")

        Search by contact:
        >>> search_users("9876543210")
    """
    try:
        # Validate query is provided
        if not query or not query.strip():
            return {
                "success": False,
                "error": "Query parameter is required and cannot be empty",
                "query": query,
                "total_hits": 0,
                "returned_count": 0,
                "users": []
            }

        logger.info(f"search_users tool called: query='{query}'")

        # Get search client and execute search
        client = get_search_client()

        # Use default limit of 3 for user searches
        search_response = await client.search(
            entity_type="user",
            query=query,
            limit=3  # Default limit for user searches
        )

        # Convert search response to expected format
        if search_response.success:
            users = []
            for result in search_response.items:
                user_data = result.data
                user = {
                    "id": user_data.get("user_id") or user_data.get("dbid"),
                    "name": user_data.get("user_name"),
                    "email": user_data.get("user_email"),
                    "contact": user_data.get("user_contact"),
                    "userlogonname": user_data.get("user_userlogonname"),
                    "contact2": user_data.get("user_contact2"),
                    "usertype": user_data.get("user_type"),
                    "score": result.score
                }
                users.append(user)

            results = {
                "success": True,
                "query": query,
                "total_hits": search_response.total_hits,
                "returned_count": len(users),
                "users": users
            }
        else:
            results = {
                "success": False,
                "error": search_response.error or 'Search failed',
                "query": query,
                "total_hits": 0,
                "returned_count": 0,
                "users": []
            }

        logger.info(
            f"search_users completed: success={results.get('success')}, "
            f"hits={results.get('total_hits')}, returned={results.get('returned_count')}"
        )

        return results

    except ValueError as e:
        logger.error(f"Validation error in search_users: {e}")
        return {
            "success": False,
            "error": str(e),
            "query": query,
            "total_hits": 0,
            "returned_count": 0,
            "users": []
        }

    except Exception as e:
        logger.error(f"Unexpected error in search_users tool: {e}", exc_info=True)
        return {
            "success": False,
            "error": f"Search failed: {str(e)}",
            "query": query,
            "total_hits": 0,
            "returned_count": 0,
            "users": []
        }

