"""
@cross-cutting
@module topology.engine_metering
@tags @xc:bindings

sep-4 (decision 9): lightweight usage metering at the engine
*_remote seams — call counts / bytes / latency accumulated into
EngineUsageWindow ROWS (one per engine x UTC hour), never logs.

Contract: record() MUST NEVER break the call path — every failure
mode (no manager yet, class unregistered, DB refusal) degrades to
silently-not-tracked, and usage_report() says so honestly.
"""

import time
from datetime import datetime, timezone

#: Keep the report bounded: a week of hourly windows.
REPORT_WINDOWS = 168


def _manager():
    # read the ATTRIBUTE, not an imported copy — set_manager()
    # rebinds the module global after we may have been imported.
    try:
        from topology import provider_registry
        return getattr(provider_registry, 'MANAGER', None)
    except Exception:
        return None


def _window_start(now=None):
    dt = datetime.fromtimestamp(now if now is not None else
                                time.time(), tz=timezone.utc)
    return dt.strftime('%Y-%m-%dT%H:00:00Z')


def record(engine, ok, started, bytes_out=0, bytes_in=0):
    """Accumulate one remote call into this hour's window row.
    `started` is the time.time() taken before the request."""
    try:
        manager = _manager()
        if manager is None:
            return False
        tables = getattr(manager, 'objectTables', None) or {}
        if 'EngineUsageWindow' not in tables:
            return False  # class not registered here — not tracked
        window = _window_start()
        key = f'{engine}:{window}'
        row = None
        for candidate in tables['EngineUsageWindow'].values():
            if getattr(candidate, 'name', '') == key:
                row = candidate
                break
        if row is None:
            from topology.topology_modules import EngineUsageWindow
            row = EngineUsageWindow(name=key, engine=engine,
                                    window_start=window,
                                    manager=manager)
        elapsed_ms = int((time.time() - started) * 1000)
        row.calls = int(getattr(row, 'calls', 0) or 0) + 1
        if not ok:
            row.errors = int(getattr(row, 'errors', 0) or 0) + 1
        row.bytes_out = int(getattr(row, 'bytes_out', 0) or 0) \
            + int(bytes_out or 0)
        row.bytes_in = int(getattr(row, 'bytes_in', 0) or 0) \
            + int(bytes_in or 0)
        row.latency_ms_sum = int(getattr(row, 'latency_ms_sum', 0)
                                 or 0) + elapsed_ms
        row.latency_ms_max = max(int(getattr(row, 'latency_ms_max',
                                             0) or 0), elapsed_ms)
        try:
            manager.db.saveInstanceInDB(row)
        except Exception:
            pass
        return True
    except Exception:
        return False


def usage_report(manager, engine):
    """The windows for one engine, newest first — or the honest
    'not tracked yet' when nothing was ever recorded here."""
    tables = getattr(manager, 'objectTables', None) or {}
    rows = [r for r in tables.get('EngineUsageWindow', {}).values()
            if getattr(r, 'engine', '') == engine]
    if not rows:
        return {'tracked': False, 'windows': [],
                'note': 'no traffic recorded through this '
                        'instance\'s seam yet — metering starts '
                        'with the first remote call'}
    rows.sort(key=lambda r: getattr(r, 'window_start', ''),
              reverse=True)
    windows = []
    for r in rows[:REPORT_WINDOWS]:
        calls = int(getattr(r, 'calls', 0) or 0)
        lat_sum = int(getattr(r, 'latency_ms_sum', 0) or 0)
        windows.append({
            'windowStart': getattr(r, 'window_start', ''),
            'calls': calls,
            'errors': int(getattr(r, 'errors', 0) or 0),
            'bytesOut': int(getattr(r, 'bytes_out', 0) or 0),
            'bytesIn': int(getattr(r, 'bytes_in', 0) or 0),
            'latencyMsAvg': (lat_sum // calls) if calls else 0,
            'latencyMsMax': int(getattr(r, 'latency_ms_max', 0)
                                or 0),
        })
    return {'tracked': True, 'windows': windows, 'note': ''}


def binding_url(engine):
    """The EngineProviderBinding rung of the resolution ladder —
    the row form of the *_ENGINES_URL knob ('' when unbound)."""
    try:
        manager = _manager()
        if manager is None:
            return ''
        tables = getattr(manager, 'objectTables', None) or {}
        for row in tables.get('EngineProviderBinding', {}).values():
            if getattr(row, 'name', '') == engine:
                return (getattr(row, 'url', '') or '').rstrip('/')
    except Exception:
        pass
    return ''
