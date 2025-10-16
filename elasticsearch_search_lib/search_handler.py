"""
Search Handler

Executes Elasticsearch searches using the query builder.
"""

import logging
from typing import Optional

from elasticsearch import Elasticsearch
from elasticsearch import exceptions as es_exceptions

from elasticsearch_search_lib.query_builder import QueryBuilder
from elasticsearch_search_lib.models import SearchResponse, SearchResult
from elasticsearch_search_lib.exceptions import SearchExecutionError, ValidationError

logger = logging.getLogger(__name__)


class SearchHandler:
    """
    Handles Elasticsearch search execution.
    
    Uses QueryBuilder to construct queries and executes them against
    Elasticsearch, returning type-safe SearchResponse objects.
    """
    
    def __init__(
        self,
        es_client: Elasticsearch,
        query_builder: Optional[QueryBuilder] = None,
    ):
        """
        Initialize search handler.
        
        Args:
            es_client: Elasticsearch client instance
            query_builder: Query builder instance. If None, creates new builder.
        """
        self.es_client = es_client
        self.query_builder = query_builder or QueryBuilder()
        
    async def search(
        self,
        entity_type: str,
        query: str,
        tenant_id: str,
        limit: Optional[int] = None,
        from_offset: int = 0,
    ) -> SearchResponse:
        """
        Execute search for an entity type.
        
        Args:
            entity_type: Type of entity to search
            query: Search query string
            tenant_id: Tenant identifier for index naming
            limit: Maximum number of results (uses entity default if None)
            from_offset: Offset for pagination
            
        Returns:
            SearchResponse with results or error
        """
        try:
            # Validate inputs
            if not query or not query.strip():
                raise ValidationError("Search query cannot be empty")
            
            # Get entity configuration for default limit
            entity_config = self.query_builder.get_entity_config(entity_type)
            
            # Use entity's default limit if not specified
            if limit is None:
                limit = entity_config.default_limit
            
            # Enforce max limit
            if limit > entity_config.max_limit:
                logger.warning(
                    f"Requested limit {limit} exceeds max {entity_config.max_limit}, "
                    f"using max limit"
                )
                limit = entity_config.max_limit
            
            # Ensure minimum limit
            if limit < 1:
                limit = 1
            
            # Build query
            es_query = self.query_builder.build_search_query(
                entity_type=entity_type,
                query=query.strip(),
                limit=limit,
                from_offset=from_offset,
            )
            
            # Get index name
            index_name = self.query_builder.get_index_name(entity_type, tenant_id)
            
            logger.debug(f"Searching index '{index_name}' for entity '{entity_type}'")
            
            # Execute search
            response = self.es_client.search(
                index=index_name,
                body=es_query
            )
            
            # Process results
            return self._process_response(response, entity_type, query, index_name)
            
        except es_exceptions.NotFoundError:
            logger.warning(
                f"Index not found for entity type '{entity_type}' and tenant '{tenant_id}'"
            )
            return SearchResponse.error_response(
                entity_type=entity_type,
                query=query,
                error=f"No data available for entity type '{entity_type}'",
            )
            
        except (ValidationError, SearchExecutionError) as e:
            logger.error(f"Search failed: {e}")
            return SearchResponse.error_response(
                entity_type=entity_type,
                query=query,
                error=str(e),
            )
            
        except Exception as e:
            logger.error(f"Unexpected error during search: {e}", exc_info=True)
            return SearchResponse.error_response(
                entity_type=entity_type,
                query=query,
                error=f"Search failed: {str(e)}",
            )
    
    def _process_response(
        self,
        response: dict,
        entity_type: str,
        query: str,
        index_name: str,
    ) -> SearchResponse:
        """
        Process Elasticsearch response into SearchResponse.
        
        Args:
            response: Raw Elasticsearch response
            entity_type: Entity type that was searched
            query: Search query string
            index_name: Index that was searched
            
        Returns:
            SearchResponse with processed results
        """
        hits = response.get('hits', {}).get('hits', [])
        total_hits = response.get('hits', {}).get('total', {})
        
        # Handle different Elasticsearch versions
        if isinstance(total_hits, dict):
            total_count = total_hits.get('value', 0)
        else:
            total_count = total_hits
        
        # Convert hits to SearchResult objects
        items = []
        for hit in hits:
            source = hit.get('_source', {})
            score = hit.get('_score', 0.0)
            
            result = SearchResult(
                data=source,
                score=score,
                index=hit.get('_index', index_name),
                id=hit.get('_id', ''),
            )
            items.append(result)
        
        logger.info(
            f"Search completed for '{entity_type}': query='{query}', "
            f"hits={total_count}, returned={len(items)}"
        )
        
        return SearchResponse.success_response(
            entity_type=entity_type,
            query=query,
            total_hits=total_count,
            items=items,
            index_name=index_name,
        )

