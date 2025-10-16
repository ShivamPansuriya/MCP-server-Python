"""
Tests for user search functionality and API compatibility.
"""

import pytest
from unittest.mock import Mock, patch, AsyncMock
import asyncio

from user_search_handler import UserSearchHandler, get_search_handler
from search_users_tool import search_users
from search_users_tool_new import search_users as search_users_new


class TestUserSearchHandler:
    """Test cases for UserSearchHandler class."""
    
    @patch('elasticsearch_lib.create_entity_handler')
    def test_handler_initialization(self, mock_create_handler):
        """Test UserSearchHandler initialization."""
        # Mock the entity handler
        mock_handler = Mock()
        mock_entity = Mock()
        mock_entity.get_enabled_fields.return_value = [
            Mock(name="user_name", fuzziness="AUTO", boost=2.0),
            Mock(name="user_email", fuzziness=0, boost=3.0)
        ]
        mock_handler.entity = mock_entity
        mock_create_handler.return_value = mock_handler
        
        handler = UserSearchHandler(tenant_id="test_tenant")
        
        assert handler.tenant_id == "test_tenant"
        assert handler.user_handler == mock_handler
        assert len(handler.enabled_fields) == 2
        
        # Verify create_entity_handler was called correctly
        mock_create_handler.assert_called_once_with(
            entity_type="user",
            tenant_id="test_tenant"
        )
    
    @patch('elasticsearch_lib.create_entity_handler')
    def test_get_index_name(self, mock_create_handler):
        """Test index name generation."""
        mock_create_handler.return_value = Mock()
        handler = UserSearchHandler(tenant_id="test_tenant")
        
        index_name = handler._get_index_name()
        assert index_name == "test_tenant_user"
    
    @patch('elasticsearch_lib.create_entity_handler')
    async def test_search_users_by_query_success(self, mock_create_handler):
        """Test successful user search by query."""
        # Mock the entity handler and search results
        mock_handler = Mock()
        mock_entity = Mock()
        mock_entity.get_enabled_fields.return_value = []
        mock_handler.entity = mock_entity
        
        # Mock search results
        mock_result = Mock()
        mock_result.data = {
            "id": "123",
            "name": "John Doe",
            "email": "john.doe@example.com",
            "contact": "555-1234",
            "userLogonName": "jdoe",
            "contact2": "555-5678",
            "userType": "requester"
        }
        mock_result.score = 5.5
        mock_handler.search.return_value = [mock_result]
        
        mock_create_handler.return_value = mock_handler
        
        handler = UserSearchHandler(tenant_id="test_tenant")
        result = await handler.search_users_by_query("John", limit=5)
        
        # Verify result structure
        assert result["success"] is True
        assert result["query"] == "John"
        assert result["total_hits"] == 1
        assert result["returned_count"] == 1
        assert len(result["users"]) == 1
        
        # Verify user data
        user = result["users"][0]
        assert user["id"] == "123"
        assert user["name"] == "John Doe"
        assert user["email"] == "john.doe@example.com"
        assert user["userlogonname"] == "jdoe"
        assert user["score"] == 5.5
    
    @patch('elasticsearch_lib.create_entity_handler')
    async def test_search_users_by_query_empty_query(self, mock_create_handler):
        """Test search with empty query."""
        mock_create_handler.return_value = Mock()
        handler = UserSearchHandler(tenant_id="test_tenant")
        
        result = await handler.search_users_by_query("", limit=5)
        
        assert result["success"] is False
        assert "empty" in result["error"].lower()
        assert result["total_hits"] == 0
        assert result["returned_count"] == 0
        assert result["users"] == []
    
    @patch('elasticsearch_lib.create_entity_handler')
    async def test_search_users_by_query_limit_validation(self, mock_create_handler):
        """Test limit validation in search."""
        mock_handler = Mock()
        mock_entity = Mock()
        mock_entity.get_enabled_fields.return_value = []
        mock_handler.entity = mock_entity
        mock_handler.search.return_value = []
        mock_create_handler.return_value = mock_handler
        
        handler = UserSearchHandler(tenant_id="test_tenant")
        
        # Test with invalid limits
        result = await handler.search_users_by_query("test", limit=0)
        assert result["success"] is True  # Should be corrected to valid limit
        
        result = await handler.search_users_by_query("test", limit=15)
        assert result["success"] is True  # Should be corrected to valid limit
    
    @patch('elasticsearch_lib.create_entity_handler')
    async def test_search_users_by_query_exception_handling(self, mock_create_handler):
        """Test exception handling in search."""
        mock_handler = Mock()
        mock_entity = Mock()
        mock_entity.get_enabled_fields.return_value = []
        mock_handler.entity = mock_entity
        mock_handler.search.side_effect = Exception("Search failed")
        mock_create_handler.return_value = mock_handler
        
        handler = UserSearchHandler(tenant_id="test_tenant")
        result = await handler.search_users_by_query("test", limit=5)
        
        assert result["success"] is False
        assert "Search failed" in result["error"]
        assert result["total_hits"] == 0
        assert result["returned_count"] == 0
        assert result["users"] == []


class TestUserSearchTool:
    """Test cases for search_users tool function."""
    
    @patch('user_search_handler.get_search_handler')
    async def test_search_users_success(self, mock_get_handler):
        """Test successful search_users tool call."""
        # Mock handler and its response
        mock_handler = Mock()
        mock_handler.search_users_by_query = AsyncMock(return_value={
            "success": True,
            "query": "John",
            "total_hits": 1,
            "returned_count": 1,
            "users": [
                {
                    "id": "123",
                    "name": "John Doe",
                    "email": "john.doe@example.com",
                    "contact": "555-1234",
                    "userlogonname": "jdoe",
                    "contact2": "555-5678",
                    "usertype": "requester",
                    "score": 5.5
                }
            ]
        })
        mock_get_handler.return_value = mock_handler
        
        result = await search_users("John", limit=3)
        
        assert result["success"] is True
        assert result["query"] == "John"
        assert len(result["users"]) == 1
        assert result["users"][0]["name"] == "John Doe"
        
        # Verify handler was called correctly
        mock_handler.search_users_by_query.assert_called_once_with(
            query="John",
            limit=3
        )
    
    @patch('user_search_handler.get_search_handler')
    async def test_search_users_empty_query(self, mock_get_handler):
        """Test search_users with empty query."""
        mock_get_handler.return_value = Mock()
        
        result = await search_users("", limit=3)
        
        assert result["success"] is False
        assert "empty" in result["error"].lower()
        assert result["total_hits"] == 0
        assert result["returned_count"] == 0
        assert result["users"] == []
    
    @patch('user_search_handler.get_search_handler')
    async def test_search_users_limit_validation(self, mock_get_handler):
        """Test search_users limit validation."""
        mock_handler = Mock()
        mock_handler.search_users_by_query = AsyncMock(return_value={
            "success": True,
            "query": "test",
            "total_hits": 0,
            "returned_count": 0,
            "users": []
        })
        mock_get_handler.return_value = mock_handler
        
        # Test with invalid limits
        result = await search_users("test", limit=0)
        # Should be corrected to valid range
        mock_handler.search_users_by_query.assert_called_with(query="test", limit=1)
        
        result = await search_users("test", limit=15)
        # Should be corrected to valid range
        mock_handler.search_users_by_query.assert_called_with(query="test", limit=10)


class TestNewUserSearchTool:
    """Test cases for the new search_users implementation."""
    
    @patch('search_users_tool_new.get_search_handler')
    async def test_search_users_field_based(self, mock_get_handler):
        """Test field-based search_users function."""
        # Mock handler and its response
        mock_handler = Mock()
        mock_handler.search_users_by_fields = AsyncMock(return_value={
            "success": True,
            "field_values": {"user_name": "John", "user_email": "john@example.com"},
            "total_hits": 1,
            "returned_count": 1,
            "users": [
                {
                    "id": "123",
                    "name": "John Doe",
                    "email": "john@example.com",
                    "contact": "555-1234",
                    "userlogonname": "jdoe",
                    "contact2": "555-5678",
                    "usertype": "requester",
                    "score": 8.5
                }
            ]
        })
        mock_get_handler.return_value = mock_handler
        
        result = await search_users_new(
            name="John",
            email="john@example.com",
            limit=10
        )
        
        assert result["success"] is True
        assert len(result["users"]) == 1
        assert result["users"][0]["name"] == "John Doe"
        assert result["users"][0]["email"] == "john@example.com"
        
        # Verify handler was called with mapped fields
        mock_handler.search_users_by_fields.assert_called_once_with(
            limit=10,
            user_name="John",
            user_email="john@example.com"
        )
    
    @patch('search_users_tool_new.get_search_handler')
    async def test_search_users_with_min_score_filter(self, mock_get_handler):
        """Test search_users with minScore filtering."""
        # Mock handler response with multiple users
        mock_handler = Mock()
        mock_handler.search_users_by_fields = AsyncMock(return_value={
            "success": True,
            "field_values": {"user_name": "John"},
            "total_hits": 2,
            "returned_count": 2,
            "users": [
                {
                    "id": "123",
                    "name": "John Doe",
                    "email": "john.doe@example.com",
                    "score": 8.5
                },
                {
                    "id": "456",
                    "name": "John Smith",
                    "email": "john.smith@example.com",
                    "score": 3.2
                }
            ]
        })
        mock_get_handler.return_value = mock_handler
        
        result = await search_users_new(
            name="John",
            minScore=5.0,
            limit=10
        )
        
        assert result["success"] is True
        assert result["returned_count"] == 1  # Only one user above minScore
        assert len(result["users"]) == 1
        assert result["users"][0]["score"] == 8.5
        assert result["minScore"] == 5.0
    
    @patch('search_users_tool_new.get_search_handler')
    async def test_search_users_no_fields_provided(self, mock_get_handler):
        """Test search_users with no search fields provided."""
        mock_get_handler.return_value = Mock()
        
        result = await search_users_new(limit=10)
        
        assert result["success"] is False
        assert "at least one search field" in result["error"].lower()
        assert result["total_hits"] == 0
        assert result["returned_count"] == 0
        assert result["users"] == []


class TestSingletonHandler:
    """Test cases for singleton handler functionality."""
    
    @patch('user_search_handler.UserSearchHandler')
    def test_get_search_handler_singleton(self, mock_handler_class):
        """Test that get_search_handler returns singleton instance."""
        mock_instance = Mock()
        mock_handler_class.return_value = mock_instance
        
        # Clear any existing singleton
        import user_search_handler
        user_search_handler._search_handler = None
        
        # First call should create instance
        handler1 = get_search_handler(tenant_id="test1")
        assert handler1 == mock_instance
        mock_handler_class.assert_called_once_with(
            tenant_id="test1",
            es_host=None,
            config_path=None
        )
        
        # Second call should return same instance
        handler2 = get_search_handler(tenant_id="test2")  # Different params should be ignored
        assert handler2 == mock_instance
        assert handler1 is handler2
        
        # Handler class should only be called once
        assert mock_handler_class.call_count == 1


if __name__ == "__main__":
    pytest.main([__file__])
