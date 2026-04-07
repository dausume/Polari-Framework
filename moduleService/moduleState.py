"""
Module State Persistence

Persists module enabled/disabled state to a JSON file so that
module configuration survives server restarts.

State file location: ./data/module_state.json (inside the Docker volume)
"""

import os
import json
from datetime import datetime, timezone


def _get_state_file_path():
    """Get the path to the module state file."""
    framework_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    data_dir = os.path.join(framework_root, 'data')
    os.makedirs(data_dir, exist_ok=True)
    return os.path.join(data_dir, 'module_state.json')


def load_module_state():
    """Load persisted module state from disk.

    Returns:
        dict: {module_id: {'enabled': bool, 'last_toggled': str}} or empty dict
    """
    path = _get_state_file_path()
    if not os.path.isfile(path):
        return {}

    try:
        with open(path, 'r') as f:
            data = json.load(f)
        return data.get('modules', {})
    except Exception as e:
        print(f"[ModuleState] Warning: Could not read {path}: {e}")
        return {}


def save_module_state(module_id, enabled):
    """Persist the enabled/disabled state of a single module.

    Updates only the specified module's entry, preserving others.

    Args:
        module_id: The module identifier (e.g. 'materials_science')
        enabled: Whether the module is enabled
    """
    path = _get_state_file_path()

    # Load existing state
    existing = {}
    if os.path.isfile(path):
        try:
            with open(path, 'r') as f:
                existing = json.load(f)
        except Exception:
            existing = {}

    if 'modules' not in existing:
        existing['modules'] = {}

    existing['modules'][module_id] = {
        'enabled': bool(enabled),
        'last_toggled': datetime.now(timezone.utc).isoformat(),
    }
    existing['version'] = 1
    existing['last_updated'] = datetime.now(timezone.utc).isoformat()

    try:
        with open(path, 'w') as f:
            json.dump(existing, f, indent=2)
        print(f"[ModuleState] Saved: {module_id} enabled={enabled}")
    except Exception as e:
        print(f"[ModuleState] Warning: Could not write {path}: {e}")


def get_module_enabled(module_id, fallback=None):
    """Check if a module is enabled in persisted state.

    Args:
        module_id: The module identifier
        fallback: Value to return if no persisted state exists (None means 'not set')

    Returns:
        True/False if state exists, fallback otherwise
    """
    state = load_module_state()
    entry = state.get(module_id)
    if entry is not None and 'enabled' in entry:
        return entry['enabled']
    return fallback
