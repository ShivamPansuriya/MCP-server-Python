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
        
        # Get enabled fields with their fuzziness settings
        self.enabled_fields = []
        for field in self.config.get_enabled_fields():
            field_config = {
                'name': field.name,
                'fuzziness': field.fuzziness,
                'boost': field.boost
            }
            self.enabled_fields.append(field_config)
        
        field_names = [field['name'] for field in self.enabled_fields]
        logger.info(
            f"UserSearchHandler initialized for tenant '{self.tenant_id}' "
            f"with {len(self.enabled_fields)} search fields: {', '.join(field_names)}"
        )
    
    def _get_index_name(self) -> str:
        """
        Build Elasticsearch index name for user search.

        Follows the pattern used in itsm-main-service: {tenant}_user

        Returns:
            Index name string
        """
        return f"{self.tenant_id}_user"

    async def search_users_by_query(
        self,
        query: str,
        limit: int = 3
    ) -> Dict[str, Any]:
        """
        Search for users using field-level fuzziness with bool query.

        Uses a bool query with should clauses where each field has its own fuzziness setting:
        - fuzziness=0: Uses match_phrase for exact matching
        - fuzziness>0: Uses match with specified fuzziness level

        Args:
            query: Search query string (e.g., "ANUJKUMARJ28@GMAIL.COM", "John Doe")
            limit: Maximum number of results (default: 3, max: 10)

        Returns:
            Dictionary with search results and metadata
        """
        try:
            # Validate parameters
            if not query or not query.strip():
                raise ValueError("Search query cannot be empty")

            if limit < 1 or limit > 10:
                limit = max(1, min(limit, 10))

            # Build bool query with should clauses for each field
            should_clauses = []

            for field_config in self.enabled_fields:
                field_name = field_config['name']
                fuzziness = field_config['fuzziness']
                boost = field_config['boost']

                if fuzziness == 0 or fuzziness == "0":
                    # Use match_phrase for exact matching (fuzziness = 0)
                    clause = {
                        "match_phrase": {
                            field_name: {
                                "query": query,
                                "boost": boost
                            }
                        }
                    }
                else:
                    # Use match with fuzziness for fuzzy matching
                    clause = {
                        "match": {
                            field_name: {
                                "query": query,
                                "fuzziness": fuzziness,
                                "boost": boost
                            }
                        }
                    }

                should_clauses.append(clause)

            # Build Elasticsearch query
            es_query = {
                "query": {
                    "bool": {
                        "should": should_clauses
                    }
                },
                "size": limit,
                "from": 0,
                "sort": [],
                "_source": [
                    "dbid",
                    "user_name",
                    "user_email",
                    "user_contact",
                    "user_userlogonname",
                    "user_contact2",
                    "user_usertype"
                ]
            }

            logger.debug(f"Executing simplified search query: {es_query}")

            # Execute search
            index_name = self._get_index_name()
            es_client = self.es_client_wrapper.get_client()
            if es_client is None:
                raise ConnectionError("Failed to connect to Elasticsearch")

            response = es_client.search(
                index=index_name,
                body=es_query
            )

            # Process results
            hits = response.get("hits", {})
            total_hits = hits.get("total", {}).get("value", 0)
            documents = hits.get("hits", [])

            users = []
            for doc in documents:
                source = doc.get("_source", {})
                score = doc.get("_score", 0.0)

                user = {
                    "id": source.get("dbid"),
                    "name": source.get("user_name"),
                    "email": source.get("user_email"),
                    "contact": source.get("user_contact"),
                    "userlogonname": source.get("user_userlogonname"),
                    "contact2": source.get("user_contact2"),
                    "usertype": source.get("user_usertype"),
                    "score": score
                }
                users.append(user)

            result = {
                "success": True,
                "query": query,
                "total_hits": total_hits,
                "returned_count": len(users),
                "users": users
            }

            logger.info(f"Search completed: query='{query}', hits={total_hits}, returned={len(users)}")
            return result

        except Exception as e:
            logger.error(f"Search failed: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e),
                "query": query,
                "total_hits": 0,
                "returned_count": 0,
                "users": []
            }





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

