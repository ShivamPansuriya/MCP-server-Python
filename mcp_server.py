#!/usr/bin/env python3
"""
MCP Server with HTTP-Streamable Transport and Permission-Based Access Control

A Model Context Protocol server implementation using fastMCP with:
- HTTP-streamable transport for efficient bidirectional communication
- Permission-based filtering for tools based on user roles
- Dynamic tool generation based on user permissions from external API
- Middleware for intercepting and validating tool access
"""

import logging
from fastmcp import FastMCP

from config import AppConfig, setup_logging
from server_initializer import ServerInitializer
from search_users_tool import search_users as search_users_impl
from search_entities_tool import search_entities

# Setup logging
setup_logging()
logger = logging.getLogger(__name__)

# Load configuration
config = AppConfig.load()

# Validate configuration
if not config.validate():
    raise RuntimeError("Invalid configuration. Please check environment variables.")

# Initialize the FastMCP server
mcp = FastMCP("MCPServerPermission")

# Initialize all server components
initializer = ServerInitializer(config)
components = initializer.initialize_all()

# Register dynamic tool middleware
mcp.add_middleware(components['middleware'])
logger.info("Dynamic tool middleware registered")


# ============================================================================
# MCP Tool Definitions
# ============================================================================

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


# ============================================================================
# Server Entry Point
# ============================================================================

if __name__ == "__main__":
    """
    Start the MCP server with HTTP transport.

    Note: The create_request tool is dynamically generated per-user based on
    their permissions from the form schema API. Each authenticated user will
    receive a custom create_request tool with fields specific to their permissions.
    """
    logger.info(f"Starting MCP server on {config.server.host}:{config.server.port}")
    mcp.run(
        transport="http",
        host=config.server.host,
        port=config.server.port
    )
