"""
Tests for handler classes and their search functionality.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock

from elasticsearch_lib.handlers.simple import SimpleEntityHandler, ImpactHandler, UrgencyHandler, PriorityHandler
from elasticsearch_lib.handlers.model_based import ModelBasedEntityHandler, StatusHandler, CategoryHandler, SourceHandler
from elasticsearch_lib.handlers.hierarchical import HierarchicalEntityHandler, LocationHandler, DepartmentHandler
from elasticsearch_lib.handlers.complex import ComplexEntityHandler, UserGroupHandler, UserHandler, VendorHandler
from elasticsearch_lib.base.handler import SearchResult
from elasticsearch_lib.enums import EntityType


class TestBaseHandlerFunctionality:
    """Test cases for base handler functionality."""
    
    @patch('elasticsearch_lib.client.ElasticsearchClientManager')
    def test_handler_initialization(self, mock_client_manager):
        """Test handler initialization."""
        handler = ImpactHandler("test_tenant")
        
        assert handler.tenant_id == "test_tenant"
        assert hasattr(handler, 'entity')
        assert hasattr(handler, 'query_builder')
        assert hasattr(handler, 'client_manager')
    
    def test_get_index_name(self):
        """Test index name generation."""
        handler = ImpactHandler("test_tenant")
        index_name = handler.get_index_name()
        assert index_name == "test_tenant_impact"
    
    @patch('elasticsearch_lib.client.ElasticsearchClientManager')
    def test_process_search_response(self, mock_client_manager):
        """Test processing of search response."""
        handler = ImpactHandler("test_tenant")
        
        # Mock Elasticsearch response
        mock_response = {
            "hits": {
                "hits": [
                    {
                        "_source": {"name": "High", "dbid": "123"},
                        "_score": 5.5
                    },
                    {
                        "_source": {"name": "Medium", "dbid": "456"},
                        "_score": 3.2
                    }
                ]
            }
        }
        
        results = handler.process_search_response(mock_response)
        
        assert len(results) == 2
        assert isinstance(results[0], SearchResult)
        assert results[0].score == 5.5
        assert results[0].data["name"] == "High"
        assert results[1].score == 3.2
        assert results[1].data["name"] == "Medium"


class TestSimpleEntityHandlers:
    """Test cases for simple entity handlers."""
    
    @patch('elasticsearch_lib.client.ElasticsearchClientManager')
    def test_impact_handler(self, mock_client_manager):
        """Test ImpactHandler functionality."""
        handler = ImpactHandler("test_tenant")
        assert handler.entity.get_entity_type() == EntityType.IMPACT.value
    
    @patch('elasticsearch_lib.client.ElasticsearchClientManager')
    def test_urgency_handler(self, mock_client_manager):
        """Test UrgencyHandler functionality."""
        handler = UrgencyHandler("test_tenant")
        assert handler.entity.get_entity_type() == EntityType.URGENCY.value
    
    @patch('elasticsearch_lib.client.ElasticsearchClientManager')
    def test_priority_handler(self, mock_client_manager):
        """Test PriorityHandler functionality."""
        handler = PriorityHandler("test_tenant")
        assert handler.entity.get_entity_type() == EntityType.PRIORITY.value
    
    @patch('elasticsearch_lib.client.ElasticsearchClientManager')
    def test_simple_handler_search_by_name(self, mock_client_manager):
        """Test search by name functionality."""
        # Mock the client and response
        mock_client = Mock()
        mock_client_manager.return_value.get_client.return_value = mock_client
        mock_client.search.return_value = {
            "hits": {
                "hits": [
                    {"_source": {"name": "High Impact", "dbid": "123"}, "_score": 5.0}
                ]
            }
        }
        
        handler = ImpactHandler("test_tenant")
        results = handler.search_by_name("High", exact=False, limit=10)
        
        assert len(results) == 1
        assert results[0].data["name"] == "High Impact"
        mock_client.search.assert_called_once()


class TestModelBasedEntityHandlers:
    """Test cases for model-based entity handlers."""
    
    @patch('elasticsearch_lib.client.ElasticsearchClientManager')
    def test_status_handler(self, mock_client_manager):
        """Test StatusHandler functionality."""
        handler = StatusHandler("test_tenant")
        assert handler.entity.get_entity_type() == EntityType.STATUS.value
    
    @patch('elasticsearch_lib.client.ElasticsearchClientManager')
    def test_category_handler(self, mock_client_manager):
        """Test CategoryHandler functionality."""
        handler = CategoryHandler("test_tenant")
        assert handler.entity.get_entity_type() == EntityType.CATEGORY.value
    
    @patch('elasticsearch_lib.client.ElasticsearchClientManager')
    def test_source_handler(self, mock_client_manager):
        """Test SourceHandler functionality."""
        handler = SourceHandler("test_tenant")
        assert handler.entity.get_entity_type() == EntityType.SOURCE.value
    
    @patch('elasticsearch_lib.client.ElasticsearchClientManager')
    def test_model_based_search_with_model_filter(self, mock_client_manager):
        """Test search with model filtering."""
        # Mock the client and response
        mock_client = Mock()
        mock_client_manager.return_value.get_client.return_value = mock_client
        mock_client.search.return_value = {
            "hits": {
                "hits": [
                    {"_source": {"name": "Open", "model": "incident", "dbid": "123"}, "_score": 5.0}
                ]
            }
        }
        
        handler = StatusHandler("test_tenant")
        results = handler.search("Open", model="incident", limit=10)
        
        assert len(results) == 1
        assert results[0].data["name"] == "Open"
        mock_client.search.assert_called_once()


class TestHierarchicalEntityHandlers:
    """Test cases for hierarchical entity handlers."""
    
    @patch('elasticsearch_lib.client.ElasticsearchClientManager')
    def test_location_handler(self, mock_client_manager):
        """Test LocationHandler functionality."""
        handler = LocationHandler("test_tenant")
        assert handler.entity.get_entity_type() == EntityType.LOCATION.value
    
    @patch('elasticsearch_lib.client.ElasticsearchClientManager')
    def test_department_handler(self, mock_client_manager):
        """Test DepartmentHandler functionality."""
        handler = DepartmentHandler("test_tenant")
        assert handler.entity.get_entity_type() == EntityType.DEPARTMENT.value
    
    @patch('elasticsearch_lib.client.ElasticsearchClientManager')
    def test_hierarchical_search_by_hierarchy(self, mock_client_manager):
        """Test search by hierarchy functionality."""
        # Mock the client and response
        mock_client = Mock()
        mock_client_manager.return_value.get_client.return_value = mock_client
        mock_client.search.return_value = {
            "hits": {
                "hits": [
                    {"_source": {"name": "Building A", "hierarchy": "Campus > Building A", "dbid": "123"}, "_score": 5.0}
                ]
            }
        }
        
        handler = LocationHandler("test_tenant")
        results = handler.search_by_hierarchy("Building A", exact=False, limit=10)
        
        assert len(results) == 1
        assert results[0].data["name"] == "Building A"
        mock_client.search.assert_called_once()


class TestComplexEntityHandlers:
    """Test cases for complex entity handlers."""
    
    @patch('elasticsearch_lib.client.ElasticsearchClientManager')
    def test_user_group_handler(self, mock_client_manager):
        """Test UserGroupHandler functionality."""
        handler = UserGroupHandler("test_tenant")
        assert handler.entity.get_entity_type() == EntityType.USER_GROUP.value
    
    @patch('elasticsearch_lib.client.ElasticsearchClientManager')
    def test_user_handler(self, mock_client_manager):
        """Test UserHandler functionality."""
        handler = UserHandler("test_tenant")
        assert handler.entity.get_entity_type() == EntityType.USER.value
    
    @patch('elasticsearch_lib.client.ElasticsearchClientManager')
    def test_vendor_handler(self, mock_client_manager):
        """Test VendorHandler functionality."""
        handler = VendorHandler("test_tenant")
        assert handler.entity.get_entity_type() == EntityType.VENDOR.value
    
    @patch('elasticsearch_lib.client.ElasticsearchClientManager')
    def test_user_search_by_email(self, mock_client_manager):
        """Test user search by email functionality."""
        # Mock the client and response
        mock_client = Mock()
        mock_client_manager.return_value.get_client.return_value = mock_client
        mock_client.search.return_value = {
            "hits": {
                "hits": [
                    {
                        "_source": {
                            "user_name": "John Doe",
                            "user_email": "john.doe@example.com",
                            "user_userlogonname": "jdoe",
                            "user_contact": "123-456-7890",
                            "user_contact2": "098-765-4321",
                            "dbid": "123"
                        },
                        "_score": 5.0
                    }
                ]
            }
        }
        
        handler = UserHandler("test_tenant")
        results = handler.search_by_email("john.doe@example.com", exact=True, limit=10)
        
        assert len(results) == 1
        assert results[0].data["user_email"] == "john.doe@example.com"
        mock_client.search.assert_called_once()
    
    @patch('elasticsearch_lib.client.ElasticsearchClientManager')
    def test_user_search_by_logon_name(self, mock_client_manager):
        """Test user search by logon name functionality."""
        # Mock the client and response
        mock_client = Mock()
        mock_client_manager.return_value.get_client.return_value = mock_client
        mock_client.search.return_value = {
            "hits": {
                "hits": [
                    {
                        "_source": {
                            "user_name": "John Doe",
                            "user_email": "john.doe@example.com",
                            "user_userlogonname": "jdoe",
                            "dbid": "123"
                        },
                        "_score": 5.0
                    }
                ]
            }
        }
        
        handler = UserHandler("test_tenant")
        results = handler.search_by_logon_name("jdoe", exact=False, limit=10)
        
        assert len(results) == 1
        assert results[0].data["user_userlogonname"] == "jdoe"
        mock_client.search.assert_called_once()


class TestHandlerErrorHandling:
    """Test cases for handler error handling."""
    
    @patch('elasticsearch_lib.client.ElasticsearchClientManager')
    def test_search_with_elasticsearch_error(self, mock_client_manager):
        """Test handling of Elasticsearch errors."""
        # Mock client to raise an exception
        mock_client = Mock()
        mock_client_manager.return_value.get_client.return_value = mock_client
        mock_client.search.side_effect = Exception("Elasticsearch connection failed")
        
        handler = ImpactHandler("test_tenant")
        results = handler.search_by_name("High", exact=False, limit=10)
        
        # Should return empty list on error
        assert results == []
    
    @patch('elasticsearch_lib.client.ElasticsearchClientManager')
    def test_search_with_invalid_limit(self, mock_client_manager):
        """Test handling of invalid limit values."""
        mock_client = Mock()
        mock_client_manager.return_value.get_client.return_value = mock_client
        mock_client.search.return_value = {"hits": {"hits": []}}
        
        handler = ImpactHandler("test_tenant")
        
        # Test with negative limit
        results = handler.search_by_name("High", exact=False, limit=-5)
        assert results == []
        
        # Test with very large limit
        results = handler.search_by_name("High", exact=False, limit=1000)
        # Should be clamped to maximum allowed


class TestHandlerIntegration:
    """Integration tests for handlers."""

    @patch('elasticsearch_lib.client.ElasticsearchClientManager')
    def test_multi_field_search(self, mock_client_manager):
        """Test multi-field search functionality."""
        # Mock the client and response
        mock_client = Mock()
        mock_client_manager.return_value.get_client.return_value = mock_client
        mock_client.search.return_value = {
            "hits": {
                "hits": [
                    {
                        "_source": {
                            "user_name": "John Doe",
                            "user_email": "john.doe@example.com",
                            "dbid": "123"
                        },
                        "_score": 5.0
                    }
                ]
            }
        }

        handler = UserHandler("test_tenant")
        results = handler.search_by_fields(
            user_name="John",
            user_email="john.doe@example.com",
            limit=10
        )

        assert len(results) == 1
        assert results[0].data["user_name"] == "John Doe"
        mock_client.search.assert_called_once()

    @patch('elasticsearch_lib.client.ElasticsearchClientManager')
    def test_search_result_data_mapping(self, mock_client_manager):
        """Test that search results are properly mapped."""
        # Mock the client and response
        mock_client = Mock()
        mock_client_manager.return_value.get_client.return_value = mock_client
        mock_client.search.return_value = {
            "hits": {
                "hits": [
                    {
                        "_source": {
                            "user_name": "Jane Smith",
                            "user_email": "jane.smith@example.com",
                            "user_userlogonname": "jsmith",
                            "user_contact": "555-1234",
                            "user_contact2": "555-5678",
                            "dbid": "456"
                        },
                        "_score": 7.5
                    }
                ]
            }
        }

        handler = UserHandler("test_tenant")
        results = handler.search("Jane", limit=10)

        assert len(results) == 1
        result = results[0]

        # Verify SearchResult structure
        assert isinstance(result, SearchResult)
        assert result.score == 7.5
        assert isinstance(result.data, dict)

        # Verify data mapping
        expected_data = {
            "name": "Jane Smith",
            "email": "jane.smith@example.com",
            "userLogonName": "jsmith",
            "contact": "555-1234",
            "contact2": "555-5678",
            "id": "456"
        }

        for key, expected_value in expected_data.items():
            assert result.data.get(key) == expected_value


if __name__ == "__main__":
    pytest.main([__file__])
