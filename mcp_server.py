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
from elasticsearch_client import get_elasticsearch_client
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

# Initialize Elasticsearch client for user search
logger.info("Initializing Elasticsearch client for user search...")
try:
    es_client_wrapper = get_elasticsearch_client()
    if es_client_wrapper.connect():
        logger.info("Elasticsearch client connected successfully")
    else:
        logger.warning("Elasticsearch client failed to connect - search_users tool may not work")
except Exception as e:
    logger.error(f"Error initializing Elasticsearch client: {e}", exc_info=True)
    logger.warning("search_users tool will be available but may fail at runtime")

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
async def search_users(
    name: str = None,
    email: str = None,
    contact: str = None,
    userlogonname: str = None,
    contact2: str = None,
    userType: UserType = None,
    limit: int = 10,
    minScore: float = None
) -> dict:
    """
    Search for users using fuzzy matching on specific fields.

    Searches user records by specific fields with fuzzy matching for typo tolerance.
    At least one search field must be provided.

    Args:
        name: Search by user's full name
        email: Search by email address
        contact: Search by primary contact number
        userlogonname: Search by user login name
        contact2: Search by secondary contact number
        userType: Optional filter by user type. Valid values: "requester" or "technician"
        limit: Maximum number of results to return (1-100, default: 10)
        minScore: Minimum confidence score threshold. Only return users with score >= this value (e.g., 7.0)

    Returns:
        Dictionary containing search results with user information
    """
    return await search_users_impl(
        name=name,
        email=email,
        contact=contact,
        userlogonname=userlogonname,
        contact2=contact2,
        userType=userType,
        limit=limit,
        minScore=minScore
    )


# NOTE: The create_request tool is now dynamically generated per-user
# based on their permissions from the form schema API. The static version
# has been removed and replaced by the dynamic tool middleware.
#
# Each authenticated user will receive a custom create_request tool with
# fields specific to their permissions.


if __name__ == "__main__":
    # Run with HTTP transport (uses StreamableHttpTransport internally)
    mcp.run(transport="http", host="127.0.0.1", port=9092)
