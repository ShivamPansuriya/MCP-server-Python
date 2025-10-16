"""
Integration tests for the complete elasticsearch_lib system.
"""

import pytest
from unittest.mock import Mock, patch, AsyncMock

from elasticsearch_lib import create_entity_handler, get_elasticsearch_client
from elasticsearch_lib.factory import EntityFactory
from elasticsearch_lib.enums import EntityType


class TestLibraryIntegration:
    """Integration tests for the complete library."""
    
    def test_library_imports(self):
        """Test that all library components can be imported."""
        # Test main library imports
        from elasticsearch_lib import (
            BaseEntity, BaseQueryBuilder, BaseHandler, BaseConfig,
            ElasticsearchClientManager, EntityFactory, EntityRegistry,
            ConfigurationManager, create_entity_handler, get_elasticsearch_client
        )
        
        # Test entity imports
        from elasticsearch_lib.entities import (
            SimpleEntity, ImpactEntity, UrgencyEntity, PriorityEntity,
            ModelBasedEntity, StatusEntity, CategoryEntity, SourceEntity,
            HierarchicalEntity, LocationEntity, DepartmentEntity,
            ComplexEntity, UserGroupEntity, UserEntity, VendorEntity
        )
        
        # Test handler imports
        from elasticsearch_lib.handlers import (
            SimpleEntityHandler, ImpactHandler, UrgencyHandler, PriorityHandler,
            ModelBasedEntityHandler, StatusHandler, CategoryHandler, SourceHandler,
            HierarchicalEntityHandler, LocationHandler, DepartmentHandler,
            ComplexEntityHandler, UserGroupHandler, UserHandler, VendorHandler
        )
        
        # Test enum imports
        from elasticsearch_lib.enums import EntityType, ModelType, UserType, SearchStrategy
        
        # If we get here, all imports succeeded
        assert True
    
    def test_entity_factory_registration(self):
        """Test that entity factory can register and create all entity types."""
        # Register default handlers
        EntityFactory.register_default_handlers()
        
        # Test that all entity types are registered
        expected_types = [
            EntityType.IMPACT.value,
            EntityType.URGENCY.value,
            EntityType.PRIORITY.value,
            EntityType.STATUS.value,
            EntityType.CATEGORY.value,
            EntityType.SOURCE.value,
            EntityType.LOCATION.value,
            EntityType.DEPARTMENT.value,
            EntityType.USER_GROUP.value,
            EntityType.USER.value,
            EntityType.VENDOR.value
        ]
        
        registered_types = EntityFactory.get_registry().list_entity_types()
        for entity_type in expected_types:
            assert entity_type in registered_types
    
    def test_create_all_entity_handlers(self):
        """Test creating handlers for all entity types."""
        EntityFactory.register_default_handlers()
        
        entity_types = [
            EntityType.IMPACT.value,
            EntityType.URGENCY.value,
            EntityType.PRIORITY.value,
            EntityType.STATUS.value,
            EntityType.CATEGORY.value,
            EntityType.SOURCE.value,
            EntityType.LOCATION.value,
            EntityType.DEPARTMENT.value,
            EntityType.USER_GROUP.value,
            EntityType.USER.value,
            EntityType.VENDOR.value
        ]
        
        for entity_type in entity_types:
            handler = create_entity_handler(entity_type, "test_tenant")
            assert handler is not None
            assert handler.tenant_id == "test_tenant"
            assert hasattr(handler, 'entity')
            assert hasattr(handler, 'query_builder')
    
    @patch('elasticsearch_lib.client.ElasticsearchClientManager')
    def test_elasticsearch_client_integration(self, mock_client_manager):
        """Test Elasticsearch client integration."""
        mock_client = Mock()
        mock_client_manager.return_value.get_client.return_value = mock_client
        
        # Test getting client
        client = get_elasticsearch_client()
        assert client is not None
        
        # Test that handlers can use the client
        handler = create_entity_handler(EntityType.USER.value, "test_tenant")
        assert handler.client_manager is not None


class TestUserSearchIntegration:
    """Integration tests for user search functionality."""
    
    @patch('elasticsearch_lib.create_entity_handler')
    async def test_user_search_handler_integration(self, mock_create_handler):
        """Test complete user search handler integration."""
        # Mock the entity handler
        mock_handler = Mock()
        mock_entity = Mock()
        mock_entity.get_enabled_fields.return_value = [
            Mock(name="user_name", fuzziness="AUTO", boost=2.0),
            Mock(name="user_email", fuzziness=0, boost=3.0)
        ]
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
        
        # Test the complete flow
        from user_search_handler import UserSearchHandler
        handler = UserSearchHandler(tenant_id="test_tenant")
        result = await handler.search_users_by_query("John", limit=5)
        
        # Verify the complete result structure
        assert result["success"] is True
        assert result["query"] == "John"
        assert result["total_hits"] == 1
        assert result["returned_count"] == 1
        assert len(result["users"]) == 1
        
        user = result["users"][0]
        assert user["id"] == "123"
        assert user["name"] == "John Doe"
        assert user["email"] == "john.doe@example.com"
        assert user["userlogonname"] == "jdoe"
        assert user["score"] == 5.5
    
    @patch('search_users_tool_new.get_search_handler')
    async def test_search_tool_integration(self, mock_get_handler):
        """Test search tool integration with new library."""
        # Mock handler response
        mock_handler = Mock()
        mock_handler.search_users_by_fields = AsyncMock(return_value={
            "success": True,
            "field_values": {"user_name": "John"},
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
                    "score": 8.5
                }
            ]
        })
        mock_get_handler.return_value = mock_handler
        
        # Test the new search function
        from search_users_tool_new import search_users
        result = await search_users(name="John", limit=10)
        
        assert result["success"] is True
        assert len(result["users"]) == 1
        assert result["users"][0]["name"] == "John Doe"
        
        # Verify the handler was called with correct parameters
        mock_handler.search_users_by_fields.assert_called_once_with(
            limit=10,
            user_name="John"
        )


class TestBackwardCompatibility:
    """Test backward compatibility with existing implementations."""
    
    @patch('user_search_handler.create_entity_handler')
    async def test_original_api_compatibility(self, mock_create_handler):
        """Test that the original API still works with new implementation."""
        # Mock the entity handler
        mock_handler = Mock()
        mock_entity = Mock()
        mock_entity.get_enabled_fields.return_value = []
        mock_handler.entity = mock_entity
        mock_handler.search.return_value = []
        mock_create_handler.return_value = mock_handler
        
        # Test original search_users_tool function
        from search_users_tool import search_users
        result = await search_users("test query", limit=3)
        
        # Should return the expected structure
        assert "success" in result
        assert "query" in result
        assert "total_hits" in result
        assert "returned_count" in result
        assert "users" in result
    
    @patch('user_search_handler.create_entity_handler')
    def test_singleton_handler_compatibility(self, mock_create_handler):
        """Test that singleton handler pattern still works."""
        mock_handler = Mock()
        mock_entity = Mock()
        mock_entity.get_enabled_fields.return_value = []
        mock_handler.entity = mock_entity
        mock_create_handler.return_value = mock_handler
        
        from user_search_handler import get_search_handler
        
        # First call
        handler1 = get_search_handler(tenant_id="test1")
        
        # Second call should return same instance
        handler2 = get_search_handler(tenant_id="test2")
        
        assert handler1 is handler2
        # create_entity_handler should only be called once
        assert mock_create_handler.call_count == 1


class TestErrorHandling:
    """Test error handling across the system."""
    
    def test_invalid_entity_type(self):
        """Test handling of invalid entity types."""
        EntityFactory.register_default_handlers()
        
        with pytest.raises(ValueError, match="Unknown entity type"):
            create_entity_handler("invalid_entity", "test_tenant")
    
    @patch('elasticsearch_lib.create_entity_handler')
    async def test_search_error_handling(self, mock_create_handler):
        """Test search error handling."""
        # Mock handler that raises an exception
        mock_handler = Mock()
        mock_entity = Mock()
        mock_entity.get_enabled_fields.return_value = []
        mock_handler.entity = mock_entity
        mock_handler.search.side_effect = Exception("Search failed")
        mock_create_handler.return_value = mock_handler
        
        from user_search_handler import UserSearchHandler
        handler = UserSearchHandler(tenant_id="test_tenant")
        result = await handler.search_users_by_query("test", limit=5)
        
        # Should return error response
        assert result["success"] is False
        assert "Search failed" in result["error"]
        assert result["users"] == []


class TestPerformanceConsiderations:
    """Test performance-related aspects."""
    
    def test_handler_creation_performance(self):
        """Test that handler creation is reasonably fast."""
        import time
        
        EntityFactory.register_default_handlers()
        
        start_time = time.time()
        
        # Create multiple handlers
        for i in range(10):
            handler = create_entity_handler(EntityType.USER.value, f"tenant_{i}")
            assert handler is not None
        
        end_time = time.time()
        
        # Should complete in reasonable time (less than 1 second for 10 handlers)
        assert (end_time - start_time) < 1.0
    
    def test_singleton_efficiency(self):
        """Test that singleton pattern is efficient."""
        import time
        
        from user_search_handler import get_search_handler
        
        # Clear singleton
        import user_search_handler
        user_search_handler._search_handler = None
        
        with patch('user_search_handler.create_entity_handler') as mock_create:
            mock_handler = Mock()
            mock_entity = Mock()
            mock_entity.get_enabled_fields.return_value = []
            mock_handler.entity = mock_entity
            mock_create.return_value = mock_handler
            
            start_time = time.time()
            
            # Multiple calls should be fast after first initialization
            for i in range(100):
                handler = get_search_handler()
                assert handler is not None
            
            end_time = time.time()
            
            # Should complete quickly (less than 0.1 seconds for 100 calls)
            assert (end_time - start_time) < 0.1
            
            # create_entity_handler should only be called once
            assert mock_create.call_count == 1


if __name__ == "__main__":
    pytest.main([__file__])
