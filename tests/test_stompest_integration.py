#!/usr/bin/env python3
"""
Test stompest integration with WebSocket client.

This test verifies that the stompest STOMP parser correctly handles
various STOMP frame types from the server.
"""

import json
from stompest.protocol import StompParser


def test_connected_frame():
    """Test parsing CONNECTED frame."""
    print("=" * 60)
    print("TEST 1: CONNECTED Frame")
    print("=" * 60)
    
    message = b'CONNECTED\nversion:1.2\nheart-beat:10000,10000\n\n\x00'
    
    parser = StompParser('1.2')
    parser.add(message)
    
    if parser.canRead():
        frame = parser.get()
        print(f"✅ Command: {frame.command}")
        print(f"✅ Headers: {frame.headers}")
        print(f"✅ Body: {frame.body}")
        assert frame.command == 'CONNECTED'
        assert frame.headers['version'] == '1.2'
        print("✅ CONNECTED frame test PASSED!\n")
    else:
        print("❌ FAILED: No frame available\n")
        return False
    
    return True


def test_message_frame_without_content_length():
    """Test parsing MESSAGE frame without content-length header."""
    print("=" * 60)
    print("TEST 2: MESSAGE Frame (without content-length)")
    print("=" * 60)
    
    message = b'MESSAGE\ndestination:/users/execute-task/python-service\ncontent-type:application/json\n\n{"id":265}\x00'
    
    parser = StompParser('1.2')
    parser.add(message)
    
    if parser.canRead():
        frame = parser.get()
        print(f"✅ Command: {frame.command}")
        print(f"✅ Headers: {frame.headers}")
        print(f"✅ Body: {frame.body}")
        
        # Parse JSON
        payload = json.loads(frame.body.decode('utf-8'))
        print(f"✅ Parsed JSON: {payload}")
        
        assert frame.command == 'MESSAGE'
        assert payload['id'] == 265
        print("✅ MESSAGE frame test PASSED!\n")
    else:
        print("❌ FAILED: No frame available\n")
        return False
    
    return True


def test_message_frame_with_incorrect_content_length():
    """Test parsing MESSAGE frame with incorrect content-length (server bug)."""
    print("=" * 60)
    print("TEST 3: MESSAGE Frame (with INCORRECT content-length)")
    print("=" * 60)
    
    # Original message from server with incorrect content-length (9 instead of 10)
    original_message = '''MESSAGE
destination:/users/execute-task/python-service
content-type:application/json
subscription:sub-0
message-id:1c2305cb-6c89-762a-a06b-3bc1f4f16323-3
content-length:9

{"id":265}\x00'''
    
    print(f"Original message (with content-length:9):")
    print(repr(original_message))
    print()
    
    # Remove content-length header (workaround for server bug)
    import re
    message_fixed = re.sub(r'content-length:[^\n]*\n', '', original_message, flags=re.IGNORECASE)
    
    print(f"Fixed message (content-length removed):")
    print(repr(message_fixed))
    print()
    
    parser = StompParser('1.2')
    parser.add(message_fixed.encode('utf-8'))
    
    if parser.canRead():
        frame = parser.get()
        print(f"✅ Command: {frame.command}")
        print(f"✅ Headers: {frame.headers}")
        print(f"✅ Body: {frame.body}")
        
        # Parse JSON
        payload = json.loads(frame.body.decode('utf-8'))
        print(f"✅ Parsed JSON: {payload}")
        
        assert frame.command == 'MESSAGE'
        assert payload['id'] == 265
        print("✅ MESSAGE frame with incorrect content-length test PASSED!\n")
    else:
        print("❌ FAILED: No frame available\n")
        return False
    
    return True


def test_error_frame():
    """Test parsing ERROR frame."""
    print("=" * 60)
    print("TEST 4: ERROR Frame")
    print("=" * 60)
    
    message = b'ERROR\nmessage:Invalid command\n\nSomething went wrong\x00'
    
    parser = StompParser('1.2')
    parser.add(message)
    
    if parser.canRead():
        frame = parser.get()
        print(f"✅ Command: {frame.command}")
        print(f"✅ Headers: {frame.headers}")
        print(f"✅ Body: {frame.body.decode('utf-8')}")
        
        assert frame.command == 'ERROR'
        assert frame.headers['message'] == 'Invalid command'
        print("✅ ERROR frame test PASSED!\n")
    else:
        print("❌ FAILED: No frame available\n")
        return False
    
    return True


def test_multiple_frames():
    """Test parsing multiple frames in sequence."""
    print("=" * 60)
    print("TEST 5: Multiple Frames in Sequence")
    print("=" * 60)
    
    parser = StompParser('1.2')
    
    # Add CONNECTED frame
    parser.add(b'CONNECTED\nversion:1.2\n\n\x00')
    
    # Add MESSAGE frame
    parser.add(b'MESSAGE\ndestination:/test\n\n{"id":1}\x00')
    
    # Add another MESSAGE frame
    parser.add(b'MESSAGE\ndestination:/test\n\n{"id":2}\x00')
    
    frames = []
    while parser.canRead():
        frame = parser.get()
        frames.append(frame)
        print(f"✅ Parsed frame: {frame.command}")
    
    assert len(frames) == 3
    assert frames[0].command == 'CONNECTED'
    assert frames[1].command == 'MESSAGE'
    assert frames[2].command == 'MESSAGE'
    
    payload1 = json.loads(frames[1].body.decode('utf-8'))
    payload2 = json.loads(frames[2].body.decode('utf-8'))
    
    assert payload1['id'] == 1
    assert payload2['id'] == 2
    
    print("✅ Multiple frames test PASSED!\n")
    return True


def main():
    """Run all tests."""
    print("\n" + "=" * 60)
    print("STOMPEST INTEGRATION TESTS")
    print("=" * 60 + "\n")
    
    tests = [
        test_connected_frame,
        test_message_frame_without_content_length,
        test_message_frame_with_incorrect_content_length,
        test_error_frame,
        test_multiple_frames,
    ]
    
    results = []
    for test in tests:
        try:
            result = test()
            results.append(result)
        except Exception as e:
            print(f"❌ Test failed with exception: {e}\n")
            results.append(False)
    
    # Summary
    print("=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)
    passed = sum(results)
    total = len(results)
    print(f"Passed: {passed}/{total}")
    
    if passed == total:
        print("✅ ALL TESTS PASSED!")
    else:
        print(f"❌ {total - passed} test(s) failed")
    
    return passed == total


if __name__ == '__main__':
    success = main()
    exit(0 if success else 1)

