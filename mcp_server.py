#!/usr/bin/env python3
"""
MCP Server with HTTP-Streamable Transport and Permission-Based Access Control

A Model Context Protocol server implementation using fastMCP with:
- HTTP-streamable transport for efficient bidirectional communication
- Permission-based filtering for tools based on user roles
- Dynamic tool generation based on user permissions from external API
- Middleware for intercepting and validating tool access
"""

import uuid
import logging
from datetime import datetime
from fastmcp import FastMCP

from api_client import FormSchemaClient
from dynamic_tool_manager import DynamicToolManager
from dynamic_tool_middleware import DynamicToolMiddleware
from search_users_tool import search_users as search_users_impl
from search_entities_tool import search_entities, get_supported_entity_types, get_entity_fields
from user_type_enum import UserType

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Configure dynamic form schema API URL
FORM_SCHEMA_API_URL = "http://172.16.11.131/api/module/request/form"

# Initialize the FastMCP server
mcp = FastMCP("MCPServerPermission")

# Initialize components for dynamic tool generation
logger.info("Initializing dynamic tool system...")
schema_client = FormSchemaClient(
    api_url=FORM_SCHEMA_API_URL,
    cache_ttl=300,  # 5 minutes cache
    verbose=True
)
tool_manager = DynamicToolManager(cache_ttl_seconds=300)

# Create and add dynamic tool middleware
dynamic_middleware = DynamicToolMiddleware(
    schema_client=schema_client,
    tool_manager=tool_manager,
    tool_name="create_request",
    tool_description=(
        "Creates a new request with dynamically defined fields based on your permissions. "
        "The available fields are determined by the form schema API and may vary based on "
        "user permissions."
    )
)
mcp.add_middleware(dynamic_middleware)
logger.info("Dynamic tool middleware registered")

# Initialize elasticsearch search library
logger.info("Initializing Elasticsearch search library...")
try:
    from elasticsearch_search_lib import SearchClient
    # Create search client with default tenant
    search_client = SearchClient(tenant_id="apolo")
    logger.info(f"Search library initialized with {len(search_client.get_supported_entities())} entity types")
except Exception as e:
    logger.error(f"Error initializing search library: {e}", exc_info=True)
    logger.warning("Search tools will be available but may fail at runtime")
    search_client = None

@mcp.tool
def add(a: int, b: int) -> int:
    """
    Adds two integer numbers together.
    
    Args:
        a: First integer number
        b: Second integer number
        
    Returns:
        The sum of a and b
    """
    return a + b

@mcp.tool
def echo(message: str) -> str:
    """
    Echoes back the provided message.
    
    Args:
        message: The message to echo back
        
    Returns:
        The same message that was provided
    """
    return f"Echo: {message}"


@mcp.tool
def multiply(a: int, b: int) -> int:
    """
    Multiplies two integer numbers.

    Args:
        a: First integer number
        b: Second integer number

    Returns:
        The product of a and b
    """
    return a * b


@mcp.tool
async def search_users(query: str) -> dict:
    """
    Search for users using a simple query string.

    Simplified search function that accepts only a query string.
    All other parameters (limit, tenant_id, etc.) are handled internally
    through configuration and defaults.

    Args:
        query: Search query string (e.g., "ANUJKUMARJ28@GMAIL.COM", "John Doe", "9876543210")

    Returns:
        Dictionary containing search results with user information
    """
    return await search_users_impl(query)


@mcp.tool
async def search_entities_by_type(entity_type: str, query: str) -> dict:
    """
    Search for entities of any type using a unified approach.

    This function can search across all supported entity types using
    the same unified query builder and search handler.

    Args:
        entity_type: Type of entity to search (user, impact, urgency, priority,
                    status, category, source, location, department, usergroup, vendor)
        query: Search query string

    Returns:
        Dictionary containing search results with entity information
    """
    return await search_entities(entity_type, query)


# NOTE: The create_request tool is now dynamically generated per-user
# based on their permissions from the form schema API. The static version
# has been removed and replaced by the dynamic tool middleware.
#
# Each authenticated user will receive a custom create_request tool with
# fields specific to their permissions.


if __name__ == "__main__":
    # Run with HTTP transport (uses StreamableHttpTransport internally)
    mcp.run(transport="http", host="127.0.0.1", port=9092)
