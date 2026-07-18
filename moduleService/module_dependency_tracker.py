"""
@module moduleService.module_dependency_tracker

Dependency tracking across BOTH worlds (msci-21, Dustin's directive):

  - REAL PYTHON LIBRARIES: what each boundary/module imports (via the
    existing scan_python_imports), expanded into full requires-trees
    through importlib.metadata — with SHARED downstream dependencies
    computed ONCE and marked, so the tree is honest about what would
    and would not be duplicated by an install.
  - POLARI BOUNDARIES/MODULES: the framework's top-level packages are
    DECLARED BOUNDARIES (materials, models/simulations, no-code, …);
    cross-boundary imports are scanned as boundary EDGES, and
    modules/polari*Module code-modules keep their existing
    detect_cross_module_dependencies edges.

Install planning honors [[knobs-and-suggestions]]: `plan_install`
returns the UNION of missing packages as a SUGGESTION (deduplicated —
one resolver run installs shared downstream deps exactly once);
`install_packages` executes only on explicit confirmation and reports
honestly, including that a runtime install lives only until the image
is rebuilt (requirements.txt is the durable home).
"""

import os
import re
import subprocess
import sys
from importlib import metadata as importlib_metadata
from typing import Any, Dict, List, Optional, Set

from moduleService.moduleDiscovery import scan_python_imports

# ---------------------------------------------------------------------
# Declared framework boundaries — the coherent-module map at the
# material / model / engine / no-code / … seams. Each entry is a
# boundary NODE; cross-boundary imports are the tracked EDGES.
# ---------------------------------------------------------------------
FRAMEWORK_BOUNDARIES: Dict[str, str] = {
    'materialsScience': 'Materials: identities, scale levels, '
                        'formulation searches, FEM/DFT model '
                        'definitions, engines',
    'simulations': 'Models: simulation definitions, runners, '
                   'multi-scale compositions, stages, profiles',
    'polariNoCode': 'No-code: solution graphs, the execution engine, '
                    'operations',
    'matrices': 'Math: matrix/equation definitions + executors',
    'simSpace': 'Visualization: sim-space definitions, bindings, '
                'snapshot compilers',
    'xr': 'Visualization: XR mode/framing cascade settings + '
          'per-mode interface variants',
    'simSpace2D': 'Visualization: 2D primitives',
    'simSpace3D': 'Visualization: 3D primitives',
    'polariPeers': 'Distribution: peers, module bundles, module '
                   'projects',
    'moduleService': 'Modules: discovery, metadata, dependency '
                     'tracking',
    'polariApiServer': 'API: the falcon server + endpoint surfaces',
    'polariDBmanagement': 'Persistence: DB adapters',
    'polariDataTyping': 'Typing: polyTyping and friends',
    'polariAnalytics': 'Analytics',
    'accessControl': 'Access control',
    'waxprint': 'Wax-3D-Printing: pellet-fed auger-screw wax printer — '
                'two-zone melt + safety, bead cooling/voxelization, '
                'movement patterns, print-recipe optimizer, a registered '
                'sim space, and no-code wax-printer commands',
}

_IMPORT_RE = re.compile(
    r'^\s*(?:from|import)\s+([A-Za-z_][A-Za-z0-9_]*)', re.MULTILINE)

# A plausible pip distribution name — the underlying import scanner
# occasionally emits comma-tails ('os,'), doc-string template tokens
# ('{package_name}'), and punctuation; none of those are packages.
_VALID_PKG_RE = re.compile(r'^[A-Za-z0-9][A-Za-z0-9._-]*$')
# Framework-internal top-level module names the scanner can leak.
_INTERNAL_NAMES = {'managedDataComms', 'managedFiles', 'managedDB',
                   'managedExecutables', 'managedImages'}


_FRAMEWORK_DIRS: Optional[frozenset] = None


def _framework_dirs() -> frozenset:
    """Top-level directories of THIS framework — internal modules
    that must never be mistaken for installable pip packages
    (tt-11 fix: the install plan was suggesting `pip install
    aquaponics ... topology waxprint`)."""
    global _FRAMEWORK_DIRS
    if _FRAMEWORK_DIRS is None:
        root = _framework_root()
        dirs = set()
        for scan_root in (root, os.path.join(root, 'modules')):
            try:
                dirs.update(
                    entry for entry in os.listdir(scan_root)
                    if os.path.isdir(os.path.join(scan_root, entry)))
            except OSError:
                pass
        _FRAMEWORK_DIRS = frozenset(dirs)
    return _FRAMEWORK_DIRS


def _sanitize_import_names(names) -> List[str]:
    """Keep only plausible external package names: valid pip-name
    shape, not stdlib, not framework-internal top-level modules,
    not this framework's own module directories."""
    stdlib = getattr(sys, 'stdlib_module_names', frozenset())
    out = []
    for raw in names or []:
        name = str(raw).strip().rstrip(',;')
        if (not name or not _VALID_PKG_RE.match(name)
                or name in _INTERNAL_NAMES
                or name.split('.')[0] in stdlib
                or name.split('.')[0] in _framework_dirs()):
            continue
        out.append(name)
    return sorted(set(out))


def _framework_root() -> str:
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def scan_boundary_imports(boundary: str,
                          root: Optional[str] = None) -> List[str]:
    """Which OTHER declared boundaries a boundary's code imports —
    the tracked edges between coherent modules. Text-level scan (also
    catches the lazy in-function imports the codebase prefers)."""
    root = root or _framework_root()
    directory = os.path.join(root, boundary)
    if not os.path.isdir(directory):
        return []
    hits: Set[str] = set()
    for dirpath, _dirnames, filenames in os.walk(directory):
        if '__pycache__' in dirpath:
            continue
        for filename in filenames:
            if not filename.endswith('.py'):
                continue
            try:
                with open(os.path.join(dirpath, filename),
                          encoding='utf-8', errors='ignore') as f:
                    source = f.read()
            except OSError:
                continue
            for match in _IMPORT_RE.finditer(source):
                top = match.group(1)
                if top in FRAMEWORK_BOUNDARIES and top != boundary:
                    hits.add(top)
    return sorted(hits)


def boundary_graph(root: Optional[str] = None) -> Dict[str, Any]:
    """The coherent-module map: every declared boundary with its
    outgoing edges (imports of other boundaries), the REVERSE edges
    (which boundaries import it — tt-1, computed by inverting the
    scan since imports are stored outbound-only), and its external
    python imports."""
    root = root or _framework_root()
    nodes = []
    for boundary, description in sorted(FRAMEWORK_BOUNDARIES.items()):
        directory = os.path.join(root, boundary)
        present = os.path.isdir(directory)
        nodes.append({
            'name': boundary,
            'description': description,
            'present': present,
            'boundaryImports': scan_boundary_imports(boundary, root)
            if present else [],
            'pythonImports': _sanitize_import_names(
                scan_python_imports(directory)) if present else [],
        })
    dependents: Dict[str, List[str]] = {}
    for node in nodes:
        for imported in node['boundaryImports']:
            dependents.setdefault(imported, []).append(node['name'])
    for node in nodes:
        node['boundaryDependents'] = sorted(
            dependents.get(node['name'], []))
    return {'boundaries': nodes}


# ---------------------------------------------------------------------
# Python requires-trees (importlib.metadata).
# ---------------------------------------------------------------------

_REQ_NAME_RE = re.compile(r'^\s*([A-Za-z0-9][A-Za-z0-9._-]*)')


_IMPORT_TO_DIST: Optional[Dict[str, List[str]]] = None


def _installed_version(package: str) -> Optional[str]:
    """Resolve a version by DISTRIBUTION name, falling back to the
    import-name -> distribution map (skfem -> scikit-fem, jwt ->
    PyJWT, …) — the scanner sees import names, pip sees dists."""
    global _IMPORT_TO_DIST
    try:
        return importlib_metadata.version(package)
    except importlib_metadata.PackageNotFoundError:
        pass
    if _IMPORT_TO_DIST is None:
        try:
            _IMPORT_TO_DIST = dict(
                importlib_metadata.packages_distributions())
        except Exception:
            _IMPORT_TO_DIST = {}
    for dist in _IMPORT_TO_DIST.get(package, []):
        try:
            return importlib_metadata.version(dist)
        except importlib_metadata.PackageNotFoundError:
            continue
    return None


def _requires(package: str) -> List[Dict[str, Any]]:
    """A package's declared requirements: [{name, spec, conditional}].
    Requirements guarded by environment markers are kept but marked
    conditional (honest — whether they apply depends on the marker)."""
    try:
        raw = importlib_metadata.requires(package) or []
    except importlib_metadata.PackageNotFoundError:
        return []
    out = []
    for req in raw:
        conditional = ';' in req
        spec = req.split(';')[0].strip()
        match = _REQ_NAME_RE.match(spec)
        if not match:
            continue
        out.append({'name': match.group(1),
                    'spec': spec[len(match.group(1)):].strip(),
                    'conditional': conditional})
    return out


def python_dependency_tree(package: str,
                           _seen: Optional[Dict[str, bool]] = None,
                           depth: int = 0, max_depth: int = 6
                           ) -> Dict[str, Any]:
    """One package's requires-tree. A package already expanded
    ANYWHERE in this tree-walk is emitted as a leaf with
    shared=True instead of being expanded again — shared downstream
    dependencies appear once, which is exactly the non-duplication
    story an installer must honor."""
    seen = _seen if _seen is not None else {}
    version = _installed_version(package)
    node: Dict[str, Any] = {'name': package, 'resolvedVersion': version,
                            'installed': version is not None,
                            'shared': False, 'children': []}
    key = package.lower()
    if key in seen:
        node['shared'] = True
        return node
    seen[key] = True
    if version is None or depth >= max_depth:
        return node
    for req in _requires(package):
        child = python_dependency_tree(req['name'], seen, depth + 1,
                                       max_depth)
        child['spec'] = req['spec']
        if req['conditional']:
            child['conditional'] = True
        node['children'].append(child)
    return node


def python_dependency_forest(packages: List[str]) -> Dict[str, Any]:
    """Requires-trees for a package set with ONE shared `seen` map, so
    a dependency shared BETWEEN top-level packages is expanded exactly
    once across the whole forest."""
    seen: Dict[str, bool] = {}
    trees = [python_dependency_tree(p, seen) for p in sorted(packages)]
    return {'trees': trees,
            'distinctPackages': len(seen),
            'note': 'shared=true nodes are expanded elsewhere in this '
                    'forest — an install must not duplicate them'}


# ---------------------------------------------------------------------
# Persisted dependency rows.
# ---------------------------------------------------------------------

def refresh_dependency_rows(manager) -> Dict[str, Any]:
    """(Re)populate PolariModuleDependency rows for every declared
    boundary: its python imports (with resolved/missing status) and
    its boundary edges. Idempotent by name."""
    from polariPeers.polari_module_dependency import (
        PolariModuleDependency,
    )
    table = (getattr(manager, 'objectTables', None) or {}).get(
        'PolariModuleDependency', {}) or {}
    existing = {getattr(r, 'name', ''): r for r in (
        table.values() if isinstance(table, dict) else table)}
    graph = boundary_graph()
    created, updated = 0, 0
    for node in graph['boundaries']:
        if not node['present']:
            continue
        entries = (
            [('python', dep) for dep in node['pythonImports']]
            + [('polari', dep) for dep in node['boundaryImports']]
        )
        for kind, dep in entries:
            name = f"{node['name']}:{kind}:{dep}"
            version = _installed_version(dep) if kind == 'python' else ''
            status = ('installed' if kind == 'python' and version
                      else 'missing' if kind == 'python'
                      else 'declared')
            row = existing.get(name)
            if row is None:
                PolariModuleDependency(
                    name=name, module_id=node['name'], kind=kind,
                    dep_name=dep, resolved_version=version or '',
                    status=status,
                    reason=f"import scan of {node['name']}/",
                    manager=manager)
                created += 1
            else:
                if (getattr(row, 'status', '') != status
                        or getattr(row, 'resolved_version', '')
                        != (version or '')):
                    row.status = status
                    row.resolved_version = version or ''
                    try:
                        manager.db.saveInstanceInDB(row)
                    except Exception:
                        pass
                    updated += 1
    return {'ok': True, 'created': created, 'updated': updated,
            'boundaries': len([n for n in graph['boundaries']
                               if n['present']])}


# ---------------------------------------------------------------------
# Install planning + execution (union-resolve, never duplicate).
# ---------------------------------------------------------------------

def plan_install(manager=None) -> Dict[str, Any]:
    """The SUGGESTION: the union of missing python dependencies across
    every boundary, deduplicated, as ONE pip invocation — a single
    resolver run installs shared downstream dependencies exactly once
    (running pip per-module would re-resolve and can duplicate or
    conflict)."""
    graph = boundary_graph()
    missing: Dict[str, List[str]] = {}
    for node in graph['boundaries']:
        for dep in node['pythonImports']:
            if _installed_version(dep) is None:
                missing.setdefault(dep, []).append(node['name'])
    packages = sorted(missing)
    return {
        'packages': packages,
        'neededBy': missing,
        'command': (['pip', 'install'] + packages) if packages else [],
        'suggestion': {
            'action': 'POST /api/modules/dependencies/install with '
                      '{"confirm": true} to run the single pip '
                      'invocation above',
            'reason': 'one resolver run installs shared downstream '
                      'dependencies exactly once',
            'durability': 'a runtime install lives only until the '
                          'image is rebuilt — add accepted packages '
                          'to requirements.txt for keeps',
        } if packages else None,
        'note': '' if packages else 'nothing missing — every scanned '
                                    'import resolves in this '
                                    'environment',
    }


def install_packages(packages: List[str],
                     timeout: int = 600) -> Dict[str, Any]:
    """Execute ONE pip install for the confirmed package set. Honest
    report; never raises."""
    if not packages:
        return {'ok': True, 'installed': [],
                'note': 'nothing to install'}
    cmd = [sys.executable, '-m', 'pip', 'install'] + list(packages)
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True,
                              timeout=timeout)
    except Exception as e:
        return {'ok': False, 'error': str(e), 'command': cmd}
    report = {
        'ok': proc.returncode == 0,
        'command': cmd,
        'stdoutTail': (proc.stdout or '')[-2000:],
        'stderrTail': (proc.stderr or '')[-2000:],
        'resolved': {p: _installed_version(p) for p in packages},
        'durability': 'installed into the RUNNING container only — '
                      'persist accepted packages in requirements.txt '
                      '(backend) or the msci-engines Dockerfile pins',
    }
    if proc.returncode != 0:
        report['error'] = f'pip exited {proc.returncode}'
    return report
