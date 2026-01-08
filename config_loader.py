"""
Configuration Loader for Polari Framework

This module provides a clean interface to load and access configuration
from config.yaml. It handles environment-specific overrides and provides
convenient access to configuration values.

Usage:
    from config_loader import config

    # Access configuration values
    port = config.get('backend.port')
    db_type = config.get('database.type')
    in_docker = config.get('in_docker_container')

    # With default values
    log_level = config.get('logging.level', 'INFO')

    # Get entire sections
    backend_config = config.get_section('backend')
"""

import os
import yaml
from pathlib import Path
from typing import Any, Dict, Optional


class ConfigLoader:
    """
    Configuration loader that reads from config.yaml and provides
    convenient access to configuration values.
    """

    def __init__(self, config_file: str = 'config.yaml', environment: Optional[str] = None):
        """
        Initialize the configuration loader.

        Args:
            config_file: Path to the YAML configuration file
            environment: Environment name (development, production, testing)
                        If None, uses DEPLOY_ENV environment variable or defaults to 'development'
        """
        self.config_path = Path(__file__).parent / config_file

        # Determine environment
        self.environment = environment or os.environ.get('DEPLOY_ENV', 'development')

        # Check if running in Docker
        self.in_docker = self._check_docker_environment()

        # Load configuration
        self._config = self._load_config()

    def _check_docker_environment(self) -> bool:
        """
        Check if the application is running inside a Docker container.

        Returns:
            True if running in Docker, False otherwise
        """
        # Check environment variable
        in_docker_env = os.environ.get('IN_DOCKER_CONTAINER', '').lower()
        if in_docker_env == 'true':
            return True

        # Check for .dockerenv file (another indicator)
        if Path('/.dockerenv').exists():
            return True

        return False

    def _merge_dict(self, base: Dict, override: Dict) -> Dict:
        """
        Recursively merge override dict into base dict.

        Args:
            base: Base dictionary
            override: Dictionary with override values

        Returns:
            Merged dictionary
        """
        result = base.copy()
        for key, value in override.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = self._merge_dict(result[key], value)
            else:
                result[key] = value
        return result

    def _load_config(self) -> Dict[str, Any]:
        """
        Load configuration from YAML file with environment-specific overrides.

        Returns:
            Configuration dictionary

        Raises:
            FileNotFoundError: If config file doesn't exist
            yaml.YAMLError: If config file is invalid YAML
        """
        if not self.config_path.exists():
            raise FileNotFoundError(f"Configuration file not found: {self.config_path}")

        with open(self.config_path, 'r') as f:
            config = yaml.safe_load(f)

        # Merge shared and application sections into a flat structure
        merged_config = {}

        # Add shared configuration at top level
        if 'shared' in config:
            merged_config.update(config['shared'])

        # Add application configuration at top level
        if 'application' in config:
            merged_config.update(config['application'])

        # Apply environment-specific overrides
        if 'environments' in config and self.environment in config['environments']:
            env_overrides = config['environments'][self.environment]

            # Merge shared overrides
            if 'shared' in env_overrides:
                merged_config = self._merge_dict(merged_config, env_overrides['shared'])

            # Merge application overrides
            if 'application' in env_overrides:
                merged_config = self._merge_dict(merged_config, env_overrides['application'])

        return merged_config

    def get(self, key: str, default: Any = None) -> Any:
        """
        Get a configuration value using dot notation.

        Args:
            key: Configuration key in dot notation (e.g., 'backend.port')
            default: Default value if key doesn't exist

        Returns:
            Configuration value or default

        Examples:
            >>> config.get('backend.port')
            3000
            >>> config.get('database.type')
            'sqlite'
            >>> config.get('nonexistent.key', 'default_value')
            'default_value'
        """
        keys = key.split('.')
        value = self._config

        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default

        return value

    def get_section(self, section: str) -> Dict[str, Any]:
        """
        Get an entire configuration section.

        Args:
            section: Section name (e.g., 'backend', 'database')

        Returns:
            Dictionary containing the section configuration

        Examples:
            >>> config.get_section('backend')
            {'port': 3000, 'url': 'localhost'}
        """
        return self.get(section, {})

    def get_int(self, key: str, default: int = 0) -> int:
        """
        Get a configuration value as an integer.

        Args:
            key: Configuration key in dot notation
            default: Default value if key doesn't exist

        Returns:
            Configuration value as integer
        """
        value = self.get(key, default)
        try:
            return int(value)
        except (ValueError, TypeError):
            return default

    def get_bool(self, key: str, default: bool = False) -> bool:
        """
        Get a configuration value as a boolean.

        Args:
            key: Configuration key in dot notation
            default: Default value if key doesn't exist

        Returns:
            Configuration value as boolean
        """
        value = self.get(key, default)
        if isinstance(value, bool):
            return value
        if isinstance(value, str):
            return value.lower() in ('true', '1', 'yes', 'on')
        return bool(value)

    def get_string(self, key: str, default: str = '') -> str:
        """
        Get a configuration value as a string.

        Args:
            key: Configuration key in dot notation
            default: Default value if key doesn't exist

        Returns:
            Configuration value as string
        """
        value = self.get(key, default)
        return str(value) if value is not None else default

    def reload(self) -> None:
        """
        Reload configuration from file.

        Useful for development when configuration changes without restarting.
        """
        self._config = self._load_config()

    @property
    def all(self) -> Dict[str, Any]:
        """
        Get all configuration as a dictionary.

        Returns:
            Complete configuration dictionary
        """
        return self._config.copy()

    def __repr__(self) -> str:
        """String representation of the config loader."""
        return f"ConfigLoader(environment='{self.environment}', in_docker={self.in_docker})"


# Global configuration instance
# Import this in your modules: from config_loader import config
config = ConfigLoader()


# Convenience functions for backward compatibility
def get_config(key: str, default: Any = None) -> Any:
    """
    Get a configuration value (convenience function).

    Args:
        key: Configuration key in dot notation
        default: Default value if key doesn't exist

    Returns:
        Configuration value or default
    """
    return config.get(key, default)


def get_backend_port() -> int:
    """
    Get the backend server port.

    Returns:
        Backend port number (defaults to 3000)
    """
    # Check environment variable first (for backward compatibility)
    env_port = os.environ.get("BACKEND_APP_PORT")
    if env_port:
        try:
            return int(env_port)
        except ValueError:
            pass

    # Fall back to configuration
    return config.get_int('backend.port', 3000)


def is_in_docker() -> bool:
    """
    Check if running inside Docker container.

    Returns:
        True if running in Docker, False otherwise
    """
    return config.in_docker


if __name__ == '__main__':
    # Test the configuration loader
    print(f"Configuration Loader Test")
    print(f"=" * 60)
    print(f"Environment: {config.environment}")
    print(f"In Docker: {config.in_docker}")
    print(f"Backend Port: {config.get_int('backend.port')}")
    print(f"Database Type: {config.get('database.type')}")
    print(f"Logging Level: {config.get('logging.level')}")
    print(f"=" * 60)
