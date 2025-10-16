"""
Error Handling Example

Demonstrates proper error handling with the library.
"""

import asyncio
from elasticsearch_search_lib import SearchClient
from elasticsearch_search_lib.exceptions import (
    SearchLibraryError,
    ConfigurationError,
    EntityNotFoundError,
    SearchExecutionError,
    ValidationError,
)


async def main():
    """Demonstrate error handling."""
    
    client = SearchClient(tenant_id="apolo")
    
    # Example 1: Handle unsupported entity type
    print("="*60)
    print("Example 1: Unsupported Entity Type")
    print("="*60)
    
    try:
        results = await client.search("invalid_entity", "test")
    except EntityNotFoundError as e:
        print(f"✓ Caught EntityNotFoundError: {e}")
        print(f"  Available entities: {e.available_entities}")
    
    # Example 2: Handle empty query
    print("\n" + "="*60)
    print("Example 2: Empty Query")
    print("="*60)
    
    try:
        results = await client.search("user", "")
    except ValidationError as e:
        print(f"✓ Caught ValidationError: {e}")
    
    # Example 3: Graceful error handling with response
    print("\n" + "="*60)
    print("Example 3: Check Response Success")
    print("="*60)
    
    # This won't raise an exception, but returns error response
    results = await client.search("user", "test_query_that_might_fail")
    
    if results.success:
        print(f"✓ Search successful: {results.total_hits} hits")
    else:
        print(f"✗ Search failed: {results.error}")
    
    # Example 4: Catch all library errors
    print("\n" + "="*60)
    print("Example 4: Catch All Library Errors")
    print("="*60)
    
    try:
        # Try to get config for invalid entity
        config = client.get_entity_config("invalid_entity")
    except SearchLibraryError as e:
        print(f"✓ Caught SearchLibraryError: {e}")
        print(f"  Exception type: {type(e).__name__}")
    
    # Example 5: Safe entity checking
    print("\n" + "="*60)
    print("Example 5: Safe Entity Checking")
    print("="*60)
    
    entity_to_search = "user"
    
    if client.is_entity_supported(entity_to_search):
        print(f"✓ Entity '{entity_to_search}' is supported")
        results = await client.search(entity_to_search, "test")
        print(f"  Search completed: {results.success}")
    else:
        print(f"✗ Entity '{entity_to_search}' is not supported")
    
    # Example 6: Multiple error types
    print("\n" + "="*60)
    print("Example 6: Handle Multiple Error Types")
    print("="*60)
    
    async def safe_search(entity_type: str, query: str):
        """Safely execute search with comprehensive error handling."""
        try:
            results = await client.search(entity_type, query)
            
            if results.success:
                return f"✓ Found {results.total_hits} results"
            else:
                return f"✗ Search failed: {results.error}"
                
        except EntityNotFoundError as e:
            return f"✗ Entity not found: {e.entity_type}"
        except ValidationError as e:
            return f"✗ Validation error: {e}"
        except SearchExecutionError as e:
            return f"✗ Execution error: {e}"
        except SearchLibraryError as e:
            return f"✗ Library error: {e}"
        except Exception as e:
            return f"✗ Unexpected error: {e}"
    
    # Test various scenarios
    test_cases = [
        ("user", "john"),           # Valid
        ("invalid", "test"),        # Invalid entity
        ("user", ""),               # Empty query
    ]
    
    for entity, query in test_cases:
        result = await safe_search(entity, query)
        print(f"  search('{entity}', '{query}'): {result}")


if __name__ == "__main__":
    asyncio.run(main())

