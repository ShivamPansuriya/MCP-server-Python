"""
Tool Execution Handler for Dynamic MCP Tools

Handles the actual execution of dynamically generated tools by calling
backend APIs or business logic with validated arguments.
"""

import uuid
import logging
from datetime import datetime
from typing import Dict, Any

logger = logging.getLogger(__name__)


async def execute_dynamic_tool(
    auth_token: str,
    tool_name: str,
    **kwargs
) -> Dict[str, Any]:
    """
    Execute a dynamically generated tool with user authentication context.
    
    This is the backend handler that processes tool execution requests.
    It receives validated arguments from the dynamically generated tool
    functions and performs the actual business logic.
    
    Args:
        auth_token: User's authentication token for context
        tool_name: Name of the tool being executed
        **kwargs: Dynamic arguments based on the tool's schema
        
    Returns:
        Dictionary containing the execution result
    """
    logger.info(f"Executing dynamic tool '{tool_name}' for user: {auth_token[:20]}...")
    logger.debug(f"Tool arguments: {kwargs}")
    
    try:
        # Generate unique request ID
        request_id = str(uuid.uuid4())
        timestamp = datetime.utcnow().isoformat() + "Z"
        
        # Build response with metadata
        response = {
            "id": request_id,
            "timestamp": timestamp,
            "status": "pending",
            "tool_name": tool_name,
            "user_token": auth_token[:20] + "...",  # Truncated for security
        }
        
        # Add all dynamic fields from kwargs
        if kwargs:
            response["data"] = kwargs
        
        logger.info(f"Successfully executed tool '{tool_name}' with request ID: {request_id}")
        
        return response
        
    except Exception as e:
        logger.error(f"Error executing tool '{tool_name}': {e}", exc_info=True)
        
        # Return structured error response
        return {
            "error": True,
            "message": f"Failed to execute tool '{tool_name}': {str(e)}",
            "tool_name": tool_name,
            "timestamp": datetime.utcnow().isoformat() + "Z"
        }


async def execute_create_request_tool(
    auth_token: str,
    tool_name: str,
    **kwargs
) -> Dict[str, Any]:
    """
    Specialized execution handler for 'create_request' tool.
    
    This handler mimics the behavior of the original static create_request
    tool but with dynamic schema-based arguments.
    
    Args:
        auth_token: User's authentication token
        tool_name: Should be "create_request"
        **kwargs: Dynamic request fields based on user's schema
        
    Returns:
        Dictionary containing the created request details
    """
    logger.info(f"Creating request for user: {auth_token[:20]}...")
    logger.debug(f"Request data: {kwargs}")
    
    try:
        # Generate unique request ID
        request_id = str(uuid.uuid4())
        timestamp = datetime.utcnow().isoformat() + "Z"
        
        # Build response matching original create_request format
        response = {
            "id": request_id,
            "timestamp": timestamp,
            "status": "pending"
        }
        
        # Add all provided fields
        if kwargs:
            response.update(kwargs)
        
        logger.info(f"Successfully created request with ID: {request_id}")
        
        return response
        
    except Exception as e:
        logger.error(f"Error creating request: {e}", exc_info=True)
        
        # Return structured error response
        return {
            "error": True,
            "message": f"Failed to create request: {str(e)}",
            "timestamp": datetime.utcnow().isoformat() + "Z"
        }


class ToolExecutionRouter:
    """
    Routes tool execution to appropriate handlers based on tool name.
    
    This allows different tools to have different execution logic while
    maintaining a unified interface for the dynamic tool system.
    """
    
    def __init__(self):
        """Initialize the execution router with default handlers."""
        self._handlers: Dict[str, Any] = {
            "create_request": execute_create_request_tool,
            # Add more specialized handlers here as needed
        }
        self._default_handler = execute_dynamic_tool
        logger.info(f"ToolExecutionRouter initialized with {len(self._handlers)} specialized handlers")
    
    def register_handler(self, tool_name: str, handler: Any) -> None:
        """
        Register a specialized handler for a specific tool.
        
        Args:
            tool_name: Name of the tool
            handler: Async callable that handles execution
        """
        self._handlers[tool_name] = handler
        logger.info(f"Registered specialized handler for tool: {tool_name}")
    
    async def execute(self, auth_token: str, tool_name: str, **kwargs) -> Dict[str, Any]:
        """
        Route tool execution to the appropriate handler.
        
        Args:
            auth_token: User's authentication token
            tool_name: Name of the tool to execute
            **kwargs: Tool arguments
            
        Returns:
            Execution result from the handler
        """
        # Get specialized handler or use default
        handler = self._handlers.get(tool_name, self._default_handler)
        
        logger.debug(f"Routing tool '{tool_name}' to handler: {handler.__name__}")
        
        # Execute with handler
        return await handler(auth_token=auth_token, tool_name=tool_name, **kwargs)


# Global router instance
_global_router = ToolExecutionRouter()


def get_execution_router() -> ToolExecutionRouter:
    """
    Get the global tool execution router instance.
    
    Returns:
        Global ToolExecutionRouter instance
    """
    return _global_router

