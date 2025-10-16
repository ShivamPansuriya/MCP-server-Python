"""
Query Builder

Builds Elasticsearch queries from entity configurations.
Implements conditional query strategy based on fuzziness settings.
"""

import logging
from typing import Dict, Any, Optional

from elasticsearch_search_lib.config.loader import ConfigLoader
from elasticsearch_search_lib.models import EntityConfig, FieldConfig
from elasticsearch_search_lib.exceptions import EntityNotFoundError, ValidationError

logger = logging.getLogger(__name__)


class QueryBuilder:
    """
    Builds Elasticsearch queries for entity searches.
    
    Implements conditional query strategy:
    - fuzziness = 0: Uses match_phrase for exact matching
    - fuzziness > 0: Uses match with fuzziness for fuzzy matching
    """
    
    def __init__(self, config_loader: Optional[ConfigLoader] = None):
        """
        Initialize query builder.
        
        Args:
            config_loader: Configuration loader instance.
                          If None, creates a new loader with default config.
        """
        self.config_loader = config_loader or ConfigLoader()
        
    def build_search_query(
        self,
        entity_type: str,
        query: str,
        limit: int = 10,
        from_offset: int = 0,
    ) -> Dict[str, Any]:
        """
        Build Elasticsearch query for entity search.
        
        Args:
            entity_type: Type of entity to search
            query: Search query string
            limit: Maximum number of results
            from_offset: Offset for pagination
            
        Returns:
            Elasticsearch query dictionary
            
        Raises:
            EntityNotFoundError: If entity type not found in configuration
            ValidationError: If query is empty or invalid
        """
        # Validate inputs
        if not query or not query.strip():
            raise ValidationError("Search query cannot be empty")
        
        # Get entity configuration
        entity_config = self.config_loader.get_entity_config(entity_type)
        
        # Get enabled fields
        enabled_fields = entity_config.get_enabled_fields()
        if not enabled_fields:
            raise ValidationError(f"No enabled fields found for entity type '{entity_type}'")
        
        # Build should clauses for each enabled field
        should_clauses = []
        
        for field in enabled_fields:
            clause = self._build_field_clause(field, query.strip())
            should_clauses.append(clause)
        
        # Build the complete query
        es_query = {
            "query": {
                "bool": {
                    "should": should_clauses,
                    "minimum_should_match": 1
                }
            },
            "size": limit,
            "from": from_offset,
            "sort": [
                {"_score": {"order": "desc"}}
            ]
        }
        
        # Add min_score if configured
        if entity_config.min_score > 0:
            es_query["min_score"] = entity_config.min_score
        
        logger.debug(
            f"Built query for entity '{entity_type}' with {len(should_clauses)} field clauses"
        )
        
        return es_query
    
    def _build_field_clause(self, field: FieldConfig, query: str) -> Dict[str, Any]:
        """
        Build query clause for a single field.
        
        Implements conditional query strategy:
        - fuzziness = 0: match_phrase (exact matching)
        - fuzziness > 0: match with fuzziness (fuzzy matching)
        
        Args:
            field: Field configuration
            query: Search query string
            
        Returns:
            Elasticsearch query clause
        """
        field_name = field.name
        fuzziness = field.fuzziness
        boost = field.boost
        
        # Conditional query type based on fuzziness
        if fuzziness == 0 or fuzziness == '0':
            # Use match_phrase for exact matching
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
        
        return clause
    
    def get_index_name(self, entity_type: str, tenant_id: str) -> str:
        """
        Build Elasticsearch index name.
        
        Args:
            entity_type: Type of entity
            tenant_id: Tenant identifier
            
        Returns:
            Index name following pattern: {tenant_id}_{entity_type}
        """
        return f"{tenant_id}_{entity_type}"
    
    def get_entity_config(self, entity_type: str) -> EntityConfig:
        """
        Get configuration for an entity type.
        
        Args:
            entity_type: Entity type name
            
        Returns:
            EntityConfig instance
            
        Raises:
            EntityNotFoundError: If entity type not found
        """
        return self.config_loader.get_entity_config(entity_type)
    
    def get_supported_entities(self) -> list[str]:
        """
        Get list of supported entity types.
        
        Returns:
            List of entity type names
        """
        return self.config_loader.get_supported_entities()
    
    def is_entity_supported(self, entity_type: str) -> bool:
        """
        Check if entity type is supported.
        
        Args:
            entity_type: Entity type name
            
        Returns:
            True if entity is supported
        """
        return self.config_loader.is_entity_supported(entity_type)

