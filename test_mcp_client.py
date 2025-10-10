#!/usr/bin/env python3
"""
Simple MCP client to test the server
"""
import asyncio
import json
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

async def test_with_stdio():
    """Test using stdio transport (simpler than HTTP)"""
    # This won't work for HTTP server, but let's try HTTP client
    pass

async def test_with_http():
    """Test using HTTP transport"""
    from mcp.client.sse import sse_client
    
    url = "http://127.0.0.1:9092/mcp"
    headers = {
        "Authorization": "Bearer test-token"
    }
    
    print("🔍 Testing MCP Server via SSE client")
    print(f"URL: {url}")
    print()
    
    try:
        async with sse_client(url, headers=headers) as (read, write):
            async with ClientSession(read, write) as session:
                # Initialize
                print("📡 Initializing session...")
                await session.initialize()
                print("✅ Session initialized")
                print()
                
                # List tools
                print("📡 Listing tools...")
                tools = await session.list_tools()
                print(f"✅ Found {len(tools.tools)} tools:")
                print()
                
                for tool in tools.tools:
                    print(f"  📦 {tool.name}")
                    print(f"     Description: {tool.description}")
                    if hasattr(tool, 'inputSchema') and tool.inputSchema:
                        props = tool.inputSchema.get('properties', {})
                        if props:
                            print(f"     Parameters: {list(props.keys())}")
                    print()
                    
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_with_http())

