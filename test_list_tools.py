#!/usr/bin/env python3
"""
Quick test script to verify list/tools endpoint works
"""
import asyncio
import httpx
import json

async def test_list_tools():
    """Test the list/tools endpoint"""
    # For FastMCP with HTTP transport, we need to:
    # 1. First initialize a session
    # 2. Then call tools/list

    base_url = "http://127.0.0.1:9092/mcp"

    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json, text/event-stream",
        "Authorization": "Bearer test-token"
    }

    # First, initialize the session
    init_payload = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "initialize",
        "params": {
            "protocolVersion": "2024-11-05",
            "capabilities": {},
            "clientInfo": {
                "name": "test-client",
                "version": "1.0.0"
            }
        }
    }

    tools_payload = {
        "jsonrpc": "2.0",
        "id": 2,
        "method": "tools/list",
        "params": {}
    }
    
    print("🔍 Testing MCP server...")
    print(f"Base URL: {base_url}")
    print(f"Headers: {headers}")
    print()

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            # Step 1: Initialize session
            print("📡 Step 1: Initializing session...")
            init_response = await client.post(base_url, json=init_payload, headers=headers)
            print(f"Status: {init_response.status_code}")

            if init_response.status_code == 200:
                init_data = init_response.json()
                print(f"✅ Session initialized")
                print(json.dumps(init_data, indent=2))
            else:
                print(f"❌ Init failed: {init_response.text}")
                return

            print("\n" + "="*80 + "\n")

            # Step 2: List tools
            print("📡 Step 2: Listing tools...")
            tools_response = await client.post(base_url, json=tools_payload, headers=headers)
            print(f"Status: {tools_response.status_code}")

            if tools_response.status_code == 200:
                data = tools_response.json()
                print("📦 Response Data:")
                print(json.dumps(data, indent=2))

                # Check if we have tools
                if "result" in data and "tools" in data["result"]:
                    tools = data["result"]["tools"]
                    print(f"\n✅ Found {len(tools)} tools:")
                    for tool in tools:
                        print(f"  - {tool.get('name')}: {tool.get('description', 'No description')[:80]}")
                        if tool.get('name') == 'create_request':
                            print(f"    📋 Parameters: {list(tool.get('inputSchema', {}).get('properties', {}).keys())}")
                else:
                    print("⚠️ No tools found in response")
            else:
                print(f"❌ Error: {tools_response.text}")
                
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_list_tools())

