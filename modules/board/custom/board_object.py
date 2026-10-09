"""
@module board.custom.board_object

THE BOARD OBJECT (brd-bo, PCB_FROM_SCRATCH_PLAN §2b, his ruling 2026-10-03): one board definition shared by KiCad, Zephyr,
FreeRTOS/ESP-IDF, bare C and Polari, built around the pin/net assignment. This file gathers a board's layers from rows (a
server's tables, or the seeds when there is no server), hashes them (the BOARD SHA every view carries), checks the rules, and
makes the one edit the "flip between them" proof needs (assign a net to another pin).

Layers (rows):  Identity = BoardDefinition (brd-0's, extended — no second board class) · Soc = SocDefinition + SocPin ·
BoardHardware = BoardHardware + BoardNet + Connector + ConnectorPin · PinAssignment = BoardPin · RuntimeProfile.

Rules checked here (and by the selftest):
  * pins are named ONCE — one BoardPin per canonical name per board, its row name '<board>:<canonical>';
  * a SoC pin is assigned at most once per board (a second BoardPin on the same soc_pin is REFUSED);
  * every BoardPin's net is a BoardNet, its connector pin a ConnectorPin, its soc pin a SocPin of the board's SoC;
  * a firmware symbol names one pin.
"""
import copy
import hashlib
import inspect
import json

LAYER_CLASSES = ('SocDefinition', 'SocPin', 'BoardHardware', 'BoardNet', 'Connector', 'ConnectorPin', 'BoardPin', 'RuntimeProfile',
                 # ucd-0a: the hardware chain's rows travel with the layers (chain_for walks them from the same tables)
                 'Peripheral', 'PeripheralSignal', 'PinFunction', 'Register', 'RegisterField')
ALIASES = {'uno': 'arduino-uno-r3', 'arduino-uno': 'arduino-uno-r3', 'arduino-uno-r3': 'arduino-uno-r3',
           'c3': 'esp32-c3', 'esp32c3': 'esp32-c3', 'esp32-c3': 'esp32-c3'}
#: the BoardPin fields that ARE the assignment (what views carry and conflicts compare)
ASSIGN_FIELDS = ('canonical', 'number', 'soc_pin', 'net', 'connector_pin', 'function', 'peripheral', 'signal', 'firmware_symbol',
                 'alias', 'electrical_json')
#: bare-C firmware symbols → the gen knob they feed (board.custom.variants)
SYMBOL_KNOBS = {'LED_PIN': 'led_pin', 'PWM_PIN': 'pwm_pin', 'ADC_CHANNEL': 'adc_channel'}


class BoardObjectRefused(ValueError):
    pass


def board_name(alias):
    b = ALIASES.get(str(alias).lower(), str(alias))
    return b


def _fields(cls_name):
    from board import board_basis
    cls = getattr(board_basis, cls_name)
    return [p for p in inspect.signature(cls.__init__).parameters if p not in ('self', 'manager')]


def as_dict(row, cls_name):
    if isinstance(row, dict):
        return dict(row)
    return {f: getattr(row, f, None) for f in _fields(cls_name)}


_SEED = {}


def seed_tables():
    """{class: [dict]} — the seed rows (what a fresh server holds)."""
    if not _SEED:
        from board.custom.register_map import board_rows
        from board.custom import board_object_seed as S
        boards = board_rows()
        for b in boards:
            b.update(S.IDENTITY.get(b['name'], {}))
        _SEED.update(S.build(boards))
        _SEED['BoardDefinition'] = boards
        from board.custom.board_pin_nets import SEED_BOARD_PIN_NETS   # ucd-0c: the demo bench's circuit links travel with the seed tables too
        _SEED['BoardPinNet'] = [dict(r) for r in SEED_BOARD_PIN_NETS]
    return copy.deepcopy(_SEED)


def tables_from_manager(manager):
    out = {}
    for cls in LAYER_CLASSES + ('BoardDefinition', 'DatasheetFact'):
        out[cls] = [as_dict(r, cls) for r in ((manager.objectTables or {}).get(cls, {}) or {}).values()]
    return out


def rows_for(board, tables=None):
    """One board's layers as dicts. Raises BoardObjectRefused when the board has no BoardPin rows (not modelled yet)."""
    board = board_name(board)
    t = tables if tables is not None else seed_tables()
    ident = next((b for b in t.get('BoardDefinition', []) if b.get('name') == board), None)
    pins = sorted([p for p in t.get('BoardPin', []) if p.get('board') == board], key=lambda p: (str(p.get('connector_pin') or 'zz'), int(p.get('number') or 0), p['canonical']))
    if not pins:
        known = sorted({p.get('board') for p in t.get('BoardPin', [])})
        raise BoardObjectRefused('%s has no BoardPin rows — modelled boards: %s (every other device is a Road)' % (board, ', '.join(known)))
    soc_name = (ident or {}).get('soc_definition') or ''
    hw = next((h for h in t.get('BoardHardware', []) if h.get('board') == board), None)
    return {'board': board, 'identity': ident or {'name': board}, 'soc': next((s for s in t.get('SocDefinition', []) if s.get('name') == soc_name), None),
            'soc_pins': [s for s in t.get('SocPin', []) if s.get('soc') == soc_name], 'hardware': hw,
            'nets': [n for n in t.get('BoardNet', []) if n.get('board') == board],
            'connectors': [c for c in t.get('Connector', []) if c.get('board') == board],
            'connector_pins': sorted([c for c in t.get('ConnectorPin', []) if c.get('board') == board], key=lambda c: (c['connector'], int(c['number']))),
            'pins': pins, 'profiles': {p['runtime']: p for p in t.get('RuntimeProfile', []) if p.get('board') == board}}


def board_sha(r):
    """The canonical hash of a board's layers (Identity's soc/revision + every layer row). Views carry it."""
    def clean(rows):
        return sorted([{k: v for k, v in x.items() if k not in ('id',)} for x in rows], key=lambda x: str(x.get('name')))
    body = {'board': r['board'], 'soc': (r['soc'] or {}).get('name', ''), 'revision': r['identity'].get('revision', ''),
            'pins': clean(r['pins']), 'nets': clean(r['nets']), 'connectors': clean(r['connectors']),
            'connector_pins': clean(r['connector_pins']), 'hardware': clean([r['hardware']] if r['hardware'] else []),
            'profiles': clean(list(r['profiles'].values())), 'soc_pins': clean(r['soc_pins'])}
    return hashlib.sha256(json.dumps(body, sort_keys=True, default=str).encode()).hexdigest()


def validate(r):
    """Every rule broken, as sentences (empty = the board object holds)."""
    why = []
    seen_c, seen_s, seen_sym = {}, {}, {}
    nets = {n['net'] for n in r['nets']}
    cpins = {'%s:%d' % (c['connector'], int(c['number'])) for c in r['connector_pins']}
    spins = {s['pin'] for s in r['soc_pins']}
    for p in r['pins']:
        c = p['canonical']
        if c in seen_c:
            why.append('pin %s is named twice (pins are named once)' % c)
        seen_c[c] = p
        if p['name'] != '%s:%s' % (r['board'], c):
            why.append('BoardPin %s: its name must be <board>:<canonical> (%s:%s)' % (p['name'], r['board'], c))
        if p['soc_pin']:
            if p['soc_pin'] in seen_s:
                why.append('SoC pin %s is assigned twice (%s and %s) — refused' % (p['soc_pin'], seen_s[p['soc_pin']], c))
            seen_s[p['soc_pin']] = c
            if spins and p['soc_pin'] not in spins:
                why.append('pin %s: soc pin %s is not a SocPin of %s' % (c, p['soc_pin'], (r['soc'] or {}).get('name', '?')))
        if p['net'] and p['net'] not in nets:
            why.append('pin %s: net %s is not a BoardNet of %s' % (c, p['net'], r['board']))
        if p['connector_pin'] and p['connector_pin'] not in cpins:
            why.append('pin %s: connector pin %s is not a ConnectorPin' % (c, p['connector_pin']))
    nets_now = {p['canonical']: p['net'] for p in r['pins']}
    for cp in r['connector_pins']:
        if cp.get('board_pin') and nets_now.get(cp['board_pin'], cp['net']) != cp['net']:
            why.append('connector pin %s:%s (%s) is wired to %s but carries net %s, not %s' % (cp['connector'], cp['number'], cp['label'], cp['board_pin'],
                                                                                            cp['net'], nets_now.get(cp['board_pin'])))
        sym = p.get('firmware_symbol') or ''
        if sym:
            if sym in seen_sym:
                why.append('firmware symbol %s names two pins (%s, %s)' % (sym, seen_sym[sym], c))
            seen_sym[sym] = c
    return why


def check_assignment(rows_pins, soc_pin_rows=None):
    """The rules on a raw list of BoardPin dicts (one board) — used before a new set is accepted."""
    r = {'board': rows_pins[0]['board'] if rows_pins else '', 'pins': rows_pins, 'nets': [{'net': p['net']} for p in rows_pins],
         'connector_pins': [], 'soc_pins': soc_pin_rows or [], 'soc': None}
    return [w for w in validate(r) if 'connector pin' not in w]


def pin_of_symbol(r, sym):
    return next((p for p in r['pins'] if p.get('firmware_symbol') == sym), None)


def pin_knobs(board, tables=None):
    """({knob: number}, {knob: canonical}) — the bare-C pin constants (LED_PIN, PWM_PIN, ADC_CHANNEL) FROM BoardPin rows."""
    return knobs_of(rows_for(board, tables))


def knobs_of(r):
    """pin_knobs over an already-gathered (possibly edited) board."""
    knobs, src = {}, {}
    for sym, knob in SYMBOL_KNOBS.items():
        p = pin_of_symbol(r, sym)
        if p is not None:
            knobs[knob] = int(p['number'])
            src[knob] = p['canonical']
    return knobs, src


def pin_by_canonical(r, canonical):
    return next((p for p in r['pins'] if p['canonical'] == canonical), None)


def _reserved(r):
    out = {}
    for prof in r['profiles'].values():
        if prof.get('supported'):
            for x in json.loads(prof.get('peripherals_json') or '[]'):
                if isinstance(x, dict) and x.get('reserved'):
                    out[x['name']] = '%s (%s runtime)' % (x.get('use', ''), prof['runtime'])
    return out


def assign(r, net, to):
    """THE ONE EDIT of the flip proof: move net `net` (with its function, peripheral, signal and C symbol) to pin `to`.
    The vacated pin keeps its canonical name; on a labelled header pin its net returns to its own label, an unlabelled
    pin row (a bare GPIO) is dropped. → (new rows, [touched canonical names]); BoardObjectRefused names why not."""
    r = copy.deepcopy(r)
    src = next((p for p in r['pins'] if p['net'] == net), None)
    if src is None:
        raise BoardObjectRefused('no pin of %s carries net %s' % (r['board'], net))
    if src['canonical'] == to:
        return r, []
    dst = pin_by_canonical(r, to)
    soc_pin = dst['soc_pin'] if dst else to
    srow = next((s for s in r['soc_pins'] if s['pin'] == soc_pin), None)
    if dst is None and srow is None:
        raise BoardObjectRefused('%s has no pin %s (no BoardPin, no SocPin)' % (r['board'], to))
    if dst is not None and dst['function'] not in ('gpio',) and dst['net'] != dst['canonical']:
        raise BoardObjectRefused('pin %s already carries net %s (%s) — move that first' % (to, dst['net'], dst['function']))
    peripheral, signal = src['peripheral'], src['signal']
    fns = json.loads(srow['functions_json']) if srow else []
    if src['function'] == 'pwm':
        from board.custom.soc_atmega328p import FUNCTION_PERIPHERAL, PWM_FUNCTIONS
        oc = [f for f in fns if f in PWM_FUNCTIONS]
        if not oc:
            raise BoardObjectRefused('pin %s (%s) has no Output Compare function — not a PWM pin (%s)' % (to, soc_pin, '/'.join(fns)))
        peripheral, signal = FUNCTION_PERIPHERAL[oc[0]]
        res = _reserved(r)
        if peripheral in res:
            raise BoardObjectRefused('pin %s is %s %s, but %s is reserved: %s' % (to, peripheral, signal, peripheral, res[peripheral]))
    elif src['function'] == 'adc':
        adc = [f for f in fns if f.startswith('ADC')]
        if not adc:
            raise BoardObjectRefused('pin %s (%s) has no ADC channel' % (to, soc_pin))
        signal = adc[0]
    moved = {k: src[k] for k in ('net', 'function', 'firmware_symbol', 'electrical_json')}
    moved.update(peripheral=peripheral, signal=signal)
    if src['connector_pin']:
        src.update(net=src['canonical'], function='gpio', peripheral='', signal='', firmware_symbol='')
    else:
        r['pins'] = [p for p in r['pins'] if p is not src]
    if dst is None:
        dst = {'name': '%s:%s' % (r['board'], to), 'board': r['board'], 'canonical': to, 'number': int(''.join(ch for ch in to if ch.isdigit()) or -1),
               'soc_pin': soc_pin, 'connector_pin': '', 'alias': '', 'facts_json': json.dumps([srow['fact']]) if srow.get('fact') else '[]',
               'undetermined': '', 'notes': ''}
        r['pins'].append(dst)
    dst.update(moved, origin='edited: net %s moved from %s' % (net, src['canonical']))
    nets_now = {p['canonical']: p['net'] for p in r['pins']}
    for cp in r['connector_pins']:   # a connector pin wired to a board pin carries that pin's net (ICSP SCK follows D13 …)
        if cp.get('board_pin') in nets_now:
            cp['net'] = nets_now[cp['board_pin']]
    names = {n['net'] for n in r['nets']}
    for p in r['pins']:
        if p['net'] not in names:
            r['nets'].append({'name': '%s:%s' % (r['board'], p['net']), 'board': r['board'], 'net': p['net'], 'net_class': 'signal', 'volts': 0.0,
                              'circuit_net': '', 'fact': '', 'notes': 'added by assign'})
            names.add(p['net'])
    why = validate(r)
    if why:
        raise BoardObjectRefused('; '.join(why))
    return r, sorted({src['canonical'], to})


def to_tables(r, tables):
    """Put one board's (edited) layers back into a full {class: [dict]} set (for rendering from an edited copy)."""
    t = copy.deepcopy(tables)
    b = r['board']
    t['BoardPin'] = [p for p in t['BoardPin'] if p.get('board') != b] + r['pins']
    t['BoardNet'] = [n for n in t['BoardNet'] if n.get('board') != b] + r['nets']
    t['ConnectorPin'] = [c for c in t['ConnectorPin'] if c.get('board') != b] + r['connector_pins']
    return t
