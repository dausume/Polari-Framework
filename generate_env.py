#!/usr/bin/env python3
"""
Generate .env file from config.yaml

This script reads the config.yaml file and generates a .env file
that can be used by Docker Compose and the Dockerfile.

Usage:
    python generate_env.py [environment]

Arguments:
    environment: Optional environment name (development, production, testing)
                 Defaults to 'development'

The .env file is generated for Docker Compose compatibility and contains
variables from the 'shared' section of config.yaml.
"""

import sys
import yaml
from pathlib import Path
from typing import Dict, Any


def merge_dict(base: Dict, override: Dict) -> Dict:
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
            result[key] = merge_dict(result[key], value)
        else:
            result[key] = value
    return result


def load_config(env: str = 'development') -> Dict[str, Any]:
    """
    Load configuration from config.yaml with environment-specific overrides.

    Args:
        env: Environment name (development, production, testing)

    Returns:
        Configuration dictionary
    """
    config_path = Path(__file__).parent / 'config.yaml'

    if not config_path.exists():
        raise FileNotFoundError(f"Configuration file not found: {config_path}")

    with open(config_path, 'r') as f:
        config = yaml.safe_load(f)

    # Apply environment-specific overrides
    if 'environments' in config and env in config['environments']:
        env_overrides = config['environments'][env]

        # Merge overrides into shared and application sections
        if 'shared' in env_overrides:
            config['shared'] = merge_dict(config.get('shared', {}), env_overrides['shared'])
        if 'application' in env_overrides:
            config['application'] = merge_dict(config.get('application', {}), env_overrides['application'])
        if 'dockerfile' in env_overrides:
            config['dockerfile'] = merge_dict(config.get('dockerfile', {}), env_overrides['dockerfile'])

    return config


def generate_env_file(config: Dict[str, Any], output_path: Path) -> None:
    """
    Generate .env file from configuration.

    Args:
        config: Configuration dictionary from YAML
        output_path: Path where .env file should be written
    """
    lines = [
        "# AUTO-GENERATED FILE - DO NOT EDIT DIRECTLY",
        "# This file is generated from config.yaml",
        "# To make changes, edit config.yaml and run: python generate_env.py",
        "",
        "# General Configuration",
    ]

    # Extract shared configuration
    shared = config.get('shared', {})

    # General settings
    in_docker = shared.get('in_docker_container', True)
    deploy_env = shared.get('deploy_env', 'development')

    lines.append(f"IN_DOCKER_CONTAINER={str(in_docker).lower()}")
    lines.append(f"DEPLOY_ENV={deploy_env}")
    lines.append("")

    # Backend configuration
    lines.append("# Backend Configurations and Defaults")
    backend = shared.get('backend', {})
    backend_url = backend.get('url', 'localhost')
    backend_port = backend.get('port', 3000)

    lines.append(f"BACKEND_URL={backend_url}")
    lines.append(f"BACKEND_LOCALHOST_PORT={backend_port}")
    lines.append(f"BACKEND_CONTAINER_PORT={backend_port}")

    # Database configuration (from application section for docker-compose if needed)
    app_config = config.get('application', {})
    db_config = app_config.get('database', {})
    db_type = db_config.get('type', 'sqlite')
    lines.append(f"BACKEND_DB={db_type}")
    lines.append("")

    # Frontend configuration
    lines.append("# Frontend Configuration Variables and Defaults")
    frontend = shared.get('frontend', {})
    frontend_url = frontend.get('url', 'localhost')
    frontend_port_local = frontend.get('port_local', 4200)
    frontend_port_container = frontend.get('port_container', 4200)

    lines.append(f"FRONTEND_URL={frontend_url}")
    lines.append(f"FRONTEND_LOCALHOST_PORT={frontend_port_local}")
    lines.append(f"FRONTEND_CONTAINER_PORT={frontend_port_container}")
    lines.append("")

    # Dockerfile-specific variables (for ARG in Dockerfile if needed)
    dockerfile_config = config.get('dockerfile', {})
    freetype = dockerfile_config.get('freetype', {})
    if freetype:
        lines.append("# Dockerfile Build Configuration")
        lines.append(f"FREETYPE_VERSION={freetype.get('version', '2.6.1')}")
        lines.append(f"FREETYPE_DIR={freetype.get('build_dir', '/build/freetype-2.6.1')}")

    # Write to file
    with open(output_path, 'w') as f:
        f.write('\n'.join(lines))
        f.write('\n')  # End with newline

    print(f"✓ Generated .env file: {output_path}")
    print(f"  Environment: {deploy_env}")
    print(f"  Backend Port: {backend_port}")
    print(f"  Frontend Port: {frontend_port_local}")


def main():
    """Main entry point for the script."""
    # Get environment from command line or default to 'development'
    env = sys.argv[1] if len(sys.argv) > 1 else 'development'

    print(f"Generating .env file for environment: {env}")
    print("-" * 50)

    try:
        # Load configuration with environment overrides
        config = load_config(env)

        # Generate .env file in the same directory as this script
        output_path = Path(__file__).parent / '.env'
        generate_env_file(config, output_path)

        print("-" * 50)
        print("✓ Success! .env file has been generated")
        print("")
        print("You can now run:")
        print("  docker-compose build")
        print("  docker-compose up")

    except FileNotFoundError as e:
        print(f"✗ Error: {e}", file=sys.stderr)
        sys.exit(1)
    except yaml.YAMLError as e:
        print(f"✗ Error parsing config.yaml: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"✗ Unexpected error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()
