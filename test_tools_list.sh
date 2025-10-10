#!/bin/bash

echo "🔍 Testing MCP Server - tools/list endpoint"
echo "============================================"
echo ""

# First, initialize
echo "📡 Step 1: Initialize session"
curl -X POST http://127.0.0.1:9092/mcp \
  -H "Content-Type: application/json" \
  -H "Accept: application/json, text/event-stream" \
  -H "Authorization: Bearer test-token" \
  -d '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2024-11-05","capabilities":{},"clientInfo":{"name":"test","version":"1.0"}}}' \
  --no-buffer 2>&1 | grep -A 1 "event: message" | tail -1 | sed 's/^data: //' | jq '.'

echo ""
echo "============================================"
echo ""

# Then list tools
echo "📡 Step 2: List tools"
curl -X POST http://127.0.0.1:9092/mcp \
  -H "Content-Type: application/json" \
  -H "Accept: application/json, text/event-stream" \
  -H "Authorization: Bearer test-token" \
  -d '{"jsonrpc":"2.0","id":2,"method":"tools/list","params":{}}' \
  --no-buffer 2>&1 | grep -A 1 "event: message" | tail -1 | sed 's/^data: //' | jq '.'

echo ""
echo "✅ Test complete!"

