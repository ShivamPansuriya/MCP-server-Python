"""
Pytest configuration and fixtures for elasticsearch_lib tests.
"""

import pytest
import sys
import os
from unittest.mock import Mock, patch

# Add the parent directory to the Python path so we can import the modules
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


@pytest.fixture
def mock_elasticsearch_client():
    """Mock Elasticsearch client for testing."""
    mock_client = Mock()
    mock_client.search.return_value = {
        "hits": {
            "hits": [],
            "total": {"value": 0}
        }
    }
    return mock_client


@pytest.fixture
def mock_client_manager():
    """Mock ElasticsearchClientManager for testing."""
    with patch('elasticsearch_lib.client.ElasticsearchClientManager') as mock:
        mock_instance = Mock()
        mock_instance.get_client.return_value = Mock()
        mock.return_value = mock_instance
        yield mock


@pytest.fixture
def sample_user_data():
    """Sample user data for testing."""
    return {
        "user_name": "John Doe",
        "user_email": "john.doe@example.com",
        "user_userlogonname": "jdoe",
        "user_contact": "555-1234",
        "user_contact2": "555-5678",
        "user_usertype": "requester",
        "dbid": "123"
    }


@pytest.fixture
def sample_elasticsearch_response():
    """Sample Elasticsearch response for testing."""
    return {
        "hits": {
            "hits": [
                {
                    "_source": {
                        "user_name": "John Doe",
                        "user_email": "john.doe@example.com",
                        "user_userlogonname": "jdoe",
                        "user_contact": "555-1234",
                        "user_contact2": "555-5678",
                        "user_usertype": "requester",
                        "dbid": "123"
                    },
                    "_score": 5.5
                },
                {
                    "_source": {
                        "user_name": "Jane Smith",
                        "user_email": "jane.smith@example.com",
                        "user_userlogonname": "jsmith",
                        "user_contact": "555-9876",
                        "user_contact2": "555-6543",
                        "user_usertype": "technician",
                        "dbid": "456"
                    },
                    "_score": 4.2
                }
            ],
            "total": {"value": 2}
        }
    }


@pytest.fixture(autouse=True)
def reset_singletons():
    """Reset singleton instances before each test."""
    # Note: The new elasticsearch_search_lib doesn't use singletons in the same way
    # This fixture is kept for compatibility but doesn't need to do anything
    yield


@pytest.fixture
def mock_entity_handler():
    """Mock entity handler for testing."""
    mock_handler = Mock()
    mock_entity = Mock()
    mock_entity.get_enabled_fields.return_value = [
        Mock(name="name", fuzziness="AUTO", boost=2.0),
        Mock(name="dbid", fuzziness=0, boost=1.0)
    ]
    mock_handler.entity = mock_entity
    mock_handler.search.return_value = []
    mock_handler.search_by_fields.return_value = []
    mock_handler.search_by_email.return_value = []
    return mock_handler
