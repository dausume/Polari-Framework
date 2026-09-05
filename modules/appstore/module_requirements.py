"""
@module appstore.module_requirements

Per-module DEPENDENCY + ENGINE accounting for the downloads
surfaces (Dustin 2026-08-24: counting files is not honest — the
additional libraries and engines take DEFINITIVE space that either
gets installed dynamically after an online deb, or must ride
inside an offline deb / on the offline media).

Derivation, not declaration: the module's real imports
(moduleService.moduleDiscovery.scan_python_imports) map to
installed distributions (importlib.metadata.packages_distributions)
and expand through their full requires-closure. Sizes are MEASURED
from the live environment (sum of each distribution's installed
files); a distribution this environment lacks is reported
installed=False with bytes=None — "unmeasured", never invented.

ENGINES are the non-pip layer: system binaries and heavyweight
backends a module leans on. They are curated per module (there is
no import statement to scan for a subprocess binary) with a
detection probe each; anything not listed renders as "no engines
declared", which is an honest gap, not a claim of zero.

@consumers
  - appstore.app_deb_builder (manifest + offline wheel set)
  - appstore.app_debs_page (per-item accounting lines)
  - appstore.selftest_module_requirements
"""

import os
import re
import shutil
from importlib import metadata as importlib_metadata

#: a requirement's name ends at the first extra/version/marker char
_REQ_NAME_RE = re.compile(r'[\s\[<>=!~;(]')

from moduleService import module_registry
from moduleService.moduleDiscovery import scan_python_imports

#: module → engines it leans on. kind 'python' = a pip
#: distribution (can ride an offline deb as a wheel); 'system' = a
#: distro/system binary (rides the offline MEDIA apt closure or the
#: distro's own repos — never a pip wheel). Curated + probed.
ENGINE_MAP = {
    'materials_science': [
        {'name': 'scikit-fem', 'kind': 'python', 'probe': 'skfem',
         'note': 'FEM engine (Darcy/thermal/structural solves)'},
        {'name': 'pyscf', 'kind': 'python', 'probe': 'pyscf',
         'note': 'DFT engine (molecular layer)'},
        {'name': 'ase', 'kind': 'python', 'probe': 'ase',
         'note': 'atomic-structure toolkit'},
    ],
    'hwdigital': [
        {'name': 'verilator', 'kind': 'system',
         'probe': 'verilator', 'note': 'HDL simulation'},
        {'name': 'ngspice', 'kind': 'system', 'probe': 'ngspice',
         'note': 'analog/SPICE simulation'},
    ],
    'hwfpga': [
        {'name': 'verilator', 'kind': 'system',
         'probe': 'verilator', 'note': 'HDL simulation'},
    ],
    'islemesh': [
        {'name': 'docker', 'kind': 'system', 'probe': 'docker',
         'note': 'container runtime for mesh apps'},
    ],
    # vpn-1: Polari only mirrors + renders; the engines run on the
    # isle. `cryptography` is the keygen fallback (one-time delivery),
    # wireguard-tools is optional (qr / wg pubkey on this box).
    'vpn': [
        {'name': 'cryptography', 'kind': 'python', 'probe': 'cryptography',
         'note': 'X25519 keygen fallback (device-side keys preferred)'},
    ],
    'grpcbridge': [
        {'name': 'grpcio', 'kind': 'python', 'probe': 'grpc',
         'note': 'gRPC runtime'},
    ],
}


def _dist_size_bytes(dist):
    """Measured on-disk size of one installed distribution — the
    definitive number, from the files the installer recorded."""
    total = 0
    try:
        for f in (dist.files or []):
            try:
                total += os.path.getsize(dist.locate_file(f))
            except OSError:
                continue
    except Exception:
        return None
    return total or None


def _closure(dist_names):
    """Expand installed distributions through their requires
    closure; uninstalled names stay (unmeasured leaves)."""
    seen, queue = set(), list(dist_names)
    while queue:
        name = queue.pop()
        key = name.lower()
        if key in seen:
            continue
        seen.add(key)
        try:
            for req in (importlib_metadata.requires(name) or []):
                if ';' in req:          # environment markers =
                    continue            # conditional; stay honest
                dep = _REQ_NAME_RE.split(req.strip(), 1)[0]
                if dep and dep.lower() not in seen:
                    queue.append(dep)
        except importlib_metadata.PackageNotFoundError:
            continue
    return sorted(seen)


def _measure(names):
    """[{name, installed, version, bytes}] for a distribution-name
    closure, measured live."""
    out = []
    for name in _closure(sorted(names)):
        try:
            dist = importlib_metadata.distribution(name)
            out.append({
                'name': dist.metadata['Name'] or name,
                'installed': True,
                'version': dist.version,
                'bytes': _dist_size_bytes(dist),
            })
        except importlib_metadata.PackageNotFoundError:
            out.append({'name': name, 'installed': False,
                        'version': None, 'bytes': None})
    return sorted(out, key=lambda l: l['name'].lower())


def module_scan(module, root=None):
    """(pip_libraries, polari_requires) — the module's scanned
    imports split into real third-party distributions vs OTHER
    POLARI MODULES (which are module→module requires, never pip
    payload; the registry's own `requires` field unions in)."""
    froot = root or module_registry._framework_root()
    modules = module_registry.load_registry(froot)['modules']
    entry = modules.get(module, {})
    module_dir = os.path.join(froot,
                              entry.get('path',
                                        f'modules/{module}'))
    if not os.path.isdir(module_dir):
        return [], sorted(entry.get('requires', []))
    imports = scan_python_imports(module_dir)
    polari_names = set(modules)
    polari_requires = {name for name in imports
                       if name in polari_names and name != module}
    polari_requires.update(entry.get('requires', []))
    pkg_to_dist = importlib_metadata.packages_distributions()
    roots = set()
    for name in imports:
        if name in polari_names:
            continue
        for dist in pkg_to_dist.get(name, [name]):
            roots.add(dist)
    return _measure(roots), sorted(polari_requires)


def module_engines(module):
    """Curated engines with live detection; python engines carry
    their MEASURED closure bytes (None = not installed here, so
    unmeasured — never invented). [] = none declared, an honest
    gap, not a claim of zero."""
    engines = []
    for engine in ENGINE_MAP.get(module, []):
        size = None
        if engine['kind'] == 'python':
            measured = _measure([engine['name']])
            present = any(l['installed'] for l in measured
                          if l['name'].lower()
                          == engine['name'].lower())
            if not present:
                try:
                    __import__(engine['probe'])
                    present = True
                except ImportError:
                    present = False
            sizes = [l['bytes'] for l in measured
                     if l['bytes'] is not None]
            size = sum(sizes) if present and sizes else None
        else:
            present = shutil.which(engine['probe']) is not None
        engines.append({**engine, 'present': present,
                        'bytes': size})
    return engines


def module_requirements(module, root=None):
    """The full accounting one module's downloads need to be
    honest about: pip libraries (measured), polari module
    requires, engines (probed), and totals with an explicit
    unmeasured count — partial is stated, never papered over."""
    libraries, polari_requires = module_scan(module, root)
    measured = [l['bytes'] for l in libraries
                if l['bytes'] is not None]
    return {
        'module': module,
        'libraries': libraries,
        'librariesBytes': sum(measured),
        'librariesUnmeasured': sum(1 for l in libraries
                                   if l['bytes'] is None),
        'polariRequires': polari_requires,
        'engines': module_engines(module),
    }
