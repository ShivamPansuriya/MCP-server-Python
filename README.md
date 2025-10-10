# MCP Server with Dynamic Per-User Tool Generation

A Model Context Protocol (MCP) server implementation using FastMCP that dynamically generates tools based on user permissions from an external API.

## Features

- **Dynamic Tool Generation**: Tools are generated at runtime based on user-specific schemas from an external API
- **Per-User Permissions**: Each authenticated user receives tools tailored to their permissions
- **Intelligent Caching**: Both API schemas and generated tools are cached with TTL for performance
- **Graceful Degradation**: Falls back to static tools if API is unavailable
- **Comprehensive Logging**: Detailed logging at INFO, DEBUG, WARNING, and ERROR levels
- **Thread-Safe**: Concurrent requests from multiple users are handled safely

## Architecture

### Components

1. **`mcp_server.py`** - Main server entry point
   - Initializes FastMCP server
   - Registers static tools (add, echo, multiply)
   - Sets up dynamic tool middleware

2. **`api_client.py`** - External API integration
   - `FormSchemaClient`: Fetches and parses schemas from external API
   - `FormSchemaCache`: Caches API responses with TTL
   - Converts API field definitions to JSON Schema format

3. **`dynamic_tool_manager.py`** - Tool lifecycle management
   - `DynamicToolManager`: Manages per-user tool storage
   - Thread-safe caching with TTL
   - Cache statistics and invalidation

4. **`tool_function_factory.py`** - Dynamic function generation
   - Creates typed async functions from JSON schemas
   - Generates proper `inspect.Signature` for FastMCP validation
   - Maps JSON Schema types to Python types

5. **`tool_execution_handler.py`** - Tool execution backend
   - `ToolExecutionRouter`: Routes tool calls to appropriate handlers
   - Specialized handlers for different tool types
   - Structured error responses

6. **`dynamic_tool_middleware.py`** - FastMCP middleware
   - Intercepts `list/tools` requests
   - Extracts authentication tokens
   - Generates and caches user-specific tools
   - Returns combined static + dynamic tools

## Installation

1. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

2. **Configure the API URL:**
   Edit `mcp_server.py` and set the `FORM_SCHEMA_API_URL` to your external API endpoint:
   ```python
   FORM_SCHEMA_API_URL = "http://172.16.11.131/api/module/request/form"
   ```

## Usage

### Starting the Server

```bash
python mcp_server.py
```

The server will start on `http://127.0.0.1:9092/mcp`

### Authentication

The server expects authentication via HTTP `Authorization` header:

```
Authorization: Bearer <your-token>
```

The token is used to:
1. Fetch user-specific schema from the external API
2. Generate tools with fields the user has permission to access
3. Cache tools for subsequent requests

### Available Tools

#### Static Tools (Always Available)

- **`add(a: int, b: int) -> int`** - Adds two numbers
- **`echo(message: str) -> str`** - Echoes a message
- **`multiply(a: int, b: int) -> int`** - Multiplies two numbers

#### Dynamic Tools (User-Specific)

- **`create_request(...)`** - Creates a request with fields based on user permissions
  - Parameters are dynamically generated from the external API schema
  - Each user sees different parameters based on their permissions
  - Required fields, enums, and types are enforced

## How It Works

### Request Flow

1. **Client sends `list/tools` request** with `Authorization: Bearer <token>`

2. **Middleware intercepts the request:**
   - Extracts auth token from header
   - Checks if tools are cached for this user
   - If cached: Returns cached tools
   - If not cached: Proceeds to generation

3. **Tool Generation:**
   - Fetches schema from external API with user's token
   - Parses API response into JSON Schema
   - Creates typed async function with proper signature
   - Converts function to FastMCP `Tool` object
   - Caches the tool for future requests

4. **Response:**
   - Returns list of static tools + dynamic tools
   - Client sees tools specific to their permissions

### Tool Execution Flow

1. **Client calls `create_request` tool** with arguments

2. **FastMCP validates arguments** against the generated function signature

3. **Tool execution handler:**
   - Receives validated arguments
   - Processes the request
   - Returns structured response with ID, timestamp, status

## Configuration

### Cache TTL

Both schema cache and tool cache use 5-minute TTL by default. To change:

```python
# In mcp_server.py
schema_client = FormSchemaClient(
    api_url=FORM_SCHEMA_API_URL,
    cache_ttl=300,  # Change this value (seconds)
    verbose=True
)
tool_manager = DynamicToolManager(cache_ttl_seconds=300)  # Change this value
```

### Logging Level

To change logging verbosity:

```python
# In mcp_server.py
logging.basicConfig(
    level=logging.DEBUG,  # Change to DEBUG, INFO, WARNING, or ERROR
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
```

## Testing

See `TEST_SCENARIOS.md` for comprehensive test scenarios including:

- User-specific tool generation
- Caching behavior
- Tool execution
- Error handling
- Validation enforcement

## API Schema Format

The external API should return a response with this structure:

```json
{
  "fieldList": [
    {
      "name": "Subject",
      "paramName": "subject",
      "type": "TextFieldRest",
      "required": true,
      "description": "Request subject",
      "groupIds": [1, 2],
      "hidden": false,
      "removed": false,
      "inActive": false
    }
  ]
}
```

Supported field types:
- `TextFieldRest` → `string`
- `NumberFieldRest` → `number`
- `DropDownFieldRest` → `string` with enum
- `MultiSelectDropDownFieldRest` → `array` of strings
- And more (see `api_client.py` for full mapping)

## Security Considerations

- Authentication tokens are truncated in logs and responses
- Tokens are validated on each request
- No token = static tools only (graceful degradation)
- FastMCP validates all tool arguments before execution

## Troubleshooting

### Server won't start
- Check that all dependencies are installed: `pip install -r requirements.txt`
- Verify Python version is 3.12+
- Check logs for import errors

### Tools not appearing
- Verify `Authorization` header is present and correctly formatted
- Check server logs for API fetch errors
- Ensure external API is accessible
- Verify user has permissions in the external system

### Cache not updating
- Default TTL is 5 minutes
- Manually clear cache: Call `tool_manager.clear_all_tools()` or restart server
- Check logs for cache hit/miss messages

## License

[Your License Here]

## Contributing

[Your Contributing Guidelines Here]

