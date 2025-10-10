# Test Scenarios for Dynamic MCP Tool Generation

This document defines comprehensive test scenarios to validate the dynamic, per-user MCP tool generation system.

## Test Environment Setup

### Prerequisites
- MCP server running on `http://127.0.0.1:9092`
- External API available at `http://172.16.11.131/api/module/request/form`
- Two test users with different permissions:
  - **User A**: Token `test-token-user-a` (has access to fields: subject, requester, description)
  - **User B**: Token `test-token-user-b` (has access to fields: subject, priority, category)

### Tools for Testing
- MCP client (e.g., `mcp-client` CLI or custom test script)
- `curl` for HTTP requests
- Logging enabled at INFO level

---

## Test Scenarios

### TC1: User A Requests Tools → Receives Tools Based on Their Schema

**Objective:** Verify that User A receives a `create_request` tool with fields specific to their permissions.

**Steps:**
1. Start the MCP server
2. Send `list/tools` request with Authorization header: `Bearer test-token-user-a`
3. Inspect the returned tool list

**Expected Result:**
- Response includes static tools: `add`, `echo`, `multiply`
- Response includes dynamic tool: `create_request`
- `create_request` tool schema includes parameters: `subject`, `requester`, `description`
- `create_request` tool schema does NOT include: `priority`, `category`

**Verification:**
```bash
# Using curl to test
curl -X POST http://127.0.0.1:9092/mcp/v1/tools/list \
  -H "Authorization: Bearer test-token-user-a" \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc": "2.0", "id": 1, "method": "tools/list"}'
```

**Success Criteria:** ✅ Tool list contains `create_request` with User A's specific fields

---

### TC2: User B Requests Tools → Receives Different Tools Than User A

**Objective:** Verify that User B receives a `create_request` tool with different fields than User A.

**Steps:**
1. Send `list/tools` request with Authorization header: `Bearer test-token-user-b`
2. Compare the returned tool schema with User A's schema

**Expected Result:**
- Response includes static tools: `add`, `echo`, `multiply`
- Response includes dynamic tool: `create_request`
- `create_request` tool schema includes parameters: `subject`, `priority`, `category`
- `create_request` tool schema does NOT include: `requester`, `description`

**Verification:**
```bash
curl -X POST http://127.0.0.1:9092/mcp/v1/tools/list \
  -H "Authorization: Bearer test-token-user-b" \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc": "2.0", "id": 1, "method": "tools/list"}'
```

**Success Criteria:** ✅ User B's `create_request` tool has different parameters than User A's

---

### TC3: Same User Requests Tools Twice → Receives Cached Tools (Fast Response)

**Objective:** Verify that cached tools are reused for subsequent requests within the TTL period.

**Steps:**
1. Send first `list/tools` request with Authorization header: `Bearer test-token-user-a`
2. Note the response time
3. Immediately send second `list/tools` request with same token
4. Note the response time
5. Check server logs for cache hit messages

**Expected Result:**
- First request: Logs show "Generating new tools for user"
- Second request: Logs show "Using cached tools for user"
- Second request is faster than first request
- Both requests return identical tool schemas

**Verification:**
Check server logs for:
```
INFO - Generating new tools for user: test-token-user-a...
INFO - Using cached tools for user: test-token-user-a...
```

**Success Criteria:** ✅ Second request uses cached tools and is faster

---

### TC4: User Executes Dynamic Tool → Tool Executes Successfully with Provided Args

**Objective:** Verify that the dynamically generated `create_request` tool can be executed with valid arguments.

**Steps:**
1. Send `tools/call` request to execute `create_request` with User A's token
2. Provide valid arguments: `{"subject": "Test Request", "requester": "John Doe", "description": "Test description"}`
3. Inspect the response

**Expected Result:**
- Tool executes successfully
- Response includes:
  - `id`: UUID
  - `timestamp`: ISO format timestamp
  - `status`: "pending"
  - `data`: Contains all provided arguments

**Verification:**
```bash
curl -X POST http://127.0.0.1:9092/mcp/v1/tools/call \
  -H "Authorization: Bearer test-token-user-a" \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "id": 1,
    "method": "tools/call",
    "params": {
      "name": "create_request",
      "arguments": {
        "subject": "Test Request",
        "requester": "John Doe",
        "description": "Test description"
      }
    }
  }'
```

**Success Criteria:** ✅ Tool executes and returns structured response with all provided data

---

### TC5: API Returns Error → System Returns Empty/Fallback Tools Gracefully

**Objective:** Verify graceful degradation when the external API is unavailable.

**Steps:**
1. Stop the external API or use an invalid API URL
2. Send `list/tools` request with valid token
3. Inspect the response and server logs

**Expected Result:**
- Server logs show error: "Error generating dynamic tools"
- Server logs show: "Falling back to static tools only due to error"
- Response includes only static tools: `add`, `echo`, `multiply`
- Response does NOT include `create_request` tool
- No server crash or unhandled exceptions

**Verification:**
Check server logs for graceful error handling and fallback behavior.

**Success Criteria:** ✅ System degrades gracefully, returns static tools only

---

### TC6: Invalid AuthToken → System Handles Gracefully

**Objective:** Verify that requests without authentication are handled properly.

**Steps:**
1. Send `list/tools` request without Authorization header
2. Send `list/tools` request with invalid token format
3. Inspect responses

**Expected Result:**
- Server logs show: "No auth token found - returning only static tools"
- Response includes only static tools: `add`, `echo`, `multiply`
- No server crash or errors

**Verification:**
```bash
# No auth header
curl -X POST http://127.0.0.1:9092/mcp/v1/tools/list \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc": "2.0", "id": 1, "method": "tools/list"}'

# Invalid format
curl -X POST http://127.0.0.1:9092/mcp/v1/tools/list \
  -H "Authorization: InvalidFormat" \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc": "2.0", "id": 1, "method": "tools/list"}'
```

**Success Criteria:** ✅ System handles missing/invalid tokens gracefully, returns static tools

---

### TC7: Schema with Required Fields → Tool Validation Enforces Requirements

**Objective:** Verify that required fields are enforced during tool execution.

**Steps:**
1. Assume User A's schema has `subject` as required field
2. Send `tools/call` request without the `subject` parameter
3. Inspect the error response

**Expected Result:**
- Tool execution fails with validation error
- Error message indicates missing required parameter: `subject`
- Response includes clear error information

**Verification:**
```bash
curl -X POST http://127.0.0.1:9092/mcp/v1/tools/call \
  -H "Authorization: Bearer test-token-user-a" \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "id": 1,
    "method": "tools/call",
    "params": {
      "name": "create_request",
      "arguments": {
        "requester": "John Doe"
      }
    }
  }'
```

**Success Criteria:** ✅ Validation error is raised for missing required field

---

### TC8: Schema with Enum Fields → Tool Validation Enforces Enum Values

**Objective:** Verify that enum constraints are enforced during tool execution.

**Steps:**
1. Assume User B's schema has `priority` field with enum: ["low", "medium", "high"]
2. Send `tools/call` request with invalid enum value: `priority: "critical"`
3. Inspect the error response

**Expected Result:**
- Tool execution fails with validation error
- Error message indicates invalid enum value
- Response includes clear error information

**Verification:**
```bash
curl -X POST http://127.0.0.1:9092/mcp/v1/tools/call \
  -H "Authorization: Bearer test-token-user-b" \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "id": 1,
    "method": "tools/call",
    "params": {
      "name": "create_request",
      "arguments": {
        "subject": "Test",
        "priority": "critical"
      }
    }
  }'
```

**Success Criteria:** ✅ Validation error is raised for invalid enum value

---

## Test Execution Checklist

- [ ] TC1: User A receives correct tools
- [ ] TC2: User B receives different tools
- [ ] TC3: Caching works correctly
- [ ] TC4: Tool execution succeeds
- [ ] TC5: API errors handled gracefully
- [ ] TC6: Invalid tokens handled gracefully
- [ ] TC7: Required fields enforced
- [ ] TC8: Enum values enforced

## Notes

- All tests should be executed with the server running in verbose mode for detailed logging
- Check server logs after each test to verify expected behavior
- Cache TTL is 5 minutes - wait for cache expiration to test cache invalidation
- For production testing, use real API endpoints and authentication tokens

