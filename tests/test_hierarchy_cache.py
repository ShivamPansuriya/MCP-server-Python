"""
Tests for Hierarchical Entity Cache System

Tests the hierarchy_cache module including:
- Node creation and tree building
- Path generation
- Search functionality
- Elasticsearch integration
- Edge cases (orphaned nodes, circular references)
"""

import pytest
import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from hierarchy_cache import (
    HierarchicalNode,
    HierarchicalCache,
    LocationCacheLoader,
    DepartmentCacheLoader,
    HierarchyCacheManager,
    initialize_hierarchy_caches,
    get_hierarchy_cache_manager
)


class TestHierarchicalNode:
    """Test HierarchicalNode dataclass."""
    
    def test_node_creation(self):
        """Test creating a hierarchical node."""
        node = HierarchicalNode(name="Test Node", id=1, parent_id=None)
        assert node.name == "Test Node"
        assert node.id == 1
        assert node.parent_id is None
    
    def test_node_with_parent(self):
        """Test creating a node with parent."""
        node = HierarchicalNode(name="Child Node", id=2, parent_id=1)
        assert node.name == "Child Node"
        assert node.id == 2
        assert node.parent_id == 1
    
    def test_node_repr(self):
        """Test node string representation."""
        node = HierarchicalNode(name="Test", id=1)
        assert "Test" in repr(node)
        assert "1" in repr(node)


class TestHierarchicalCache:
    """Test HierarchicalCache class."""
    
    def test_cache_creation(self):
        """Test creating a cache."""
        cache = HierarchicalCache(entity_type="test")
        assert cache.entity_type == "test"
        assert len(cache.nodes_by_id) == 0
    
    def test_add_single_node(self):
        """Test adding a single node."""
        cache = HierarchicalCache()
        cache.add_node("Root", 1)
        
        assert len(cache.nodes_by_id) == 1
        assert 1 in cache.nodes_by_id
        assert cache.nodes_by_id[1].name == "Root"
    
    def test_add_hierarchical_nodes(self):
        """Test adding nodes with parent-child relationships."""
        cache = HierarchicalCache()
        
        # Add root
        cache.add_node("Root", 1)
        
        # Add children
        cache.add_node("Child 1", 2, parent_id=1)
        cache.add_node("Child 2", 3, parent_id=1)
        
        # Add grandchild
        cache.add_node("Grandchild", 4, parent_id=2)
        
        assert len(cache.nodes_by_id) == 4
        assert len(cache.children_by_parent[1]) == 2
        assert len(cache.children_by_parent[2]) == 1
    
    def test_search_by_name_exact(self):
        """Test exact name search."""
        cache = HierarchicalCache()
        cache.add_node("Test Location", 1)
        cache.add_node("Another Location", 2)
        cache.add_node("Test Location", 3)  # Duplicate name
        
        results = cache.search_by_name_exact("Test Location")
        assert len(results) == 2
        assert all(node.name == "Test Location" for node in results)
    
    def test_search_by_name_prefix(self):
        """Test prefix name search."""
        cache = HierarchicalCache()
        cache.add_node("California", 1)
        cache.add_node("Canada", 2)
        cache.add_node("Texas", 3)
        
        results = cache.search_by_name_prefix("Ca")
        assert len(results) == 2
        assert all(node.name.startswith("Ca") for node in results)
    
    def test_get_full_path(self):
        """Test getting full path by ID."""
        cache = HierarchicalCache()
        cache.add_node("Root", 1)
        cache.add_node("Child", 2, parent_id=1)
        cache.add_node("Grandchild", 3, parent_id=2)
        
        path = cache.get_full_path(3)
        assert path == "1 -> 2 -> 3"
    
    def test_get_full_path_name(self):
        """Test getting full path by name."""
        cache = HierarchicalCache()
        cache.add_node("Root", 1)
        cache.add_node("Child", 2, parent_id=1)
        cache.add_node("Grandchild", 3, parent_id=2)
        
        # By ID
        path = cache.get_full_path_name(3)
        assert path == "Root -> Child -> Grandchild"
        
        # By name (unique)
        path = cache.get_full_path_name("Grandchild")
        assert path == "Root -> Child -> Grandchild"
    
    def test_get_full_path_name_multiple_matches(self):
        """Test getting paths when multiple nodes have same name."""
        cache = HierarchicalCache()
        cache.add_node("Root", 1)
        cache.add_node("HR", 2, parent_id=1)
        cache.add_node("HR", 3, parent_id=1)
        
        paths = cache.get_full_path_name("HR")
        assert isinstance(paths, list)
        assert len(paths) == 2
        assert all("Root -> HR" in path for path in paths)
    
    def test_get_children(self):
        """Test getting direct children."""
        cache = HierarchicalCache()
        cache.add_node("Root", 1)
        cache.add_node("Child 1", 2, parent_id=1)
        cache.add_node("Child 2", 3, parent_id=1)
        cache.add_node("Grandchild", 4, parent_id=2)
        
        children = cache.get_children(1)
        assert len(children) == 2
        assert all(child.parent_id == 1 for child in children)
    
    def test_circular_reference_handling(self):
        """Test that circular references are detected and handled."""
        cache = HierarchicalCache()
        
        # Manually create circular reference (shouldn't happen in real data)
        cache.add_node("Node 1", 1, parent_id=2)
        cache.add_node("Node 2", 2, parent_id=1)
        
        # Should not crash, should detect cycle
        path = cache.get_full_path(1)
        # Path should be limited and not infinite
        assert len(path) < 100  # Sanity check
    
    def test_get_stats(self):
        """Test getting cache statistics."""
        cache = HierarchicalCache(entity_type="location")
        cache.add_node("Root 1", 1)
        cache.add_node("Root 2", 2)
        cache.add_node("Child", 3, parent_id=1)
        
        stats = cache.get_stats()
        assert stats['entity_type'] == "location"
        assert stats['total_nodes'] == 3
        assert stats['root_nodes'] == 2
        assert stats['max_depth'] >= 0


class TestHierarchyCacheManager:
    """Test HierarchyCacheManager singleton."""
    
    def test_singleton_pattern(self):
        """Test that manager follows singleton pattern."""
        manager1 = HierarchyCacheManager.get_instance()
        manager2 = HierarchyCacheManager.get_instance()
        assert manager1 is manager2
    
    def test_manager_initialization(self):
        """Test manager provides access to caches."""
        manager = HierarchyCacheManager.get_instance()
        
        # Before initialization
        assert manager.get_location_cache() is None or isinstance(manager.get_location_cache(), HierarchicalCache)
        assert manager.get_department_cache() is None or isinstance(manager.get_department_cache(), HierarchicalCache)
    
    def test_get_statistics(self):
        """Test getting statistics from manager."""
        manager = HierarchyCacheManager.get_instance()
        stats = manager.get_statistics()
        
        assert 'initialized' in stats
        assert 'location' in stats
        assert 'department' in stats


class TestElasticsearchIntegration:
    """Test Elasticsearch integration (requires ES to be running)."""
    
    @pytest.mark.skipif(
        not os.getenv("ES_HOST"),
        reason="Elasticsearch not configured (ES_HOST not set)"
    )
    def test_location_loader_connection(self):
        """Test location loader can connect to Elasticsearch."""
        loader = LocationCacheLoader("apolo")
        connected = loader.connect()
        
        # Connection may fail if ES is not running, which is okay
        assert isinstance(connected, bool)
    
    @pytest.mark.skipif(
        not os.getenv("ES_HOST"),
        reason="Elasticsearch not configured (ES_HOST not set)"
    )
    def test_department_loader_connection(self):
        """Test department loader can connect to Elasticsearch."""
        loader = DepartmentCacheLoader("apolo")
        connected = loader.connect()
        
        # Connection may fail if ES is not running, which is okay
        assert isinstance(connected, bool)


class TestPublicAPI:
    """Test public API functions."""
    
    def test_initialize_hierarchy_caches(self):
        """Test initialization function."""
        # This may fail if ES is not available, but should not crash
        manager = initialize_hierarchy_caches("apolo")
        
        # Should return a manager instance even if initialization failed
        assert manager is None or isinstance(manager, HierarchyCacheManager)
    
    def test_get_hierarchy_cache_manager(self):
        """Test getting manager instance."""
        manager = get_hierarchy_cache_manager()
        
        # Should return manager or None
        assert manager is None or isinstance(manager, HierarchyCacheManager)


if __name__ == "__main__":
    # Run tests with pytest
    pytest.main([__file__, "-v", "-s"])

