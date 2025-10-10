#!/bin/bash

echo "🔍 Testing MCP Server with session management"
echo "=============================================="
echo ""

# Create a temporary file for cookies/session
COOKIE_FILE=$(mktemp)

echo "📡 Step 1: Initialize session and capture session ID"
INIT_RESPONSE=$(curl -s -X POST http://127.0.0.1:9092/mcp \
  -H "Content-Type: application/json" \
  -H "Accept: application/json, text/event-stream" \
  -H "Authorization: Bearer test-token" \
  -c "$COOKIE_FILE" \
  -d '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2024-11-05","capabilities":{},"clientInfo":{"name":"test","version":"1.0"}}}' \
  --no-buffer 2>&1)

echo "$INIT_RESPONSE" | grep -A 1 "event: message" | tail -1 | sed 's/^data: //' | jq '.'

echo ""
echo "============================================"
echo ""

# Extract session ID from response headers or cookies
echo "📡 Step 2: List tools using same session"
TOOLS_RESPONSE=$(curl -s -X POST http://127.0.0.1:9092/mcp \
  -H "Content-Type: application/json" \
  -H "Accept: application/json, text/event-stream" \
  -H "Authorization: Bearer test-token" \
  -b "$COOKIE_FILE" \
  -d '{"jsonrpc":"2.0","id":2,"method":"tools/list","params":{}}' \
  --no-buffer 2>&1)

echo "$TOOLS_RESPONSE" | grep -A 1 "event: message" | tail -1 | sed 's/^data: //' | jq '.'

# Cleanup
rm -f "$COOKIE_FILE"

echo ""
echo "✅ Test complete!"

