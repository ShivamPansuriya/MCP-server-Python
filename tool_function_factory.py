"""
Tool Function Factory for Dynamic MCP Tool Generation

Creates typed async functions from JSON Schema definitions that can be
registered as FastMCP tools.
"""

import inspect
import logging
from typing import Dict, Callable, Any, Optional, List, get_origin, get_args
from functools import wraps

logger = logging.getLogger(__name__)


# JSON Schema type to Python type mapping
JSON_SCHEMA_TYPE_MAP = {
    "string": str,
    "number": float,
    "integer": int,
    "boolean": bool,
    "array": list,
    "object": dict,
    "null": type(None),
}


def parse_json_schema_type(schema_type: str, property_def: Dict) -> type:
    """
    Convert JSON Schema type to Python type annotation.
    
    Args:
        schema_type: JSON Schema type string (e.g., "string", "number")
        property_def: Full property definition from schema (for array items, etc.)
        
    Returns:
        Python type for annotation
    """
    base_type = JSON_SCHEMA_TYPE_MAP.get(schema_type, str)
    
    # For arrays, we use List type hint
    if schema_type == "array":
        items_def = property_def.get("items", {})
        item_type = items_def.get("type", "string")
        item_python_type = JSON_SCHEMA_TYPE_MAP.get(item_type, str)
        return List[item_python_type]
    
    return base_type


def extract_parameters_from_schema(schema: Dict) -> List[Dict[str, Any]]:
    """
    Extract parameter definitions from JSON Schema.

    Args:
        schema: JSON Schema object with properties and optional required fields

    Returns:
        List of parameter definitions with name, type, required, default, description
    """
    try:
        properties = schema.get("properties", {})
        required_fields = schema.get("required", [])

        parameters = []

        for param_name, prop_def in properties.items():
            try:
                schema_type = prop_def.get("type", "string")
                python_type = parse_json_schema_type(schema_type, prop_def)

                param_info = {
                    "name": param_name,
                    "type": python_type,
                    "required": param_name in required_fields,
                    "description": prop_def.get("description", ""),
                    "default": prop_def.get("default"),
                    "enum": prop_def.get("enum"),
                }

                parameters.append(param_info)
            except Exception as e:
                logger.warning(f"Error parsing parameter '{param_name}': {e}. Skipping.")
                continue

        logger.debug(f"Extracted {len(parameters)} parameters from schema")
        return parameters

    except Exception as e:
        logger.error(f"Error extracting parameters from schema: {e}")
        return []


def create_tool_function(
    tool_name: str,
    schema: Dict,
    execution_handler: Callable,
    tool_description: Optional[str] = None
) -> Callable:
    """
    Dynamically create a typed async function from JSON Schema.
    
    This function generates a properly typed async function that:
    1. Has correct parameter names and type annotations from the schema
    2. Validates required vs optional parameters
    3. Calls the execution_handler with validated arguments
    4. Has proper __name__, __doc__, and __signature__ for FastMCP
    
    Args:
        tool_name: Name of the tool (becomes function name)
        schema: JSON Schema defining the tool's parameters
        execution_handler: Async function to call with validated arguments
        tool_description: Optional description for the tool's docstring
        
    Returns:
        Async callable function ready to be registered as a FastMCP tool
    """
    # Extract parameters from schema
    param_defs = extract_parameters_from_schema(schema)
    
    # Build function signature
    params = []

    for param_def in param_defs:
        param_name = param_def["name"]
        param_type = param_def.get("type", Any)
        is_required = param_def.get("required", False)
        default_value = param_def.get("default", inspect.Parameter.empty)

        if is_required:
            # Required parameter, no default
            param = inspect.Parameter(
                param_name,
                inspect.Parameter.POSITIONAL_OR_KEYWORD,
                annotation=param_type
            )
        else:
            # Optional parameter, set default (could be None)
            param = inspect.Parameter(
                param_name,
                inspect.Parameter.POSITIONAL_OR_KEYWORD,
                default=default_value,
                annotation=param_type
            )

        params.append(param)

    # Sort parameters: required (no default) first, then optional (with defaults)
    # This is required by Python - parameters with defaults must come after those without
    params.sort(key=lambda p: (p.default is not inspect.Parameter.empty, p.name))

    try:
        signature = inspect.Signature(params)
    except Exception as e:
        logger.error(f"Error creating signature for tool '{tool_name}': {e}")
    
    # Create the async function template
    async def tool_template(**kwargs):
        """Dynamically generated tool function."""
        try:
            logger.debug(f"Executing tool '{tool_name}' with args: {list(kwargs.keys())}")

            # Call the execution handler with all arguments
            result = await execution_handler(tool_name=tool_name, **kwargs)
            return result
        except Exception as e:
            logger.error(f"Error in tool template for '{tool_name}': {e}", exc_info=True)
            raise
    
    # Create wrapper that enforces the signature
    @wraps(tool_template)
    async def tool_wrapper(*args, **kwargs):
        try:
            # Bind arguments to signature for validation
            bound_args = signature.bind(*args, **kwargs)
            bound_args.apply_defaults()

            # Call template with bound arguments
            return await tool_template(**bound_args.arguments)
        except TypeError as e:
            logger.error(f"Argument binding error for tool '{tool_name}': {e}")
            raise ValueError(f"Invalid arguments for tool '{tool_name}': {e}")
        except Exception as e:
            logger.error(f"Error in tool wrapper for '{tool_name}': {e}", exc_info=True)
            raise
    
    # Set function metadata
    tool_wrapper.__name__ = tool_name
    tool_wrapper.__signature__ = signature  # type: ignore

    # Build __annotations__ dict for Pydantic
    # This is critical for FastMCP's Tool.from_function() to work
    annotations = {}
    for param_def in param_defs:
        annotations[param_def["name"]] = param_def["type"]
    # Add return type annotation
    annotations["return"] = Dict
    tool_wrapper.__annotations__ = annotations

    # Build docstring
    if tool_description:
        docstring = tool_description
    else:
        docstring = f"Dynamically generated tool: {tool_name}"
    
    # Add parameter documentation
    if param_defs:
        docstring += "\n\nArgs:"
        for param_def in param_defs:
            param_name = param_def["name"]
            param_desc = param_def["description"] or "No description"
            required_marker = " (required)" if param_def["required"] else " (optional)"
            docstring += f"\n    {param_name}: {param_desc}{required_marker}"
    
    tool_wrapper.__doc__ = docstring
    
    logger.info(f"Created tool function '{tool_name}' with {len(param_defs)} parameters")
    
    return tool_wrapper


def create_execution_handler(auth_token: str, backend_handler: Callable) -> Callable:
    """
    Create an execution handler that binds the auth_token to the backend handler.
    
    This allows the dynamically generated tool functions to call a common
    backend handler while maintaining user context.
    
    Args:
        auth_token: User's authentication token
        backend_handler: The actual backend function that processes requests
        
    Returns:
        Async callable that wraps the backend handler with auth context
    """
    async def execution_handler(tool_name: str, **kwargs) -> Dict:
        """Execute tool with user authentication context."""
        logger.debug(f"Execution handler called for tool '{tool_name}' with token: {auth_token[:20]}...")
        
        # Call backend handler with auth context
        result = await backend_handler(
            auth_token=auth_token,
            tool_name=tool_name,
            **kwargs
        )
        
        return result
    
    return execution_handler

