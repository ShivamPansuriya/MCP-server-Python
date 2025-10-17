"""
Hierarchical Entity Cache System

Provides in-memory tree caches for hierarchical entities (locations, departments)
with fast lookups and path generation capabilities.

Based on the OptimizedLocationCache pattern from treiTree.py but generalized
to support multiple entity types.
"""

import sys
import bisect
import logging
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple, Union
from collections import defaultdict

logger = logging.getLogger(__name__)


@dataclass
class HierarchicalNode:
    """
    Lightweight hierarchical node with minimal memory footprint.
    
    Represents a single entity in a hierarchy (location, department, etc.)
    """
    name: str
    id: Union[str, int]
    parent_id: Optional[Union[str, int]] = None

    def __post_init__(self):
        # Intern strings to reduce memory usage for duplicate names
        if isinstance(self.name, str):
            self.name = sys.intern(self.name)
        if isinstance(self.id, str):
            self.id = sys.intern(self.id)
        if isinstance(self.parent_id, str):
            self.parent_id = sys.intern(self.parent_id)

    def __repr__(self):
        return f"HierarchicalNode(name='{self.name}', id='{self.id}')"


class HierarchicalCache:
    """
    High-performance hierarchical entity cache.

    Features:
    - O(1) ID lookups via HashMap
    - O(log N) name searches via sorted arrays + binary search
    - O(1) path lookups via pre-computed cache
    - Handles deep hierarchies efficiently
    - Thread-safe for read operations after construction
    """

    def __init__(self, entity_type: str = "entity"):
        """
        Initialize hierarchical cache.
        
        Args:
            entity_type: Type of entity being cached (for logging/debugging)
        """
        self.entity_type = entity_type
        
        # Primary storage: O(1) ID lookups
        self.nodes_by_id: Dict[Union[str, int], HierarchicalNode] = {}

        # Sorted indices for binary search: O(log N) lookups
        self.names_sorted: List[Tuple[str, Union[str, int]]] = []  # (name, id)
        self.names_lower_sorted: List[Tuple[str, Union[str, int]]] = []  # (name.lower(), id)

        # Name-to-IDs mapping for handling duplicates
        self.name_to_ids: Dict[str, List[Union[str, int]]] = defaultdict(list)

        # Pre-computed paths cache: O(1) path lookups
        self.paths_cache: Dict[Union[str, int], str] = {}
        self.paths_name_cache: Dict[Union[str, int], str] = {}

        # Children mapping for hierarchy traversal
        self.children_by_parent: Dict[Union[str, int], List[Union[str, int]]] = defaultdict(list)

        # Build state
        self._indices_built = False
        self._paths_computed = False

    def add_node(self, name: str, id_: Union[str, int], parent_id: Optional[Union[str, int]] = None):
        """
        Add a node to the cache.

        Args:
            name: Entity name
            id_: Unique entity identifier
            parent_id: Parent entity ID (None for root nodes)
        """
        # Create and store node
        node = HierarchicalNode(name, id_, parent_id)
        self.nodes_by_id[id_] = node

        # Track children for hierarchy
        if parent_id is not None:
            self.children_by_parent[parent_id].append(id_)

        # Track name duplicates
        self.name_to_ids[name.lower()].append(id_)

        # Mark indices as needing rebuild
        self._indices_built = False
        self._paths_computed = False

    def update_node(self, id_: Union[str, int], name: str, parent_id: Optional[Union[str, int]] = None) -> bool:
        """
        Update an existing node in the cache, or add it if it doesn't exist (upsert).

        This method replaces an existing node's name and parent_id while maintaining
        cache integrity. If the node doesn't exist, it will be added to the cache.
        All related indices and tracking structures are updated.

        Args:
            id_: Unique entity identifier of the node to update/add
            name: New entity name
            parent_id: New parent entity ID (None for root nodes)

        Returns:
            True if node was updated/added successfully

        Example:
            >>> cache.update_node(123, "New York Office", parent_id=100)
            True
        """
        # Check if node exists - if not, add it
        if id_ not in self.nodes_by_id:
            logger.debug(f"Node {id_} not found in cache, adding it")
            self.add_node(name, id_, parent_id)
            return True

        old_node = self.nodes_by_id[id_]
        old_name = old_node.name
        old_parent_id = old_node.parent_id

        # Remove old name from name tracking
        if old_name.lower() in self.name_to_ids:
            try:
                self.name_to_ids[old_name.lower()].remove(id_)
                # Clean up empty lists
                if not self.name_to_ids[old_name.lower()]:
                    del self.name_to_ids[old_name.lower()]
            except ValueError:
                logger.warning(f"Node {id_} not found in name_to_ids for '{old_name}'")

        # Remove from old parent's children list
        if old_parent_id is not None and old_parent_id in self.children_by_parent:
            try:
                self.children_by_parent[old_parent_id].remove(id_)
                # Clean up empty lists
                if not self.children_by_parent[old_parent_id]:
                    del self.children_by_parent[old_parent_id]
            except ValueError:
                logger.warning(f"Node {id_} not found in children list of parent {old_parent_id}")

        # Create updated node
        updated_node = HierarchicalNode(name, id_, parent_id)
        self.nodes_by_id[id_] = updated_node

        # Add to new parent's children list
        if parent_id is not None:
            self.children_by_parent[parent_id].append(id_)

        # Track new name
        self.name_to_ids[name.lower()].append(id_)

        # Mark indices as needing rebuild
        self._indices_built = False
        self._paths_computed = False

        logger.debug(
            f"Updated {self.entity_type} node {id_}: "
            f"name '{old_name}' -> '{name}', "
            f"parent {old_parent_id} -> {parent_id}"
        )

        return True

    def remove_node(self, id_: Union[str, int]) -> bool:
        """
        Remove a node from the cache by its ID.

        This method removes a node and updates all related indices and tracking structures.
        If the node has children, they will be orphaned (parent_id set to None).

        Args:
            id_: Unique entity identifier of the node to remove

        Returns:
            True if node was removed successfully, False if node doesn't exist

        Example:
            >>> cache.remove_node(123)
            True
        """
        # Check if node exists
        if id_ not in self.nodes_by_id:
            logger.warning(f"Cannot remove node {id_}: node not found in cache")
            return False

        node = self.nodes_by_id[id_]
        node_name = node.name
        node_parent_id = node.parent_id

        # Handle children - orphan them by setting their parent_id to None
        if id_ in self.children_by_parent:
            child_ids = self.children_by_parent[id_].copy()
            for child_id in child_ids:
                if child_id in self.nodes_by_id:
                    child_node = self.nodes_by_id[child_id]
                    # Create new node with parent_id = None
                    orphaned_node = HierarchicalNode(child_node.name, child_node.id, None)
                    self.nodes_by_id[child_id] = orphaned_node

            # Remove the children mapping
            del self.children_by_parent[id_]
            logger.warning(f"Orphaned {len(child_ids)} children of node {id_}")

        # Remove from parent's children list
        if node_parent_id is not None and node_parent_id in self.children_by_parent:
            try:
                self.children_by_parent[node_parent_id].remove(id_)
                # Clean up empty lists
                if not self.children_by_parent[node_parent_id]:
                    del self.children_by_parent[node_parent_id]
            except ValueError:
                logger.warning(f"Node {id_} not found in children list of parent {node_parent_id}")

        # Remove from name tracking
        if node_name.lower() in self.name_to_ids:
            try:
                self.name_to_ids[node_name.lower()].remove(id_)
                # Clean up empty lists
                if not self.name_to_ids[node_name.lower()]:
                    del self.name_to_ids[node_name.lower()]
            except ValueError:
                logger.warning(f"Node {id_} not found in name_to_ids for '{node_name}'")

        # Remove from paths caches
        self.paths_cache.pop(id_, None)
        self.paths_name_cache.pop(id_, None)

        # Remove from primary storage
        del self.nodes_by_id[id_]

        # Mark indices as needing rebuild
        self._indices_built = False
        self._paths_computed = False

        logger.debug(f"Removed {self.entity_type} node {id_} ('{node_name}')")

        return True

    def _build_indices(self):
        """Build sorted indices for fast searching. Call after all nodes added."""
        if self._indices_built:
            return

        # Build sorted name indices for binary search
        name_id_pairs = [(node.name, node.id) for node in self.nodes_by_id.values()]
        self.names_sorted = sorted(name_id_pairs, key=lambda x: x[0])

        # Build lowercase sorted index with lowercase names
        name_lower_id_pairs = [(node.name.lower(), node.id) for node in self.nodes_by_id.values()]
        self.names_lower_sorted = sorted(name_lower_id_pairs, key=lambda x: x[0])

        self._indices_built = True

    def _compute_paths(self):
        """Pre-compute all entity paths for O(1) access."""
        if self._paths_computed:
            return

        self._build_indices()  # Ensure indices are built first

        # Compute paths for all nodes
        for node_id, node in self.nodes_by_id.items():
            # Build ID path
            id_path = self._build_id_path(node_id)
            self.paths_cache[node_id] = " -> ".join(str(id_) for id_ in id_path)

            # Build name path
            name_path = self._build_name_path(node_id)
            self.paths_name_cache[node_id] = " -> ".join(name_path)

        self._paths_computed = True

    def _build_id_path(self, node_id: Union[str, int]) -> List[Union[str, int]]:
        """Build path of IDs from root to given node."""
        path = []
        current_id = node_id
        visited = set()  # Prevent infinite loops

        while current_id is not None and current_id in self.nodes_by_id:
            if current_id in visited:
                logger.warning(f"Circular reference detected in {self.entity_type} hierarchy at node {current_id}")
                break  # Circular reference detected
            visited.add(current_id)

            path.append(current_id)
            current_id = self.nodes_by_id[current_id].parent_id

        return list(reversed(path))

    def _build_name_path(self, node_id: Union[str, int]) -> List[str]:
        """Build path of names from root to given node."""
        id_path = self._build_id_path(node_id)
        return [self.nodes_by_id[id_].name for id_ in id_path]

    def search_by_name_exact(self, name: str) -> List[HierarchicalNode]:
        """
        Find nodes whose name exactly matches.

        Args:
            name: Exact name to search for

        Returns:
            List of matching HierarchicalNode objects
        """
        self._build_indices()

        # Handle case-insensitive search
        matching_ids = self.name_to_ids.get(name.lower(), [])
        return [self.nodes_by_id[id_] for id_ in matching_ids]

    def search_by_name_prefix(self, prefix: str) -> List[HierarchicalNode]:
        """
        Find nodes whose name starts with given prefix.

        Args:
            prefix: Name prefix to search for

        Returns:
            List of matching HierarchicalNode objects
        """
        self._build_indices()

        prefix_lower = prefix.lower()
        results = []

        # Binary search for first match
        start_idx = bisect.bisect_left(self.names_lower_sorted, (prefix_lower, ""))

        # Collect all matches
        for i in range(start_idx, len(self.names_lower_sorted)):
            name_lower, node_id = self.names_lower_sorted[i]
            if not name_lower.startswith(prefix_lower):
                break
            results.append(self.nodes_by_id[node_id])

        return results

    def get_full_path(self, node_id: Union[str, int]) -> str:
        """
        Return the full path (IDs) of a given node.

        Args:
            node_id: Node identifier

        Returns:
            Path string with IDs separated by " -> "
        """
        self._compute_paths()
        return self.paths_cache.get(node_id, "")

    def get_full_path_name(self, identifier: Union[str, int]) -> Union[str, List[str]]:
        """
        Return full path (names) given either node_id or name.

        Args:
            identifier: Either a node ID or an entity name

        Returns:
            Path string with names, or list of paths if multiple matches
        """
        self._compute_paths()

        # Try as node ID first
        if identifier in self.nodes_by_id:
            return self.paths_name_cache.get(identifier, "")

        # Try as name
        matching_nodes = self.search_by_name_exact(str(identifier))
        if not matching_nodes:
            return ""

        if len(matching_nodes) == 1:
            return self.paths_name_cache.get(matching_nodes[0].id, "")

        # Multiple matches - return all paths
        return [self.paths_name_cache.get(node.id, "") for node in matching_nodes]

    def get_children(self, node_id: Union[str, int]) -> List[HierarchicalNode]:
        """
        Get direct children of a node.

        Args:
            node_id: Parent node identifier

        Returns:
            List of child HierarchicalNode objects
        """
        child_ids = self.children_by_parent.get(node_id, [])
        return [self.nodes_by_id[child_id] for child_id in child_ids]

    def get_stats(self) -> Dict[str, Union[int, float]]:
        """
        Get cache statistics.

        Returns:
            Dictionary with cache statistics
        """
        total_nodes = len(self.nodes_by_id)
        root_nodes = sum(1 for node in self.nodes_by_id.values() if node.parent_id is None)

        # Calculate depth statistics
        depths = []
        for node_id in self.nodes_by_id:
            depth = len(self._build_id_path(node_id)) - 1
            depths.append(depth)

        return {
            'entity_type': self.entity_type,
            'total_nodes': total_nodes,
            'root_nodes': root_nodes,
            'max_depth': max(depths) if depths else 0,
            'avg_depth': sum(depths) / len(depths) if depths else 0,
            'indices_built': self._indices_built,
            'paths_computed': self._paths_computed
        }


# -------------------------------
# Elasticsearch Data Loaders
# -------------------------------

class BaseEntityLoader:
    """
    Base class for loading hierarchical entities from Elasticsearch.

    Handles common Elasticsearch operations and provides template for
    entity-specific field mapping.
    """

    def __init__(self, tenant_id: str, entity_type: str, index_suffix: str):
        """
        Initialize entity loader.

        Args:
            tenant_id: Tenant identifier for index naming
            entity_type: Type of entity (for logging)
            index_suffix: Index suffix (e.g., "location", "department")
        """
        self.tenant_id = tenant_id
        self.entity_type = entity_type
        self.index_name = f"{tenant_id}_{index_suffix}"
        self.es_client = None

    def connect(self) -> bool:
        """Connect to Elasticsearch using existing client infrastructure."""
        try:
            from elasticsearch_client import get_elasticsearch_client

            es_wrapper = get_elasticsearch_client()

            if es_wrapper.connect():
                self.es_client = es_wrapper.get_client()
                logger.info(f"Connected to Elasticsearch for {self.entity_type} loading")
                return True
            else:
                logger.error(f"Failed to connect to Elasticsearch for {self.entity_type}")
                return False

        except ImportError as e:
            logger.error(f"elasticsearch_client module not found: {e}")
            return False
        except Exception as e:
            logger.error(f"Failed to connect to Elasticsearch: {e}", exc_info=True)
            return False

    def load_entities(self, cache: HierarchicalCache) -> bool:
        """
        Load all entities from Elasticsearch into the cache.

        Args:
            cache: HierarchicalCache instance to populate

        Returns:
            True if successful, False otherwise
        """
        if not self.es_client:
            logger.error(f"Not connected to Elasticsearch for {self.entity_type}")
            return False

        try:
            # Check if index exists
            if not self.es_client.indices.exists(index=self.index_name):
                logger.warning(f"Index '{self.index_name}' does not exist")
                return False

            # Get all entities using scroll API for large datasets
            query = {
                "query": {"match_all": {}},
                "size": 1000  # Process in batches
            }

            response = self.es_client.search(
                index=self.index_name,
                body=query,
                scroll='2m'
            )

            scroll_id = response['_scroll_id']
            hits = response['hits']['hits']
            total_loaded = 0

            # Process first batch
            total_loaded += self._process_batch(cache, hits)

            # Process remaining batches
            while len(hits) > 0:
                response = self.es_client.scroll(scroll_id=scroll_id, scroll='2m')
                hits = response['hits']['hits']
                total_loaded += self._process_batch(cache, hits)

            # Clear scroll
            self.es_client.clear_scroll(scroll_id=scroll_id)

            logger.info(f"✅ Loaded {total_loaded} {self.entity_type} entities from Elasticsearch")
            return True

        except Exception as e:
            logger.error(f"Error loading {self.entity_type} entities: {e}", exc_info=True)
            return False

    def _process_batch(self, cache: HierarchicalCache, hits: list) -> int:
        """
        Process a batch of Elasticsearch hits.

        Must be implemented by subclasses to handle entity-specific field mapping.

        Args:
            cache: HierarchicalCache to populate
            hits: List of Elasticsearch hit documents

        Returns:
            Number of entities successfully loaded
        """
        raise NotImplementedError("Subclasses must implement _process_batch")


class LocationCacheLoader(BaseEntityLoader):
    """Loads location entities from Elasticsearch into HierarchicalCache."""

    def __init__(self, tenant_id: str = "apolo"):
        """
        Initialize location loader.

        Args:
            tenant_id: Tenant identifier for index naming
        """
        super().__init__(tenant_id, "location", "location")

    def _process_batch(self, cache: HierarchicalCache, hits: list) -> int:
        """Process a batch of location documents."""
        loaded_count = 0

        for hit in hits:
            try:
                source = hit['_source']

                # Extract location data based on ES schema
                location_id = source.get('dbid')
                location_name = source.get('location_name', '')
                parent_id = source.get('location_parentid')

                # Validate required fields
                if location_id is None or not location_name:
                    logger.warning(f"Skipping location with missing required fields: {hit.get('_id', 'unknown')}")
                    continue

                # Convert parent_id = 0 to None (root nodes)
                if parent_id == 0:
                    parent_id = None

                # Add to cache
                cache.add_node(location_name, location_id, parent_id)
                loaded_count += 1

            except Exception as e:
                logger.warning(f"Error processing location {hit.get('_id', 'unknown')}: {e}")
                continue

        return loaded_count


class DepartmentCacheLoader(BaseEntityLoader):
    """Loads department entities from Elasticsearch into HierarchicalCache."""

    def __init__(self, tenant_id: str = "apolo"):
        """
        Initialize department loader.

        Args:
            tenant_id: Tenant identifier for index naming
        """
        super().__init__(tenant_id, "department", "department")

    def _process_batch(self, cache: HierarchicalCache, hits: list) -> int:
        """Process a batch of department documents."""
        loaded_count = 0

        for hit in hits:
            try:
                source = hit['_source']

                # Extract department data based on ES schema
                department_id = source.get('dbid')
                department_name = source.get('department_name', '')
                parent_id = source.get('department_parentid')

                # Validate required fields
                if department_id is None or not department_name:
                    logger.warning(f"Skipping department with missing required fields: {hit.get('_id', 'unknown')}")
                    continue

                # Convert parent_id = 0 to None (root nodes)
                if parent_id == 0:
                    parent_id = None

                # Add to cache
                cache.add_node(department_name, department_id, parent_id)
                loaded_count += 1

            except Exception as e:
                logger.warning(f"Error processing department {hit.get('_id', 'unknown')}: {e}")
                continue

        return loaded_count


# -------------------------------
# Hierarchy Cache Manager
# -------------------------------

class HierarchyCacheManager:
    """
    Manages multiple hierarchical entity caches (locations, departments).

    Provides a unified interface for accessing and managing separate tree
    structures for different entity types. Implements singleton pattern
    to ensure single initialization.
    """

    _instance: Optional['HierarchyCacheManager'] = None
    _initialized: bool = False

    def __init__(self):
        """Initialize cache manager (use get_instance() instead)."""
        self.location_cache: Optional[HierarchicalCache] = None
        self.department_cache: Optional[HierarchicalCache] = None
        self._tenant_id: Optional[str] = None

    @classmethod
    def get_instance(cls) -> 'HierarchyCacheManager':
        """
        Get singleton instance of cache manager.

        Returns:
            HierarchyCacheManager instance
        """
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def initialize(self, tenant_id: str) -> bool:
        """
        Initialize both location and department caches.

        Args:
            tenant_id: Tenant identifier for index naming

        Returns:
            True if at least one cache was successfully initialized
        """
        if self._initialized:
            logger.info("Hierarchy caches already initialized")
            return True

        self._tenant_id = tenant_id
        logger.info(f"Initializing hierarchy caches for tenant '{tenant_id}'...")

        location_success = self._initialize_location_cache(tenant_id)
        department_success = self._initialize_department_cache(tenant_id)

        # Mark as initialized if at least one succeeded
        if location_success or department_success:
            self._initialized = True
            logger.info("✅ Hierarchy cache initialization complete")
            self._log_statistics()
            return True
        else:
            logger.error("❌ Failed to initialize any hierarchy caches")
            return False

    def _initialize_location_cache(self, tenant_id: str) -> bool:
        """Initialize location cache."""
        try:
            logger.info("Loading location hierarchy...")

            # Create cache
            self.location_cache = HierarchicalCache(entity_type="location")

            # Load data from Elasticsearch
            loader = LocationCacheLoader(tenant_id)

            if not loader.connect():
                logger.error("Failed to connect to Elasticsearch for locations")
                return False

            if not loader.load_entities(self.location_cache):
                logger.error("Failed to load location data")
                return False

            # Build indices and compute paths
            self.location_cache._build_indices()
            self.location_cache._compute_paths()

            logger.info("✅ Location cache initialized successfully")
            return True

        except Exception as e:
            logger.error(f"Error initializing location cache: {e}", exc_info=True)
            self.location_cache = None
            return False

    def _initialize_department_cache(self, tenant_id: str) -> bool:
        """Initialize department cache."""
        try:
            logger.info("Loading department hierarchy...")

            # Create cache
            self.department_cache = HierarchicalCache(entity_type="department")

            # Load data from Elasticsearch
            loader = DepartmentCacheLoader(tenant_id)

            if not loader.connect():
                logger.error("Failed to connect to Elasticsearch for departments")
                return False

            if not loader.load_entities(self.department_cache):
                logger.error("Failed to load department data")
                return False

            # Build indices and compute paths
            self.department_cache._build_indices()
            self.department_cache._compute_paths()

            logger.info("✅ Department cache initialized successfully")
            return True

        except Exception as e:
            logger.error(f"Error initializing department cache: {e}", exc_info=True)
            self.department_cache = None
            return False

    def _log_statistics(self):
        """Log statistics for all initialized caches."""
        if self.location_cache:
            stats = self.location_cache.get_stats()
            logger.info(
                f"📊 Location Cache: {stats['total_nodes']} nodes, "
                f"{stats['root_nodes']} roots, max depth {stats['max_depth']}"
            )

        if self.department_cache:
            stats = self.department_cache.get_stats()
            logger.info(
                f"📊 Department Cache: {stats['total_nodes']} nodes, "
                f"{stats['root_nodes']} roots, max depth {stats['max_depth']}"
            )

    def get_location_cache(self) -> Optional[HierarchicalCache]:
        """
        Get location cache instance.

        Returns:
            HierarchicalCache for locations or None if not initialized
        """
        return self.location_cache

    def get_department_cache(self) -> Optional[HierarchicalCache]:
        """
        Get department cache instance.

        Returns:
            HierarchicalCache for departments or None if not initialized
        """
        return self.department_cache

    def is_initialized(self) -> bool:
        """Check if caches have been initialized."""
        return self._initialized

    def get_statistics(self) -> Dict[str, any]:
        """
        Get statistics for all caches.

        Returns:
            Dictionary with statistics for each cache
        """
        stats = {
            'tenant_id': self._tenant_id,
            'initialized': self._initialized,
            'location': self.location_cache.get_stats() if self.location_cache else None,
            'department': self.department_cache.get_stats() if self.department_cache else None,
        }
        return stats


# -------------------------------
# Public API
# -------------------------------

def initialize_hierarchy_caches(tenant_id: str = "apolo") -> Optional[HierarchyCacheManager]:
    """
    Initialize hierarchical entity caches for locations and departments.

    This is the main entry point for setting up the cache system. It should
    be called once during server startup.

    Args:
        tenant_id: Tenant identifier for index naming (default: "apolo")

    Returns:
        HierarchyCacheManager instance if successful, None if completely failed

    Example:
        >>> # During server startup
        >>> cache_manager = initialize_hierarchy_caches("apolo")
        >>> if cache_manager:
        ...     location_cache = cache_manager.get_location_cache()
        ...     dept_cache = cache_manager.get_department_cache()
    """
    try:
        logger.info("=" * 60)
        logger.info("🚀 Initializing Hierarchy Cache System")
        logger.info("=" * 60)

        # Get singleton manager instance
        manager = HierarchyCacheManager.get_instance()

        # Initialize caches
        success = manager.initialize(tenant_id)

        if success:
            logger.info("=" * 60)
            logger.info("✅ Hierarchy Cache System Ready")
            logger.info("=" * 60)
            return manager
        else:
            logger.warning("⚠️ Hierarchy cache initialization failed, but server can continue")
            return manager  # Return manager even if initialization failed

    except Exception as e:
        logger.error(f"❌ Critical error during hierarchy cache initialization: {e}", exc_info=True)
        logger.warning("Server will continue without hierarchy caches")
        return None


def get_hierarchy_cache_manager() -> Optional[HierarchyCacheManager]:
    """
    Get the singleton hierarchy cache manager instance.

    Returns:
        HierarchyCacheManager instance or None if not initialized

    Example:
        >>> manager = get_hierarchy_cache_manager()
        >>> if manager and manager.is_initialized():
        ...     location_cache = manager.get_location_cache()
    """
    return HierarchyCacheManager.get_instance() if HierarchyCacheManager._instance else None

