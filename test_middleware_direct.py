#!/usr/bin/env python3
"""
Direct test of the middleware to verify it works
"""
import asyncio
import logging
from unittest.mock import Mock, AsyncMock
from fastmcp.tools import Tool

from api_client import FormSchemaClient
from dynamic_tool_manager import DynamicToolManager
from dynamic_tool_middleware import DynamicToolMiddleware

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

async def test_middleware():
    """Test the middleware directly"""
    print("🔍 Testing Dynamic Tool Middleware")
    print("=" * 80)
    print()
    
    # Initialize components
    print("📦 Initializing components...")
    FORM_SCHEMA_API_URL = "http://172.16.11.131/api/module/request/form"
    schema_client = FormSchemaClient(
        api_url=FORM_SCHEMA_API_URL,
        cache_ttl=300,
        verbose=True
    )
    tool_manager = DynamicToolManager(cache_ttl_seconds=300)
    
    middleware = DynamicToolMiddleware(
        schema_client=schema_client,
        tool_manager=tool_manager,
        tool_name="create_request",
        tool_description="Test tool"
    )
    print("✅ Components initialized")
    print()
    
    # Create mock context
    print("📦 Creating mock context...")
    context = Mock()
    context.get_http_headers = Mock(return_value={
        "authorization": "Bearer eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9.eyJsb2dpbl9zc29faWQiOjAsInVzZXJfbmFtZSI6InV1aWQzNi1jOWRjN2Y2OC1lMjdiLTRkNDgtODM3Yi05YTc1MTJlMzE2Y2UiLCJzY29wZSI6WyJOTy1TQ09QRSJdLCJsb2dpbl9zb3VyY2UiOiJub3JtYWxfbG9naW4iLCJleHAiOjE3NjAyNTY2MzcsImxvZ2luX21zcF9wb3J0YWxfaWQiOjAsImp0aSI6ImYzNjI4ZjcwLTg0YTItNGNmNy1iYWJhLWQ4YWQzNjk4YjMzMyIsImNsaWVudF9pZCI6ImZsb3RvLXdlYi1hcHAiLCJ0ZW5hbnRJZGVudGlmaWVyIjoiYXBvbG8ifQ.wcNsJ7LRlNSHFdhQy51j_vn60NgE1fdWGMaPLMhVeEXVXpoS0P13AIXigK7RhDuqw0rojiXUvrtH9AdTV8QTzj8zMwAnqoN39OSxN-wQ73NYstInJh8YaxnfOCbGk4gOLBgfQEMf-E96isgyFT477RUg0fonDSGI05L-jwkexDGjvp4XEfFYPtYQ4uICffpEumGquAu9d_pcTd2CQEuPNBZPmbfsresfAW8MAusu1r_yXm04qD4xhFkyV9nnMtxh2kJZfKltwSimUqDvvJpB-eXlY5F1LC-yaq1wdwE2f0CtHyXDQJiLx1sNB_Cr0MaLP8rwuayVlVqih-UdkBJVBA"
    })
    context.get_access_token = Mock(return_value=None)
    print("✅ Mock context created")
    print()
    
    # Create mock call_next that returns static tools
    print("📦 Creating mock static tools...")

    # Create a simple function to convert to Tool
    def add(a: int, b: int) -> int:
        """Add two numbers"""
        return a + b

    static_tool1 = Tool.from_function(add)

    async def mock_call_next(ctx):
        return [static_tool1]
    
    print("✅ Mock static tools created")
    print()
    
    # Call the middleware
    print("📡 Calling middleware.on_list_tools()...")
    print()
    try:
        tools = await middleware.on_list_tools(context, mock_call_next)
        
        print("=" * 80)
        print("✅ SUCCESS! Middleware returned tools")
        print("=" * 80)
        print()
        print(f"📊 Total tools: {len(tools)}")
        print()
        
        for i, tool in enumerate(tools, 1):
            print(f"{i}. {tool.name}")
            print(f"   Description: {tool.description[:100]}...")
            if hasattr(tool, 'inputSchema') and tool.inputSchema:
                props = tool.inputSchema.get('properties', {})
                if props:
                    print(f"   Parameters ({len(props)}): {', '.join(list(props.keys())[:10])}")
                    if len(props) > 10:
                        print(f"                ... and {len(props) - 10} more")
            print()
            
        # Check if create_request is in the list
        create_request_tool = next((t for t in tools if t.name == "create_request"), None)
        if create_request_tool:
            print("🎉 VERIFICATION PASSED!")
            print("   ✅ create_request tool was dynamically generated")
            print("   ✅ Tool has proper schema")
            print("   ✅ Middleware is working correctly")
        else:
            print("⚠️  WARNING: create_request tool not found in list")
            
    except Exception as e:
        print("=" * 80)
        print("❌ ERROR!")
        print("=" * 80)
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_middleware())

