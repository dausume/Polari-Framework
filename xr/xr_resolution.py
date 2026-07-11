"""
@module xr.xr_resolution

The XR cascade resolver (xr-1): pure functions, no I/O beyond reading
manager.objectTables. Resolution walks individual → multiscale → type
→ global and takes the FIRST explicitly-set value ('unset'/'' means
"inherit upward"); a directly-set lower level always beats a higher
one. The resolved value ALWAYS carries provenance — resolvedFrom names
the deciding level so "why is there no VR button" is answerable.

Builtin fallbacks when the whole ladder is unset:
  mode    = 'none'    (XR is opt-in at some level, never ambient)
  framing = 'exhibit' (museum mode — the comfort-safe entry)

@consumers
  - xr.xr_api (/api/xr/resolve)
  - xr.selftest_xr
"""

from xr.xr_settings import xr_global_settings_row

BUILTIN_MODE = 'none'
BUILTIN_FRAMING = 'exhibit'

# Ladder order, lowest (most specific, always wins when set) first.
LEVELS = ('individual', 'multiscale', 'type', 'global')


def _is_set(value) -> bool:
    return bool(value) and value != 'unset'


def resolve_ladder(individual='', multiscale='', type_default='',
                   global_value='', builtin=''):
    """First explicitly-set value walking down the ladder.

    Returns (value, resolvedFrom) where resolvedFrom is the deciding
    level name, or 'builtin' when nothing on the ladder is set.
    """
    rungs = (
        ('individual', individual),
        ('multiscale', multiscale),
        ('type', type_default),
        ('global', global_value),
    )
    for level, value in rungs:
        if _is_set(value):
            return value, level
    return builtin, 'builtin'


def effective_category(definition):
    """The Q1b vocabulary: explicit category field wins; otherwise the
    definition's owning module supplies the derived default.

    Returns (category, source) with source in
    'explicit' | 'module' | 'none'.
    """
    explicit = getattr(definition, 'category', '') or ''
    if explicit:
        return explicit, 'explicit'
    module = getattr(definition, 'owning_module', '') or ''
    if module:
        return module, 'module'
    return '', 'none'


def _rows(manager, class_name):
    tables = getattr(manager, 'objectTables', None) or {}
    return (tables.get(class_name) or {}).values()


def _row_by_name(manager, class_name, name):
    if not name:
        return None
    for row in _rows(manager, class_name):
        if getattr(row, 'name', '') == name:
            return row
    return None


def type_default_for(manager, category):
    """The XrTypeDefault row for a category (None when absent)."""
    if not category:
        return None
    for row in _rows(manager, 'XrTypeDefault'):
        if getattr(row, 'category', '') == category:
            return row
    return None


def resolve_for_space(manager, space_name, multiscale_name=''):
    """Full cascade resolution for one SimSpaceDefinition, optionally
    viewed through a multiscale context (the msim page passes its own
    definition name; a standalone viewer passes none — the multiscale
    rung then reads as unset).

    Returns a dict the API serves verbatim:
      {mode, modeResolvedFrom, framing, framingResolvedFrom,
       category, categorySource, spaceName, multiscaleName}
    Raises ValueError for an unknown space (honest 404 at the API).
    """
    space = _row_by_name(manager, 'SimSpaceDefinition', space_name)
    if space is None:
        raise ValueError(f'unknown SimSpaceDefinition "{space_name}"')

    msim = _row_by_name(
        manager, 'MultiScaleSimulationDefinition', multiscale_name)
    if multiscale_name and msim is None:
        raise ValueError(
            f'unknown MultiScaleSimulationDefinition "{multiscale_name}"')

    category, category_source = effective_category(space)
    type_row = type_default_for(manager, category)
    global_row = xr_global_settings_row(manager)

    mode, mode_from = resolve_ladder(
        individual=getattr(space, 'xr_mode', ''),
        multiscale=getattr(msim, 'xr_mode', '') if msim else '',
        type_default=getattr(type_row, 'xr_mode', '') if type_row else '',
        global_value=getattr(global_row, 'xr_mode', ''),
        builtin=BUILTIN_MODE,
    )
    framing, framing_from = resolve_ladder(
        individual=getattr(space, 'xr_framing', ''),
        multiscale=getattr(msim, 'xr_framing', '') if msim else '',
        type_default=getattr(type_row, 'xr_framing', '') if type_row else '',
        global_value=getattr(global_row, 'xr_framing', ''),
        builtin=BUILTIN_FRAMING,
    )
    return {
        'spaceName': space_name,
        'multiscaleName': multiscale_name or '',
        'mode': mode,
        'modeResolvedFrom': mode_from,
        'framing': framing,
        'framingResolvedFrom': framing_from,
        'category': category,
        'categorySource': category_source,
    }
