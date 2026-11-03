"""
@module cmod.custom.config_rows

cfg-0: THE ONE PLACE the configuration engine finds, creates and drops rows (BenchSolution, BenchConditions, ConfigOption, CatomConfiguration,
ConfigChoice, ConfigOptionGrade, ConfigOptionResult). Rows are read as plain dicts of their constructor fields, so the rest of the engine never touches a
row object. With no live manager a write raises ConfigRefused; it is never faked.
"""
import inspect
import json


class ConfigRefused(Exception):
    def __init__(self, why, status=422):
        Exception.__init__(self, why)
        self.why, self.status = why, status


def _cls(cls_name):
    if cls_name in ('BenchSolution', 'BenchConditions'):
        import board.objects.board as B
        return getattr(B, cls_name)
    import cmod.objects.cmod as C
    if hasattr(C, cls_name):
        return getattr(C, cls_name)
    if cls_name == 'SolutionDefinition':   # bss-5: the drawing row the canvas page lists
        from polariApiServer.solutionDefinition import SolutionDefinition
        return SolutionDefinition
    import board.objects.board as B
    import types
    found = getattr(B, cls_name)
    if isinstance(found, types.ModuleType):   # cfg-1: a board class its package does not re-export resolves to its module - take the class from it
        found = getattr(found, cls_name)
    return found


def _fields(cls):
    return [p for p in inspect.signature(cls.__init__).parameters if p not in ('self', 'manager')]


def _table(manager, cls_name):
    tabs = getattr(manager, 'objectTables', None)
    return {} if tabs is None else tabs.setdefault(cls_name, {})


def as_dict(row):
    return {k: getattr(row, k, '') for k in _fields(type(row))}


def rows(manager, cls_name, **where):
    """Every row of the class as a dict, narrowed by field equality."""
    out = [as_dict(r) for r in _table(manager, cls_name).values() if getattr(r, 'name', '')]
    return [r for r in out if all(r.get(k) == v for k, v in where.items())]


def get(manager, cls_name, name):
    return next((r for r in rows(manager, cls_name) if r['name'] == name), None)


def _save(manager, row):
    try:
        manager.db.saveInstanceInDB(row)
    except Exception:  # noqa: BLE001 - an in-memory manager (selftest) has no database; the row stays in the tree
        pass


def upsert(manager, cls_name, name, **fields):
    """Create the row `name`, or set its fields (constructor fields only). -> the row as a dict."""
    if getattr(manager, 'objectTables', None) is None:
        raise ConfigRefused('no live server to keep the %s row in' % cls_name, status=409)
    cls = _cls(cls_name)
    allowed = set(_fields(cls))
    f = {k: v for k, v in fields.items() if k in allowed}
    row = next((r for r in _table(manager, cls_name).values() if getattr(r, 'name', '') == name), None)
    if row is None:
        row = cls(manager=manager, name=name, **f)
    else:
        for k, v in f.items():
            setattr(row, k, v)
    _save(manager, row)
    return as_dict(row)


def drop(manager, cls_name, **where):
    """Drop every row matching; -> how many."""
    t = _table(manager, cls_name)
    keys = [k for k, r in t.items() if all(getattr(r, f, None) == v for f, v in where.items())]
    for k in keys:
        row = t.pop(k)
        try:
            manager.db.deleteInstanceInDB(row)
        except Exception:  # noqa: BLE001 - the in-memory drop still converges
            pass
    return len(keys)


def sets(option):
    """An option's {variable: value} (its sets_json read once, here)."""
    try:
        v = json.loads(option.get('sets_json') or '{}')
        return v if isinstance(v, dict) else {}
    except ValueError:
        return {}
