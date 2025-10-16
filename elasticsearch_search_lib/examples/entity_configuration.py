"""
Entity Configuration Example

Demonstrates how to access and use entity configuration.
"""

import asyncio
from elasticsearch_search_lib import SearchClient


async def main():
    """Demonstrate entity configuration access."""
    
    # Create search client
    client = SearchClient(tenant_id="apolo")
    
    # Get all supported entities
    entities = client.get_supported_entities()
    print(f"Total supported entities: {len(entities)}\n")
    
    # Show configuration for each entity type
    for entity_type in entities:
        print("="*60)
        print(f"Entity: {entity_type.upper()}")
        print("="*60)
        
        # Get entity configuration
        config = client.get_entity_config(entity_type)
        
        print(f"\nSettings:")
        print(f"  Fuzziness: {config.fuzziness}")
        print(f"  Default Limit: {config.default_limit}")
        print(f"  Max Limit: {config.max_limit}")
        print(f"  Min Score: {config.min_score}")
        
        # Get enabled fields
        fields = client.get_entity_fields(entity_type)
        print(f"\nEnabled Fields ({len(fields)}):")
        
        for field in fields:
            print(f"  - {field.name}")
            print(f"    Boost: {field.boost}")
            print(f"    Fuzziness: {field.fuzziness}")
        
        print()
    
    # Demonstrate checking entity support
    print("="*60)
    print("Checking Entity Support")
    print("="*60)
    
    test_entities = ["user", "impact", "invalid_entity"]
    
    for entity in test_entities:
        supported = client.is_entity_supported(entity)
        status = "✓ Supported" if supported else "✗ Not Supported"
        print(f"{entity}: {status}")
    
    # Get index names
    print("\n" + "="*60)
    print("Index Names")
    print("="*60)
    
    for entity_type in ["user", "impact", "location"]:
        index_name = client.get_index_name(entity_type)
        print(f"{entity_type}: {index_name}")


if __name__ == "__main__":
    asyncio.run(main())

