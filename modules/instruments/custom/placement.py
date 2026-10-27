"""
@module instruments.custom.placement

osc-8 (OSCILLOSCOPE_PLAN.md §2c, his ask 2026-10-27: "place devices like oscilloscopes on the bench (or more than one) and use them in simulation as well"):
the instruments on a bench as UNITS with PROBES, each unit USED IN SIMULATION through its own emulator.

  units(bench_name, manager)                -> one row per UNIT: a bench entry {model, count} is count units named `<bench>-<model>-<n>`; each carries its
                                               probes (ScopeChannel rows keyed by the unit's endpoint name - D-osc-9 recommended: the class exists and a real
                                               instrument's channels use the same rows), its endpoint status (not started | unchecked | answered | stopped ...),
                                               and the emulator profile that stands in for it.
  profile_for_model(row)                    -> (profile name, stand_in): the row's own `emulator_profile` when it is emulated (the DHO804), else a CAPABILITY
                                               STAND-IN built from the row's cited numbers and registered as `row:<name>` in emulator.PROFILES (channels, bits,
                                               sample rate and depth per channel count, sensitivity, timebase; a -1 takes a default the profile's `basis` names).
                                               The PROTOCOL is Polari's agilent-lineage emulator, not the instrument's (ScopeFun speaks its own USB protocol, the
                                               DSO138 a serial text line) - `*IDN?` says POLARI,<model>-EMU and `basis` says "capability stand-in". That is what
                                               "use them in simulation" honestly means before osc-7's adapters exist.
  probe(manager, bench, {model, unit, channel, line})  -> a ScopeChannel row `<unit>-ch<n>` with `probing` = the bench LINE (a board pin / net the pin view
                                               knows: PD2, adc0 ...); refuses a channel the model does not have (the DSO138 has one; a logic input is not a
                                               scope channel - said in the words); an empty line clears the probe. The signal kind rides on the pin view's
                                               vocabulary (board.custom.signal_kinds): a port bit is a level, an ADC line a voltage.
  simulate(manager, bench, {stimulus | events (+cps, seconds), units?})  -> per unit WITH probes: stop any running emulator of that name, start one on the
                                               unit's profile (the endpoint row is REUSED - no duplicate endpoints), feed its probes from the stimulus / events
                                               (captures.feed_device: a line the stimulus does not drive is REFUSED naming the known ones - the row carries the
                                               words); one row per unit. ALIGNMENT: every unit is fed from the SAME stimulus clock, so cross-unit alignment is
                                               exact BY CONSTRUCTION - a simulation property, said on every row; real units keep the testability caveat
                                               (a shared trigger; jitter -1 until measured). Then the existing capture / chart doors work per unit.
"""
import re

from board.custom import bench as BENCH
from instruments.custom import captures as X
from instruments.custom import catalog as C

_PORT_BIT = re.compile(r'^P[A-L]\d{1,2}$', re.IGNORECASE)
_CH_FIELDS = ('name', 'endpoint', 'channel', 'enabled', 'scale_v_div', 'offset_v', 'coupling', 'bw_limit', 'probe', 'label', 'probing', 'basis',
              'signal_kind', 'threshold_v', 'pair_channel')
ALIGNMENT_SIMULATED = ('exact by construction: every unit is fed from the same stimulus clock (a simulation property); real units need a shared trigger and '
                       'their alignment is -1 until measured (testability rule)')
#: the defaults a stand-in takes for a -1 on the row (each one is said in the profile's basis, never silently)
_DEFAULTS = {'channels': 1, 'bits': 8, 'srate': 1e6, 'depth': 1e4, 'scale_min': 1e-3, 'scale_max': 10.0, 'tb_min': 5e-9, 'tb_max': 500.0}


def unit_name(bench_name, model, n):
    return '%s-%s-%d' % (bench_name, model, int(n))


# ---------------------------------------------------------------------------------------------------- stand-in profiles
def _pos(v):
    try:
        f = float(v)
    except (TypeError, ValueError):
        return -1.0
    return f if f > 0 else -1.0


def _per_count(table_json, channels, flat, default, label, used, said):
    """{1..channels: value}: the row's per-channel-count table, a missing count taking the nearest LOWER count's value (a scope never gains rate or depth
    with more channels on), then the flat number, then the default (said)."""
    t = {int(k): float(v) for k, v in C._j(table_json, {}).items() if _pos(v) > 0}
    out, last = {}, None
    for n in range(1, channels + 1):
        if n in t:
            last = t[n]
        elif last is None:
            last = _pos(flat)
            if last < 0:
                last = default
                said.append('%s %g (no number on the row)' % (label, default))
            else:
                used.append('%s %g' % (label, last))
        out[n] = last
    if t:
        used.append('%s per channel count %s' % (label, ', '.join('%d ch %g' % (k, v) for k, v in sorted(t.items()))))
    return out


def standin_profile(row):
    """A capability stand-in emulator profile from an Instrument row's cited numbers; every default is named in `basis`."""
    used, said = [], []
    ch = int(row.get('channels') or -1)
    if ch <= 0:
        ch, _ = _DEFAULTS['channels'], said.append('channels %d (unverified on the row)' % _DEFAULTS['channels'])
    else:
        used.append('channels %d' % ch)
    bits = int(row.get('resolution_bits') or -1)
    if bits <= 0:
        bits, _ = _DEFAULTS['bits'], said.append('bits %d (unverified on the row)' % _DEFAULTS['bits'])
    else:
        used.append('bits %d' % bits)
    srate = _per_count(row.get('sample_rate_by_channels_json'), ch, row.get('sample_rate_sps'), _DEFAULTS['srate'], 'sample rate Sa/s', used, said)
    depth = _per_count(row.get('memory_depth_by_channels_json'), ch, row.get('memory_depth_pts'), _DEFAULTS['depth'], 'depth pts', used, said)
    nums = {}
    for key, field, label in (('scale_min', 'sensitivity_min_v_div', 'sensitivity min V/div'), ('scale_max', 'sensitivity_max_v_div', 'sensitivity max V/div'),
                              ('tb_min', 'timebase_min_s_div', 'timebase min s/div'), ('tb_max', 'timebase_max_s_div', 'timebase max s/div')):
        v = _pos(row.get(field))
        if v < 0:
            nums[key] = _DEFAULTS[key]
            said.append('%s %g (unverified on the row)' % (label, _DEFAULTS[key]))
        else:
            nums[key] = v
            used.append('%s %g' % (label, v))
    transports = ', '.join(t.get('name', '?') for t in C._j(row.get('transports_json'), [])) or 'unverified'
    return {'vendor': str(row.get('vendor') or 'UNKNOWN').upper(), 'model': str(row.get('model') or row.get('name') or 'MODEL').upper().replace(',', ' '),
            'instrument': row.get('name', ''), 'dialect': 'agilent', 'channels': ch, 'bits': bits, 'max_srate': srate, 'max_depth': depth,
            'page_points': 250000, 'default_depth': int(min(10000, depth[1])), 'divisions_h': 10, 'divisions_v': 8, 'pretrigger_div': -5,
            'scale_min': nums['scale_min'], 'scale_max': nums['scale_max'], 'tb_min': nums['tb_min'], 'tb_max': nums['tb_max'], 'bw_limits': ('OFF',),
            'stand_in': True,
            'basis': 'CAPABILITY STAND-IN for %s (osc-8): the limits are the Instrument row\'s cited numbers (%s)%s; the PROTOCOL is Polari\'s agilent-lineage '
                     'SCPI emulator, not the instrument\'s own (%s) - *IDN? says POLARI,%s-EMU; 10 x 8 divisions, -5 div pre-trigger and 250k-point pages are '
                     'the emulator\'s conventions, not the instrument\'s' % (row.get('name', ''), '; '.join(used) or 'none',
                                                                               ('; defaults said: ' + '; '.join(said)) if said else '', transports,
                                                                               str(row.get('model') or '').upper())}


def profile_for_model(row):
    """(profile name, stand_in) - the row's own emulator profile when it is emulated, else a stand-in registered as row:<name>."""
    from instruments.custom.emulator import PROFILES
    own = row.get('emulator_profile') or ''
    if row.get('emulated') and own in PROFILES:
        return own, False
    name = 'row:%s' % row.get('name', '')
    if name not in PROFILES:
        PROFILES[name] = standin_profile(row)
    return name, True


# ---------------------------------------------------------------------------------------------------- probes (ScopeChannel rows)
def channel_rows(manager=None):
    return X._rows(manager, 'ScopeChannel', _CH_FIELDS)


def probes_of(unit, manager=None):
    """{channel: line} for the unit's channels that are on a line."""
    return {int(r['channel']): r['probing'] for r in channel_rows(manager) if r.get('endpoint') == unit and r.get('probing')}


def _kind_of_line(line):
    from board.custom import signal_kinds as SK
    kind, why = SK.kind_of(line)
    if kind == 'undetermined' and _PORT_BIT.match(line or ''):
        return 'digital', 'a port bit (%s) is a level -> digital (no family rule names it; the port-bit pattern decides)' % line
    if kind == 'undetermined':
        return 'analog', 'no family rule names %r and it is not a port bit: read as volts (analog) until typed otherwise' % line
    return kind, why


# ---------------------------------------------------------------------------------------------------- units
def _entries(bench_name, manager):
    b = BENCH.bench(bench_name, manager)
    if b is None:
        return None, []
    return b, [e for e in C._j(b.get('instruments_json'), []) if e.get('model')]


def units(bench_name, manager=None):
    b, entries = _entries(bench_name, manager)
    if b is None:
        return None
    models = {m['name']: m for m in C.model_rows(manager)}
    eps = {e['name']: e for e in X.endpoints(manager)}
    rows = []
    for e in entries:
        m = models.get(e['model'])
        for n in range(1, int(e.get('count') or 1) + 1):
            u = unit_name(bench_name, e['model'], n)
            if m is None:
                profile, stand_in = '', True
            else:
                profile, stand_in = profile_for_model(m)
            probes = probes_of(u, manager)
            ep = eps.get(u) or {}
            rows.append({'unit': u, 'model': e['model'], 'title': (m or {}).get('title', e['model']), 'n': n, 'channels': int((m or {}).get('channels') or -1),
                         'probes': '; '.join('ch%d <- %s' % (c, l) for c, l in sorted(probes.items())) or '(none)', 'probes_json': probes,
                         'endpoint_status': ep.get('status') or 'not started', 'port': ep.get('port') or 0, 'profile': profile,
                         'profile_kind': 'stand-in (capability only)' if stand_in else 'model profile', 'note': e.get('note', '')})
    return rows


def _find_unit(bench_name, manager, body):
    """-> (status, payload | the unit row + its model)"""
    b, entries = _entries(bench_name, manager)
    if b is None:
        return 404, {'ok': False, 'error': 'no bench named %r' % bench_name, 'known': [x['name'] for x in BENCH.benches(manager)]}
    model = str((body or {}).get('model', '')).strip()
    entry = next((e for e in entries if e['model'] == model), None)
    if entry is None:
        return 404, {'ok': False, 'error': 'no instrument %r on bench %s' % (model, bench_name), 'known': [e['model'] for e in entries]}
    try:
        n = int(body.get('unit') or 1)
    except (TypeError, ValueError):
        return 400, {'ok': False, 'error': 'unit is the unit number (1..count)'}
    count = int(entry.get('count') or 1)
    if n < 1 or n > count:
        return 400, {'ok': False, 'error': 'bench %s has %d unit(s) of %s: unit must be 1..%d' % (bench_name, count, model, count)}
    m = next((x for x in C.models(manager) if x['name'] == model), None)
    if m is None:
        return 404, {'ok': False, 'error': 'no instrument model named %r' % model}
    return 200, {'unit': unit_name(bench_name, model, n), 'model': m, 'n': n}


def probe(manager, bench_name, body):
    body = body if isinstance(body, dict) else {}
    status, found = _find_unit(bench_name, manager, body)
    if status != 200:
        return status, found
    m, u = found['model'], found['unit']
    try:
        ch = int(body.get('channel') or 0)
    except (TypeError, ValueError):
        return 400, {'ok': False, 'error': 'channel is a whole number'}
    nch = int(m.get('channels') or -1)
    if nch < 1:
        return 400, {'ok': False, 'error': '%s has an unverified channel count on its row: no channel can be probed until it is read' % m['name']}
    if ch < 1 or ch > nch:
        dg = int(m.get('digital_channels') or 0)
        extra = ('; its %d logic input(s) are not scope channels (a logic input reads levels, never volts)' % dg) if dg > 0 else ''
        return 400, {'ok': False, 'error': '%s %s has %d analog channel(s): channel must be 1..%d%s' % (m.get('vendor', ''), m.get('model', ''), nch, nch, extra)}
    line = str(body.get('line') or '').strip()
    name = '%s-ch%d' % (u, ch)
    if not line:
        hit = next((r for r in channel_rows(manager) if r['name'] == name), None)
        if hit:
            X._upsert(manager, 'ScopeChannel', _CH_FIELDS, dict(hit, probing='', label='', basis='typed: probe cleared'))
        return 200, {'ok': True, 'bench': bench_name, 'unit': u, 'channel': ch, 'line': '', 'rows': units(bench_name, manager)}
    kind, why = _kind_of_line(line)
    row = {'name': name, 'endpoint': u, 'channel': ch, 'enabled': True, 'scale_v_div': 1.0, 'offset_v': 0.0, 'coupling': 'DC', 'bw_limit': 'OFF', 'probe': 1.0,
           'label': line, 'probing': line, 'basis': 'typed (osc-8 probe door); signal kind: %s' % why, 'signal_kind': kind, 'threshold_v': -1.0, 'pair_channel': 0}
    X._upsert(manager, 'ScopeChannel', _CH_FIELDS, row)
    return 201, {'ok': True, 'bench': bench_name, 'unit': u, 'channel': ch, 'line': line, 'signal_kind': kind, 'why': why, 'rows': units(bench_name, manager)}


# ---------------------------------------------------------------------------------------------------- simulate
def _running(name):
    return name in X._EMUS or X._on_worker(name) is not None


def simulate(manager, bench_name, body):
    body = body if isinstance(body, dict) else {}
    rows_all = units(bench_name, manager)
    if rows_all is None:
        return 404, {'ok': False, 'error': 'no bench named %r' % bench_name, 'known': [x['name'] for x in BENCH.benches(manager)]}
    feed = {}
    if body.get('stimulus'):
        feed['stimulus'] = str(body['stimulus']).strip()
    elif body.get('events') is not None:
        feed['events'] = body['events']
        for k in ('cps', 'seconds', 'depth'):
            if body.get(k) not in (None, ''):
                feed[k] = body[k]
    else:
        return 400, {'ok': False, 'error': 'give a stimulus (a cycle_stimuli variant, e.g. uno-light) or events (the twin\'s pin events) to simulate from'}
    wanted = body.get('units')
    if isinstance(wanted, str):
        wanted = [w.strip() for w in wanted.split(',') if w.strip()]
    chosen = [r for r in rows_all if not wanted or r['unit'] in wanted]
    if wanted and not chosen:
        return 404, {'ok': False, 'error': 'none of the named units is on bench %s' % bench_name, 'known': [r['unit'] for r in rows_all]}
    out, seconds, ref, known = [], -1.0, '', []
    for r in chosen:
        u, probes = r['unit'], r['probes_json']
        row = {'unit': u, 'model': r['model'], 'profile': r['profile'], 'profile_kind': r['profile_kind'], 'endpoint': u, 'port': 0, 'channels_fed': '', 'lines': '',
               'ok': False, 'refusal': '', 'alignment': ALIGNMENT_SIMULATED}
        if not probes:
            row['refusal'] = 'no probes: put a channel on a line first (the probe door)'
            out.append(row)
            continue
        if not r['profile']:
            row['refusal'] = 'no emulator profile: the model row %r is unknown on this instance' % r['model']
            out.append(row)
            continue
        if _running(u):
            X.stop_emulator(manager, u)
        st, started = X.start_emulator(manager, {'profile': r['profile'], 'name': u, 'restart': True})
        if st != 201:
            row['refusal'] = started.get('error', 'the emulator did not start')
            out.append(row)
            continue
        row['port'] = started.get('port', 0)
        st, fed = X.feed_device(manager, u, dict(feed, channels={str(c): l for c, l in probes.items()}))
        if st != 200:
            row['refusal'] = fed.get('error', 'the feed was refused')
            if fed.get('known'):
                known = fed['known']
                row['refusal'] += ' (known lines: %s)' % ', '.join(fed['known'])
            out.append(row)
            continue
        seconds, ref, known = fed.get('seconds', seconds), fed.get('source_ref', ref), fed.get('lines', known)
        row.update(ok=True, channels_fed=', '.join('ch%s' % c for c in sorted(probes, key=int)), lines=', '.join(probes[c] for c in sorted(probes, key=int)))
        out.append(row)
    fed_n = sum(1 for r in out if r['ok'])
    return 200, {'ok': fed_n > 0 and all(r['ok'] or 'no probes' in r['refusal'] for r in out), 'bench': bench_name, 'units': len(out), 'fed': fed_n,
                 'seconds': seconds, 'source_ref': ref, 'known_lines': known, 'alignment': ALIGNMENT_SIMULATED, 'rows': out}


def stop_all(manager, bench_name):
    """Stops every running emulator of the bench's units (the selftests' cleanup; a page door later)."""
    stopped = []
    for r in units(bench_name, manager) or []:
        if _running(r['unit']):
            X.stop_emulator(manager, r['unit'])
            stopped.append(r['unit'])
    return 200, {'ok': True, 'bench': bench_name, 'stopped': stopped}


# ---------------------------------------------------------------------------------------------------- doors
def units_door(manager, bench_name):
    rows = units(bench_name, manager)
    if rows is None:
        return 404, {'ok': False, 'error': 'no bench named %r' % bench_name, 'known': [x['name'] for x in BENCH.benches(manager)]}
    return 200, {'ok': True, 'bench': bench_name, 'rows': rows}
