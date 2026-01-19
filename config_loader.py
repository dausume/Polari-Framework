"""
Configuration Loader for Polari Framework

This module provides a clean interface to load and access configuration
with a tiered configuration system:

TIER 1 (Build-time):    config.yaml - Baked into image, base defaults
TIER 2 (Startup-time):  Environment variables - Override at container startup
TIER 3 (Runtime):       Runtime config dict - Can be changed via API while running

Priority: Runtime > Environment Variables > config.yaml

Usage:
    from config_loader import config

    # Access configuration values (respects tier priority)
    port = config.get('backend.port')
    db_type = config.get('database.type')
    in_docker = config.get('in_docker_container')

    # With default values
    log_level = config.get('logging.level', 'INFO')

    # Get entire sections
    backend_config = config.get_section('backend')

    # Runtime configuration (Tier 3)
    config.set_runtime('backend.port', 3001)  # Change port at runtime
    config.get_runtime('backend.port')        # Get runtime value
"""

import os
import yaml
import json
from pathlib import Path
from typing import Any, Dict, Optional, Callable, List
from threading import Lock


class ConfigLoader:
    """
    Configuration loader with tiered configuration support:
    - Tier 1: config.yaml (build-time defaults)
    - Tier 2: Environment variables (startup-time overrides)
    - Tier 3: Runtime config dict (can be changed while running)
    """

    # Mapping of config keys to environment variable names (Tier 2)
    ENV_VAR_MAPPING = {
        'backend.port': 'BACKEND_HTTP_PORT',
        'backend.url': 'BACKEND_URL',
        'backend.https_port': 'BACKEND_HTTPS_PORT',
        'ssl.enabled': 'SSL_ENABLED',
        'ssl.cert_path': 'SSL_CERT_PATH',
        'ssl.key_path': 'SSL_KEY_PATH',
        'ssl.https_port': 'BACKEND_HTTPS_PORT',
        'frontend.port': 'FRONTEND_HTTP_PORT',
        'frontend.url': 'FRONTEND_URL',
        'frontend.https_port': 'FRONTEND_HTTPS_PORT',
        'logging.level': 'LOG_LEVEL',
        'api.enable_cors': 'CORS_ENABLED',
        'api.cors_origins': 'CORS_ORIGINS',  # Comma-separated list of allowed origins
        'deploy_env': 'DEPLOY_ENV',
        'in_docker_container': 'IN_DOCKER_CONTAINER',
    }

    # Keys that can be modified at runtime (Tier 3)
    RUNTIME_CONFIGURABLE_KEYS = {
        'backend.port',
        'backend.url',
        'backend.https_port',
        'ssl.enabled',
        'logging.level',
        'api.enable_cors',
        'api.timeout',
        'connection.retry_interval',
        'connection.max_retry_time',
    }

    def __init__(self, config_file: str = 'config.yaml', environment: Optional[str] = None):
        """
        Initialize the configuration loader with tiered configuration support.

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

        # Tier 1: Load base configuration from YAML
        self._tier1_config = self._load_config()

        # Tier 3: Runtime configuration (starts empty)
        self._tier3_runtime = {}
        self._runtime_lock = Lock()

        # Callbacks for runtime config changes
        self._change_callbacks: List[Callable[[str, Any], None]] = []

        # Combined config (for backward compatibility)
        self._config = self._tier1_config

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
        Get a configuration value using dot notation with tier priority:
        Tier 3 (Runtime) > Tier 2 (Environment) > Tier 1 (YAML)

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
        # Tier 3: Check runtime configuration first
        with self._runtime_lock:
            if key in self._tier3_runtime:
                return self._tier3_runtime[key]

        # Tier 2: Check environment variables
        env_value = self._get_from_env(key)
        if env_value is not None:
            return env_value

        # Tier 1: Fall back to YAML configuration
        return self._get_from_yaml(key, default)

    def _get_from_env(self, key: str) -> Optional[Any]:
        """
        Get a configuration value from environment variables (Tier 2).

        Args:
            key: Configuration key in dot notation

        Returns:
            Environment variable value or None if not set
        """
        env_var = self.ENV_VAR_MAPPING.get(key)
        if env_var:
            value = os.environ.get(env_var)
            if value is not None:
                # Try to convert to appropriate type
                return self._convert_env_value(value)
        return None

    def _convert_env_value(self, value: str) -> Any:
        """
        Convert environment variable string to appropriate type.

        Args:
            value: String value from environment variable

        Returns:
            Converted value (bool, int, or string)
        """
        # Check for boolean
        if value.lower() in ('true', 'yes', 'on', '1'):
            return True
        if value.lower() in ('false', 'no', 'off', '0'):
            return False

        # Check for integer
        try:
            return int(value)
        except ValueError:
            pass

        # Return as string
        return value

    def _get_from_yaml(self, key: str, default: Any = None) -> Any:
        """
        Get a configuration value from YAML config (Tier 1).

        Args:
            key: Configuration key in dot notation
            default: Default value if key doesn't exist

        Returns:
            Configuration value or default
        """
        keys = key.split('.')
        value = self._tier1_config

        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default

        return value

    # =========================================================================
    # TIER 3: Runtime Configuration Methods
    # =========================================================================

    def set_runtime(self, key: str, value: Any) -> bool:
        """
        Set a runtime configuration value (Tier 3).
        Only keys in RUNTIME_CONFIGURABLE_KEYS can be modified.

        Args:
            key: Configuration key in dot notation
            value: New value to set

        Returns:
            True if set successfully, False if key is not runtime-configurable
        """
        if key not in self.RUNTIME_CONFIGURABLE_KEYS:
            print(f"[Config] Warning: Key '{key}' is not runtime-configurable")
            return False

        with self._runtime_lock:
            old_value = self._tier3_runtime.get(key)
            self._tier3_runtime[key] = value
            print(f"[Config] Runtime config updated: {key} = {value}")

        # Notify callbacks
        for callback in self._change_callbacks:
            try:
                callback(key, value)
            except Exception as e:
                print(f"[Config] Callback error: {e}")

        return True

    def get_runtime(self, key: str) -> Optional[Any]:
        """
        Get a runtime configuration value (Tier 3 only).

        Args:
            key: Configuration key in dot notation

        Returns:
            Runtime value or None if not set at runtime
        """
        with self._runtime_lock:
            return self._tier3_runtime.get(key)

    def clear_runtime(self, key: str = None) -> None:
        """
        Clear runtime configuration.

        Args:
            key: Specific key to clear, or None to clear all
        """
        with self._runtime_lock:
            if key:
                self._tier3_runtime.pop(key, None)
            else:
                self._tier3_runtime.clear()

    def on_config_change(self, callback: Callable[[str, Any], None]) -> None:
        """
        Register a callback for runtime configuration changes.

        Args:
            callback: Function to call with (key, new_value) when config changes
        """
        self._change_callbacks.append(callback)

    def get_config_tier(self, key: str) -> str:
        """
        Determine which tier a configuration value comes from.

        Args:
            key: Configuration key in dot notation

        Returns:
            'tier3_runtime', 'tier2_env', 'tier1_yaml', or 'default'
        """
        with self._runtime_lock:
            if key in self._tier3_runtime:
                return 'tier3_runtime'

        if self._get_from_env(key) is not None:
            return 'tier2_env'

        if self._get_from_yaml(key) is not None:
            return 'tier1_yaml'

        return 'default'

    def get_all_tiers(self, key: str) -> Dict[str, Any]:
        """
        Get a configuration value from all tiers for debugging.

        Args:
            key: Configuration key in dot notation

        Returns:
            Dictionary with values from each tier
        """
        return {
            'tier1_yaml': self._get_from_yaml(key),
            'tier2_env': self._get_from_env(key),
            'tier3_runtime': self.get_runtime(key),
            'effective': self.get(key)
        }

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
    # Test the tiered configuration loader
    print("=" * 70)
    print("TIERED CONFIGURATION LOADER TEST")
    print("=" * 70)
    print(f"\nEnvironment: {config.environment}")
    print(f"In Docker: {config.in_docker}")

    print("\n" + "-" * 70)
    print("TIER 1 (Build-time - config.yaml):")
    print("-" * 70)
    print(f"  Backend Port: {config._get_from_yaml('backend.port')}")
    print(f"  Database Type: {config._get_from_yaml('database.type')}")
    print(f"  Logging Level: {config._get_from_yaml('logging.level')}")

    print("\n" + "-" * 70)
    print("TIER 2 (Startup-time - Environment Variables):")
    print("-" * 70)
    print(f"  BACKEND_HTTP_PORT env: {os.environ.get('BACKEND_HTTP_PORT', 'not set')}")
    print(f"  LOG_LEVEL env: {os.environ.get('LOG_LEVEL', 'not set')}")

    print("\n" + "-" * 70)
    print("TIER 3 (Runtime - Configurable):")
    print("-" * 70)
    print(f"  Runtime configurable keys: {config.RUNTIME_CONFIGURABLE_KEYS}")

    print("\n" + "-" * 70)
    print("EFFECTIVE VALUES (respects tier priority):")
    print("-" * 70)
    print(f"  Backend Port: {config.get('backend.port')} (from: {config.get_config_tier('backend.port')})")
    print(f"  Logging Level: {config.get('logging.level')} (from: {config.get_config_tier('logging.level')})")

    # Demonstrate runtime configuration
    print("\n" + "-" * 70)
    print("RUNTIME CONFIGURATION DEMO:")
    print("-" * 70)
    print(f"  Setting backend.port to 3001 at runtime...")
    config.set_runtime('backend.port', 3001)
    print(f"  Backend Port now: {config.get('backend.port')} (from: {config.get_config_tier('backend.port')})")
    print(f"  All tiers for backend.port: {config.get_all_tiers('backend.port')}")

    print("\n" + "=" * 70)
