# Elasticsearch Search Library

A simple, configuration-driven Elasticsearch search library for ITSM entities.

## Features

- **Simple API**: Clean, intuitive interface for entity searches
- **XML Configuration**: Entity-level settings with field-specific configurations
- **11 Entity Types**: Support for all ITSM entity types
- **Conditional Queries**: Automatic query type selection based on fuzziness
- **Type Safety**: Dataclass-based models for configuration and results
- **Async Support**: Full async/await support for search operations

## Quick Start

### Installation

The library is part of your project. No additional installation needed.

### Basic Usage

```python
from elasticsearch_search_lib import SearchClient

# Create search client
client = SearchClient(tenant_id="apolo")

# Search for users
results = await client.search("user", "john doe", limit=10)

# Access results
print(f"Found {results.total_hits} users")
for item in results.items:
    print(f"Name: {item.data['user_name']}, Score: {item.score}")
```

### Search Different Entity Types

```python
# Search impacts
results = await client.search("impact", "High")

# Search locations
results = await client.search("location", "Building A")

# Search vendors
results = await client.search("vendor", "Microsoft")
```

## Supported Entity Types

The library supports 11 ITSM entity types:

### Simple Entities (name, id)
- `impact` - Impact levels
- `urgency` - Urgency levels
- `priority` - Priority levels

### Model-Based Entities (name, id, model)
- `status` - Status values
- `category` - Categories
- `source` - Sources

### Hierarchical Entities (hierarchy, parent/child)
- `location` - Locations with hierarchy
- `department` - Departments with hierarchy

### Complex Entities (multiple fields)
- `usergroup` - User groups
- `user` - Users (name, email, contact, etc.)
- `vendor` - Vendors

## Configuration

### Entity-Level Settings

Each entity has its own configuration in `config/search_config.xml`:

```xml
<entity type="user">
    <fuzziness>AUTO</fuzziness>
    <defaultLimit>10</defaultLimit>
    <maxLimit>100</maxLimit>
    <minScore>0.0</minScore>
    <fields>
        <!-- Field configurations -->
    </fields>
</entity>
```

**Settings:**
- `fuzziness`: Fuzzy matching tolerance (0, 1, 2, AUTO)
- `defaultLimit`: Default number of results
- `maxLimit`: Maximum allowed results
- `minScore`: Minimum relevance score threshold

### Field-Level Settings

Each field can have its own configuration:

```xml
<field>
    <name>user_name</name>
    <boost>3.0</boost>
    <enabled>true</enabled>
    <fuzziness>AUTO</fuzziness>
</field>
```

**Settings:**
- `name`: Field name in Elasticsearch
- `boost`: Relevance boost multiplier
- `enabled`: Whether field is included in searches
- `fuzziness`: Field-specific fuzziness (overrides entity default)

## API Reference

### SearchClient

Main client for entity searches.

#### Constructor

```python
SearchClient(
    tenant_id: str,
    es_host: Optional[str] = None,
    es_port: int = 9200,
    config_path: Optional[str] = None
)
```

**Parameters:**
- `tenant_id`: Tenant identifier for index naming
- `es_host`: Elasticsearch host (defaults to ES_HOST env var or 'localhost')
- `es_port`: Elasticsearch port (default: 9200)
- `config_path`: Path to configuration file (uses default if None)

#### Methods

##### search()

```python
async def search(
    entity_type: str,
    query: str,
    limit: Optional[int] = None,
    from_offset: int = 0
) -> SearchResponse
```

Search for entities.

**Parameters:**
- `entity_type`: Type of entity to search
- `query`: Search query string
- `limit`: Maximum results (uses entity default if None)
- `from_offset`: Offset for pagination

**Returns:** `SearchResponse` object

##### get_supported_entities()

```python
def get_supported_entities() -> List[str]
```

Get list of supported entity types.

##### get_entity_config()

```python
def get_entity_config(entity_type: str) -> EntityConfig
```

Get configuration for an entity type.

##### get_entity_fields()

```python
def get_entity_fields(entity_type: str) -> List[FieldConfig]
```

Get enabled fields for an entity type.

##### is_entity_supported()

```python
def is_entity_supported(entity_type: str) -> bool
```

Check if an entity type is supported.

### SearchResponse

Response object from search operations.

**Attributes:**
- `success`: Whether search was successful
- `entity_type`: Entity type that was searched
- `query`: Search query string
- `total_hits`: Total number of matching documents
- `returned_count`: Number of results in this response
- `items`: List of `SearchResult` objects
- `index_name`: Elasticsearch index that was searched
- `error`: Error message (if search failed)

**Methods:**
- `to_dict()`: Convert to dictionary
- `__len__()`: Get number of results
- `__iter__()`: Iterate over results
- `__getitem__(index)`: Get result by index

### SearchResult

Single search result item.

**Attributes:**
- `data`: Source data from Elasticsearch document
- `score`: Relevance score
- `index`: Index name where document was found
- `id`: Document ID

**Methods:**
- `get(key, default)`: Get value from data dictionary
- `to_dict()`: Convert to dictionary

## Query Strategy

The library uses conditional query types based on fuzziness:

### Exact Matching (fuzziness = 0)

Uses `match_phrase` for exact phrase matching:

```json
{
  "match_phrase": {
    "user_email": {
      "query": "john@example.com",
      "boost": 2.5
    }
  }
}
```

### Fuzzy Matching (fuzziness > 0)

Uses `match` with fuzziness for tolerant matching:

```json
{
  "match": {
    "user_name": {
      "query": "john doe",
      "fuzziness": "AUTO",
      "boost": 3.0
    }
  }
}
```

## Error Handling

The library provides custom exceptions:

```python
from elasticsearch_search_lib.exceptions import (
    SearchLibraryError,      # Base exception
    ConfigurationError,      # Configuration errors
    EntityNotFoundError,     # Entity type not found
    SearchExecutionError,    # Search execution errors
    ValidationError,         # Input validation errors
)

try:
    results = await client.search("user", "john")
except EntityNotFoundError as e:
    print(f"Entity not found: {e}")
except SearchExecutionError as e:
    print(f"Search failed: {e}")
except SearchLibraryError as e:
    print(f"Library error: {e}")
```

## Examples

### Pagination

```python
# Get first page
page1 = await client.search("user", "john", limit=10, from_offset=0)

# Get second page
page2 = await client.search("user", "john", limit=10, from_offset=10)
```

### Check Entity Support

```python
if client.is_entity_supported("user"):
    results = await client.search("user", "john")
else:
    print("User entity not supported")
```

### Get Entity Configuration

```python
config = client.get_entity_config("user")
print(f"Default limit: {config.default_limit}")
print(f"Max limit: {config.max_limit}")
print(f"Min score: {config.min_score}")
```

### Get Entity Fields

```python
fields = client.get_entity_fields("user")
for field in fields:
    print(f"{field.name}: boost={field.boost}, fuzziness={field.fuzziness}")
```

## Architecture

```
elasticsearch_search_lib/
├── __init__.py           # Public API
├── client.py             # SearchClient
├── query_builder.py      # Query construction
├── search_handler.py     # Search execution
├── models.py             # Data models
├── exceptions.py         # Custom exceptions
└── config/
    ├── loader.py         # Configuration loader
    └── search_config.xml # Entity configurations
```

## License

Internal ITSM project library.

