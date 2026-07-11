"""
@module polariApiServer.module_gating

modsplit-1: per-instance module gating — each backend registers ONLY
the definition classes of the modules assigned to it.

The knob: env POLARI_MODULES, a comma list of module/package names
('materialsScience,aquaponics'). Unset/empty = ALL modules (today's
monolithic behavior, fully backward compatible). Dotted assignment
names ('materialsScience.dft') match their parent package.

A class's module IS its defining package (cls.__module__ top level) —
no hand-maintained map to drift. CORE packages register everywhere:
the object tree, typing, access control, no-code, sim-space/display
definitions, and the mesh substrate (peers/topology/resources/locks/
refs) every instance needs to coordinate.

Downstream effects of filtering defClassList are automatic (seam
survey 2026-07-11): seeds skip classes absent from objectTypingDict,
CRUDE endpoints are created only from objectTypingDict, and boot
restore skips unknown tables — so one filter point gives a smaller
honest CRUDE surface, no phantom seeds, no phantom restores.
"""

import os
from typing import Optional, Set

# Packages every instance needs to boot + coordinate in the mesh.
CORE_PACKAGES = frozenset({
    'polariApiServer', 'polariDataTyping', 'polariDBmanagement',
    'polariNetworking', 'polariNoCode', 'accessControl', 'matrices',
    'simSpace', 'simSpace2D', 'simSpace3D', 'polariPeers', 'topology',
    'resources', 'simulationLocks', 'polariRefs', 'xr',
    'objectTreeDecorators', 'objectTreeManagerDecorators', '__main__',
})

# Opt-in packages NEVER ride the unset-knob monolithic default (acct-0:
# test objects load ONLY in test builds). They register only when
# POLARI_MODULES names them explicitly or POLARI_TEST_BUILD is set —
# a normal build's clean absence is itself a pinned behavior
# (testing.absence_probe asserts it).
OPT_IN_PACKAGES = frozenset({'testing'})


def is_test_build() -> bool:
    """The test-build knob: POLARI_TEST_BUILD=true (Dockerfile.test
    lineage). Enables opt-in packages without having to enumerate
    every other module in POLARI_MODULES."""
    raw = (os.environ.get('POLARI_TEST_BUILD') or '').strip().lower()
    return raw in ('1', 'true', 'yes', 'on')


def enabled_module_names() -> Optional[Set[str]]:
    """None = all modules (knob unset — monolithic default)."""
    raw = (os.environ.get('POLARI_MODULES') or '').strip()
    if not raw:
        return None
    return {entry.strip().split('.')[0] for entry in raw.split(',')
            if entry.strip()}


def module_of_class(cls) -> str:
    return (getattr(cls, '__module__', '') or '').split('.')[0]


def module_enabled(package: str) -> bool:
    if package in CORE_PACKAGES:
        return True
    enabled = enabled_module_names()
    if package in OPT_IN_PACKAGES:
        if is_test_build():
            return True
        return enabled is not None and package in enabled
    return True if enabled is None else package in enabled


def class_enabled(cls) -> bool:
    return module_enabled(module_of_class(cls))


def gate_summary(all_classes) -> dict:
    """Boot-log evidence: what this instance keeps vs drops."""
    enabled = enabled_module_names()
    kept, dropped = {}, {}
    for cls in all_classes:
        package = module_of_class(cls)
        bucket = kept if class_enabled(cls) else dropped
        bucket.setdefault(package, 0)
        bucket[package] += 1
    return {'modulesKnob': sorted(enabled) if enabled else 'ALL',
            'kept': kept, 'dropped': dropped}
