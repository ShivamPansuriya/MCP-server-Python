"""
Configuration Loader

Loads and parses XML configuration into type-safe dataclass models.
"""

import logging
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Dict, Optional

from elasticsearch_search_lib.models import EntityConfig, FieldConfig
from elasticsearch_search_lib.exceptions import ConfigurationError

logger = logging.getLogger(__name__)


class ConfigLoader:
    """
    Loads entity configurations from XML file.
    
    Parses XML configuration and creates EntityConfig and FieldConfig
    dataclass instances for type-safe access.
    """
    
    def __init__(self, config_path: Optional[str] = None):
        """
        Initialize configuration loader.
        
        Args:
            config_path: Path to XML configuration file.
                        If None, uses default path relative to this module.
        """
        if config_path is None:
            # Default to search_config.xml in same directory as this module
            config_dir = Path(__file__).parent
            config_path = str(config_dir / "search_config.xml")
        
        self.config_path = config_path
        self._configs: Optional[Dict[str, EntityConfig]] = None
        
    def load(self) -> Dict[str, EntityConfig]:
        """
        Load all entity configurations from XML.
        
        Returns:
            Dictionary mapping entity type to EntityConfig
            
        Raises:
            ConfigurationError: If configuration file is invalid or not found
        """
        if self._configs is not None:
            return self._configs
        
        try:
            config_file = Path(self.config_path)
            if not config_file.exists():
                raise ConfigurationError(f"Configuration file not found: {self.config_path}")
            
            logger.info(f"Loading configuration from {self.config_path}")
            tree = ET.parse(config_file)
            root = tree.getroot()
            
            configs = {}
            entities_elem = root.find('entities')
            
            if entities_elem is None:
                raise ConfigurationError("No <entities> element found in configuration")
            
            for entity_elem in entities_elem.findall('entity'):
                entity_type = entity_elem.get('type')
                if not entity_type:
                    logger.warning("Skipping entity without 'type' attribute")
                    continue
                
                try:
                    config = self._parse_entity(entity_elem, entity_type)
                    configs[entity_type] = config
                except Exception as e:
                    raise ConfigurationError(
                        f"Failed to parse configuration for entity '{entity_type}': {e}"
                    )
            
            if not configs:
                raise ConfigurationError("No valid entity configurations found")
            
            self._configs = configs
            logger.info(f"Loaded configuration for {len(configs)} entity types")
            return configs
            
        except ET.ParseError as e:
            raise ConfigurationError(f"Invalid XML syntax in {self.config_path}: {e}")
        except Exception as e:
            if isinstance(e, ConfigurationError):
                raise
            raise ConfigurationError(f"Failed to load configuration: {e}")
    
    def _parse_entity(self, entity_elem: ET.Element, entity_type: str) -> EntityConfig:
        """Parse a single entity configuration."""
        # Parse entity-level settings
        fuzziness = self._get_text(entity_elem, 'fuzziness', 'AUTO')
        default_limit = int(self._get_text(entity_elem, 'defaultLimit', '10'))
        max_limit = int(self._get_text(entity_elem, 'maxLimit', '100'))
        min_score = float(self._get_text(entity_elem, 'minScore', '0.0'))
        
        # Parse fields
        fields = []
        fields_elem = entity_elem.find('fields')
        if fields_elem is not None:
            for field_elem in fields_elem.findall('field'):
                field = self._parse_field(field_elem, fuzziness)
                fields.append(field)
        
        return EntityConfig(
            entity_type=entity_type,
            fuzziness=fuzziness,
            default_limit=default_limit,
            max_limit=max_limit,
            min_score=min_score,
            fields=fields,
        )
    
    def _parse_field(self, field_elem: ET.Element, entity_fuzziness: str) -> FieldConfig:
        """Parse a single field configuration."""
        name = self._get_text(field_elem, 'name', required=True)
        boost = float(self._get_text(field_elem, 'boost', '1.0'))
        enabled = self._get_text(field_elem, 'enabled', 'true').lower() == 'true'
        fuzziness = self._get_text(field_elem, 'fuzziness', entity_fuzziness)
        
        # Convert fuzziness to int if it's a numeric string
        if fuzziness.isdigit():
            fuzziness = int(fuzziness)
        
        return FieldConfig(
            name=name,
            boost=boost,
            enabled=enabled,
            fuzziness=fuzziness,
        )
    
    def _get_text(
        self,
        parent: ET.Element,
        tag: str,
        default: Optional[str] = None,
        required: bool = False
    ) -> str:
        """Get text content of a child element."""
        elem = parent.find(tag)
        if elem is not None and elem.text:
            return elem.text.strip()
        
        if required:
            raise ConfigurationError(f"Required element <{tag}> not found or empty")
        
        return default
    
    def get_entity_config(self, entity_type: str) -> EntityConfig:
        """
        Get configuration for a specific entity type.
        
        Args:
            entity_type: Entity type name
            
        Returns:
            EntityConfig for the entity
            
        Raises:
            ConfigurationError: If configuration not loaded
            EntityNotFoundError: If entity type not found
        """
        from elasticsearch_search_lib.exceptions import EntityNotFoundError
        
        configs = self.load()
        
        if entity_type not in configs:
            raise EntityNotFoundError(entity_type, list(configs.keys()))
        
        return configs[entity_type]
    
    def get_supported_entities(self) -> list[str]:
        """
        Get list of all supported entity types.
        
        Returns:
            List of entity type names
        """
        configs = self.load()
        return list(configs.keys())
    
    def is_entity_supported(self, entity_type: str) -> bool:
        """
        Check if an entity type is supported.
        
        Args:
            entity_type: Entity type name
            
        Returns:
            True if entity is supported
        """
        configs = self.load()
        return entity_type in configs

