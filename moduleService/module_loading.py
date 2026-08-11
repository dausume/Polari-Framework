"""
@module moduleService.module_loading

mp-3 (MODULE_PROJECTS_PLAN): the CORE boots without downstream.

Feature modules are becoming their own downloadable sub-projects
(``pol modules get|drop``). When a module's code is NOT locally
present, the core must still boot — its imports in
polariApiServer.polariServer are guarded per module: present code
imports exactly as before; absent code stubs its symbols (SEED_*
lists -> [], everything else -> None) and records the absence in
``MISSING_FEATURE_MODULES`` so every surface can say honestly
"not downloaded — pol modules get <m>".

The truth for "downloaded" is the FILESYSTEM (either import root:
the framework root for not-yet-moved modules, modules/ for moved
ones) — same rule as module_registry.sync, never a stale flag.

A module that IS downloaded but fails to import stays a LOUD
failure — lazy loading must never silently swallow broken code.

@consumers
  - polariApiServer.polariServer (guarded import blocks + endpoint
    construction gates)
  - polariApiServer.modulesAPI (missing-module rows)
  - moduleService.selftest_lazy_imports (drift guard: every symbol
    polariServer imports from a feature module must be stubbable)
"""

import os

from polariApiServer.module_gating import module_enabled

# Every module that mp-2/mp-4 split into its own sub-project. These
# (and ONLY these) may be absent from a checkout; core packages are
# always required and their imports stay static.
FEATURE_MODULES = frozenset({
    'appstore',
    'aquaponics', 'biomining', 'bizops', 'climate', 'dmvdata',
    'electrodevice',
    'gears', 'grpcbridge', 'hwdigital', 'hwfpga', 'magnetics',
    'mathshapes', 'meshassets', 'microalgae', 'motors',
    'nutrition', 'odooconnect', 'plant_morphology', 'polariapps',
    'scoring',
    'supplychain', 'tanks', 'techtree', 'testing', 'waxprint',
    'waxsupply', 'zones',
})

# Cross-feature top-level imports (survey 2026-07-18): dropping a
# module someone downloaded still needs is refused honestly by the
# pol CLI (the registry mirrors this as `requires`).
FEATURE_REQUIRES = {
    # appstore reads PolariAppDefinition ROWS (no top-level import),
    # so its polariapps dependency lives only in the registry JSON —
    # this mirror is for genuine Python imports (drift selftest pins
    # it as a subset of the registry).
    'aquaponics': ('plant_morphology', 'scoring'),
    'bizops': ('supplychain',),
    # co2-A: climate reuses the aquaponics steady-state gas
    # balance (one equation, two callers - a room of people is the
    # crop's CO2 draw with the sign flipped) and the dmvdata
    # GovSource/SourceRetrieval provenance registry. It owns no
    # copy of either.
    'climate': ('aquaponics', 'dmvdata'),
    'dmvdata': ('scoring',),
    'magnetics': ('supplychain',),
    'motors': ('magnetics',),
    # gr-1: gears imports nothing from mathshapes YET (the geometry
    # generator is gr-3), but the registry entry names the coupling
    # so a drop refuses honestly once gr-3 lands.
    'gears': ('mathshapes',),
    # mesh-1: the fit engine reads OrganModel rows.
    'meshassets': ('plant_morphology',),
    'mathshapes': ('aquaponics', 'plant_morphology'),
    'electrodevice': ('hwdigital',),
    'zones': ('scoring',),
}

# Modules that MOVE into modules/ (mp-4) but stay required for boot
# (they are CORE_PACKAGES in module_gating / polariServer imports
# them statically): drop refuses these until they are lazified too.
CORE_REQUIRED_MODULES = frozenset({'topology', 'resources', 'xr'})

# Populated by polariServer's guarded import blocks at import time:
# {module_name: honest message}. ModulesAPI + boot logging read it.
MISSING_FEATURE_MODULES = {}


def _framework_root():
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def module_code_dir(name, root=None):
    """The directory holding <name>'s code, from either import root
    (framework root for not-yet-moved modules, modules/ for moved
    ones) — or None when the code is not locally present."""
    root = root or _framework_root()
    for candidate in (os.path.join(root, 'modules', name),
                      os.path.join(root, name)):
        if os.path.isdir(candidate):
            return candidate
    return None


def feature_downloaded(name, root=None):
    return module_code_dir(name, root) is not None


def feature_available(name, root=None):
    """Downloaded AND enabled on this instance (POLARI_MODULES /
    opt-in gating) — the gate endpoint constructions use."""
    return feature_downloaded(name, root) and module_enabled(name)


def missing_message(name):
    return (f"module '{name}' is not downloaded — "
            f"pol modules get {name}")


def stub_feature_symbols(globalns, module_name, symbol_names):
    """Fill a missing feature module's symbols so the core still
    boots: SEED_* -> empty list (seed loops no-op), everything else
    -> None (defClassList filters Nones; endpoint constructions are
    gated on feature_available). Records the absence."""
    for symbol in symbol_names:
        globalns[symbol] = [] if symbol.startswith('SEED_') else None
    MISSING_FEATURE_MODULES[module_name] = missing_message(module_name)


def import_feature_blocks(globalns, blocks):
    """dyn-1: replay the declarative feature-import table
    (polariApiServer.feature_imports.FEATURE_IMPORT_BLOCKS) into a
    namespace — the exact semantics of the old guarded try/except
    blocks: present code imports as before; absent code stubs every
    symbol of the failing BLOCK (SEED_* -> [], else None) and records
    the module in MISSING_FEATURE_MODULES; downloaded-but-broken code
    re-raises LOUDLY (feature_import_error decides which)."""
    import importlib
    for module_name, imports in blocks:
        _import_one_block(globalns, module_name, imports, importlib)


def _import_one_block(globalns, module_name, imports, importlib):
    staged = {}
    try:
        for path, symbols in imports:
            mod = importlib.import_module(path)
            for symbol in symbols:
                staged[symbol] = _resolve_from_import(
                    mod, path, symbol, importlib)
    except ImportError as exc:
        feature_import_error(module_name, exc)  # re-raises if downloaded
        all_symbols = tuple(s for _, syms in imports for s in syms)
        stub_feature_symbols(globalns, module_name, all_symbols)
        return
    globalns.update(staged)


def unstub_feature_module(globalns, module_name, blocks):
    """dyn-2/4: after a module's code arrives at runtime, re-run its
    entries from the SAME declaration the boot path used, rebinding
    the real symbols over the stubs. Raises ImportError (loudly) if
    the code still cannot import; on success removes the module from
    MISSING_FEATURE_MODULES. Callers must invalidate import caches
    first when the code was fetched after process start
    (importlib.invalidate_caches())."""
    import importlib
    importlib.invalidate_caches()
    entries = [(m, imports) for m, imports in blocks if m == module_name]
    if not entries:
        raise KeyError(f'no feature-import entries for {module_name!r}')
    for _, imports in entries:
        for path, symbols in imports:
            mod = importlib.import_module(path)
            for symbol in symbols:
                globalns[symbol] = _resolve_from_import(
                    mod, path, symbol, importlib)
    MISSING_FEATURE_MODULES.pop(module_name, None)


def _resolve_from_import(mod, path, symbol, importlib):
    """``from <path> import <symbol>`` semantics: attribute first,
    then submodule fallback (a from-import of a submodule works in
    Python even when the parent has not imported it as an attribute),
    and ImportError — never AttributeError — when neither exists."""
    try:
        return getattr(mod, symbol)
    except AttributeError:
        try:
            return importlib.import_module(f'{path}.{symbol}')
        except ImportError as exc:
            raise ImportError(
                f"cannot import name '{symbol}' from '{path}'"
            ) from exc


def feature_import_error(module_name, exc):
    """Decide what an ImportError in a guarded feature-import block
    means. Absent code -> return True (caller stubs). Present code
    -> re-raise: a downloaded module that cannot import is a real
    breakage and must stay loud, never a silent skip."""
    if feature_downloaded(module_name):
        raise exc
    return True


def boot_report():
    """One honest boot line per missing module (polariServer prints
    this after the import block)."""
    return [f'[ModuleLoading] {msg}'
            for msg in MISSING_FEATURE_MODULES.values()]
