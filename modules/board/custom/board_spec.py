"""
@module board.custom.board_spec

ONE CITED BOARD SPEC -> THE BOARD OBJECT's ROWS (bob-5, 2026-10-30, his "go ahead" on the boards on his bench that had no pins). The UNO and the C3 each grew
their own module; the next boards are declared as a SPEC - every value carries the fact it comes from - and this file turns a spec into the same rows
(DatasheetFact, SocDefinition, SocPin, BoardPin, BoardNet, Connector, ConnectorPin, BoardHardware), so a new dev board is data, not code.

A spec (a dict, see board_zero.SPEC):
  board, soc, title, vendor, package, isa, cpu_clock_hz, logic=(volts, why)
  docs     {key: (document, revision, url)}                      every fact names one
  facts    [(key, value, unit, where, notes, doc key, 'board'|'soc')]
  soc_pins [{pin, package_pin, functions, default, fact, notes}]
  pins     [{canonical, number, soc_pin, function, peripheral, signal, alias, notes, origin, facts}]   chip pins brought out (a BoardPin each)
  headers  [{connector, kind, footprint, order_note, fact, notes, labels: [...]}]                    physical order, pin 1 first
  label_pin {header label: BoardPin canonical}                                                      a label no entry names is a power / input / NC label
  power    {label: (net, class, volts, why, fact)}                     the labels that are not chip pins but carry a net (rails, ground, reset)
  rails    [{net, volts, max_ma, fact}]                                                             cited supply limits (BoardHardware.power_rails_json)
  electrical {max_ma, sink_ma?, fact, kind}                                                         the per-pin limit every chip pin carries (sink_ma when it differs)
  positions {(connector, n): (x, y)} + position_basis                                               cited header positions, when a board file gives them
  inputs   {label: words}                                                                           what an input label is on this board (EN, RST)
  components, hardware {crystal, usb_bridge_chip, source, undetermined, notes}

Unknown stays unknown: a header label that is neither a chip pin nor a cited power label becomes a ConnectorPin with no net and the reason in notes.
"""
import json


def _fact(spec, key, value, unit, where, notes, doc, owner):
    d, rev, url = spec['docs'][doc]
    who = spec['soc'] if owner == 'soc' else spec['board']
    return {'name': '%s:%s' % (who, key), 'board': who, 'fact_key': key, 'value': str(value), 'unit': unit, 'document': d, 'revision': rev,
            'page_table': where, 'url': url, 'notes': notes}


def facts(spec):
    return [_fact(spec, *f) for f in spec['facts']]


def soc_definition(spec):
    return {'name': spec['soc'], 'title': spec['soc_title'], 'vendor': spec['vendor'], 'package': spec['package'], 'isa': spec['isa'],
            'cpu_clock_hz': spec['cpu_clock_hz'], 'memory_map_json': '[]', 'peripherals_json': '[]',
            'clocks_json': json.dumps([{'name': 'cpu0', 'hz': spec['cpu_clock_hz'], 'fact': spec.get('clock_fact', '')}]),
            'pin_count': len(spec['soc_pins']), 'facts_json': json.dumps([f['name'] for f in facts(spec) if f['board'] == spec['soc']]),
            'source': spec['soc_source'], 'zephyr_soc': spec.get('zephyr_soc', ''), 'vendor_target': spec.get('vendor_target', ''),
            'undetermined': spec.get('soc_undetermined', ''), 'notes': ''}


def soc_pins(spec):
    return [{'name': '%s:%s' % (spec['soc'], p['pin']), 'soc': spec['soc'], 'pin': p['pin'], 'port': p['pin'][:2], 'bit': int(p['pin'][2:]) if p['pin'][2:].isdigit() else 0,
             'package_pin': str(p.get('package_pin', '')), 'functions_json': json.dumps(p.get('functions', [])), 'default_function': p.get('default', ''),
             'fact': p.get('fact', ''), 'notes': p.get('notes', '')} for p in spec['soc_pins']]


def header_of(spec):
    """{BoardPin canonical: 'J1:9'} - the first header pin each chip pin sits on."""
    out = {}
    for h in spec['headers']:
        for i, lab in enumerate(h['labels'], 1):
            c = spec['label_pin'].get(lab)
            if c:
                out.setdefault(c, '%s:%d' % (h['connector'], i))
    return out


def board_pins(spec):
    where, el = header_of(spec), spec.get('electrical') or {}
    rows = []
    for p in spec['pins']:
        rows.append({'name': '%s:%s' % (spec['board'], p['canonical']), 'board': spec['board'], 'canonical': p['canonical'], 'number': int(p.get('number', 0) or 0),
                     'soc_pin': p['soc_pin'], 'net': p['canonical'], 'connector_pin': where.get(p['canonical'], ''), 'function': p.get('function', 'gpio'),
                     'peripheral': p.get('peripheral', ''), 'signal': p.get('signal', ''), 'firmware_symbol': '', 'alias': p.get('alias', ''),
                     'electrical_json': json.dumps(el, sort_keys=True) if el else '{}', 'facts_json': json.dumps(sorted(set(p.get('facts', [])))),
                     'origin': p.get('origin', ''), 'undetermined': p.get('undetermined', ''), 'notes': p.get('notes', '')})
    return rows


def nets(spec):
    out = [{'name': '%s:%s' % (spec['board'], p['canonical']), 'board': spec['board'], 'net': p['canonical'], 'net_class': 'signal', 'volts': 0.0, 'circuit_net': '',
            'fact': '', 'notes': 'the pin\'s own net (the board joins nothing else to it on the headers)'} for p in spec['pins']]
    seen = set()
    for net, cls, volts, why, fact in spec['power'].values():
        if net in seen:
            continue
        seen.add(net)
        out.append({'name': '%s:%s' % (spec['board'], net), 'board': spec['board'], 'net': net, 'net_class': cls, 'volts': volts, 'circuit_net': '',
                    'fact': fact, 'notes': why})
    return out


def connectors(spec):
    conns, pins = [], []
    for h in spec['headers']:
        conns.append({'name': '%s:%s' % (spec['board'], h['connector']), 'board': spec['board'], 'connector': h['connector'], 'ref': h['connector'],
                      'kind': h.get('kind', 'header'), 'pin_count': len(h['labels']), 'footprint': h.get('footprint', ''), 'order_note': h.get('order_note', ''),
                      'fact': h['fact'], 'notes': h.get('notes', '')})
        for i, lab in enumerate(h['labels'], 1):
            c = spec['label_pin'].get(lab)
            pw = spec['power'].get(lab)
            net, note = (c, '') if c else (pw[0], '') if pw else ('', 'NC: not connected (%s)' % h['fact']) if lab == 'NC' else ('', 'label %r: no cited net' % lab)
            pins.append({'name': '%s:%s:%d' % (spec['board'], h['connector'], i), 'board': spec['board'], 'connector': h['connector'], 'number': i, 'label': lab,
                         'net': net, 'board_pin': c or '', 'fact': h['fact'], 'notes': note})
    return conns, pins


def hardware(spec):
    hw = spec.get('hardware') or {}
    return {'name': spec['board'], 'board': spec['board'], 'components_json': json.dumps(spec.get('components', [])),
            'power_rails_json': json.dumps(spec.get('rails', [])), 'crystal': hw.get('crystal', ''), 'usb_bridge_chip': hw.get('usb_bridge_chip', ''),
            'usb_ids_json': '[]', 'facts_json': json.dumps(hw.get('facts', [])), 'source': hw.get('source', ''), 'undetermined': hw.get('undetermined', ''),
            'notes': hw.get('notes', '')}


def specs():
    """Every board declared as a spec (bob-5)."""
    from board.custom import board_elecrow_s3, board_feather_m0, board_zero
    return [board_zero.SPEC, board_feather_m0.SPEC, board_elecrow_s3.SPEC]


def spec_of(board):
    return next((s for s in specs() if s['board'] == board), None)


def positions(board):
    """({(connector, number): (x, y)}, basis) - a spec board's cited header positions ({} + the reason when none are cited)."""
    s = spec_of(board)
    return ((s.get('positions') or {}), s.get('position_basis', '')) if s else ({}, '')


def input_words(board, label):
    """What a spec board's input label is (EN, RST ...) - '' when the spec says nothing."""
    s = spec_of(board)
    return ((s or {}).get('inputs') or {}).get(label, '')


def logic_level(board):
    """(volts, why) | (None, '') - a spec board's own cited logic level (electrical_check._board_logic_level reads it)."""
    for s in specs():
        if s['board'] == board:
            return s['logic']
    return None, ''


def layers():
    """{class: rows} of every spec board - what board_object_seed adds to the UNO's and the C3's."""
    out = {k: [] for k in ('DatasheetFact', 'SocDefinition', 'SocPin', 'BoardPin', 'BoardNet', 'Connector', 'ConnectorPin', 'BoardHardware')}
    seen_soc = set()
    for s in specs():
        out['DatasheetFact'] += facts(s)
        if s['soc'] not in seen_soc:
            seen_soc.add(s['soc'])
            out['SocDefinition'].append(soc_definition(s))
        have = {p['name'] for p in out['SocPin']}
        out['SocPin'] += [p for p in soc_pins(s) if p['name'] not in have]   # two boards on one chip: the SocPins they name, once
        out['BoardPin'] += board_pins(s)
        out['BoardNet'] += nets(s)
        c, p = connectors(s)
        out['Connector'] += c
        out['ConnectorPin'] += p
        out['BoardHardware'].append(hardware(s))
    names = set()
    out['DatasheetFact'] = [f for f in out['DatasheetFact'] if not (f['name'] in names or names.add(f['name']))]
    return out
