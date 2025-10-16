"""
Configuration management for tools.

This module handles loading and managing tool configurations from YAML files
and environment variables.
"""

import os
import yaml
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field
from pathlib import Path
import logging
from dotenv import load_dotenv

logger = logging.getLogger(__name__)


@dataclass
class ToolConfig:
    """Configuration for a single tool."""
    name: str
    type: str
    enabled: bool = True
    config: Dict[str, Any] = field(default_factory=dict)
    category: str = "general"
    
    def get_env_value(self, key: str, default: Any = None) -> Any:
        """
        Get configuration value with environment variable override.
        
        Args:
            key: Configuration key
            default: Default value if not found
            
        Returns:
            Configuration value
        """
        # Check environment variable first (with tool name prefix)
        env_key = f"{self.name.upper()}_{key.upper()}"
        env_value = os.getenv(env_key)
        
        if env_value is not None:
            # Try to convert to appropriate type
            if isinstance(default, bool):
                return env_value.lower() in ('true', '1', 'yes', 'on')
            elif isinstance(default, int):
                try:
                    return int(env_value)
                except ValueError:
                    pass
            elif isinstance(default, float):
                try:
                    return float(env_value)
                except ValueError:
                    pass
            return env_value
        
        # Fall back to config value
        return self.config.get(key, default)


class ToolsConfigManager:
    """Manager for loading and managing tool configurations."""
    
    def __init__(self, config_dir: str = None):
        """
        Initialize the configuration manager.
        
        Args:
            config_dir: Directory containing configuration files
        """
        self.config_dir = Path(config_dir) if config_dir else Path.cwd() / "config"
        self.tools_config: Dict[str, ToolConfig] = {}
        
        # Load environment variables
        load_dotenv()
        
    def load_config(self, config_file: str = "tools.yaml") -> Dict[str, ToolConfig]:
        """
        Load tool configurations from YAML file.
        
        Args:
            config_file: Name of the configuration file
            
        Returns:
            Dictionary of tool configurations
        """
        config_path = self.config_dir / config_file
        
        if not config_path.exists():
            logger.warning(f"Configuration file not found: {config_path}")
            return self._load_default_config()
        
        try:
            with open(config_path, 'r') as f:
                config_data = yaml.safe_load(f)
            
            self.tools_config = {}
            
            # Parse tools configuration
            tools_section = config_data.get('tools', {})
            
            for tool_name, tool_data in tools_section.items():
                tool_config = ToolConfig(
                    name=tool_name,
                    type=tool_data.get('type', 'unknown'),
                    enabled=tool_data.get('enabled', True),
                    config=tool_data.get('config', {}),
                    category=tool_data.get('category', 'general')
                )
                self.tools_config[tool_name] = tool_config
            
            logger.info(f"Loaded {len(self.tools_config)} tool configurations from {config_path}")
            return self.tools_config
            
        except Exception as e:
            logger.error(f"Error loading configuration from {config_path}: {e}")
            return self._load_default_config()
    
    def _load_default_config(self) -> Dict[str, ToolConfig]:
        """Load default configuration when no config file is found."""
        logger.info("Loading default tool configuration")
        
        default_tools = {
            'openai': ToolConfig(
                name='openai',
                type='llm',
                enabled=bool(os.getenv('OPENAI_API_KEY')),
                config={
                    'api_key': os.getenv('OPENAI_API_KEY'),
                    'model': os.getenv('OPENAI_MODEL', 'gpt-3.5-turbo'),
                    'max_tokens': int(os.getenv('OPENAI_MAX_TOKENS', '1000')),
                    'temperature': float(os.getenv('OPENAI_TEMPERATURE', '0.7'))
                },
                category='llm'
            ),
            'gemini': ToolConfig(
                name='gemini',
                type='llm',
                enabled=bool(os.getenv('GEMINI_API_KEY')),
                config={
                    'api_key': os.getenv('GEMINI_API_KEY'),
                    'model': os.getenv('GEMINI_MODEL', 'gemini-pro'),
                    'max_tokens': int(os.getenv('GEMINI_MAX_TOKENS', '1000')),
                    'temperature': float(os.getenv('GEMINI_TEMPERATURE', '0.7'))
                },
                category='llm'
            ),
            'postgresql': ToolConfig(
                name='postgresql',
                type='database',
                enabled=bool(os.getenv('POSTGRES_URL')),
                config={
                    'url': os.getenv('POSTGRES_URL'),
                    'host': os.getenv('POSTGRES_HOST', 'localhost'),
                    'port': int(os.getenv('POSTGRES_PORT', '5432')),
                    'database': os.getenv('POSTGRES_DB'),
                    'username': os.getenv('POSTGRES_USER'),
                    'password': os.getenv('POSTGRES_PASSWORD'),
                    'pool_size': int(os.getenv('POSTGRES_POOL_SIZE', '10'))
                },
                category='database'
            ),
            'neo4j': ToolConfig(
                name='neo4j',
                type='database',
                enabled=bool(os.getenv('NEO4J_URI')),
                config={
                    'uri': os.getenv('NEO4J_URI'),
                    'username': os.getenv('NEO4J_USER'),
                    'password': os.getenv('NEO4J_PASSWORD'),
                    'database': os.getenv('NEO4J_DATABASE', 'neo4j')
                },
                category='database'
            )
        }
        
        self.tools_config = default_tools
        return default_tools
    
    def get_tool_config(self, tool_name: str) -> Optional[ToolConfig]:
        """
        Get configuration for a specific tool.
        
        Args:
            tool_name: Name of the tool
            
        Returns:
            ToolConfig or None if not found
        """
        return self.tools_config.get(tool_name)
    
    def list_enabled_tools(self) -> List[str]:
        """
        List all enabled tools.
        
        Returns:
            List of enabled tool names
        """
        return [name for name, config in self.tools_config.items() if config.enabled]
    
    def get_tools_by_category(self, category: str) -> List[ToolConfig]:
        """
        Get all tools in a specific category.
        
        Args:
            category: Category name
            
        Returns:
            List of ToolConfig objects
        """
        return [config for config in self.tools_config.values() if config.category == category]
    
    def save_config(self, config_file: str = "tools.yaml") -> None:
        """
        Save current configuration to YAML file.
        
        Args:
            config_file: Name of the configuration file
        """
        config_path = self.config_dir / config_file
        
        # Ensure config directory exists
        config_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Convert to YAML format
        config_data = {
            'tools': {
                name: {
                    'type': config.type,
                    'enabled': config.enabled,
                    'category': config.category,
                    'config': config.config
                }
                for name, config in self.tools_config.items()
            }
        }
        
        try:
            with open(config_path, 'w') as f:
                yaml.dump(config_data, f, default_flow_style=False, indent=2)
            
            logger.info(f"Saved configuration to {config_path}")
            
        except Exception as e:
            logger.error(f"Error saving configuration to {config_path}: {e}")


# Global configuration manager
_config_manager = ToolsConfigManager()


def load_tools_config(config_dir: str = None, config_file: str = "tools.yaml") -> Dict[str, ToolConfig]:
    """
    Load tools configuration from file.
    
    Args:
        config_dir: Directory containing configuration files
        config_file: Name of the configuration file
        
    Returns:
        Dictionary of tool configurations
    """
    global _config_manager
    
    if config_dir:
        _config_manager = ToolsConfigManager(config_dir)
    
    return _config_manager.load_config(config_file)


def get_tool_config(tool_name: str) -> Optional[ToolConfig]:
    """
    Get configuration for a specific tool.
    
    Args:
        tool_name: Name of the tool
        
    Returns:
        ToolConfig or None if not found
    """
    return _config_manager.get_tool_config(tool_name)


def get_config_manager() -> ToolsConfigManager:
    """Get the global configuration manager."""
    return _config_manager