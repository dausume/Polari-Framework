"""
@module board.custom.hwsys_refs

hsp-1: does a `Class:name` ref RESOLVE to a row? One place for the whole Hardware System arc (links, paths, selftest). The board tables in hand are searched
first (so a row removed from `tables` is gone); a class owned by another module (hwnocode Runtime, grpcbridge bridge, cmod FirmwareSolution ...) is read from
that module's code-owned seeds, imported lazily so board still loads when they are absent; a live `manager` overlays all of it. `Person` has no class yet and
never resolves (said, not hidden).
"""
import json


def _live(manager, cls):
    if manager is None:
        return None
    tbl = (getattr(manager, 'objectTables', None) or {}).get(cls)
    return {getattr(r, 'name', '') for r in tbl.values()} if tbl else None


def _seed_names(cls):
    """Names of the code-owned seed rows of a class that lives outside board (lazy; unknown / module absent -> None)."""
    try:
        if cls == 'Runtime':
            from hwnocode.custom.runtimes import RUNTIME_ROWS
            return {r['name'] for r in RUNTIME_ROWS}
        if cls == 'HardwareBridgeDefinition':
            from grpcbridge.mapping_basis import SEED_LIGHT_BRIDGE
            return {SEED_LIGHT_BRIDGE['name']}
        if cls == 'FirmwareSolution':
            from cmod import cmod_seed
            return {r['name'] for r in cmod_seed.LIGHT_FIRMWARE_ROWS}
        if cls == 'SolutionDefinition':
            from hwnocode.custom import light_solutions as LS
            return {LS.LIGHT_SOLUTION, LS.TOGGLE_SOLUTION}
        if cls == 'LightState':
            return {'uno-light'}
        if cls == 'WireContract':
            from board.custom import compat
            c, _ = compat.pinned_contract('LightState')
            return {'LightState@uno-light'} if c else set()
        if cls == 'Person':
            return set()   # no Person class exists yet: the person participant is a role
    except Exception:   # noqa: BLE001 — the other module is absent on this node
        return None
    return None


def resolves(ref, tables, manager=None, extra=None):
    """(ok, why) — `ref` is 'Class:name'. `extra` = {class: names} computed alongside (the SystemLink rows of the system in hand)."""
    cls, _, name = (ref or '').partition(':')
    if not cls or not name:
        return False, 'empty ref'
    if extra and cls in extra:
        return (name in extra[cls]), ('' if name in extra[cls] else 'no %s row %s in this system' % (cls, name))
    rows = tables.get(cls)
    if rows:
        hit = any(r.get('name') == name for r in rows)
        return hit, '' if hit else 'no %s row named %s in the tables' % (cls, name)
    live = _live(manager, cls)
    if live is not None:
        return (name in live), '' if name in live else 'no %s row named %s on this server' % (cls, name)
    seeds = _seed_names(cls)
    if seeds is None:
        return False, 'class %s is not known here (its module may be absent)' % cls
    if cls == 'Person':
        return False, 'there is no Person class yet: the person participant stands as a role, not a row'
    return (name in seeds), '' if name in seeds else 'no %s row named %s' % (cls, name)


def refs_of(js):
    return json.loads(js) if isinstance(js, str) else (js or [])
