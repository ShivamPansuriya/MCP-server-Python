"""
Data Models for Elasticsearch Search Library

Type-safe dataclasses for configuration and search results.
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Union


@dataclass(frozen=True)
class FieldConfig:
    """
    Configuration for a single search field.
    
    Attributes:
        name: Field name (e.g., 'user_name', 'impact_id')
        boost: Relevance boost multiplier (default: 1.0)
        enabled: Whether field is included in searches (default: True)
        fuzziness: Fuzzy matching tolerance (0, 1, 2, or 'AUTO')
    """
    name: str
    boost: float = 1.0
    enabled: bool = True
    fuzziness: Union[int, str] = 'AUTO'
    
    def __post_init__(self):
        """Validate field configuration."""
        if self.boost < 0:
            raise ValueError(f"Boost must be non-negative, got {self.boost}")
        
        if isinstance(self.fuzziness, int) and self.fuzziness < 0:
            raise ValueError(f"Fuzziness must be non-negative, got {self.fuzziness}")
        
        if isinstance(self.fuzziness, str) and self.fuzziness not in ('AUTO', '0', '1', '2'):
            raise ValueError(f"Invalid fuzziness value: {self.fuzziness}")
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'name': self.name,
            'boost': self.boost,
            'enabled': self.enabled,
            'fuzziness': self.fuzziness,
        }


@dataclass(frozen=True)
class EntityConfig:
    """
    Configuration for an entity type.
    
    Attributes:
        entity_type: Entity type name (e.g., 'user', 'impact')
        fuzziness: Default fuzziness for this entity
        default_limit: Default number of results to return
        max_limit: Maximum allowed results
        min_score: Minimum relevance score threshold
        fields: List of field configurations
    """
    entity_type: str
    fuzziness: Union[int, str] = 'AUTO'
    default_limit: int = 10
    max_limit: int = 100
    min_score: float = 0.0
    fields: List[FieldConfig] = field(default_factory=list)
    
    def __post_init__(self):
        """Validate entity configuration."""
        if self.default_limit < 1:
            raise ValueError(f"default_limit must be positive, got {self.default_limit}")
        
        if self.max_limit < self.default_limit:
            raise ValueError(f"max_limit ({self.max_limit}) must be >= default_limit ({self.default_limit})")
        
        if self.min_score < 0:
            raise ValueError(f"min_score must be non-negative, got {self.min_score}")
    
    def get_enabled_fields(self) -> List[FieldConfig]:
        """Get only enabled fields."""
        return [f for f in self.fields if f.enabled]
    
    def get_field(self, field_name: str) -> Optional[FieldConfig]:
        """Get field configuration by name."""
        for f in self.fields:
            if f.name == field_name:
                return f
        return None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'entity_type': self.entity_type,
            'fuzziness': self.fuzziness,
            'default_limit': self.default_limit,
            'max_limit': self.max_limit,
            'min_score': self.min_score,
            'fields': [f.to_dict() for f in self.fields],
        }


@dataclass(frozen=True)
class SearchResult:
    """
    Single search result item.
    
    Attributes:
        data: Source data from Elasticsearch document
        score: Relevance score
        index: Index name where document was found
        id: Document ID
    """
    data: Dict[str, Any]
    score: float
    index: str
    id: str
    
    def get(self, key: str, default: Any = None) -> Any:
        """Get value from data dictionary."""
        return self.data.get(key, default)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'data': self.data,
            'score': self.score,
            'index': self.index,
            'id': self.id,
        }


@dataclass
class SearchResponse:
    """
    Complete search response.
    
    Attributes:
        success: Whether search was successful
        entity_type: Entity type that was searched
        query: Search query string
        total_hits: Total number of matching documents
        returned_count: Number of results in this response
        items: List of search result items
        index_name: Elasticsearch index that was searched
        error: Error message if search failed
    """
    success: bool
    entity_type: str
    query: str
    total_hits: int = 0
    returned_count: int = 0
    items: List[SearchResult] = field(default_factory=list)
    index_name: str = ""
    error: Optional[str] = None
    
    @classmethod
    def success_response(
        cls,
        entity_type: str,
        query: str,
        total_hits: int,
        items: List[SearchResult],
        index_name: str,
    ) -> "SearchResponse":
        """Create a successful search response."""
        return cls(
            success=True,
            entity_type=entity_type,
            query=query,
            total_hits=total_hits,
            returned_count=len(items),
            items=items,
            index_name=index_name,
            error=None,
        )
    
    @classmethod
    def error_response(
        cls,
        entity_type: str,
        query: str,
        error: str,
    ) -> "SearchResponse":
        """Create an error search response."""
        return cls(
            success=False,
            entity_type=entity_type,
            query=query,
            total_hits=0,
            returned_count=0,
            items=[],
            index_name="",
            error=error,
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        result = {
            'success': self.success,
            'entity_type': self.entity_type,
            'query': self.query,
            'total_hits': self.total_hits,
            'returned_count': self.returned_count,
            'results': [item.to_dict() for item in self.items],
            'index_name': self.index_name,
        }
        
        if self.error:
            result['error'] = self.error
        
        return result
    
    def __len__(self) -> int:
        """Return number of results."""
        return len(self.items)
    
    def __iter__(self):
        """Iterate over result items."""
        return iter(self.items)
    
    def __getitem__(self, index: int) -> SearchResult:
        """Get result by index."""
        return self.items[index]

