"""
@cross-cutting
@module polariPeers.module_fetcher
@tags @xc:bindings

Materialize module PROJECTS from their ModuleSourceConfig rows.

git/github: clone into modules/<name> (or fetch+checkout when already
cloned); the materialized commit SHA lands in fetched_version.
file: copy a local tree. peer: refused honestly — peer modules travel
as DATA BUNDLES through the existing module_loader flow, not as code
folders (the refusal says exactly that).

Never silent: every outcome updates the row (status/fetched_version/
last_error) and returns a report; fetch_suggestions() surfaces
configured-but-absent modules as evidence-bearing suggestions.
"""

import os
import shutil
import subprocess

MODULES_DIR_NAME = 'modules'


def _framework_root():
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _modules_dir():
    return os.path.join(_framework_root(), MODULES_DIR_NAME)


def _find_config(manager, name):
    table = (manager.objectTables or {}).get('ModuleSourceConfig', {})
    rows = table.values() if isinstance(table, dict) else table
    for row in rows:
        if getattr(row, 'name', '') == name:
            return row
    return None


def _run_git(args, cwd, timeout=300):
    result = subprocess.run(
        ['git'] + args, cwd=cwd, capture_output=True, text=True,
        timeout=timeout)
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or result.stdout.strip())
    return result.stdout.strip()


def _persist(manager, row):
    db = getattr(manager, 'db', None)
    if db is not None:
        try:
            db.saveInstanceInDB(row)
        except Exception:
            pass


def fetch_module_project(manager, name, modules_dir=None):
    """Materialize one configured module project. Returns
    {'ok', 'name', 'action' ('cloned'|'updated'|'copied'),
     'fetchedVersion', 'path'} or an honest refusal."""
    config = _find_config(manager, name)
    if config is None:
        return {'ok': False, 'name': name,
                'error': f"no ModuleSourceConfig named '{name}'"}
    modulesDir = modules_dir or _modules_dir()
    os.makedirs(modulesDir, exist_ok=True)
    targetPath = os.path.join(modulesDir, name)
    kind = config.source_kind

    try:
        if kind in ('git', 'github'):
            url = config.locator
            if kind == 'github' and '://' not in url:
                url = f'https://github.com/{url}.git'
            if os.path.isdir(os.path.join(targetPath, '.git')):
                _run_git(['fetch', '--all', '--tags'], cwd=targetPath)
                _run_git(['checkout', config.ref or 'HEAD'],
                         cwd=targetPath)
                if not config.ref:
                    # default branch: fast-forward to its remote state
                    _run_git(['pull', '--ff-only'], cwd=targetPath)
                action = 'updated'
            else:
                cloneArgs = ['clone', url, targetPath]
                if config.ref:
                    cloneArgs = ['clone', '--branch', config.ref,
                                 url, targetPath]
                _run_git(cloneArgs, cwd=modulesDir)
                action = 'cloned'
            version = _run_git(['rev-parse', 'HEAD'], cwd=targetPath)
        elif kind == 'file':
            source = config.locator
            if not os.path.isabs(source):
                source = os.path.join(_framework_root(), source)
            if not os.path.isdir(source):
                raise RuntimeError(f'source path not found: {source}')
            if os.path.abspath(source) != os.path.abspath(targetPath):
                if os.path.isdir(targetPath):
                    shutil.rmtree(targetPath)
                shutil.copytree(source, targetPath)
            action = 'copied'
            version = ''
        elif kind == 'peer':
            return {'ok': False, 'name': name,
                    'error': 'peer modules install as DATA BUNDLES via '
                             'POST /api/modules/install (module_loader), '
                             'not as code folders — use that flow.'}
        else:
            return {'ok': False, 'name': name,
                    'error': f"unknown source_kind '{kind}' "
                             "(git | github | file | peer)"}
    except Exception as e:
        config.status = 'error'
        config.last_error = str(e)[:500]
        _persist(manager, config)
        return {'ok': False, 'name': name, 'error': str(e)}

    config.status = 'fetched'
    config.fetched_version = version
    config.last_error = ''
    _persist(manager, config)
    return {'ok': True, 'name': name, 'action': action,
            'fetchedVersion': version, 'path': targetPath}


def project_statuses(manager, modules_dir=None):
    """Every configured project + whether its folder actually exists —
    the row's status is reconciled against the filesystem."""
    modulesDir = modules_dir or _modules_dir()
    table = (manager.objectTables or {}).get('ModuleSourceConfig', {})
    rows = table.values() if isinstance(table, dict) else list(table)
    statuses = []
    for row in rows:
        present = os.path.isdir(os.path.join(modulesDir, row.name))
        if present and row.status == 'absent':
            row.status = 'fetched'
        elif not present and row.status == 'fetched':
            row.status = 'absent'
        statuses.append({
            'name': row.name, 'sourceKind': row.source_kind,
            'locator': row.locator, 'ref': row.ref,
            'autoFetch': bool(row.auto_fetch), 'status': row.status,
            'fetchedVersion': row.fetched_version,
            'folderPresent': present, 'lastError': row.last_error,
        })
    return statuses


def fetch_suggestions(manager, modules_dir=None):
    """Evidence-bearing suggestions for configured-but-absent projects
    (never auto-applied — surfacing only)."""
    suggestions = []
    for status in project_statuses(manager, modules_dir):
        if status['folderPresent']:
            continue
        suggestions.append({
            'module': status['name'],
            'evidence': f"ModuleSourceConfig '{status['name']}' points at "
                        f"{status['sourceKind']}:{status['locator']} but "
                        f"modules/{status['name']} is not materialized.",
            'knob': 'POST /api/module-projects/fetch',
            'action': f'{{"name": "{status["name"]}"}} — or set '
                      f'auto_fetch on the config row.',
        })
    return suggestions


def auto_fetch_configured(manager, modules_dir=None):
    """Boot hook: fetch ONLY rows with the auto_fetch knob on. Absent
    rows without the knob become suggestions, never downloads."""
    results = []
    for status in project_statuses(manager, modules_dir):
        if status['autoFetch'] and not status['folderPresent']:
            results.append(fetch_module_project(
                manager, status['name'], modules_dir))
    return results
