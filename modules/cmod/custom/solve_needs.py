"""
@module cmod.custom.solve_needs

sol-0: from ONE choice of isotope variants (one per job) to the pin NEEDS the search must place - and the board's pin universe with how scarce each pin function is.

A need is one pin the chosen routes ask for: {id, job, route, role (the Mission role: "the button"), part (which pin OF THE ROUTE: "the register's clock"), kind (the
pp-0 / TASK_KINDS kind), okind (the pp-1 overlap-table kind: interrupt-in = INT0/INT1, pin-change-in = PCINTn, comparator-in = AIN0/AIN1), patterns (the function names
that satisfy it), importance, purposes, phases, reserved, drive}.

  - A job whose Mission profile is RESERVED (the transport lines) keeps that profile as its need; the route adds no second pin.
  - Any other job: the route's own declared profiles (iso-0) stand in for the Mission profile (same role, importance, Purposes, phases), a profile with `functions_all`
    becomes one need per function (the comparator's two inputs), a profile marked `same_pin` joins the one before it (the 1-Wire data wire).
  - The BUS signals (SPI clock / MOSI / MISO, I2C data / clock) are shared by every device on the bus by design: two routes that both need `spi-sck` get ONE need
    (`bus-shared`, said in the candidate) - the select / load lines are per device and are not merged.

SCARCITY (how special a pin is) is DERIVED, not typed: a function family's scarcity = 1 / (number of header pins that carry it), so the two external-interrupt pins cost
0.5 each, the six PWM pins ~0.17 each, the twenty pin-change pins 0.05 each. A pin's specialisation cost for a need = the scarcity of every family the pin carries that
the need does NOT itself use. The search keeps the cheapest pins and says why.
"""
import fnmatch
import json
import re

from board.custom import soc_functions as SF   # c3pf: the ESP32-C3's functions are PinFunction rows, its kinds patterns over their names
from cmod.custom import solve_inputs as SI

BUS_KINDS = ('spi-sck', 'spi-mosi', 'spi-miso', 'i2c-sda', 'i2c-scl')
FAMILIES = (('external-interrupt', re.compile(r'^INT[01]$')), ('pin-change', re.compile(r'^PCINT\d+$')), ('pwm', re.compile(r'^OC\d[AB]$')),
            ('adc', re.compile(r'^ADC\d$')), ('comparator', re.compile(r'^AIN[01]$')), ('spi', re.compile(r'^(MOSI|MISO|SCK|SS)$')), ('twi', re.compile(r'^(SDA|SCL)$')),
            ('usart', re.compile(r'^(RXD|TXD|XCK)$')), ('timer-clock', re.compile(r'^T[01]$')), ('capture', re.compile(r'^ICP1$')), ('clock-out', re.compile(r'^CLKO$')))


def family(fn, soc=None):
    if SF.has_vocab(soc):
        return SF.family(soc, fn)
    return next((name for name, rx in FAMILIES if rx.match(fn)), None)


def pin_universe(hw, tables):
    """[{canonical, soc_pin, number, functions}] in board order (D0..D13, A0..A5) then the package-only analog pins (ADC6, ADC7: bonded on the TQFP, no header)."""
    board = hw['board']
    socpins = {p['pin']: p for p in tables['SocPin'] if p['soc'] == hw['soc']}
    pf = {}
    if SF.has_vocab(hw['soc']):   # c3pf: the PinFunction rows ARE the vocabulary (GPIO, GPIO_INT, the IO MUX functions, every GPIO-matrix signal), in row order
        for f in tables.get('PinFunction', []):
            if f['soc'] == hw['soc']:
                pf.setdefault(f['soc_pin'], []).append(f['function'])
    out = []
    for b in tables['BoardPin']:
        if b['board'] != board:
            continue
        sp = socpins.get(b['soc_pin'])
        fns = list(pf.get(sp['name']) if sp and sp['name'] in pf else (['GPIO'] if sp else []) + (json.loads(sp['functions_json'] or '[]') if sp else []))
        if sp and SF.has_vocab(hw['soc']) and any(x['board'] == board and x['pin'] == b['canonical'] and x['phase'] == 'reset' for x in tables.get('PinLifecycleConstraint', [])):
            fns.append('@strapping')   # c3pf: a pad sampled at reset (boot mode) is a scarce kind of pad - the family costs a need that does not use it
        out.append({'canonical': b['canonical'], 'soc_pin': b['soc_pin'], 'functions': fns, 'header': True})
    labels = sorted({c['label'] for c in tables.get('PackageContact', []) if re.match(r'^ADC[67]$', c['label'])})
    have = {p['canonical'] for p in out}
    out += [{'canonical': lab, 'soc_pin': '', 'functions': [lab], 'header': False} for lab in labels if lab not in have]
    for i, p in enumerate(out):
        p['index'] = i
    return out


def scarcity(universe, soc=None):
    """{family: 1 / header pins that carry it} over the header pins."""
    count = {}
    for p in universe:
        if p['header']:
            for f in {family(fn, soc) for fn in p['functions']} - {None}:
                count[f] = count.get(f, 0) + 1
    return {f: round(1.0 / n, 4) for f, n in count.items()}


def pick_function(pin, patterns):
    for pat in patterns:
        for fn in pin['functions']:
            if fnmatch.fnmatchcase(fn, pat):
                return fn
    return None


def spec_cost(pin, fn, scar, soc=None):
    """The scarce families the pin carries beyond the one the need uses -> (cost, [family names wasted])."""
    used = family(fn, soc)
    fams = sorted({family(f, soc) for f in pin['functions']} - {None, used})
    return round(sum(scar.get(f, 0.0) for f in fams), 4), fams


def _okind(kind, pats):
    from board.custom import profile_overlap_kinds as K
    if any(p.startswith('AIN') for p in pats):
        return 'comparator-in'
    if kind == 'interrupt-in' and pats and all(p.startswith('PCINT') for p in pats):
        return 'pin-change-in'
    return kind if kind in K.KINDS else 'digital-in'


def _kind_patterns(kind, soc=None):
    own = SF.kind_patterns(soc, kind) if SF.has_vocab(soc) else None
    if own is not None:
        return list(own)
    from cmod.custom.isotope_variants_eligibility import KIND_FUNCTIONS
    return KIND_FUNCTIONS.get(kind) or ['GPIO*']


def _need(job, route, role, part, kind, pats, importance, purposes, phases, reserved, drive, note='', also=()):
    return {'id': '%s:%s' % (job, re.sub(r'[^a-z0-9]+', '-', part.lower()).strip('-')[:40]), 'job': job, 'jobs': [job], 'route': route, 'role': role, 'part': part, 'kind': kind,
            'okind': _okind(kind, pats), 'patterns': list(pats), 'importance': importance, 'purposes': list(purposes), 'phases': list(phases), 'reserved': reserved,
            'drive': drive, 'note': note, 'also': list(also), 'bus_shared': False}


def needs_for(combo, by_job, fixed, soc=None):
    """combo = {job: variant row dict}; by_job = {job: [Mission profiles]}; fixed = Mission profiles with no catalogued job -> [need]. `soc`: the hardware's SoC - on one
    with its own function vocabulary (the ESP32-C3) the kind names the patterns, the UNO-style functions_any of a route's profile (INT0, OC*) is not used."""
    from cmod.custom import pin_profiles as PP
    needs = []
    for job, v in combo.items():
        mps = by_job[job]
        imp = min((m.get('importance') or 'required' for m in mps), key=PP.IMPORTANCE.index)
        purposes = sorted({x for m in mps for x in m['purposes']})
        phases = sorted({ph for m in mps for ph in (m.get('lifecycle_phases') or [])} or {'runtime'}, key=PP.PHASE_ORDER.index)
        phases = [ph for ph in phases if ph in ('init', 'runtime')] or ['runtime']      # the phases the ladder is asked in: the ones the firmware runs in
        reserved = [m for m in mps if m.get('reserved')]
        if reserved:
            for m in reserved:
                needs.append(_need(job, v['route'], m['role'], m['role'] + ' (' + m['kind'] + ')', m['kind'], _kind_patterns(m['kind'], soc), m.get('importance') or imp, m['purposes'], phases, True, m.get('drive') or {}))
            continue
        drive = (mps[0].get('drive') or {})
        for pr in json.loads(v['profiles_json'] or '[]'):
            kind = pr['kind']
            direct = pr.get('part') == pr['role']
            if pr.get('same_pin') and needs and needs[-1]['job'] == job:
                needs[-1]['also'].append(kind)
                continue
            if pr.get('functions_all'):
                for fnp in pr['functions_all']:
                    needs.append(_need(job, v['route'], pr['role'], '%s - %s' % (pr.get('part', ''), fnp), kind, [fnp], imp, purposes, phases, False, {}, pr.get('note', '')))
                continue
            pats = (SF.kind_patterns(soc, kind) if SF.has_vocab(soc) else None) or pr.get('functions_any') or _kind_patterns(kind, soc)
            for i in range(int(pr.get('count', 1))):
                nd = _need(job, v['route'], pr['role'], pr.get('part', '') + ('' if int(pr.get('count', 1)) == 1 else ' #%d' % (i + 1)), kind, pats, imp, purposes, phases, False,
                           drive if direct else {}, pr.get('note', ''))
                needs.append(nd)
    for m in fixed:
        needs.append(_need('(none)', 'fixed', m['role'], m['role'] + ' (' + m['kind'] + ')', m['kind'], _kind_patterns(m['kind'], soc), m.get('importance') or 'required', m['purposes'],
                           [ph for ph in (m.get('lifecycle_phases') or ['runtime']) if ph in ('init', 'runtime')] or ['runtime'], bool(m.get('reserved')), m.get('drive') or {}))
    return _merge_bus(needs)


def _merge_bus(needs):
    out, seen = [], {}
    for n in needs:
        if n['kind'] in BUS_KINDS:
            k = n['kind']
            if k in seen:
                e = seen[k]
                e['jobs'] = sorted(set(e['jobs']) | set(n['jobs']))
                e['purposes'] = sorted(set(e['purposes']) | set(n['purposes']))
                e['bus_shared'] = True
                from cmod.custom import pin_profiles as PP
                e['importance'] = min(e['importance'], n['importance'], key=PP.IMPORTANCE.index)
                continue
            seen[k] = n
        out.append(n)
    ids = {}
    for n in out:        # two needs of one id (e.g. two plain output pins of one route) get a stable suffix
        ids[n['id']] = ids.get(n['id'], 0) + 1
        if ids[n['id']] > 1:
            n['id'] += '#%d' % ids[n['id']]
    return out


def need_text(n):
    return '%s [%s]' % (n['part'] if n['part'] != n['role'] else n['role'], n['kind'])
