"""
@module electrodevice.custom.layout_rows

lay-0/lay-1: the one place the layout engine creates, finds and drops ROWS (WireColorScheme, LayoutEdit). A row needs a live manager (the server's); with none the engine still
READS (seeds), but a write is refused in words, never faked.
"""
from electrodevice.custom.layout_words import LayoutRefused


def table(manager, cls_name):
    tabs = getattr(manager, 'objectTables', None)
    if tabs is None:
        return {}
    return tabs.setdefault(cls_name, {})


def rows(manager, cls_name):
    return [r for r in table(manager, cls_name).values() if getattr(r, 'name', '')]


def find(manager, cls_name, name):
    return next((r for r in rows(manager, cls_name) if r.name == name), None)


def _save(manager, row):
    try:
        manager.db.saveInstanceInDB(row)
    except Exception:  # noqa: BLE001 - an in-memory manager has no database; the row stays in the tree
        pass


def upsert(manager, cls, name, **fields):
    """Create the row `name` of class `cls`, or set its fields. -> the row."""
    if getattr(manager, 'objectTables', None) is None:
        raise LayoutRefused("no live server to keep the %s row in (run this against the backend: --api URL)" % cls.__name__, status=409)
    row = find(manager, cls.__name__, name)
    if row is None:
        row = cls(manager=manager, name=name, **fields)
    else:
        for k, v in fields.items():
            setattr(row, k, v)
    _save(manager, row)
    return row


def remove(manager, cls_name, name):
    """Drop the row `name`; -> True when there was one."""
    t = table(manager, cls_name)
    key = next((k for k, r in t.items() if getattr(r, 'name', '') == name), None)
    if key is None:
        return False
    row = t.pop(key)
    try:
        manager.db.deleteInstanceInDB(row)
    except Exception:  # noqa: BLE001 - in-memory drop still converges
        pass
    return True
