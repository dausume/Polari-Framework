"""
@module instruments.custom.captures

osc-3: the ENDPOINT / EMULATOR / CAPTURE doors behind instruments_api — rows live on the manager when there is one, else in this process's
memory (`_MEM`, the selftests' store). Every write path is a door; nothing here is seeded.

  endpoints(manager) · add_endpoint(manager, body{name, instrument, transport, address, port, note}) -> (201|400|409, payload)
  start_emulator(manager, body{profile, name?, strict_idn?, refuse_wav_data?, sources?}) -> starts an Emulator IN THIS PROCESS on a free
        loopback port and adds its endpoint row (transport scpi-raw, address 127.0.0.1 — the loopback is not an identifier); osc-5 moves it
        to an isle app and the endpoint then names the service instead
  idn(manager, name) -> asks *IDN?, writes status / last_idn / checked_at on the row, answers the words (a refusal is a 502 with the words)
  capture(manager, name, body{channels, max_points, fmt}) -> one acquisition -> a WaveformCapture row per channel (raw inline, base64, when
        <= INLINE_LIMIT bytes; the sha256 always), answers the per-channel summary
  captures(manager) · chart_rows(manager, acquisition, max_rows) -> long-form {t_s, ch1..ch4} rows for named-graph-panel, decimated by a
        plain stride to <= max_rows (every kept sample is a real sample; a min/max envelope is a later knob)
"""
import base64
import datetime
import hashlib
import json
import threading

import numpy as np

from instruments.custom import client as CL
from instruments.custom import lineage as L
from instruments.custom import sources as SRC

INLINE_LIMIT = 2 * 1024 * 1024      # bytes of payload kept inline on a dev instance (1 Mpt of WORD data)
_MEM = {'InstrumentEndpoint': {}, 'WaveformCapture': {}, 'ScopeChannel': {}}     # ScopeChannel: osc-8's probes (instruments.custom.placement)
_EMUS = {}      # endpoint name -> Emulator (this process)
_lock = threading.Lock()
_E_FIELDS = ('name', 'instrument', 'transport', 'address', 'port', 'resource', 'status', 'last_idn', 'checked_at', 'note')
_C_FIELDS = ('name', 'endpoint', 'instrument', 'channel', 'acquired_at', 'acquisition', 'points', 'format', 'lineage', 'x_increment', 'x_origin',
             'x_reference', 'y_increment', 'y_origin', 'y_reference', 'sample_rate_sps', 'memory_depth_pts', 'trigger_json', 'settings_json',
             'raw_sha256', 'raw_bytes', 'raw_path', 'raw_b64', 'preamble_text', 'source', 'source_ref', 'note')


def _now():
    return datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')


# ---------------------------------------------------------------------------------------------------- stores
def _rows(manager, cls, fields):
    if manager is None:
        return [dict(r) for r in _MEM[cls].values()]
    table = (getattr(manager, 'objectTables', None) or {}).get(cls, {}) or {}
    return [{k: getattr(r, k, '') for k in fields} for r in table.values()]


def _upsert(manager, cls, fields, row):
    if manager is None:
        _MEM[cls][row['name']] = dict(row)
        return row
    from instruments.instruments_basis import InstrumentEndpoint, WaveformCapture, ScopeChannel
    klass = {'InstrumentEndpoint': InstrumentEndpoint, 'WaveformCapture': WaveformCapture, 'ScopeChannel': ScopeChannel}[cls]
    table = (manager.objectTables or {}).setdefault(cls, {})
    hit = next((r for r in table.values() if getattr(r, 'name', '') == row['name']), None)
    if hit is None:
        hit = klass(manager=manager, **{k: row.get(k, '') for k in fields if k in row})
    else:
        for k in fields:
            if k in row:
                setattr(hit, k, row[k])
    try:
        manager.db.saveInstanceInDB(hit)
    except Exception:  # noqa: BLE001 - an in-memory manager has no db
        pass
    return row


def endpoints(manager=None):
    return _rows(manager, 'InstrumentEndpoint', _E_FIELDS)


def endpoint(manager, name):
    return next((e for e in endpoints(manager) if e['name'] == name), None)


def captures(manager=None):
    return _rows(manager, 'WaveformCapture', _C_FIELDS)


# ---------------------------------------------------------------------------------------------------- endpoints
def add_endpoint(manager, body):
    from instruments.custom import catalog as C
    from instruments.instruments_basis import TRANSPORTS
    name = str((body or {}).get('name', '')).strip()
    if not name:
        return 400, {'ok': False, 'error': 'name is required'}
    if endpoint(manager, name) is not None:
        return 409, {'ok': False, 'error': 'an endpoint named %r already exists' % name}
    inst = str(body.get('instrument', '')).strip()
    known = {m['name'] for m in C.models(manager) if m.get('kind') == 'oscilloscope'}
    if inst not in known:
        return 404, {'ok': False, 'error': 'no oscilloscope model named %r' % inst, 'known': sorted(known)}
    transport = str(body.get('transport') or 'scpi-raw')
    if transport not in TRANSPORTS:
        return 400, {'ok': False, 'error': 'transport must be one of %s' % ', '.join(TRANSPORTS)}
    try:
        port = int(body.get('port') or 0)
    except (TypeError, ValueError):
        return 400, {'ok': False, 'error': 'port must be a whole number'}
    row = {'name': name, 'instrument': inst, 'transport': transport, 'address': str(body.get('address') or '').strip(), 'port': port,
           'resource': str(body.get('resource') or ''), 'status': 'unchecked', 'last_idn': '', 'checked_at': '', 'note': str(body.get('note') or '')}
    if transport != 'emulator' and not row['address'] and not row['resource']:
        return 400, {'ok': False, 'error': 'an address (host or IP, typed here, never seeded) or a PyVISA resource string is required'}
    _upsert(manager, 'InstrumentEndpoint', _E_FIELDS, row)
    return 201, {'ok': True, 'endpoint': name, 'rows': endpoints(manager)}


_REMOTE = {}    # endpoint name -> (worker url, emulator id on the worker)   osc-5
_DESC = {}      # endpoint name -> the last source / feed words for a remote emulator (its source_ref)


def _on_worker(name):
    return _REMOTE.get(name)


def start_emulator(manager, body):
    from instruments.custom.emulator import Emulator, PROFILES
    from instruments.custom import scope_engines as SE
    from urllib.parse import urlparse
    body = body or {}
    profile = str(body.get('profile') or 'dho804')
    if profile not in PROFILES:
        return 400, {'ok': False, 'error': 'no emulator profile %r' % profile, 'known': sorted(PROFILES)}
    name = str(body.get('name') or 'emu-%s-%d' % (profile, len(_EMUS) + len(_REMOTE) + 1)).strip()
    if endpoint(manager, name) is not None:
        # osc-8: `restart` REUSES a stopped unit's endpoint row (same name, new port / session) so a bench simulated twice has no duplicate endpoints
        if not (body.get('restart') and name not in _EMUS and _on_worker(name) is None):
            return 409, {'ok': False, 'error': 'an endpoint named %r already exists' % name}
    where = SE.resolve(str(body.get('where') or 'auto'))
    if where['how'] == 'refused':
        return 502, {'ok': False, 'error': where['why'], 'where': where}
    if where['how'] == 'worker':
        # osc-5: the emulator runs on the scope-engines worker; its SCPI port is reached at the worker's host like a real instrument
        try:
            r = SE.post(where['url'], '/emulators', {'profile': profile, 'name': name, 'strict_idn': bool(body.get('strict_idn')),
                                                      'refuse_wav_data': bool(body.get('refuse_wav_data')), 'sources': body.get('sources') or {}})
        except SE.WorkerRefused as e:
            return 502, {'ok': False, 'error': 'the scope worker refused: %s' % e, 'where': where}
        host = urlparse(where['url']).hostname or ''
        _REMOTE[name] = (where['url'], r['id'])
        _DESC[name] = 'sources ' + ', '.join('ch%s %s' % (k, v) for k, v in sorted((r.get('sources') or {}).items()))
        row = {'name': name, 'instrument': PROFILES[profile]['instrument'], 'transport': 'scpi-raw', 'address': host, 'port': int(r['port']), 'resource': '',
               'status': 'unchecked', 'last_idn': '', 'checked_at': '', 'note': 'emulator on the scope-engines worker %s (id %s, session %s; %s)' % (where['url'], r['id'], r.get('session', ''), where['why'])}
        _upsert(manager, 'InstrumentEndpoint', _E_FIELDS, row)
        return 201, {'ok': True, 'endpoint': name, 'port': int(r['port']), 'session': r.get('session', ''), 'where': 'worker', 'url': where['url'], 'rows': endpoints(manager)}
    try:
        emu = Emulator(profile=profile, strict_idn=bool(body.get('strict_idn')), refuse_wav_data=bool(body.get('refuse_wav_data')))
        for ch, spec in (body.get('sources') or {}).items():
            emu.set_source(int(ch), spec)
    except ValueError as e:
        return 400, {'ok': False, 'error': str(e)}
    emu.start()
    with _lock:
        _EMUS[name] = emu
    row = {'name': name, 'instrument': PROFILES[profile]['instrument'], 'transport': 'scpi-raw', 'address': '127.0.0.1', 'port': emu.port, 'resource': '',
           'status': 'unchecked', 'last_idn': '', 'checked_at': '', 'note': 'emulator in the backend process (profile %s, session %s)' % (profile, emu.state.session)}
    _upsert(manager, 'InstrumentEndpoint', _E_FIELDS, row)
    return 201, {'ok': True, 'endpoint': name, 'port': emu.port, 'session': emu.state.session, 'where': 'local', 'rows': endpoints(manager)}


def stop_emulator(manager, name):
    from instruments.custom import scope_engines as SE
    remote = _on_worker(name)
    if remote:
        url, eid = remote
        try:
            SE.delete(url, '/emulators/%s' % eid)
        except SE.WorkerRefused as e:
            return 502, {'ok': False, 'error': 'the scope worker refused the stop: %s' % e}
        _REMOTE.pop(name, None)
        _DESC.pop(name, None)
        emu = None
    else:
        with _lock:
            emu = _EMUS.pop(name, None)
        if emu is None:
            return 404, {'ok': False, 'error': 'no running emulator named %r (in this process or on a worker)' % name}
        emu.stop()
    e = endpoint(manager, name)
    if e:
        _upsert(manager, 'InstrumentEndpoint', _E_FIELDS, dict(e, status='stopped', checked_at=_now()))
    return 200, {'ok': True, 'endpoint': name, 'rows': endpoints(manager)}


def set_source(manager, name, body):
    from instruments.custom import scope_engines as SE
    remote = _on_worker(name)
    if remote:
        try:
            ch = int((body or {}).get('channel', 0))
            r = SE.post(remote[0], '/emulators/%s/source' % remote[1], {'channel': ch, 'source': (body or {}).get('source')})
        except (TypeError, ValueError) as e:
            return 400, {'ok': False, 'error': str(e)}
        except SE.WorkerRefused as e:
            return 400, {'ok': False, 'error': str(e)}
        _DESC[name] = 'ch%d %s' % (ch, r.get('source', ''))
        return 200, {'ok': True, 'endpoint': name, 'channel': ch, 'source': r.get('source', ''), 'where': 'worker'}
    emu = _EMUS.get(name)
    if emu is None:
        return 404, {'ok': False, 'error': 'no running emulator named %r (in this process or on a worker)' % name}
    try:
        ch = int((body or {}).get('channel', 0))
        emu.set_source(ch, body.get('source'))
    except (TypeError, ValueError, KeyError) as e:
        return 400, {'ok': False, 'error': str(e) or 'channel + source are required'}
    return 200, {'ok': True, 'endpoint': name, 'channel': ch, 'source': SRC.describe(body['source'])}


def feed_device(manager, name, body):
    """osc-4: {stimulus: <variant>, channels: {'1': 'PD2', '2': 'adc0'}} or {events: [...], cps: 16000000, seconds: S, channels: {'1': 'PD6'}} ->
    the named lines become the emulator's channel sources (instruments.custom.device_feed)."""
    from instruments.custom import device_feed as DF
    from instruments.custom import scope_engines as SE
    emu = _EMUS.get(name)
    remote = _on_worker(name)
    if emu is None and not remote:
        return 404, {'ok': False, 'error': 'no running emulator named %r (in this process or on a worker)' % name}
    body = body or {}
    mapping = body.get('channels') or {}
    if not isinstance(mapping, dict) or not mapping:
        return 400, {'ok': False, 'error': 'channels is {channel number: line name}, e.g. {"1": "PD2", "2": "adc0"}'}
    try:
        if body.get('stimulus'):
            st = DF.sources_from_stimulus(str(body['stimulus']))
            lines, seconds, ref = st['sources'], st['seconds'], st['describe']
        elif body.get('events') is not None:
            lines = DF.sources_from_events(body['events'], float(body.get('cps') or 0) or 16e6)
            seconds = float(body.get('seconds') or 0) or (max((e[-1][0] for e in (l['edges'] for l in lines.values()) if e), default=1.0) * 1.1)
            ref = 'twin events (%d lines, %s cycles/s)' % (len(lines), body.get('cps') or '16e6')
        else:
            return 400, {'ok': False, 'error': 'give a stimulus (a cycle_stimuli variant) or events (the twin\'s pin events) to feed from'}
        unknown = [v for v in mapping.values() if v not in lines]
        if unknown:
            return 404, {'ok': False, 'error': 'no such line(s) in the feed: %s' % ', '.join(map(str, unknown)), 'known': sorted(lines)}
        if remote:
            # osc-5: the worker carries no board module, so the lines are resolved HERE and the specs posted
            r = SE.post(remote[0], '/emulators/%s/feed' % remote[1], {'channels': {str(ch): lines[v] for ch, v in mapping.items()}, 'seconds': seconds, 'depth': body.get('depth')})
            desc = {int(k): v for k, v in (r.get('channels') or {}).items()}
            _DESC[name] = 'feed from ' + ref
        else:
            desc = DF.feed(emu, {ch: lines[v] for ch, v in mapping.items()}, seconds, depth=body.get('depth'))
            emu.feed_ref = ref
    except KeyError as e:
        return 404, {'ok': False, 'error': 'no stimulus for variant %s' % e}
    except (TypeError, ValueError) as e:
        return 400, {'ok': False, 'error': str(e)}
    except SE.WorkerRefused as e:
        return 502, {'ok': False, 'error': 'the scope worker refused the feed: %s' % e}
    return 200, {'ok': True, 'endpoint': name, 'seconds': seconds, 'channels': {str(k): '%s <- %s' % (v, mapping[str(k)] if str(k) in mapping else mapping[k]) for k, v in desc.items()},
                 'lines': sorted(lines), 'source_ref': ref}


def _dialect(manager, e):
    """The command dialect the endpoint's instrument MODEL speaks (its Instrument row's lineage; agilent when unknown)."""
    from instruments.custom import catalog as C
    m = next((m for m in C.models(manager) if m['name'] == e.get('instrument', '')), None)
    return 'tektronix' if (m or {}).get('lineage') == 'tektronix' else 'agilent'


def _client(e, manager=None):
    return CL.ScopeClient(e.get('address') or '127.0.0.1', e.get('port') or 0, transport=e.get('transport') or 'scpi-raw', resource=e.get('resource') or '',
                          dialect=_dialect(manager, e))


def idn(manager, name):
    e = endpoint(manager, name)
    if e is None:
        return 404, {'ok': False, 'error': 'no endpoint named %r' % name}
    try:
        with _client(e, manager) as sc:
            words = sc.idn()
        status = 'answered'
    except CL.ScopeRefusal as ex:
        words, status = str(ex), 'refused'
    except OSError as ex:
        words, status = 'unreachable: %s' % ex, 'unreachable'
    _upsert(manager, 'InstrumentEndpoint', _E_FIELDS, dict(e, status=status, last_idn=words, checked_at=_now()))
    return (200 if status == 'answered' else 502), {'ok': status == 'answered', 'endpoint': name, 'status': status, 'idn': words, 'error': '' if status == 'answered' else words}


# ---------------------------------------------------------------------------------------------------- captures
def capture(manager, name, body):
    e = endpoint(manager, name)
    if e is None:
        return 404, {'ok': False, 'error': 'no endpoint named %r' % name}
    body = body or {}
    try:
        wanted = body.get('channels')
        if not wanted and str(body.get('channels_text') or '').strip():      # the page's door-form sends the typed comma list
            wanted = [c for c in str(body['channels_text']).split(',') if c.strip()]
        if not wanted:      # osc-8: blank = every channel the endpoint's MODEL has (a one-channel DSO138 stand-in is asked for channel 1 only)
            from instruments.custom import catalog as C
            m = next((m for m in C.models(manager) if m['name'] == e.get('instrument', '')), None)
            nch = int((m or {}).get('channels') or -1)
            wanted = list(range(1, (nch if 0 < nch <= 4 else 4) + 1))
        channels = [int(c) for c in wanted]
        max_points = int(body['max_points']) if body.get('max_points') not in (None, '') else None
    except (TypeError, ValueError):
        return 400, {'ok': False, 'error': 'channels must be whole numbers and max_points a whole number'}
    fmt = str(body.get('fmt') or 'WORD').upper()
    if fmt not in ('WORD', 'BYTE'):
        return 400, {'ok': False, 'error': 'fmt is WORD or BYTE'}
    acq = 'acq-%s-%s' % (datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%S'), hashlib.sha256(('%s%d' % (name, len(captures(manager)))).encode()).hexdigest()[:6])
    emu = _EMUS.get(name)
    try:
        with _client(e, manager) as sc:
            reads = sc.capture(channels, fmt=fmt, max_points=max_points)
    except CL.ScopeRefusal as ex:
        _upsert(manager, 'InstrumentEndpoint', _E_FIELDS, dict(e, status='refused', last_idn=str(ex), checked_at=_now()))
        return 502, {'ok': False, 'error': 'the instrument refused: %s' % ex, 'endpoint': name}
    except OSError as ex:
        _upsert(manager, 'InstrumentEndpoint', _E_FIELDS, dict(e, status='unreachable', last_idn=str(ex), checked_at=_now()))
        return 502, {'ok': False, 'error': 'unreachable: %s' % ex, 'endpoint': name}
    rows, now = [], _now()
    for r in reads:
        payload = r.pop('payload')
        source_ref = ''
        if emu is not None:
            source_ref = 'emulator %s session %s acquisition %d: %s%s' % (emu.state.profile, emu.state.session, emu.state.acquisitions, SRC.describe(emu.state.sources[r['channel']]),
                                                                          (' - from ' + emu.feed_ref) if getattr(emu, 'feed_ref', '') else '')
        elif _on_worker(name):
            source_ref = 'emulator on worker %s id %s: %s' % (_on_worker(name)[0], _on_worker(name)[1], _DESC.get(name, ''))
        row = {'name': '%s-ch%d' % (acq, r['channel']), 'endpoint': name, 'instrument': e.get('instrument', ''), 'channel': r['channel'], 'acquired_at': now,
               'acquisition': acq, 'points': r['points'], 'format': r['format'], 'lineage': r['lineage'],
               'x_increment': r['x_increment'], 'x_origin': r['x_origin'], 'x_reference': r['x_reference'],
               'y_increment': r['y_increment'], 'y_origin': r['y_origin'], 'y_reference': r['y_reference'],
               'sample_rate_sps': r['sample_rate_sps'], 'memory_depth_pts': r['memory_depth_pts'], 'trigger_json': json.dumps(r['trigger']),
               'settings_json': json.dumps(r['settings']), 'raw_sha256': r['raw_sha256'], 'raw_bytes': r['raw_bytes'], 'raw_path': '',
               'raw_b64': base64.b64encode(payload).decode() if len(payload) <= INLINE_LIMIT else '', 'preamble_text': r['preamble_text'],
               'source': 'emulated' if (emu is not None or _on_worker(name)) else 'real', 'source_ref': source_ref, 'note': ''}
        _upsert(manager, 'WaveformCapture', _C_FIELDS, row)
        rows.append(summary(row))
    _upsert(manager, 'InstrumentEndpoint', _E_FIELDS, dict(e, status='answered', checked_at=now))
    return 201, {'ok': True, 'endpoint': name, 'acquisition': acq, 'rows': rows}


def summary(row):
    f = {k: row[k] for k in ('x_increment', 'x_origin', 'x_reference', 'y_increment', 'y_origin', 'y_reference', 'lineage')}
    out = {k: row[k] for k in ('name', 'endpoint', 'instrument', 'channel', 'acquired_at', 'acquisition', 'points', 'format', 'lineage', 'raw_sha256', 'raw_bytes', 'source', 'source_ref')}
    out['sample_rate'] = '%g Sa/s' % row['sample_rate_sps']
    out['span_s'] = row['points'] * row['x_increment']
    out['stored'] = 'inline' if row.get('raw_b64') else ('file ' + row['raw_path'] if row.get('raw_path') else 'sha only')
    if row.get('raw_b64'):
        v = L.volts(L.samples(base64.b64decode(row['raw_b64']), row['format']), f)
        out['v_min'], out['v_max'], out['v_mean'] = float(v.min()), float(v.max()), float(v.mean())
    return out


def capture_rows(manager=None):
    return [summary(r) for r in captures(manager)]


def chart_rows(manager, acquisition, max_rows=4000):
    chs = [r for r in captures(manager) if r['acquisition'] == acquisition]
    if not chs:
        return 404, {'ok': False, 'error': 'no capture with acquisition %r' % acquisition, 'known': sorted({r['acquisition'] for r in captures(manager)})}
    series, n = {}, None
    for r in sorted(chs, key=lambda x: x['channel']):
        if not r.get('raw_b64'):
            return 409, {'ok': False, 'error': 'capture %s has no inline samples (stored %s); the chart reads inline data only in this slice' % (r['name'], r.get('raw_path') or 'sha only')}
        f = {k: r[k] for k in ('x_increment', 'x_origin', 'x_reference', 'y_increment', 'y_origin', 'y_reference', 'lineage')}
        v = L.volts(L.samples(base64.b64decode(r['raw_b64']), r['format']), f)
        series['ch%d' % r['channel']] = v
        n = min(n, len(v)) if n else len(v)
        t = L.times(len(v), f)
    n = n or 0
    stride = max(1, -(-n // int(max_rows)))
    idx = np.arange(0, n, stride)
    rows = [{'t_s': float(t[i]), **{k: float(s[i]) for k, s in series.items()}} for i in idx]
    return 200, {'ok': True, 'acquisition': acquisition, 'rows': rows, 'points': n, 'stride': stride, 'channels': sorted(series)}
