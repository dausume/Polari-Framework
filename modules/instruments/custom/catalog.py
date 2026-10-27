"""
@module instruments.custom.catalog

osc-0: the instrument MODELS as the workbench sees them, and the instruments-on-a-bench doors (OSCILLOSCOPE_PLAN.md §2 "workbench
tie-in"). The Bench row (board module) gained `instruments_json` = [{model, count, note}]; this file owns every read and write of it
so the board module never imports instruments (the dependency points instruments -> board).

    models(manager)                                   -> [dict]  live Instrument rows else the seed
    model_rows(manager)                               -> [dict]  the models with the card's TEXT fields derived (bandwidth, sample rate per channel count ...)
    bench_options(manager, bench_name)                -> [dict]  model_rows + on_bench / can_add for the picker
    instrument_rows(bench, manager)                   -> [dict]  what is on the bench
    add_instrument(manager, bench_name, body)         -> (status, payload)
    remove_instrument(manager, bench_name, body)      -> (status, payload)
Every text field says "unverified" for -1 / '' (derive-or-cite: the word is the honest value, never a guess).
"""
import json

from board.custom import bench as BENCH
from instruments import instruments_seed as SEED

_FIELDS = ('name', 'vendor', 'model', 'kind', 'family', 'channels', 'ext_trigger', 'bandwidth_hz', 'rise_time_ns', 'sample_rate_sps',
           'sample_rate_by_channels_json', 'memory_depth_pts', 'memory_depth_by_channels_json', 'resolution_bits', 'capture_rate_wfms',
           'capture_rate_basis', 'input_impedance_ohm', 'input_capacitance_pf', 'max_input_v_rms', 'sensitivity_min_v_div',
           'sensitivity_max_v_div', 'timebase_min_s_div', 'timebase_max_s_div', 'bw_limits', 'trigger_types', 'transports_json', 'lineage',
           'idn_format', 'lxi', 'display', 'size_mm', 'price_usd', 'price_basis', 'citation', 'emulated', 'emulator_profile', 'note',
           'digital_channels', 'digital_max_rate_sps', 'differential_inputs', 'ets_sample_rate_sps', 'openness', 'data_access')


def _j(text, default):
    try:
        v = json.loads(text) if isinstance(text, str) else text
    except ValueError:
        return default
    return default if v is None else v


def _dict(row):
    return dict(row) if isinstance(row, dict) else {k: getattr(row, k, '') for k in _FIELDS}


def models(manager=None):
    live = [_dict(r) for r in BENCH._live_rows(manager, 'Instrument')]
    return live or [dict(r) for r in SEED.SEED_INSTRUMENTS]


# ---------------------------------------------------------------------------------------------------- text (the card)
def _si(value, unit, places=4):
    """A number in engineering words: 1.25e9 'Sa/s' -> '1.25 GSa/s', 312.5e6 -> '312.5 MSa/s'; -1 -> 'unverified'."""
    try:
        v = float(value)
    except (TypeError, ValueError):
        return 'unverified'
    if v < 0:
        return 'unverified'
    for div, prefix in ((1e9, 'G'), (1e6, 'M'), (1e3, 'k')):
        if v >= div:
            return ('%.*g %s%s' % (places, v / div, prefix, unit)).replace(' ', ' ')
    if v < 1e-3 and v > 0:
        return '%.*g u%s' % (places, v * 1e6, unit)
    if v < 1 and v > 0:
        return '%.*g m%s' % (places, v * 1e3, unit)
    return '%.*g %s' % (places, v, unit)


def _per_channels(table_json, unit):
    t = _j(table_json, {})
    if not t:
        return 'unverified'
    return ' / '.join('%s with %s ch' % (_si(v, unit), k) for k, v in sorted(t.items(), key=lambda kv: int(kv[0])))


def _transports(text):
    ts = _j(text, [])
    out = []
    for t in ts:
        port = t.get('port', -1)
        if isinstance(port, int) and port > 0:
            out.append('%s:%d' % (t.get('name', '?'), port))
        elif port == 0:
            out.append(t.get('name', '?'))
        else:
            out.append('%s (unverified)' % t.get('name', '?'))
    return ', '.join(out) or 'unverified'


def _signals_text(m):
    """osc-6: which signal KINDS the instrument takes - 'analog x4; digital: on a spare analog channel; differential: by A - B of two channels'."""
    ch, dg, df = m.get('channels', -1), m.get('digital_channels', -1), m.get('differential_inputs', -1)
    parts = ['analog x%d' % ch if isinstance(ch, int) and ch >= 0 else 'analog: unverified']
    if isinstance(dg, int) and dg > 0:
        parts.append('digital x%d (logic inputs%s)' % (dg, (' at %s' % _si(m.get('digital_max_rate_sps', -1), 'Sa/s')) if float(m.get('digital_max_rate_sps', -1) or -1) > 0 else ''))
    elif dg == 0:
        parts.append('digital: on a spare analog channel (no logic inputs)')
    else:
        parts.append('digital: unverified')
    if isinstance(df, int) and df > 0:
        parts.append('differential x%d (native)' % df)
    elif df == 0:
        parts.append('differential: by A - B of two analog channels' if isinstance(ch, int) and ch >= 2 else 'differential: no (one channel, no native input)')
    else:
        parts.append('differential: unverified')
    ets = float(m.get('ets_sample_rate_sps', -1) or -1)
    if ets > 0:
        parts.append('ETS %s for repetitive signals' % _si(ets, 'Sa/s'))
    return '; '.join(parts)


def model_rows(manager=None):
    rows = []
    for m in models(manager):
        ch = m.get('channels', -1)
        rows.append(dict(m,
                         signals=_signals_text(m),
                         openness_text=m.get('openness') or 'unverified',
                         data_access_text=m.get('data_access') or 'unverified',
                         title='%s %s' % (m.get('vendor', ''), m.get('model', '')),
                         channels_text=('unverified' if not isinstance(ch, int) or ch < 0 else ('%d + EXT' % ch if m.get('ext_trigger') else str(ch))),
                         bandwidth=_si(m.get('bandwidth_hz', -1), 'Hz'),
                         sample_rate=_per_channels(m.get('sample_rate_by_channels_json'), 'Sa/s'),
                         memory_depth=_per_channels(m.get('memory_depth_by_channels_json'), 'pts'),
                         resolution=('%d bits' % m['resolution_bits']) if isinstance(m.get('resolution_bits'), int) and m['resolution_bits'] > 0 else 'unverified',
                         capture_rate=('{:,} wfms/s'.format(int(m['capture_rate_wfms'])) if float(m.get('capture_rate_wfms', -1) or -1) > 0 else 'unverified'),
                         sensitivity=('%s to %s' % (_si(m.get('sensitivity_min_v_div', -1), 'V/div'), _si(m.get('sensitivity_max_v_div', -1), 'V/div'))
                                      if float(m.get('sensitivity_min_v_div', -1) or -1) > 0 else 'unverified'),
                         transports=_transports(m.get('transports_json')),
                         emulator=('yes (%s)' % m.get('emulator_profile') if m.get('emulated')
                                   else ('dialect proof only (%s)' % m['emulator_profile'] if m.get('emulator_profile') else 'not yet')),
                         price=('USD %g' % m['price_usd']) if float(m.get('price_usd', -1) or -1) > 0 else 'unverified'))
    return rows


# ---------------------------------------------------------------------------------------------------- the bench
def instrument_rows(b, manager=None):
    by = {m['name']: m for m in model_rows(manager)}
    rows = []
    for e in _j((b or {}).get('instruments_json'), []):
        m = by.get(e.get('model', '')) or {'title': e.get('model', ''), 'channels_text': 'unverified', 'bandwidth': 'unverified', 'emulator': 'unverified'}
        rows.append({'model': e.get('model', ''), 'title': m['title'], 'count': int(e.get('count') or 1), 'channels': m['channels_text'],
                     'bandwidth': m['bandwidth'], 'emulator': m['emulator'], 'note': e.get('note', '')})
    return rows


def bench_options(manager=None, bench_name=''):
    b = BENCH.bench(bench_name, manager) if bench_name else None
    on = {e.get('model', ''): int(e.get('count') or 1) for e in _j((b or {}).get('instruments_json'), [])}
    return [dict(m, on_bench=on.get(m['name'], 0), can_add=m.get('kind') == 'oscilloscope', bench=bench_name) for m in model_rows(manager)]


def add_instrument(manager, bench_name, body):
    b = BENCH.bench(bench_name, manager)
    if b is None:
        return 404, {'ok': False, 'error': 'no bench named %r' % bench_name}
    key = str((body or {}).get('model', '')).strip()
    ms = {m['name']: m for m in models(manager)}
    if key not in ms:
        return 404, {'ok': False, 'error': 'no instrument model named %r' % key, 'known': sorted(ms)}
    if ms[key].get('kind') != 'oscilloscope':
        return 400, {'ok': False, 'error': '%r is a vendor lineage, not a model - read a datasheet and add the model first' % key}
    try:
        raw = body.get('count', 1)
        count = 1 if raw in (None, '') else int(raw)
    except (TypeError, ValueError):
        return 400, {'ok': False, 'error': 'count must be a whole number'}
    if count < 1:
        return 400, {'ok': False, 'error': 'count must be 1 or more'}
    entries = _j(b.get('instruments_json'), [])
    hit = next((e for e in entries if e.get('model') == key), None)
    if hit:
        hit['count'] = int(hit.get('count') or 1) + count
    else:
        entries.append({'model': key, 'count': count, 'note': str(body.get('note') or '')})
    b['instruments_json'] = json.dumps(entries)
    BENCH._save(manager, b)
    return 201, {'ok': True, 'bench': bench_name, 'added': key, 'count': count, 'rows': instrument_rows(b, manager)}


def remove_instrument(manager, bench_name, body):
    b = BENCH.bench(bench_name, manager)
    if b is None:
        return 404, {'ok': False, 'error': 'no bench named %r' % bench_name}
    key = str((body or {}).get('model', '')).strip()
    entries = _j(b.get('instruments_json'), [])
    hit = next((e for e in entries if e.get('model') == key), None)
    if hit is None:
        return 404, {'ok': False, 'error': 'no instrument %r on bench %s' % (key, bench_name)}
    if int(hit.get('count') or 1) > 1:
        hit['count'] = int(hit['count']) - 1
    else:
        entries.remove(hit)
    b['instruments_json'] = json.dumps(entries)
    BENCH._save(manager, b)
    return 200, {'ok': True, 'bench': bench_name, 'removed': key, 'rows': instrument_rows(b, manager)}


# ---------------------------------------------------------------------------------------------------- doors
def get_door(manager, params, which, bench_name=''):
    if which == 'models':
        return 200, {'ok': True, 'rows': model_rows(manager)}
    if which == 'bench-options':
        return 200, {'ok': True, 'rows': bench_options(manager, (params.get('bench') or SEED_HOME()).strip())}
    b = BENCH.bench(bench_name, manager)
    if b is None:
        return 404, {'ok': False, 'error': 'no bench named %r' % bench_name, 'known': [x['name'] for x in BENCH.benches(manager)]}
    if which == 'bench':
        return 200, {'ok': True, 'bench': bench_name, 'rows': instrument_rows(b, manager)}
    if which == 'testability':          # osc-6: GET with the needs as query params
        from instruments.custom import testability as T
        return T.door(manager, bench_name, dict(params))
    if which == 'units':                # osc-8: the bench's instruments as UNITS with probes + endpoint status
        from instruments.custom import placement as P
        return P.units_door(manager, bench_name)
    return 404, {'ok': False, 'error': 'unknown door'}


def post_door(manager, bench_name, which, body):
    if not isinstance(body, dict):
        return 400, {'ok': False, 'error': 'the body must be a JSON object'}
    if which == 'add':
        return add_instrument(manager, bench_name, body)
    if which == 'remove':
        return remove_instrument(manager, bench_name, body)
    if which == 'testability':          # osc-6: POST with the needs as the body
        from instruments.custom import testability as T
        return T.door(manager, bench_name, body)
    if which in ('probe', 'simulate', 'stop'):   # osc-8: a unit's channel on a bench line; every probed unit emulated + fed from a stimulus; stop them
        from instruments.custom import placement as P
        return {'probe': P.probe, 'simulate': P.simulate, 'stop': lambda m, b, _body: P.stop_all(m, b)}[which](manager, bench_name, body)
    return 404, {'ok': False, 'error': 'unknown door'}


def signal_kind_rows():
    from board.custom import signal_kinds as SK
    return SK.kind_rows()


def SEED_HOME():
    from board.custom import bench_seed
    return bench_seed.HOME_BENCH
