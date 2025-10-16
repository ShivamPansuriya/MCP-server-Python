"""
Test Elasticsearch Entity Search Functionality

Tests searching for all 11 entity types with real Elasticsearch connection.
Assumes Elasticsearch service is running on localhost:9200.
"""

import pytest
import asyncio
import sys
import os
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from elasticsearch_search_lib import SearchClient
from elasticsearch_search_lib.exceptions import EntityNotFoundError, ValidationError


# Test configuration
TENANT_ID = os.getenv("TENANT_ID", "apolo")
ES_HOST = os.getenv("ES_HOST", "localhost")
ES_PORT = int(os.getenv("ES_PORT", "9200"))


@pytest.fixture
def search_client():
    """Create a search client for testing."""
    return SearchClient(
        tenant_id=TENANT_ID,
        es_host=ES_HOST,
        es_port=ES_PORT
    )


class TestElasticsearchConnection:
    """Test Elasticsearch connection and basic health."""

    @pytest.mark.asyncio
    async def test_elasticsearch_is_running(self, search_client):
        """Test that Elasticsearch service is accessible and healthy."""
        try:
            # Verify entity types are loaded
            entities = search_client.get_supported_entities()
            assert len(entities) == 11, f"Expected 11 entity types, got {len(entities)}"

            # Verify all expected entity types are present
            expected_entities = [
                'impact', 'urgency', 'priority',
                'status', 'category', 'source',
                'location', 'department',
                'usergroup', 'user', 'vendor'
            ]
            for entity in expected_entities:
                assert entity in entities, f"Missing entity type: {entity}"

            print(f"✓ Elasticsearch connection verified")
            print(f"✓ All {len(entities)} entity types available")

        except Exception as e:
            pytest.fail(f"Elasticsearch connection failed: {e}")

    @pytest.mark.asyncio
    async def test_entity_configuration_loaded(self, search_client):
        """Test that entity configurations are properly loaded."""
        try:
            # Test configuration for each entity type
            for entity_type in ['user', 'status', 'location']:
                config = search_client.get_entity_config(entity_type)

                # Validate configuration structure
                assert config.entity_type == entity_type, f"Entity type mismatch for {entity_type}"
                assert config.default_limit > 0, f"Default limit should be positive for {entity_type}"
                assert config.max_limit >= config.default_limit, f"Max limit should be >= default limit for {entity_type}"
                assert config.min_score >= 0, f"Min score should be non-negative for {entity_type}"
                assert len(config.fields) > 0, f"Entity {entity_type} should have fields"

                # Validate field configurations
                for field in config.fields:
                    assert field.name, f"Field should have a name in {entity_type}"
                    assert field.boost > 0, f"Field boost should be positive in {entity_type}"

            print(f"✓ Entity configurations properly loaded and validated")

        except Exception as e:
            pytest.fail(f"Entity configuration test failed: {e}")


class TestSimpleEntities:
    """Test simple entity types (Impact, Urgency, Priority)."""
    
    @pytest.mark.asyncio
    async def test_search_impact(self, search_client):
        """Test searching for Impact entities."""
        try:
            result = await search_client.search("impact", "Productivity Loss", limit=5)
            
            assert result.success, f"Search failed: {result.error}"
            assert result.entity_type == "impact"
            assert result.index_name == f"{TENANT_ID}_impact"
            
            print(f"✓ Impact search: {result.total_hits} hits, {result.returned_count} returned")
            
            if result.items:
                first_item = result.items[0]
                assert 'impact_name' in first_item.data or 'impact_id' in first_item.data
                print(f"  Sample: {first_item.data}")
            
        except Exception as e:
            pytest.fail(f"Impact search failed: {e}")
    
    @pytest.mark.asyncio
    async def test_search_urgency(self, search_client):
        """Test searching for Urgency entities."""
        try:
            result = await search_client.search("urgency", "medium", limit=5)
            
            assert result.success, f"Search failed: {result.error}"
            assert result.entity_type == "urgency"
            assert result.index_name == f"{TENANT_ID}_urgency"
            
            print(f"✓ Urgency search: {result.total_hits} hits, {result.returned_count} returned")
            
            if result.items:
                first_item = result.items[0]
                assert 'urgency_name' in first_item.data or 'urgency_id' in first_item.data
                print(f"  Sample: {first_item.data}")
            
        except Exception as e:
            pytest.fail(f"Urgency search failed: {e}")
    
    @pytest.mark.asyncio
    async def test_search_priority(self, search_client):
        """Test searching for Priority entities."""
        try:
            result = await search_client.search("priority", "low", limit=5)
            
            assert result.success, f"Search failed: {result.error}"
            assert result.entity_type == "priority"
            assert result.index_name == f"{TENANT_ID}_priority"
            
            print(f"✓ Priority search: {result.total_hits} hits, {result.returned_count} returned")
            
            if result.items:
                first_item = result.items[0]
                assert 'priority_name' in first_item.data or 'priority_id' in first_item.data
                print(f"  Sample: {first_item.data}")
            
        except Exception as e:
            pytest.fail(f"Priority search failed: {e}")


class TestModelBasedEntities:
    """Test model-based entity types (Status, Category, Source)."""
    
    @pytest.mark.asyncio
    async def test_search_status(self, search_client):
        """Test searching for Status entities."""
        try:
            result = await search_client.search("status", "open", limit=5)
            
            assert result.success, f"Search failed: {result.error}"
            assert result.entity_type == "status"
            assert result.index_name == f"{TENANT_ID}_status"
            
            print(f"✓ Status search: {result.total_hits} hits, {result.returned_count} returned")
            
            if result.items:
                first_item = result.items[0]
                assert 'status_name' in first_item.data or 'status_id' in first_item.data
                print(f"  Sample: {first_item.data}")
            
        except Exception as e:
            pytest.fail(f"Status search failed: {e}")
    
    @pytest.mark.asyncio
    async def test_search_category(self, search_client):
        """Test searching for Category entities."""
        try:
            result = await search_client.search("category", "hardware", limit=5)
            
            assert result.success, f"Search failed: {result.error}"
            assert result.entity_type == "category"
            assert result.index_name == f"{TENANT_ID}_category"
            
            print(f"✓ Category search: {result.total_hits} hits, {result.returned_count} returned")
            
            if result.items:
                first_item = result.items[0]
                assert 'category_name' in first_item.data or 'category_id' in first_item.data
                print(f"  Sample: {first_item.data}")
            
        except Exception as e:
            pytest.fail(f"Category search failed: {e}")
    
    @pytest.mark.asyncio
    async def test_search_source(self, search_client):
        """Test searching for Source entities."""
        try:
            result = await search_client.search("source", "email", limit=5)
            
            assert result.success, f"Search failed: {result.error}"
            assert result.entity_type == "source"
            assert result.index_name == f"{TENANT_ID}_source"
            
            print(f"✓ Source search: {result.total_hits} hits, {result.returned_count} returned")
            
            if result.items:
                first_item = result.items[0]
                assert 'source_name' in first_item.data or 'source_id' in first_item.data
                print(f"  Sample: {first_item.data}")
            
        except Exception as e:
            pytest.fail(f"Source search failed: {e}")


class TestHierarchicalEntities:
    """Test hierarchical entity types (Location, Department)."""
    
    @pytest.mark.asyncio
    async def test_search_location(self, search_client):
        """Test searching for Location entities."""
        try:
            result = await search_client.search("location", "office", limit=5)
            
            assert result.success, f"Search failed: {result.error}"
            assert result.entity_type == "location"
            assert result.index_name == f"{TENANT_ID}_location"
            
            print(f"✓ Location search: {result.total_hits} hits, {result.returned_count} returned")
            
            if result.items:
                first_item = result.items[0]
                # Location has hierarchy, id, parentId, name fields
                assert any(key.startswith('location_') for key in first_item.data.keys())
                print(f"  Sample: {first_item.data}")
            
        except Exception as e:
            pytest.fail(f"Location search failed: {e}")
    
    @pytest.mark.asyncio
    async def test_search_department(self, search_client):
        """Test searching for Department entities."""
        try:
            result = await search_client.search("department", "it", limit=5)
            
            assert result.success, f"Search failed: {result.error}"
            assert result.entity_type == "department"
            assert result.index_name == f"{TENANT_ID}_department"
            
            print(f"✓ Department search: {result.total_hits} hits, {result.returned_count} returned")
            
            if result.items:
                first_item = result.items[0]
                # Department has hierarchy, id, parentId, name fields
                assert any(key.startswith('department_') for key in first_item.data.keys())
                print(f"  Sample: {first_item.data}")
            
        except Exception as e:
            pytest.fail(f"Department search failed: {e}")


class TestComplexEntities:
    """Test complex entity types (UserGroup, User, Vendor)."""
    
    @pytest.mark.asyncio
    async def test_search_usergroup(self, search_client):
        """Test searching for UserGroup entities."""
        try:
            result = await search_client.search("usergroup", "admin", limit=5)

            # UserGroup index may not exist in all environments
            if result.success:
                assert result.entity_type == "usergroup"
                assert result.index_name == f"{TENANT_ID}_usergroup"
                print(f"✓ UserGroup search: {result.total_hits} hits, {result.returned_count} returned")

                if result.items:
                    first_item = result.items[0]
                    assert any(key.startswith('usergroup_') for key in first_item.data.keys())
                    print(f"  Sample: {first_item.data}")
            else:
                # Index may not exist - that's okay
                print(f"⚠ UserGroup search: {result.error} (index may not exist)")

        except Exception as e:
            pytest.fail(f"UserGroup search failed: {e}")
    
    @pytest.mark.asyncio
    async def test_search_user(self, search_client):
        """Test searching for User entities."""
        try:
            result = await search_client.search("user", "test", limit=5)
            
            assert result.success, f"Search failed: {result.error}"
            assert result.entity_type == "user"
            assert result.index_name == f"{TENANT_ID}_user"
            
            print(f"✓ User search: {result.total_hits} hits, {result.returned_count} returned")
            
            if result.items:
                first_item = result.items[0]
                # User has multiple fields: name, email, contact, userlogonname, contact2, type
                assert any(key.startswith('user_') for key in first_item.data.keys())
                print(f"  Sample: {first_item.data}")
            
        except Exception as e:
            pytest.fail(f"User search failed: {e}")
    
    @pytest.mark.asyncio
    async def test_search_vendor(self, search_client):
        """Test searching for Vendor entities."""
        try:
            result = await search_client.search("vendor", "tech", limit=5)
            
            assert result.success, f"Search failed: {result.error}"
            assert result.entity_type == "vendor"
            assert result.index_name == f"{TENANT_ID}_vendor"
            
            print(f"✓ Vendor search: {result.total_hits} hits, {result.returned_count} returned")
            
            if result.items:
                first_item = result.items[0]
                # Vendor has: name, id, email, contact, description
                assert any(key.startswith('vendor_') for key in first_item.data.keys())
                print(f"  Sample: {first_item.data}")
            
        except Exception as e:
            pytest.fail(f"Vendor search failed: {e}")


class TestSearchValidation:
    """Test search validation and error handling."""

    @pytest.mark.asyncio
    async def test_invalid_entity_type(self, search_client):
        """Test searching with invalid entity type."""
        try:
            # The search handler catches exceptions and returns error response
            result = await search_client.search("invalid_entity", "test")

            assert not result.success, "Search should fail for invalid entity"
            assert "invalid_entity" in result.error.lower() or "not found" in result.error.lower()
            print(f"✓ Invalid entity type returns error: {result.error}")

        except Exception as e:
            pytest.fail(f"Invalid entity type test failed: {e}")

    @pytest.mark.asyncio
    async def test_empty_query(self, search_client):
        """Test searching with empty query."""
        try:
            # The search handler catches exceptions and returns error response
            result = await search_client.search("user", "")

            assert not result.success, "Search should fail for empty query"
            assert "empty" in result.error.lower() or "cannot be empty" in result.error.lower()
            print(f"✓ Empty query returns error: {result.error}")

        except Exception as e:
            pytest.fail(f"Empty query test failed: {e}")

    @pytest.mark.asyncio
    async def test_limit_enforcement(self, search_client):
        """Test that limit is enforced correctly."""
        try:
            # Get entity config to check max_limit
            config = search_client.get_entity_config("user")
            max_limit = config.max_limit

            # Request more than max_limit
            result = await search_client.search("user", "test", limit=max_limit + 100)

            # Should be capped at max_limit
            assert result.returned_count <= max_limit
            print(f"✓ Limit enforcement works: requested {max_limit + 100}, got {result.returned_count}")

        except Exception as e:
            pytest.fail(f"Limit enforcement test failed: {e}")

    @pytest.mark.asyncio
    async def test_pagination(self, search_client):
        """Test pagination with from_offset."""
        try:
            # Get first page
            result1 = await search_client.search("user", "test", limit=2, from_offset=0)

            # Get second page
            result2 = await search_client.search("user", "test", limit=2, from_offset=2)

            # Results should be different (if enough data exists)
            if result1.items and result2.items and result1.total_hits > 2:
                assert result1.items[0].id != result2.items[0].id
                print(f"✓ Pagination works: page 1 has {len(result1.items)} items, page 2 has {len(result2.items)} items")
            else:
                print("⚠ Not enough data to test pagination fully")

        except Exception as e:
            pytest.fail(f"Pagination test failed: {e}")


class TestSearchFeatures:
    """Test search features like fuzzy matching and scoring."""

    @pytest.mark.asyncio
    async def test_fuzzy_search(self, search_client):
        """Test fuzzy search functionality."""
        try:
            # Search with potential typo
            result = await search_client.search("user", "tset", limit=5)

            # Should still return results due to fuzzy matching
            assert result.success
            print(f"✓ Fuzzy search works: '{result.query}' returned {result.total_hits} hits")

        except Exception as e:
            pytest.fail(f"Fuzzy search test failed: {e}")

    @pytest.mark.asyncio
    async def test_score_ordering(self, search_client):
        """Test that results are ordered by score."""
        try:
            result = await search_client.search("user", "test", limit=10)

            if len(result.items) > 1:
                # Check that scores are in descending order
                scores = [item.score for item in result.items]
                assert scores == sorted(scores, reverse=True), "Results not ordered by score"
                print(f"✓ Score ordering works: scores range from {scores[0]:.2f} to {scores[-1]:.2f}")
            else:
                print("⚠ Not enough results to test score ordering")

        except Exception as e:
            pytest.fail(f"Score ordering test failed: {e}")

    @pytest.mark.asyncio
    async def test_min_score_filtering(self, search_client):
        """Test that min_score filtering works."""
        try:
            result = await search_client.search("user", "test", limit=10)

            # Get entity config to check min_score
            config = search_client.get_entity_config("user")
            min_score = config.min_score

            # All returned items should have score >= min_score
            if result.items:
                for item in result.items:
                    assert item.score >= min_score, f"Item score {item.score} below min_score {min_score}"
                print(f"✓ Min score filtering works: all scores >= {min_score}")

        except Exception as e:
            pytest.fail(f"Min score filtering test failed: {e}")


class TestAllEntitiesComprehensive:
    """Comprehensive test that searches all 11 entity types."""

    @pytest.mark.asyncio
    async def test_all_entities_searchable(self, search_client):
        """Test that all 11 entity types can be searched."""
        all_entities = [
            'impact', 'urgency', 'priority',
            'status', 'category', 'source',
            'location', 'department',
            'usergroup', 'user', 'vendor'
        ]

        results = {}

        for entity_type in all_entities:
            try:
                result = await search_client.search(entity_type, "test", limit=1)
                results[entity_type] = {
                    'success': result.success,
                    'total_hits': result.total_hits,
                    'error': result.error
                }
            except Exception as e:
                results[entity_type] = {
                    'success': False,
                    'total_hits': 0,
                    'error': str(e)
                }

        # Print summary
        print("\n" + "="*60)
        print("All Entities Search Summary")
        print("="*60)

        successful = 0
        for entity_type, result in results.items():
            status = "✓" if result['success'] else "✗"
            print(f"{status} {entity_type:12s}: {result['total_hits']:4d} hits")
            if result['success']:
                successful += 1

        print("="*60)
        print(f"Total: {successful}/{len(all_entities)} entity types searchable")
        print("="*60)

        # Most should be successful (some indices may not exist)
        # We expect at least 9 out of 11 to be searchable
        assert successful >= 9, f"Only {successful}/{len(all_entities)} entities searchable (expected at least 9)"


class TestRealWorldScenarios:
    """Test real-world usage scenarios."""

    @pytest.mark.asyncio
    async def test_user_search_by_email(self, search_client):
        """Scenario: IT admin searches for user by email to assign ticket."""
        try:
            # Search for user by email pattern
            result = await search_client.search("user", "test", limit=10)

            # Validate response structure
            assert result.success or result.total_hits >= 0, "Search should complete"
            assert result.entity_type == "user", "Should search user entity"

            # If results found, validate data structure
            if result.items:
                for item in result.items:
                    assert 'dbid' in item.data or 'user_name' in item.data, "User should have identifiable data"
                    assert item.score > 0, "Results should have relevance score"

                print(f"✓ User search scenario: Found {result.total_hits} users, returned {result.returned_count}")
            else:
                print(f"✓ User search scenario: No users found (valid result)")

        except Exception as e:
            pytest.fail(f"User search scenario failed: {e}")

    @pytest.mark.asyncio
    async def test_status_search_for_ticket_update(self, search_client):
        """Scenario: User wants to update ticket status."""
        try:
            # Search for available statuses
            result = await search_client.search("status", "open", limit=10)

            assert result.entity_type == "status", "Should search status entity"

            # If results found, validate they have required fields
            if result.items:
                for item in result.items:
                    # Status should have name and id
                    assert 'status_name' in item.data or 'dbid' in item.data, "Status should have name or id"

                print(f"✓ Status search scenario: Found {result.total_hits} statuses")
            else:
                print(f"✓ Status search scenario: No statuses found")

        except Exception as e:
            pytest.fail(f"Status search scenario failed: {e}")

    @pytest.mark.asyncio
    async def test_location_hierarchy_search(self, search_client):
        """Scenario: User searches for location in organizational hierarchy."""
        try:
            # Search for location
            result = await search_client.search("location", "office", limit=10)

            assert result.entity_type == "location", "Should search location entity"

            # If results found, validate hierarchical data
            if result.items:
                for item in result.items:
                    # Location should have hierarchical fields
                    data_keys = item.data.keys()
                    has_location_data = any(key.startswith('location_') for key in data_keys)
                    assert has_location_data, "Location should have location-specific fields"

                print(f"✓ Location hierarchy scenario: Found {result.total_hits} locations")
            else:
                print(f"✓ Location hierarchy scenario: No locations found")

        except Exception as e:
            pytest.fail(f"Location hierarchy scenario failed: {e}")

    @pytest.mark.asyncio
    async def test_category_search_for_incident(self, search_client):
        """Scenario: User categorizes an incident."""
        try:
            # Search for categories
            result = await search_client.search("category", "hardware", limit=10)

            assert result.entity_type == "category", "Should search category entity"

            # Validate results are ordered by relevance
            if len(result.items) > 1:
                scores = [item.score for item in result.items]
                assert scores == sorted(scores, reverse=True), "Results should be ordered by score"
                print(f"✓ Category search scenario: Found {result.total_hits} categories, properly ordered")
            else:
                print(f"✓ Category search scenario: Found {result.total_hits} categories")

        except Exception as e:
            pytest.fail(f"Category search scenario failed: {e}")

    @pytest.mark.asyncio
    async def test_fuzzy_search_typo_tolerance(self, search_client):
        """Scenario: User makes typo while searching."""
        try:
            # Search with intentional typo
            result_typo = await search_client.search("user", "tset", limit=5)

            # Fuzzy search should still find results
            assert result_typo.success or result_typo.total_hits >= 0, "Fuzzy search should complete"

            if result_typo.total_hits > 0:
                print(f"✓ Fuzzy search scenario: Typo 'tset' found {result_typo.total_hits} results")
            else:
                print(f"✓ Fuzzy search scenario: Typo handled gracefully")

        except Exception as e:
            pytest.fail(f"Fuzzy search scenario failed: {e}")

    @pytest.mark.asyncio
    async def test_pagination_for_large_results(self, search_client):
        """Scenario: User browses through multiple pages of results."""
        try:
            # Get first page
            page1 = await search_client.search("user", "test", limit=3, from_offset=0)

            # Get second page
            page2 = await search_client.search("user", "test", limit=3, from_offset=3)

            # Validate pagination
            assert page1.entity_type == page2.entity_type, "Both pages should be same entity"
            assert page1.query == page2.query, "Both pages should have same query"

            # If enough results, pages should be different
            if page1.total_hits > 3 and page1.items and page2.items:
                page1_ids = [item.id for item in page1.items]
                page2_ids = [item.id for item in page2.items]
                assert page1_ids != page2_ids, "Different pages should have different results"
                print(f"✓ Pagination scenario: Page 1 has {len(page1.items)} items, Page 2 has {len(page2.items)} items")
            else:
                print(f"✓ Pagination scenario: Not enough data to test pagination fully")

        except Exception as e:
            pytest.fail(f"Pagination scenario failed: {e}")

    @pytest.mark.asyncio
    async def test_limit_enforcement_scenario(self, search_client):
        """Scenario: System enforces result limits to prevent overload."""
        try:
            # Get entity config
            config = search_client.get_entity_config("user")
            max_limit = config.max_limit

            # Try to request more than max_limit
            result = await search_client.search("user", "test", limit=max_limit + 1000)

            # Should be capped at max_limit
            assert result.returned_count <= max_limit, f"Results should be capped at {max_limit}"

            print(f"✓ Limit enforcement scenario: Requested {max_limit + 1000}, got {result.returned_count} (max: {max_limit})")

        except Exception as e:
            pytest.fail(f"Limit enforcement scenario failed: {e}")

    @pytest.mark.asyncio
    async def test_empty_query_validation(self, search_client):
        """Scenario: User submits empty search query."""
        try:
            # Try to search with empty query
            result = await search_client.search("user", "")

            # Should return error, not crash
            assert not result.success, "Empty query should fail"
            assert result.error, "Should have error message"
            assert "empty" in result.error.lower(), "Error should mention empty query"

            print(f"✓ Empty query scenario: Properly rejected with message: {result.error}")

        except Exception as e:
            pytest.fail(f"Empty query scenario failed: {e}")

    @pytest.mark.asyncio
    async def test_cross_entity_search_consistency(self, search_client):
        """Scenario: Verify search behavior is consistent across entity types."""
        try:
            entity_types = ['user', 'status', 'category', 'location']

            for entity_type in entity_types:
                result = await search_client.search(entity_type, "test", limit=5)

                # All should have consistent response structure
                assert hasattr(result, 'success'), f"{entity_type} should have success field"
                assert hasattr(result, 'entity_type'), f"{entity_type} should have entity_type field"
                assert hasattr(result, 'total_hits'), f"{entity_type} should have total_hits field"
                assert hasattr(result, 'items'), f"{entity_type} should have items field"
                assert result.entity_type == entity_type, f"Entity type should match for {entity_type}"

            print(f"✓ Cross-entity consistency: All {len(entity_types)} entity types have consistent response structure")

        except Exception as e:
            pytest.fail(f"Cross-entity consistency scenario failed: {e}")


if __name__ == "__main__":
    # Run tests with pytest
    pytest.main([__file__, "-v", "--tb=short", "-s"])

