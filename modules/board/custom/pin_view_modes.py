"""
@module board.custom.pin_view_modes

pv-2 (PIN_VIEW_PLAN.md section 7): THE TWO VIEW MODES of the pin payload — DRIVE and SIGNAL — as per-pin fields, so the component never re-derives a rule. His vocabulary (2.8) is binding and the two
field sets NEVER share a word:

  DRIVE   (electricity: current flow and supply)   drive_relevant · drive_status · drive_why · rail · pull · limit_class · limit_basis · group_budget
  SIGNAL  (what the pin carries)                   signal_relevant · activated · capable · lifecycle

  drive_status   supplies | supplied | returns | sources-or-sinks (a committed or proposed output) | pulled-up | pulled-down | high-impedance | not-driven (base / blank / unclaimed) | undetermined
  rail           5V | 3V3 | VBUS | GND | logic-io | undetermined — from the BoardNet class / volts and the package-contact kind (never typed)
  pull           none | internal-up | internal-down (only when a claim sets it) | external (reserved: no row names an external pull today, so it is never emitted)
  limit_class    within-recommended | undetermined | over | unchecked — READ from the electrical rules' own findings (board.custom.pin_view_state._canon_verdict -> electrical_check); `limit_basis` names the rule id(s)
  group_budget   the PinGroupBudget rows (names only) the pin counts toward
  activated      the function in use at the stage ({function, resource, family, signal, direction}) — null at stage base and for every pin no claim touches
  capable        every function the pin can carry, each with its family and direction word
  lifecycle      the PinLifecycleConstraint rows for the pin at the request's phase: {name, phase, policy, condition, locks} (locks = reserved or prohibited: the lock glyph)

The chip pins (die pad, package leg) are computed from their kind, their claims and the rules; a header pin takes its line's fields from the leg it joins (the supply headers by their label); a board-part or
bench pin is relevant to a mode when the pin it joins is. Nothing here makes an electrical claim of its own: every verdict is the rules' own, and a check that has not run says `unchecked`.
"""
import json
import re

from board.custom import pin_view_state as ST
from board.custom import pv_families as F

DRIVE_STATUSES = ('supplies', 'supplied', 'returns', 'sources-or-sinks', 'pulled-up', 'pulled-down', 'high-impedance', 'not-driven', 'undetermined')
RAILS = ('5V', '3V3', 'VBUS', 'GND', 'logic-io', 'undetermined')
PULLS = ('none', 'internal-up', 'internal-down', 'external')
SUPPLY_KINDS = ('power', 'analog-supply', 'usb-supply')
GROUND_KINDS = ('ground', 'usb-ground', 'thermal-pad')
#: pad / leg kinds whose pins have a drive status at all (the others - usb data pair, signal-only pads - are drive-irrelevant)
DRIVE_KINDS = ('io', 'analog-input', 'analog-reference', 'clock-input', 'regulator-output') + SUPPLY_KINDS + GROUND_KINDS
STATUS_OF_KIND = {'power': 'supplied', 'analog-supply': 'supplied', 'usb-supply': 'supplied', 'ground': 'returns', 'usb-ground': 'returns', 'thermal-pad': 'returns', 'regulator-output': 'supplies',
                  'analog-input': 'high-impedance', 'analog-reference': 'high-impedance', 'clock-input': 'high-impedance'}
#: plain drive words for why a non-I/O pad has its status (no kind name: some kind names are signal words)
KIND_WHY = {'power': 'a supply pad: it is fed from the rail', 'analog-supply': 'an analog supply pad: it is fed from the rail', 'usb-supply': 'the USB supply pad: it is fed from VBUS', 'ground': 'a return pad',
            'usb-ground': 'the USB return pad', 'thermal-pad': 'the exposed pad, tied to the return', 'regulator-output': 'the on-chip regulator pad: it feeds a rail',
            'analog-input': 'an analog pad: leakage only', 'analog-reference': 'a reference pad: leakage only', 'clock-input': 'an oscillator pad: leakage only'}
#: header labels that are rails (the label is the BoardNet name without its leading '+')
HEADER_SUPPLY = {'+5V': 'supplies', '+3V3': 'supplies', 'VIN': 'supplies', 'GND': 'returns'}
PULL_OF_CLAIM = {'up': 'internal-up', 'down': 'internal-down'}
#: words that belong to ONE side only; the selftest scans every field of the other side for them
SIGNAL_WORDS = re.compile(r'\b(outputs?|inputs?|bidirectional|rxd\d?|txd\d?|sda|scl|miso|mosi|sck|uart|spi|i2c|protocol|signal)\b', re.I)
DRIVE_WORDS = re.compile(r'\b(sources?|sinks?|supplies|supplied|returns?|pulled|pull-up|high-impedance|rail|current)\b', re.I)
DIR_WORD = ST.SIGNAL_DIR


def _task(p):
    return next((c for c in p['consumers'] if c['kind'] == 'task'), None)


# ---------------------------------------------------------------- signal side
def _capable(p):
    out, seen = [], set()
    for s in p['signals']:
        key = (s['function'], s['family'])
        if key not in seen:
            seen.add(key)
            out.append({'function': s['function'], 'family': s['family'], 'direction': DIR_WORD.get(s['direction'], 'undetermined')})
    return out


def _activated(p):
    """The function the claim puts the pin in at this stage; None when nothing claims it (stage base, or a pin no task touches)."""
    c = _task(p)
    if c is None or p['stage'] not in ('proposed', 'committed'):
        return None
    fn = c.get('function') or ''
    if fn:
        row = next((s for s in p['signals'] if s['function'] == fn), None)
        return {'function': fn, 'resource': fn, 'family': (row or {}).get('family') or F.family_of(fn), 'signal': (row or {}).get('signal', ''),
                'direction': DIR_WORD.get((row or {}).get('direction', 'undetermined'), 'undetermined')}
    if c.get('mode') in ('in', 'out'):
        row = next((s for s in p['signals'] if s['function'] == 'GPIO'), None)
        return {'function': 'GPIO-%s' % c['mode'], 'resource': 'GPIO', 'family': 'gpio', 'signal': (row or {}).get('signal', ''), 'direction': 'outputs' if c['mode'] == 'out' else 'inputs'}
    return None


def _lifecycle(p, rows, phase):
    out = []
    for r in rows:
        if r['phase'] != phase:
            continue
        if (p['soc_pin'] and r['soc_pin'] == p['soc_pin']) or (p['level'] == 'board' and p['canonical'] and r['pin'] == p['canonical']):
            out.append({'name': r['name'], 'phase': r['phase'], 'policy': r['policy'], 'condition': r['condition'], 'locks': r['policy'] in ('reserved', 'prohibited')})
    return out


# ---------------------------------------------------------------- drive side
def _direction_of_claim(p, c):
    """'out' | 'in' | 'undetermined' - which way the claimed function goes, from the claim's mode and the pad's own signal rows."""
    if c['mode'] in ('in', 'out'):
        return c['mode']
    row = next((s for s in p['signals'] if s['function'] == c.get('function')), None)
    d = (row or {}).get('direction', 'undetermined')
    return d if d in ('in', 'out') else 'undetermined'


def _chip_drive(p, why_extra=''):
    """(status, why, pull) of one chip pin (die pad / package leg)."""
    kind = p['kind']
    if kind != 'io':
        return STATUS_OF_KIND.get(kind, 'undetermined'), KIND_WHY.get(kind, 'a pad whose electrical role the rows do not state'), 'none'
    c = _task(p)
    if c is None or p['stage'] not in ('proposed', 'committed'):
        return 'not-driven', 'no claim configures this pad at this stage (blank: tri-stated, pull-ups off)', 'none'
    pull = PULL_OF_CLAIM.get(c.get('pull') or 'none', 'none')
    d = _direction_of_claim(p, c)
    if d == 'out':
        return 'sources-or-sinks', 'claim %s drives it as a pad (the level decides source or sink)' % c['claim'], pull
    if d == 'in':
        if pull == 'internal-up':
            return 'pulled-up', 'claim %s enables the internal pull-up' % c['claim'], pull
        if pull == 'internal-down':
            return 'pulled-down', 'claim %s enables the internal pull-down' % c['claim'], pull
        return 'high-impedance', 'claim %s leaves the pad undriven with no pull (leakage only)' % c['claim'], pull
    return 'undetermined', 'claim %s uses an alternate function whose direction the rows do not state' % c['claim'], pull


def _rail_name(model, board_nets, p):
    """The rail of a chip pin: the BoardNet it ties to (class / volts), else the kind (a USB supply is VBUS), io pads are the logic-io rail."""
    net = model.rail_of.get(p['id'])
    if net is None and p['level'] == 'die':   # a die pad shares its leg's net
        leg = next((c['b'] for c in model.connections if c['kind'] == 'pad-to-leg' and c['a'] == p['id']), None)
        net = model.rail_of.get(leg)
    row = board_nets.get(net.rpartition(':')[2]) if net else None
    return _net_rail(row, p['kind'])


def _net_rail(row, kind):
    if row is not None:
        if row['net_class'] == 'ground':
            return 'GND'
        if row['net_class'] == 'power':
            v = float(row.get('volts') or 0)
            return '5V' if abs(v - 5.0) < 1e-6 else '3V3' if abs(v - 3.3) < 1e-6 else 'undetermined'
    if kind == 'usb-supply':
        return 'VBUS'
    if kind in ('usb-ground', 'ground', 'thermal-pad'):
        return 'GND'
    if kind in ('io', 'analog-input', 'clock-input', 'analog-reference'):
        return 'logic-io'
    return 'undetermined'


def _budgets(p, budgets):
    names = []
    for b in budgets:
        if b['soc'] != p['soc']:
            continue
        members = json.loads(b['members_json'] or '[]')
        if (p['soc_pin'] and p['soc_pin'] in members) or (p['kind'] in SUPPLY_KINDS + GROUND_KINDS and p['label'] in members) or (p['level'] == 'package' and p['label'] in json.loads(b['package_only_json'] or '[]')):
            names.append(b['name'])
    return names


# ---------------------------------------------------------------- the apply steps
def apply_pins(model, tables, ctx, phase='runtime'):
    """Sets the drive and signal fields on every pin (call after the stage is applied, before the protocol filter)."""
    phase = phase or 'runtime'
    nets = {n['net']: n for n in tables.get('BoardNet', []) if n['board'] == model.board}
    budgets, lifecycle = tables.get('PinGroupBudget', []), tables.get('PinLifecycleConstraint', [])
    verdict_cache = {}

    def limit(canon):
        if not canon:
            return 'unchecked', 'not a pin the drive rules name'
        if canon not in verdict_cache:
            verdict_cache[canon] = ST._canon_verdict(ctx, canon)
        return verdict_cache[canon]

    for p in model.pins.values():
        p.update({'drive_relevant': False, 'drive_status': 'undetermined', 'drive_why': '', 'rail': 'undetermined', 'pull': 'none', 'limit_class': 'unchecked', 'limit_basis': '', 'group_budget': [],
                  'signal_relevant': False, 'activated': None, 'capable': [], 'lifecycle': []})
    # 1. the chip pins
    for p in [x for x in model.pins.values() if x['level'] in ('die', 'package')]:
        status, why, pull = _chip_drive(p)
        p['drive_relevant'] = p['kind'] in DRIVE_KINDS
        p['drive_status'], p['drive_why'], p['pull'] = status, why, pull
        p['rail'] = _rail_name(model, nets, p)
        p['limit_class'], p['limit_basis'] = limit(p['canonical']) if p['kind'] == 'io' else ('unchecked', 'not an I/O pad: the drive rules name board pins')
        p['group_budget'] = _budgets(p, budgets)
        p['signal_relevant'] = p['kind'] not in SUPPLY_KINDS + GROUND_KINDS + ('regulator-output',)
        p['activated'] = _activated(p)
        p['capable'] = _capable(p)
        p['lifecycle'] = _lifecycle(p, lifecycle, phase)
    # 2. the header pins: a supply header by its label, every other from the leg it joins
    leg_of = {}
    for c in model.connections:
        if c['kind'] == 'to-header':
            leg_of.setdefault(c['b'], c['a'])
    for p in [x for x in model.pins.values() if x['level'] == 'board']:
        role = HEADER_SUPPLY.get(p['label'])
        leg = model.pins.get(leg_of.get(p['id'], ''))
        if role:
            p.update({'drive_relevant': True, 'drive_status': role, 'drive_why': 'a %s header pin' % ('supply' if role == 'supplies' else 'ground'),
                      'rail': _net_rail(nets.get(p['label']), 'power' if role == 'supplies' else 'ground')})
        elif p['label'] == 'IOREF':
            p.update({'drive_relevant': True, 'drive_why': 'the I/O reference pin: its voltage is not stated in the rows', 'rail': 'undetermined'})
        elif leg is not None:
            p.update({'drive_relevant': leg['drive_relevant'], 'drive_status': leg['drive_status'], 'drive_why': leg['drive_why'], 'rail': leg['rail'], 'pull': leg['pull'],
                      'group_budget': list(leg['group_budget'])})
        p['limit_class'], p['limit_basis'] = limit(p['canonical']) if (p['canonical'] and leg is not None and leg['kind'] == 'io') else ('unchecked', 'not a pin the drive rules name')
        if leg is not None and not role:
            p.update({'signal_relevant': leg['signal_relevant'], 'activated': leg['activated'], 'capable': list(leg['capable'])})
        p['lifecycle'] = _lifecycle(p, lifecycle, phase)
    # 3. board parts and bench pins: relevant to a mode when the pin they join is (a supply / return, or a claimed line for drive; a signal pin for signal)
    nbr = {}
    for c in model.connections:
        nbr.setdefault(c['a'], []).append(c['b'])
        nbr.setdefault(c['b'], []).append(c['a'])
    for p in [x for x in model.pins.values() if x['level'] in ('part', 'bench')]:
        ends = [model.pins[n] for n in nbr.get(p['id'], []) if n in model.pins]
        live = [e for e in ends if e['drive_relevant'] and (e['drive_status'] in ('supplies', 'supplied', 'returns') or e['stage'] in ('proposed', 'committed'))]
        p['drive_relevant'] = bool(live)
        if live:
            p['rail'] = live[0]['rail']
            p['drive_why'] = 'joins a pin that is %s' % live[0]['drive_status']
        p['signal_relevant'] = any(e['signal_relevant'] for e in ends)
        p['limit_basis'] = 'not a pin the drive rules name'


def apply_connections(model):
    """A connection is drive-relevant when both ends are, signal-relevant when both ends are (and it carries no supply / return); the component draws only those in a mode."""
    for c in model.connections:
        a, b = model.pins[c['a']], model.pins[c['b']]
        c['drive_relevant'] = bool(a['drive_relevant'] and b['drive_relevant'])
        c['signal_relevant'] = bool(a['signal_relevant'] and b['signal_relevant'] and c['signal']['family'] not in ('power', 'ground'))


# ---------------------------------------------------------------- the multi-set filters
def matches(pin, rail='', drive_status='', limit_class=''):
    """True when a pin passes the drive filters (each a comma list; empty = no filter)."""
    for val, key in ((rail, 'rail'), (drive_status, 'drive_status'), (limit_class, 'limit_class')):
        if val and pin.get(key) not in [v for v in val.split(',') if v]:
            return False
    return True


def vocabulary():
    return {'drive_statuses': list(DRIVE_STATUSES), 'rails': list(RAILS), 'pulls': list(PULLS), 'limit_classes': ['within-recommended', 'undetermined', 'over', 'unchecked'],
            'note': 'drive = electricity (current flow and supply); signal = what the pin carries. The two field sets never share a word.'}
