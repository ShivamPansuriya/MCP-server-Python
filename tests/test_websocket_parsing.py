#!/usr/bin/env python3
"""
Test script to verify WebSocket STOMP message parsing with null terminators.
"""

import json


def test_stomp_message_parsing():
    """Test the improved STOMP message parsing logic."""
    
    # Simulate the exact STOMP message format you received
    stomp_message = """MESSAGE
destination:/users/execute-task/python-service
content-type:application/json
subscription:sub-0
message-id:1c2305cb-6c89-762a-a06b-3bc1f4f16323-3
content-length:9

{"id":265}\x00"""
    
    print("=" * 80)
    print("Testing STOMP Message Parsing")
    print("=" * 80)
    print(f"\nFull STOMP message:")
    print(repr(stomp_message))
    print()
    
    # OLD METHOD (would fail)
    print("OLD METHOD (line-by-line iteration):")
    print("-" * 80)
    try:
        lines = stomp_message.split('\n')
        body_start = False
        for line in lines:
            if body_start and line.strip():
                print(f"  Attempting to parse line: {repr(line)}")
                payload = json.loads(line)  # This would fail with the \x00
                print(f"  ✅ SUCCESS: {payload}")
                break
            if line == '':
                body_start = True
    except json.JSONDecodeError as e:
        print(f"  ❌ FAILED: {e}")
        print(f"  Error: Extra data at position {e.pos}")
    
    print()
    
    # NEW METHOD (works correctly)
    print("NEW METHOD (direct body extraction):")
    print("-" * 80)
    try:
        # Split by double newline to separate headers from body
        parts = stomp_message.split('\n\n', 1)
        if len(parts) == 2:
            # Extract body and strip STOMP null terminator and whitespace
            body = parts[1].rstrip('\x00').strip()
            print(f"  Extracted body: {repr(body)}")
            payload = json.loads(body)
            print(f"  ✅ SUCCESS: Parsed payload: {payload}")
            print(f"  ✅ Payload type: {type(payload)}")
            print(f"  ✅ Payload keys: {list(payload.keys())}")
            print(f"  ✅ ID value: {payload.get('id')}")
    except json.JSONDecodeError as e:
        print(f"  ❌ FAILED: {e}")
    
    print()
    print("=" * 80)
    print("Test Complete!")
    print("=" * 80)


if __name__ == "__main__":
    test_stomp_message_parsing()

