"""
Elasticsearch Configuration Loader

Parses XML configuration file for user search field priorities and settings.
Provides fallback defaults if configuration file is missing or malformed.
"""

import logging
import os
import xml.etree.ElementTree as ET
from typing import Dict, List, Optional
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class SearchFieldConfig:
    """Configuration for a single search field."""
    name: str
    boost: float
    enabled: bool
    description: str = ""
    # Field-level overrides (optional)
    fuzziness: Optional[str] = None  # Override global fuzziness for this field
    min_score: Optional[float] = None  # Override global min_score for this field

    def get_fuzziness(self, global_fuzziness: str) -> str:
        """Get effective fuzziness (field-level or global)."""
        return self.fuzziness if self.fuzziness is not None else global_fuzziness

    def get_min_score(self, global_min_score: float) -> float:
        """Get effective min_score (field-level or global)."""
        return self.min_score if self.min_score is not None else global_min_score


@dataclass
class UserSearchConfig:
    """Complete user search configuration."""
    fuzziness: str
    default_limit: int
    search_fields: List[SearchFieldConfig]
    max_limit: int = 100
    min_score: float = 0.0

    def get_enabled_fields(self) -> List[SearchFieldConfig]:
        """Get only enabled search fields."""
        return [field for field in self.search_fields if field.enabled]

    def get_field_boosts(self) -> Dict[str, float]:
        """Get mapping of field names to boost values for enabled fields."""
        return {field.name: field.boost for field in self.get_enabled_fields()}

    def get_field_names(self) -> List[str]:
        """Get list of enabled field names in priority order."""
        return [field.name for field in self.get_enabled_fields()]


class ElasticsearchConfigLoader:
    """Loads and parses Elasticsearch user search configuration from XML."""
    
    DEFAULT_CONFIG_PATH = "config/user_search_fields.xml"
    
    # Fallback configuration if XML file is missing or malformed
    DEFAULT_CONFIG = UserSearchConfig(
        fuzziness="AUTO",
        default_limit=10,
        max_limit=100,
        min_score=0.0,
        search_fields=[
            SearchFieldConfig(name="user_name", boost=3.0, enabled=True, description="User's full name"),
            SearchFieldConfig(name="user_email", boost=2.5, enabled=True, description="User's email address"),
            SearchFieldConfig(name="user_userlogonname", boost=2.0, enabled=True, description="User's login name"),
            SearchFieldConfig(name="user_contact", boost=1.5, enabled=True, description="Primary contact number"),
            SearchFieldConfig(name="user_contact2", boost=1.0, enabled=True, description="Secondary contact number"),
        ]
    )
    
    def __init__(self, config_path: Optional[str] = None):
        """
        Initialize the configuration loader.
        
        Args:
            config_path: Path to XML configuration file (defaults to config/user_search_fields.xml)
        """
        self.config_path = config_path or self.DEFAULT_CONFIG_PATH
        self._config: Optional[UserSearchConfig] = None
    
    def load_config(self) -> UserSearchConfig:
        """
        Load configuration from XML file with fallback to defaults.
        
        Returns:
            UserSearchConfig object with search settings
        """
        if self._config is not None:
            return self._config
        
        # Check if config file exists
        if not os.path.exists(self.config_path):
            logger.warning(
                f"Configuration file not found: {self.config_path}. Using default configuration."
            )
            self._config = self.DEFAULT_CONFIG
            return self._config
        
        try:
            logger.info(f"Loading user search configuration from: {self.config_path}")
            self._config = self._parse_xml_config(self.config_path)
            logger.info(
                f"Successfully loaded configuration with {len(self._config.search_fields)} fields, "
                f"{len(self._config.get_enabled_fields())} enabled"
            )
            return self._config
            
        except Exception as e:
            logger.error(
                f"Error parsing configuration file {self.config_path}: {e}. "
                f"Using default configuration."
            )
            self._config = self.DEFAULT_CONFIG
            return self._config
    
    def _parse_xml_config(self, file_path: str) -> UserSearchConfig:
        """
        Parse XML configuration file.
        
        Args:
            file_path: Path to XML file
            
        Returns:
            UserSearchConfig object
            
        Raises:
            Exception: If XML is malformed or required elements are missing
        """
        tree = ET.parse(file_path)
        root = tree.getroot()
        
        if root.tag != "userSearchConfig":
            raise ValueError(f"Invalid root element: {root.tag}. Expected 'userSearchConfig'")
        
        # Parse fuzziness setting
        fuzziness_elem = root.find("fuzziness")
        fuzziness = fuzziness_elem.text.strip() if fuzziness_elem is not None else "AUTO"

        # Parse default limit
        limit_elem = root.find("defaultLimit")
        default_limit = int(limit_elem.text.strip()) if limit_elem is not None else 10

        # Parse max limit
        max_limit_elem = root.find("maxLimit")
        max_limit = int(max_limit_elem.text.strip()) if max_limit_elem is not None else 100

        # Parse min score
        min_score_elem = root.find("minScore")
        min_score = float(min_score_elem.text.strip()) if min_score_elem is not None else 0.0
        
        # Parse search fields
        search_fields = []
        fields_elem = root.find("searchFields")
        
        if fields_elem is None:
            raise ValueError("Missing required element: searchFields")
        
        for field_elem in fields_elem.findall("field"):
            try:
                name_elem = field_elem.find("name")
                boost_elem = field_elem.find("boost")
                enabled_elem = field_elem.find("enabled")
                desc_elem = field_elem.find("description")

                # NEW: Parse field-level overrides
                field_fuzziness_elem = field_elem.find("fuzziness")
                field_min_score_elem = field_elem.find("minScore")

                if name_elem is None or boost_elem is None:
                    logger.warning("Skipping field with missing name or boost")
                    continue

                name = name_elem.text.strip()
                boost = float(boost_elem.text.strip())
                enabled = enabled_elem.text.strip().lower() == "true" if enabled_elem is not None else True
                description = desc_elem.text.strip() if desc_elem is not None else ""

                # NEW: Parse field-level fuzziness and min_score (optional)
                field_fuzziness = field_fuzziness_elem.text.strip() if field_fuzziness_elem is not None else None
                field_min_score = float(field_min_score_elem.text.strip()) if field_min_score_elem is not None else None

                search_fields.append(SearchFieldConfig(
                    name=name,
                    boost=boost,
                    enabled=enabled,
                    description=description,
                    fuzziness=field_fuzziness,  # NEW
                    min_score=field_min_score   # NEW
                ))

            except Exception as e:
                logger.warning(f"Error parsing field element: {e}. Skipping field.")
                continue
        
        if not search_fields:
            raise ValueError("No valid search fields found in configuration")

        return UserSearchConfig(
            fuzziness=fuzziness,
            default_limit=default_limit,
            max_limit=max_limit,
            min_score=min_score,
            search_fields=search_fields
        )
    
    def reload_config(self) -> UserSearchConfig:
        """
        Force reload configuration from file.
        
        Returns:
            UserSearchConfig object
        """
        self._config = None
        return self.load_config()
    
    def get_config(self) -> UserSearchConfig:
        """
        Get current configuration (loads if not already loaded).
        
        Returns:
            UserSearchConfig object
        """
        return self.load_config()


# Singleton instance for easy access
_config_loader: Optional[ElasticsearchConfigLoader] = None


def get_config_loader(config_path: Optional[str] = None) -> ElasticsearchConfigLoader:
    """
    Get singleton configuration loader instance.
    
    Args:
        config_path: Optional custom path to configuration file
        
    Returns:
        ElasticsearchConfigLoader instance
    """
    global _config_loader
    if _config_loader is None:
        _config_loader = ElasticsearchConfigLoader(config_path)
    return _config_loader

