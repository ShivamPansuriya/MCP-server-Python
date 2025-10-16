"""
Basic Search Example

Demonstrates basic usage of the Elasticsearch Search Library.
"""

import asyncio
from elasticsearch_search_lib import SearchClient


async def main():
    """Run basic search examples."""
    
    # Create search client
    print("Creating search client...")
    client = SearchClient(tenant_id="apolo")
    
    # Get supported entities
    print("\nSupported entity types:")
    entities = client.get_supported_entities()
    print(f"  {', '.join(entities)}")
    
    # Search for users
    print("\n" + "="*60)
    print("Searching for users with query 'john'...")
    print("="*60)
    
    results = await client.search("user", "john", limit=5)
    
    if results.success:
        print(f"\nFound {results.total_hits} users, showing {results.returned_count}:")
        for i, item in enumerate(results.items, 1):
            print(f"\n{i}. {item.data.get('user_name', 'N/A')}")
            print(f"   Email: {item.data.get('user_email', 'N/A')}")
            print(f"   Score: {item.score:.2f}")
    else:
        print(f"Search failed: {results.error}")
    
    # Search for impacts
    print("\n" + "="*60)
    print("Searching for impacts with query 'high'...")
    print("="*60)
    
    results = await client.search("impact", "high", limit=5)
    
    if results.success:
        print(f"\nFound {results.total_hits} impacts, showing {results.returned_count}:")
        for i, item in enumerate(results.items, 1):
            print(f"\n{i}. {item.data.get('impact_name', 'N/A')}")
            print(f"   ID: {item.data.get('impact_id', 'N/A')}")
            print(f"   Score: {item.score:.2f}")
    else:
        print(f"Search failed: {results.error}")
    
    # Search for locations
    print("\n" + "="*60)
    print("Searching for locations with query 'building'...")
    print("="*60)
    
    results = await client.search("location", "building", limit=5)
    
    if results.success:
        print(f"\nFound {results.total_hits} locations, showing {results.returned_count}:")
        for i, item in enumerate(results.items, 1):
            print(f"\n{i}. {item.data.get('location_name', 'N/A')}")
            print(f"   Hierarchy: {item.data.get('location_hierarchy', 'N/A')}")
            print(f"   Score: {item.score:.2f}")
    else:
        print(f"Search failed: {results.error}")


if __name__ == "__main__":
    asyncio.run(main())

