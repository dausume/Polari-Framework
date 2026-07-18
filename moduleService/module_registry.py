"""
@module moduleService.module_registry

The module REGISTER (mp-1, MODULE_PROJECTS_PLAN): a small
inspectable JSON in modules/polari-modules.json listing every known
module — kind official | vendor | self — with a `downloaded` flag
that is re-derived from the filesystem on every read (the file can
never lie about what is locally present) and a `repo` field that
becomes the module's own git remote when it splits into a
sub-project (mp-2).

Self modules: user-created modules (Create Module / createClassAPI
custom objects) register here with kind 'self' — making your own
module is the same shape as using an official one.

@consumers
  - polariApiServer.modulesAPI (GET /modules/registry, create flow)
  - polari-cli scripts/modules.sh (registry | get | drop)
  - moduleService.selftest_module_registry
"""

import json
import os

REGISTRY_SCHEMA_VERSION = '1'
MODULE_KINDS = ('official', 'vendor', 'self')


def _framework_root():
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def registry_path(root=None):
    return os.path.join(root or _framework_root(), 'modules',
                        'polari-modules.json')


def load_registry(root=None):
    """The registry document, downloaded flags freshly re-derived
    from the filesystem. Missing/corrupt file → honest empty doc."""
    root = root or _framework_root()
    path = registry_path(root)
    try:
        with open(path, encoding='utf-8') as f:
            doc = json.load(f)
    except (OSError, ValueError):
        doc = {'schema_version': REGISTRY_SCHEMA_VERSION,
               'note': '', 'modules': {}}
    if not isinstance(doc.get('modules'), dict):
        doc['modules'] = {}
    for name, entry in doc['modules'].items():
        if not isinstance(entry, dict):
            continue
        module_path = entry.get('path', f'modules/{name}')
        entry['downloaded'] = os.path.isdir(
            os.path.join(root, module_path))
    return doc


def save_registry(doc, root=None):
    path = registry_path(root)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(doc, f, indent=2)
        f.write('\n')
    return path


def register_module(name, kind, description='', path='', repo='',
                    root=None):
    """Add/update one entry (self modules use kind='self'). Returns
    the fresh entry; refuses unknown kinds honestly."""
    if kind not in MODULE_KINDS:
        return {'ok': False,
                'error': f'kind "{kind}" not one of {MODULE_KINDS}'}
    doc = load_registry(root)
    entry = doc['modules'].get(name, {})
    entry.update({
        'kind': kind,
        'path': path or entry.get('path', f'modules/{name}'),
        'repo': repo or entry.get('repo', ''),
        'description': description or entry.get('description', ''),
    })
    entry['downloaded'] = os.path.isdir(os.path.join(
        root or _framework_root(), entry['path']))
    doc['modules'][name] = entry
    save_registry(doc, root)
    return {'ok': True, 'name': name, 'entry': entry}
