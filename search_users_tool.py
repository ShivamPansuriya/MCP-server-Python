"""
Search Users MCP Tool

Provides fuzzy search functionality for users via Elasticsearch.
"""

import logging
from typing import Optional, Dict, Any

from user_search_handler import get_search_handler

logger = logging.getLogger(__name__)


async def search_users(
    query: str,
    limit: int = 3
) -> Dict[str, Any]:
    """
    Search for users using a simple query string across all enabled fields.

    Searches user records across all enabled fields (name, email, contact, etc.)
    and returns the top 3 most relevant results.

    Args:
        query: Search query string (e.g., "ANUJKUMARJ28@GMAIL.COM", "John Doe", "9876543210")
        limit: Maximum number of results to return (1-10, default: 3)

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
        >>> search_users(query="ANUJKUMARJ28@GMAIL.COM")

        Search by name:
        >>> search_users(query="John Doe")

        Search by contact:
        >>> search_users(query="9876543210")

        Search with custom limit:
        >>> search_users(query="Smith", limit=5)
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

        # Validate and normalize limit
        if limit < 1 or limit > 10:
            logger.warning(f"Invalid limit {limit}, clamping to range [1, 10]")
            limit = max(1, min(limit, 10))

        logger.info(f"search_users tool called: query='{query}', limit={limit}")

        # Get search handler and execute search
        handler = get_search_handler()
        results = await handler.search_users_by_query(
            query=query,
            limit=limit
        )

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

