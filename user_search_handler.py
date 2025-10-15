"""
User Search Handler

Executes Elasticsearch user searches and formats results.
"""

import logging
import os
from typing import Dict, List, Optional, Any
from elasticsearch import exceptions as es_exceptions

from elasticsearch_client import get_elasticsearch_client
from elasticsearch_config_loader import get_config_loader
from user_search_query_builder import create_query_builder

logger = logging.getLogger(__name__)


class UserSearchHandler:
    """
    Handles user search operations against Elasticsearch.
    
    Coordinates configuration loading, query building, and search execution.
    """
    
    def __init__(
        self,
        tenant_id: Optional[str] = None,
        es_host: Optional[str] = None,
        config_path: Optional[str] = None
    ):
        """
        Initialize user search handler.
        
        Args:
            tenant_id: Tenant identifier for index naming (defaults to 'default')
            es_host: Elasticsearch host (defaults to ES_HOST env var)
            config_path: Path to configuration file (optional)
        """
        self.tenant_id = tenant_id or os.getenv("TENANT_ID", "apolo")
        self.es_host = es_host or os.getenv("ES_HOST", "localhost:9200")

        # Load configuration
        self.config_loader = get_config_loader(config_path)
        self.config = self.config_loader.get_config()
        
        # Initialize Elasticsearch client
        self.es_client_wrapper = get_elasticsearch_client(es_host=es_host)
        
        # Create query builder with field-level overrides
        field_fuzziness = {}
        field_min_scores = {}
        for field in self.config.get_enabled_fields():
            if field.fuzziness is not None:
                field_fuzziness[field.name] = field.fuzziness
            if field.min_score is not None:
                field_min_scores[field.name] = field.min_score

        self.query_builder = create_query_builder(
            field_boosts=self.config.get_field_boosts(),
            fuzziness=self.config.fuzziness,
            field_fuzziness=field_fuzziness,
            field_min_scores=field_min_scores
        )
        
        logger.info(
            f"UserSearchHandler initialized for tenant '{self.tenant_id}' "
            f"with {len(self.config.get_enabled_fields())} search fields"
        )
    
    def _get_index_name(self) -> str:
        """
        Build Elasticsearch index name for user search.
        
        Follows the pattern used in itsm-main-service: {tenant}_user
        
        Returns:
            Index name string
        """
        return f"{self.tenant_id}_user"
    
    async def search_users(
        self,
        query: str,
        user_type: Optional[str] = None,
        limit: int = 10
    ) -> Dict[str, Any]:
        """
        Search for users with fuzzy matching.

        Args:
            query: Search query string
            user_type: Optional filter by user type (requester/technician)
            limit: Maximum number of results (default: 10, max: 100)

        Returns:
            Dictionary with search results and metadata

        Raises:
            ValueError: If query is empty or parameters are invalid
        """
        # Validate parameters
        if not query or not query.strip():
            raise ValueError("Search query cannot be empty")

        # Enforce limit bounds
        limit = max(1, min(limit, 100))

        # Validate user_type
        if user_type is not None:
            user_type = self.query_builder.validate_user_type(user_type)

        logger.info(
            f"Searching users: query='{query}', user_type={user_type}, limit={limit}"
        )

    async def search_users_by_fields(
        self,
        name: Optional[str] = None,
        email: Optional[str] = None,
        contact: Optional[str] = None,
        userlogonname: Optional[str] = None,
        contact2: Optional[str] = None,
        user_type: Optional[str] = None,
        limit: int = 10,
        min_score: Optional[float] = None
    ) -> Dict[str, Any]:
        """
        Search for users by specific fields with fuzzy matching.

        Args:
            name: Search by user name
            email: Search by email address
            contact: Search by primary contact
            userlogonname: Search by login name
            contact2: Search by secondary contact
            user_type: Optional filter by user type (requester/technician)
            limit: Maximum number of results (default: 10, max: 100)
            min_score: Minimum confidence score threshold (e.g., 7.0)

        Returns:
            Dictionary with search results and metadata

        Raises:
            ValueError: If no search fields provided or parameters are invalid
        """
        # Validate at least one field is provided
        if not any([name, email, contact, userlogonname, contact2]):
            raise ValueError("At least one search field must be provided")

        # Enforce limit bounds using config values
        limit = max(1, min(limit, self.config.max_limit))

        # Use config min_score if not provided
        if min_score is None:
            min_score = self.config.min_score if self.config.min_score > 0 else None

        # Validate user_type
        if user_type is not None:
            user_type = self.query_builder.validate_user_type(user_type)

        logger.info(
            f"Searching users by fields: name={name}, email={email}, "
            f"contact={contact}, userlogonname={userlogonname}, "
            f"contact2={contact2}, user_type={user_type}, limit={limit}, "
            f"min_score={min_score}"
        )

        try:
            # Get Elasticsearch client
            es_client = self.es_client_wrapper.get_client()
            if es_client is None:
                raise ConnectionError("Failed to connect to Elasticsearch")

            # Build query
            es_query = self.query_builder.build_field_specific_query(
                name=name,
                email=email,
                contact=contact,
                userlogonname=userlogonname,
                contact2=contact2,
                user_type=user_type,
                size=limit,
                min_score=min_score
            )

            # Get index name
            index_name = self._get_index_name()

            logger.debug(f"Executing field-specific search on index: {index_name}")

            # Execute search
            response = es_client.search(
                index=index_name,
                body=es_query
            )

            # Parse and format results
            search_params = {
                "name": name,
                "email": email,
                "contact": contact,
                "userlogonname": userlogonname,
                "contact2": contact2
            }
            results = self._format_search_results(response, search_params, user_type, limit)

            # Add min_score to response if it was applied
            if min_score is not None:
                results["min_score"] = min_score

            logger.info(
                f"Field-specific search completed: found {results['total_hits']} total, "
                f"returned {results['returned_count']} results"
            )

            return results
            
        except es_exceptions.NotFoundError:
            logger.error(f"Index not found: {self._get_index_name()}")
            return {
                "success": False,
                "error": f"User index not found for tenant '{self.tenant_id}'",
                "search_fields": {
                    "name": name,
                    "email": email,
                    "contact": contact,
                    "userlogonname": userlogonname,
                    "contact2": contact2
                },
                "user_type": user_type,
                "total_hits": 0,
                "returned_count": 0,
                "users": []
            }

        except es_exceptions.ConnectionError as e:
            logger.error(f"Elasticsearch connection error: {e}")
            return {
                "success": False,
                "error": "Failed to connect to Elasticsearch",
                "search_fields": {
                    "name": name,
                    "email": email,
                    "contact": contact,
                    "userlogonname": userlogonname,
                    "contact2": contact2
                },
                "user_type": user_type,
                "total_hits": 0,
                "returned_count": 0,
                "users": []
            }

        except es_exceptions.RequestError as e:
            logger.error(f"Elasticsearch request error: {e}")
            return {
                "success": False,
                "error": f"Invalid search query: {str(e)}",
                "search_fields": {
                    "name": name,
                    "email": email,
                    "contact": contact,
                    "userlogonname": userlogonname,
                    "contact2": contact2
                },
                "user_type": user_type,
                "total_hits": 0,
                "returned_count": 0,
                "users": []
            }

        except Exception as e:
            logger.error(f"Unexpected error during user search: {e}", exc_info=True)
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
                "user_type": user_type,
                "total_hits": 0,
                "returned_count": 0,
                "users": []
            }
    
    def _format_search_results(
        self,
        es_response: Dict[str, Any],
        search_params: Any,
        user_type: Optional[str],
        limit: int
    ) -> Dict[str, Any]:
        """
        Format Elasticsearch response into structured result.

        Args:
            es_response: Raw Elasticsearch response
            search_params: Search parameters (query string or dict of fields)
            user_type: User type filter used
            limit: Limit used in search

        Returns:
            Formatted results dictionary
        """
        hits = es_response.get("hits", {})
        total_hits = hits.get("total", {}).get("value", 0)
        hit_list = hits.get("hits", [])

        # Extract user data from hits
        users = []
        for hit in hit_list:
            source = hit.get("_source", {})
            user_data = {
                "id": source.get("dbid"),
                "name": source.get("user_name"),
                "email": source.get("user_email"),
                "contact": source.get("user_contact"),
                "userlogonname": source.get("user_userlogonname"),
                "contact2": source.get("user_contact2"),
                "usertype": source.get("user_usertype"),
                "score": hit.get("_score")
            }
            users.append(user_data)

        result = {
            "success": True,
            "user_type": user_type,
            "total_hits": total_hits,
            "returned_count": len(users),
            "limit": limit,
            "users": users
        }

        # Add search params based on type
        if isinstance(search_params, dict):
            result["search_fields"] = search_params
        else:
            result["query"] = search_params

        return result


# Singleton instance
_search_handler: Optional[UserSearchHandler] = None


def get_search_handler(
    tenant_id: Optional[str] = None,
    es_host: Optional[str] = None,
    config_path: Optional[str] = None
) -> UserSearchHandler:
    """
    Get singleton user search handler instance.
    
    Args:
        tenant_id: Tenant identifier (only used on first call)
        es_host: Elasticsearch host (only used on first call)
        config_path: Configuration file path (only used on first call)
        
    Returns:
        UserSearchHandler instance
    """
    global _search_handler
    if _search_handler is None:
        _search_handler = UserSearchHandler(
            tenant_id=tenant_id,
            es_host=es_host,
            config_path=config_path
        )
    return _search_handler

