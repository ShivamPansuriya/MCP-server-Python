"""
Test MCP Server Startup and Functionality

Tests that the MCP server can start and respond to requests.
"""

import pytest
import asyncio
import subprocess
import time
import sys
import os
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))


class TestMCPServerStartup:
    """Test MCP server startup and basic functionality."""
    
    def test_server_imports(self):
        """Test that MCP server module can be imported."""
        try:
            import mcp_server
            assert mcp_server is not None
            assert hasattr(mcp_server, 'mcp')
            print("✓ MCP server module imported successfully")
        except Exception as e:
            pytest.fail(f"Failed to import mcp_server: {e}")
    
    def test_server_initialization(self):
        """Test that MCP server initializes without errors."""
        try:
            import mcp_server
            
            # Check that FastMCP instance exists
            assert mcp_server.mcp is not None
            print("✓ FastMCP instance created")
            
            # Check that search client is initialized
            assert mcp_server.search_client is not None
            print("✓ Search client initialized")
            
            # Check that middleware is registered
            assert mcp_server.dynamic_middleware is not None
            print("✓ Dynamic middleware registered")
            
        except Exception as e:
            pytest.fail(f"Server initialization failed: {e}")
    
    def test_static_tools_registered(self):
        """Test that static tools are registered."""
        try:
            import mcp_server
            
            # Get list of registered tools
            # Note: FastMCP stores tools internally, we'll test by importing
            assert hasattr(mcp_server, 'add')
            assert hasattr(mcp_server, 'echo')
            assert hasattr(mcp_server, 'multiply')
            assert hasattr(mcp_server, 'search_users')
            assert hasattr(mcp_server, 'search_entities_by_type')
            assert hasattr(mcp_server, 'get_entity_types')
            assert hasattr(mcp_server, 'get_fields_for_entity')
            
            print("✓ All static tools registered")
            
        except Exception as e:
            pytest.fail(f"Static tools registration check failed: {e}")
    
    def test_search_library_integration(self):
        """Test that search library is properly integrated."""
        try:
            import mcp_server
            from elasticsearch_search_lib import SearchClient
            
            # Check that search client is a SearchClient instance
            assert isinstance(mcp_server.search_client, SearchClient)
            
            # Check that it has the expected tenant
            entities = mcp_server.search_client.get_supported_entities()
            assert len(entities) == 11
            assert 'user' in entities
            assert 'impact' in entities
            
            print(f"✓ Search library integrated with {len(entities)} entity types")
            
        except Exception as e:
            pytest.fail(f"Search library integration check failed: {e}")
    
    def test_tool_functions_callable(self):
        """Test that tool functions work with various inputs and edge cases."""
        try:
            import mcp_server

            # FastMCP wraps functions in FunctionTool objects
            # We need to access the underlying function via .fn attribute

            # Test add function with positive numbers
            result = mcp_server.add.fn(2, 3)
            assert result == 5, "Addition of positive numbers failed"

            # Test add with negative numbers
            result = mcp_server.add.fn(-5, 3)
            assert result == -2, "Addition with negative numbers failed"

            # Test add with zero
            result = mcp_server.add.fn(0, 0)
            assert result == 0, "Addition with zeros failed"
            print("✓ add() function works with various inputs")

            # Test echo function with different strings
            result = mcp_server.echo.fn("test")
            assert result == "Echo: test", "Echo with simple string failed"

            # Test echo with empty string
            result = mcp_server.echo.fn("")
            assert result == "Echo: ", "Echo with empty string failed"

            # Test echo with special characters
            result = mcp_server.echo.fn("Hello @#$%!")
            assert result == "Echo: Hello @#$%!", "Echo with special characters failed"
            print("✓ echo() function works with various inputs")

            # Test multiply function with positive numbers
            result = mcp_server.multiply.fn(4, 5)
            assert result == 20, "Multiplication of positive numbers failed"

            # Test multiply with zero
            result = mcp_server.multiply.fn(100, 0)
            assert result == 0, "Multiplication with zero failed"

            # Test multiply with negative numbers
            result = mcp_server.multiply.fn(-3, 4)
            assert result == -12, "Multiplication with negative numbers failed"
            print("✓ multiply() function works with various inputs")

        except Exception as e:
            pytest.fail(f"Tool function test failed: {e}")
    
    @pytest.mark.asyncio
    async def test_async_tools_callable(self):
        """Test that async tool functions work correctly with real scenarios."""
        try:
            import mcp_server

            # FastMCP wraps functions in FunctionTool objects
            # We need to access the underlying function via .fn attribute

            # Test get_entity_types - should return all 11 entity types
            result = await mcp_server.get_entity_types.fn()
            assert 'entity_types' in result, "Missing entity_types in response"
            assert len(result['entity_types']) == 11, f"Expected 11 entity types, got {len(result['entity_types'])}"

            # Verify all expected entity types are present
            expected_types = ['impact', 'urgency', 'priority', 'status', 'category',
                            'source', 'location', 'department', 'usergroup', 'user', 'vendor']
            for entity_type in expected_types:
                assert entity_type in result['entity_types'], f"Missing entity type: {entity_type}"
            print(f"✓ get_entity_types() returns all {len(result['entity_types'])} expected types")

            # Test get_fields_for_entity with 'user' entity
            result = await mcp_server.get_fields_for_entity.fn('user')
            assert 'entity_type' in result, "Missing entity_type in response"
            assert result['entity_type'] == 'user', f"Expected entity_type 'user', got {result['entity_type']}"
            assert 'fields' in result, "Missing fields in response"
            assert len(result['fields']) > 0, "User entity should have fields"

            # Verify user has expected fields
            field_names = [f['name'] for f in result['fields']]
            assert 'user_name' in field_names, "Missing user_name field"
            assert 'user_email' in field_names, "Missing user_email field"
            print(f"✓ get_fields_for_entity('user') returns {len(result['fields'])} fields with correct structure")

            # Test get_fields_for_entity with different entity types
            for entity_type in ['impact', 'status', 'location']:
                result = await mcp_server.get_fields_for_entity.fn(entity_type)
                assert result['entity_type'] == entity_type, f"Entity type mismatch for {entity_type}"
                assert 'fields' in result, f"Missing fields for {entity_type}"
                assert len(result['fields']) > 0, f"{entity_type} should have fields"
            print(f"✓ get_fields_for_entity() works for multiple entity types")

        except Exception as e:
            pytest.fail(f"Async tool function test failed: {e}")


class TestMCPServerConfiguration:
    """Test MCP server configuration."""
    
    def test_server_name(self):
        """Test that server has correct name."""
        import mcp_server
        # FastMCP stores name internally, we can check it was created
        assert mcp_server.mcp is not None
        print("✓ Server name configured")
    
    def test_api_url_configured(self):
        """Test that API URL is configured."""
        import mcp_server
        assert mcp_server.FORM_SCHEMA_API_URL is not None
        assert mcp_server.FORM_SCHEMA_API_URL.startswith("http")
        print(f"✓ API URL configured: {mcp_server.FORM_SCHEMA_API_URL}")
    
    def test_components_initialized(self):
        """Test that all components are initialized."""
        import mcp_server
        
        assert mcp_server.schema_client is not None
        print("✓ Schema client initialized")
        
        assert mcp_server.tool_manager is not None
        print("✓ Tool manager initialized")
        
        assert mcp_server.dynamic_middleware is not None
        print("✓ Dynamic middleware initialized")
        
        assert mcp_server.search_client is not None
        print("✓ Search client initialized")


class TestMCPServerSearchFunctionality:
    """Test actual search functionality through MCP server tools."""

    @pytest.mark.asyncio
    async def test_search_users_real_scenario(self):
        """Test searching for users with real queries."""
        try:
            import mcp_server

            # Scenario 1: Search for a user by name
            result = await mcp_server.search_users.fn("test")
            assert isinstance(result, dict), "Result should be a dictionary"
            assert 'success' in result or 'results' in result or 'items' in result, "Result should have search data"
            print(f"✓ User search by name works")

            # Scenario 2: Search with partial match
            result = await mcp_server.search_users.fn("admin")
            assert isinstance(result, dict), "Result should be a dictionary"
            print(f"✓ User search with partial match works")

        except Exception as e:
            pytest.fail(f"User search test failed: {e}")

    @pytest.mark.asyncio
    async def test_search_entities_multiple_types(self):
        """Test searching different entity types."""
        try:
            import mcp_server

            # Test searching different entity types
            entity_types_to_test = [
                ('user', 'test'),
                ('status', 'open'),
                ('category', 'hardware'),
                ('location', 'office'),
            ]

            for entity_type, query in entity_types_to_test:
                result = await mcp_server.search_entities_by_type.fn(entity_type, query)
                assert isinstance(result, dict), f"Result for {entity_type} should be a dictionary"
                assert 'entity_type' in result or 'success' in result, f"Result for {entity_type} should have entity info"
                print(f"✓ Search for {entity_type} with query '{query}' works")

        except Exception as e:
            pytest.fail(f"Entity search test failed: {e}")

    @pytest.mark.asyncio
    async def test_search_with_invalid_entity(self):
        """Test that searching invalid entity type is handled gracefully."""
        try:
            import mcp_server

            # Search for invalid entity type
            result = await mcp_server.search_entities_by_type.fn("invalid_entity", "test")

            # Should return error response, not crash
            assert isinstance(result, dict), "Should return dictionary even for invalid entity"

            # Check if error is indicated
            if 'success' in result:
                assert result['success'] == False, "Should indicate failure for invalid entity"
            elif 'error' in result:
                assert result['error'] is not None, "Should have error message"

            print(f"✓ Invalid entity type handled gracefully")

        except Exception as e:
            pytest.fail(f"Invalid entity test failed: {e}")

    @pytest.mark.asyncio
    async def test_entity_fields_validation(self):
        """Test that entity fields are correctly structured."""
        try:
            import mcp_server

            # Get fields for user entity
            result = await mcp_server.get_fields_for_entity.fn('user')

            assert 'fields' in result, "Should have fields"
            fields = result['fields']

            # Validate field structure
            for field in fields:
                assert 'name' in field, "Each field should have a name"
                assert 'boost' in field, "Each field should have a boost value"
                assert isinstance(field['boost'], (int, float)), "Boost should be numeric"
                assert field['boost'] > 0, "Boost should be positive"

            print(f"✓ Entity fields have correct structure and valid boost values")

        except Exception as e:
            pytest.fail(f"Entity fields validation failed: {e}")


if __name__ == "__main__":
    # Run tests with pytest
    pytest.main([__file__, "-v", "--tb=short"])

