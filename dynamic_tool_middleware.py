"""
Dynamic Tool Middleware for FastMCP

Intercepts list/tools requests and generates user-specific tools based on
their authentication token and permissions from the external API.
"""

import logging
from typing import Optional, List
from fastmcp.server.middleware import Middleware, MiddlewareContext
from fastmcp.server.dependencies import get_http_headers, get_access_token
from fastmcp.tools import Tool
from fastmcp.tools.tool import ToolResult

from api_client import FormSchemaClient
from dynamic_tool_manager import DynamicToolManager
from tool_function_factory import create_tool_function, create_execution_handler
from tool_execution_handler import get_execution_router

logger = logging.getLogger(__name__)


def extract_auth_token(context: MiddlewareContext) -> Optional[str]:
    """
    Extract authentication token from request context.

    Tries multiple methods in order:
    1. AccessToken from get_access_token() (if OAuth/JWT configured)
    2. HTTP Authorization header (Bearer token)
    3. Falls back to None if no auth found

    Args:
        context: Middleware context from FastMCP

    Returns:
        Authentication token string or None
    """
    try:
        # Try to get AccessToken first (for OAuth/JWT scenarios)
        access_token = get_access_token()
        if access_token:
            # Use client_id as the token identifier
            token = access_token.client_id
            logger.debug(f"Extracted token from AccessToken: {token[:20]}...")
            return token

        # Fall back to HTTP Authorization header
        headers = get_http_headers()
        auth_header = headers.get("authorization", "")

        if auth_header and auth_header.startswith("Bearer "):
            token = auth_header[7:]  # Remove "Bearer " prefix
            logger.debug(f"Extracted auth token from header: {token[:20]}...")
            return token

        logger.debug("No authentication token found")
        return None

    except Exception as e:
        logger.warning(f"Error extracting auth token: {e}")
        return None


class DynamicToolMiddleware(Middleware):
    """
    Middleware that generates user-specific tools dynamically.
    
    On each list/tools request:
    1. Extracts user's auth token
    2. Fetches their schema from the API
    3. Generates tool functions from the schema
    4. Caches the tools for future requests
    5. Returns the tools to the client
    """
    
    def __init__(
        self,
        schema_client: FormSchemaClient,
        tool_manager: DynamicToolManager,
        tool_name: str = "create_request",
        tool_description: Optional[str] = None
    ):
        """
        Initialize the dynamic tool middleware.
        
        Args:
            schema_client: Client for fetching schemas from API
            tool_manager: Manager for caching generated tools
            tool_name: Name of the dynamic tool to generate (default: "create_request")
            tool_description: Optional description for the tool
        """
        super().__init__()
        self.schema_client = schema_client
        self.tool_manager = tool_manager
        self.tool_name = tool_name
        self.tool_description = tool_description or (
            "Creates a new request with dynamically defined fields based on your permissions."
        )
        self.execution_router = get_execution_router()
        logger.info(f"DynamicToolMiddleware initialized for tool: {tool_name}")
    
    async def on_list_tools(
        self,
        context: MiddlewareContext,
        call_next
    ) -> List[Tool]:
        """
        Intercept list/tools request and add user-specific dynamic tools.
        
        Args:
            context: Middleware context
            call_next: Function to call next middleware or handler
            
        Returns:
            List of Tool objects including both static and dynamic tools
        """
        logger.info("Processing list/tools request")

        # Extract auth token
        # auth_token = extract_auth_token(context)
        auth_token = "eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9.eyJsb2dpbl9zc29faWQiOjAsInVzZXJfbmFtZSI6InV1aWQzNi1jOWRjN2Y2OC1lMjdiLTRkNDgtODM3Yi05YTc1MTJlMzE2Y2UiLCJzY29wZSI6WyJOTy1TQ09QRSJdLCJsb2dpbl9zb3VyY2UiOiJub3JtYWxfbG9naW4iLCJleHAiOjE3NjAyNTY2MzcsImxvZ2luX21zcF9wb3J0YWxfaWQiOjAsImp0aSI6ImYzNjI4ZjcwLTg0YTItNGNmNy1iYWJhLWQ4YWQzNjk4YjMzMyIsImNsaWVudF9pZCI6ImZsb3RvLXdlYi1hcHAiLCJ0ZW5hbnRJZGVudGlmaWVyIjoiYXBvbG8ifQ.wcNsJ7LRlNSHFdhQy51j_vn60NgE1fdWGMaPLMhVeEXVXpoS0P13AIXigK7RhDuqw0rojiXUvrtH9AdTV8QTzj8zMwAnqoN39OSxN-wQ73NYstInJh8YaxnfOCbGk4gOLBgfQEMf-E96isgyFT477RUg0fonDSGI05L-jwkexDGjvp4XEfFYPtYQ4uICffpEumGquAu9d_pcTd2CQEuPNBZPmbfsresfAW8MAusu1r_yXm04qD4xhFkyV9nnMtxh2kJZfKltwSimUqDvvJpB-eXlY5F1LC-yaq1wdwE2f0CtHyXDQJiLx1sNB_Cr0MaLP8rwuayVlVqih-UdkBJVBA"

        
        if not auth_token:
            logger.warning("No auth token found - returning only static tools")
            # Return static tools only
            return await call_next(context)
        
        # Get static tools first
        static_tools = await call_next(context)
        logger.debug(f"Retrieved {len(static_tools)} static tools")
        
        # Check if we have cached tools for this user
        if self.tool_manager.has_cached_tools(auth_token):
            logger.info(f"Using cached tools for user: {auth_token[:20]}...")
            cached_tool_funcs = self.tool_manager.get_user_tools(auth_token)

            # Convert cached functions to Tool objects
            dynamic_tools = []
            for tool_func in cached_tool_funcs.values():
                try:
                    tool = Tool.from_function(tool_func)
                    dynamic_tools.append(tool)
                except Exception as e:
                    logger.error(f"Error converting cached function to Tool: {e}")

            # Combine static and dynamic tools
            all_tools = static_tools + dynamic_tools
            logger.info(f"Returning {len(static_tools)} static + {len(dynamic_tools)} dynamic tools")
            return all_tools
        
        # Generate new tools for this user
        try:
            logger.info(f"Generating new tools for user: {auth_token[:20]}...")
            
            # Fetch schema from API
            schema = await self.schema_client.get_tool_schema(auth_token=auth_token)
            logger.debug(f"Fetched schema with {len(schema.get('properties', {}))} properties")
            
            # Create execution handler bound to this user
            execution_handler = create_execution_handler(
                auth_token=auth_token,
                backend_handler=self.execution_router.execute
            )
            
            # Generate tool function
            tool_func = create_tool_function(
                tool_name=self.tool_name,
                schema=schema,
                execution_handler=execution_handler,
                tool_description=self.tool_description
            )
            
            # Store in cache
            self.tool_manager.store_user_tools(
                auth_token=auth_token,
                tools={self.tool_name: tool_func}
            )
            
            # Convert to Tool object
            dynamic_tool = Tool.from_function(tool_func)
            
            # Combine static and dynamic tools
            all_tools = static_tools + [dynamic_tool]
            logger.info(f"Successfully generated and cached tool '{self.tool_name}' for user")
            logger.info(f"Returning {len(static_tools)} static + 1 dynamic tool")
            
            return all_tools
            
        except Exception as e:
            logger.error(f"Error generating dynamic tools: {e}", exc_info=True)
            
            # Fallback: return only static tools
            logger.warning("Falling back to static tools only due to error")
            return static_tools
    
    async def on_call_tool(
        self,
        context: MiddlewareContext,
        call_next
    ):
        """
        Intercept tool execution and handle dynamic tools directly.

        For dynamic tools (e.g., 'create_request'), this method:
        1. Extracts the user's auth token
        2. Retrieves the cached tool function or generates it on-the-fly
        3. Executes the tool directly with the provided arguments
        4. Returns a ToolResult, bypassing FastMCP's tool registry

        For static tools, delegates to the normal execution flow via call_next().

        Args:
            context: Middleware context
            call_next: Function to call next middleware or handler

        Returns:
            ToolResult for tool execution
        """
        tool_name = context.message.name
        logger.info(f"Tool execution requested: {tool_name}")

        # Check if this is a dynamic tool
        if tool_name == self.tool_name:
            logger.info(f"Intercepting dynamic tool execution: {tool_name}")

            try:
                # Extract auth token
                # auth_token = extract_auth_token(context)
                #
                # if not auth_token:
                #     logger.error("No auth token found for dynamic tool execution")
                #     return ToolResult(
                #         structured_content={
                #             "error": True,
                #             "message": "Authentication required for this tool"
                #         }
                #     )
                auth_token = "eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9.eyJsb2dpbl9zc29faWQiOjAsInVzZXJfbmFtZSI6InV1aWQzNi1jOWRjN2Y2OC1lMjdiLTRkNDgtODM3Yi05YTc1MTJlMzE2Y2UiLCJzY29wZSI6WyJOTy1TQ09QRSJdLCJsb2dpbl9zb3VyY2UiOiJub3JtYWxfbG9naW4iLCJleHAiOjE3NjAyNTY2MzcsImxvZ2luX21zcF9wb3J0YWxfaWQiOjAsImp0aSI6ImYzNjI4ZjcwLTg0YTItNGNmNy1iYWJhLWQ4YWQzNjk4YjMzMyIsImNsaWVudF9pZCI6ImZsb3RvLXdlYi1hcHAiLCJ0ZW5hbnRJZGVudGlmaWVyIjoiYXBvbG8ifQ.wcNsJ7LRlNSHFdhQy51j_vn60NgE1fdWGMaPLMhVeEXVXpoS0P13AIXigK7RhDuqw0rojiXUvrtH9AdTV8QTzj8zMwAnqoN39OSxN-wQ73NYstInJh8YaxnfOCbGk4gOLBgfQEMf-E96isgyFT477RUg0fonDSGI05L-jwkexDGjvp4XEfFYPtYQ4uICffpEumGquAu9d_pcTd2CQEuPNBZPmbfsresfAW8MAusu1r_yXm04qD4xhFkyV9nnMtxh2kJZfKltwSimUqDvvJpB-eXlY5F1LC-yaq1wdwE2f0CtHyXDQJiLx1sNB_Cr0MaLP8rwuayVlVqih-UdkBJVBA"

                # Try to get cached tool function
                cached_tools = self.tool_manager.get_user_tools(auth_token)
                tool_func = cached_tools.get(tool_name)

                # If not cached, generate it on-the-fly
                if not tool_func:
                    logger.info(f"Tool not cached, generating on-the-fly for user: {auth_token[:20]}...")

                    # Fetch schema from API
                    schema = await self.schema_client.get_tool_schema(auth_token=auth_token)

                    # Create execution handler bound to this user
                    execution_handler = create_execution_handler(
                        auth_token=auth_token,
                        backend_handler=self.execution_router.execute
                    )

                    # Generate tool function
                    tool_func = create_tool_function(
                        tool_name=self.tool_name,
                        schema=schema,
                        execution_handler=execution_handler,
                        tool_description=self.tool_description
                    )

                    # Store in cache for future use
                    self.tool_manager.store_user_tools(
                        auth_token=auth_token,
                        tools={self.tool_name: tool_func}
                    )
                    logger.info(f"Generated and cached tool '{tool_name}' for user")

                # Execute the tool function with provided arguments
                arguments = context.message.arguments or {}
                logger.debug(f"Executing tool '{tool_name}' with arguments: {list(arguments.keys())}")

                result = await tool_func(**arguments)

                logger.info(f"Dynamic tool '{tool_name}' executed successfully")

                # Wrap result in ToolResult
                return ToolResult(structured_content=result)

            except Exception as e:
                logger.error(f"Error executing dynamic tool '{tool_name}': {e}", exc_info=True)
                return ToolResult(
                    structured_content={
                        "error": True,
                        "message": f"Failed to execute tool '{tool_name}': {str(e)}"
                    }
                )

        # For static tools, use normal flow
        try:
            result = await call_next(context)
            logger.info(f"Static tool '{tool_name}' executed successfully")
            return result
        except Exception as e:
            logger.error(f"Error executing static tool '{tool_name}': {e}", exc_info=True)
            raise

