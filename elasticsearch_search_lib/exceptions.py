"""
Custom Exceptions for Elasticsearch Search Library

Provides a clear exception hierarchy for different error scenarios.
"""


class SearchLibraryError(Exception):
    """
    Base exception for all library errors.
    
    All custom exceptions in this library inherit from this base class,
    allowing callers to catch all library-specific errors with a single except clause.
    """
    pass


class ConfigurationError(SearchLibraryError):
    """
    Raised when there's an error in configuration.
    
    Examples:
        - Invalid XML syntax
        - Missing required configuration fields
        - Invalid configuration values
        - Configuration file not found
    """
    pass


class EntityNotFoundError(SearchLibraryError):
    """
    Raised when an entity type is not found in configuration.
    
    Examples:
        - Searching for unsupported entity type
        - Requesting configuration for non-existent entity
    """
    
    def __init__(self, entity_type: str, available_entities: list[str] = None):
        """
        Initialize EntityNotFoundError.
        
        Args:
            entity_type: The entity type that was not found
            available_entities: List of available entity types
        """
        self.entity_type = entity_type
        self.available_entities = available_entities or []
        
        if self.available_entities:
            message = (
                f"Entity type '{entity_type}' not found. "
                f"Available types: {', '.join(self.available_entities)}"
            )
        else:
            message = f"Entity type '{entity_type}' not found"
        
        super().__init__(message)


class SearchExecutionError(SearchLibraryError):
    """
    Raised when search execution fails.
    
    Examples:
        - Elasticsearch connection error
        - Index not found
        - Query execution error
        - Timeout errors
    """
    
    def __init__(self, message: str, entity_type: str = None, query: str = None):
        """
        Initialize SearchExecutionError.
        
        Args:
            message: Error message
            entity_type: Entity type being searched (optional)
            query: Search query (optional)
        """
        self.entity_type = entity_type
        self.query = query
        
        if entity_type and query:
            full_message = f"Search failed for entity '{entity_type}' with query '{query}': {message}"
        elif entity_type:
            full_message = f"Search failed for entity '{entity_type}': {message}"
        else:
            full_message = f"Search failed: {message}"
        
        super().__init__(full_message)


class ValidationError(SearchLibraryError):
    """
    Raised when input validation fails.
    
    Examples:
        - Empty search query
        - Invalid limit values
        - Invalid offset values
        - Invalid field names
    """
    pass

