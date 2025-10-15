"""
Search Users MCP Tool

Provides fuzzy search functionality for users via Elasticsearch.
"""

import logging
from typing import Optional, Dict, Any

from user_search_handler import get_search_handler
from user_type_enum import UserType

logger = logging.getLogger(__name__)


async def search_users(
    name: Optional[str] = None,
    email: Optional[str] = None,
    contact: Optional[str] = None,
    userlogonname: Optional[str] = None,
    contact2: Optional[str] = None,
    userType: Optional[UserType] = None,
    limit: int = 10,
    minScore: Optional[float] = None
) -> Dict[str, Any]:
    """
    Search for users using fuzzy matching on specific fields.

    Searches user records by specific fields with fuzzy matching for typo tolerance.
    At least one search field must be provided.

    Args:
        name: Search by user's full name
        email: Search by email address
        contact: Search by primary contact number
        userlogonname: Search by user login name
        contact2: Search by secondary contact number
        userType: Optional filter by user type. Valid values: "requester" or "technician"
        limit: Maximum number of results to return (1-100, default: 10)
        minScore: Minimum confidence score threshold. Only return users with score >= this value (e.g., 7.0)

    Returns:
        Dictionary containing:
        - success: Boolean indicating if search was successful
        - search_fields: Dictionary of search fields used
        - user_type: The user type filter applied (if any)
        - total_hits: Total number of matching users
        - returned_count: Number of users returned in this response
        - limit: The limit applied to results
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
        Search by name:
        >>> search_users(name="John Doe")

        Search by email:
        >>> search_users(email="john@example.com")

        Search by multiple fields:
        >>> search_users(name="John", email="john@example.com")

        Search requesters only:
        >>> search_users(name="John", userType=UserType.REQUESTER)

        Search with custom limit:
        >>> search_users(name="Smith", limit=20)

        Filter by minimum score:
        >>> search_users(name="John", minScore=7.0)
    """
    try:
        # Validate at least one search field is provided
        if not any([name, email, contact, userlogonname, contact2]):
            return {
                "success": False,
                "error": "At least one search field must be provided (name, email, contact, userlogonname, or contact2)",
                "search_fields": {
                    "name": name,
                    "email": email,
                    "contact": contact,
                    "userlogonname": userlogonname,
                    "contact2": contact2
                },
                "user_type": userType.value if userType else None,
                "total_hits": 0,
                "returned_count": 0,
                "users": []
            }

        # Validate and normalize limit
        if limit < 1 or limit > 100:
            logger.warning(f"Invalid limit {limit}, clamping to range [1, 100]")
            limit = max(1, min(limit, 100))

        # Convert enum to string value
        user_type_value = userType.value if userType else None

        logger.info(
            f"search_users tool called: name={name}, email={email}, "
            f"contact={contact}, userlogonname={userlogonname}, "
            f"contact2={contact2}, userType={user_type_value}, limit={limit}, "
            f"minScore={minScore}"
        )

        # Get search handler and execute search
        handler = get_search_handler()
        results = await handler.search_users_by_fields(
            name=name,
            email=email,
            contact=contact,
            userlogonname=userlogonname,
            contact2=contact2,
            user_type=user_type_value,
            limit=limit,
            min_score=minScore
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
            "search_fields": {
                "name": name,
                "email": email,
                "contact": contact,
                "userlogonname": userlogonname,
                "contact2": contact2
            },
            "user_type": userType.value if userType else None,
            "total_hits": 0,
            "returned_count": 0,
            "users": []
        }

    except Exception as e:
        logger.error(f"Unexpected error in search_users tool: {e}", exc_info=True)
        return {
            "success": False,
            "error": f"Search failed: {str(e)}",
            "search_fields": {
                "name": name,
                "email": email,
                "contact": contact,
                "userlogonname": userlogonname,
                "contact2": contact2
            },
            "user_type": userType.value if userType else None,
            "total_hits": 0,
            "returned_count": 0,
            "users": []
        }

