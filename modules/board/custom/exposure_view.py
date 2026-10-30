"""
@module board.custom.exposure_view

hsp-0: the read side of the enclosure rows — shared by reachability, the availability ladder, the chain hops and the doors. Everything takes
`tables` = {class: [dict]} (seed or live); when a server has no EnclosureContact rows yet the view DERIVES them from the same tables (never empty).
"""
import json


def contacts(tables):
    rows = tables.get('EnclosureContact')
    if rows:
        return rows
    from board.custom import exposure as EXP
    return EXP.build(tables)['EnclosureContact']


def enclosures(tables):
    rows = tables.get('HardwareEnclosure')
    if rows:
        return rows
    from board.custom import exposure as EXP
    return EXP.build(tables)['HardwareEnclosure']


def board_rows(tables, board):
    """The crossings of the enclosures that sit on `board` + the unplaced variants (board '')."""
    boards = {e['name']: e.get('board', '') for e in enclosures(tables)}
    return [c for c in contacts(tables) if boards.get(c['enclosure'], board) in (board, '')]


def touching(rows, refs):
    refs = set(refs)
    return [c for c in rows if c['inner_ref'] in refs or c['outer_ref'] in refs]


def outer_kind(ref, tables):
    """header | rail | test-pad | part | chip | '' — what the far end of a crossing is."""
    if not ref:
        return ''
    cls, _, rest = ref.partition(':')
    if cls == 'ConnectorPin':
        return 'header'
    if cls == 'BoardNet':
        net = rest.split(':', 1)[1] if ':' in rest else rest
        return 'header' if any(cp.get('net') == net for cp in tables.get('ConnectorPin', [])) else 'rail'
    if cls == 'SchematicPart':
        name = rest.split(':')[0]
        return 'test-pad' if name.startswith('TP_') else 'header' if name.startswith(('ICSP', 'X2', 'J')) else 'part'
    if cls == 'PackageContact':
        return 'chip'
    return 'part'


def header_pins(ref, tables):
    cls, _, rest = ref.partition(':')
    if cls == 'ConnectorPin':
        return [rest]
    if cls == 'BoardNet':
        board, _, net = rest.rpartition(':') if ':' in rest else ('', '', rest)
        # a rail's header pins on ITS board (2026-10-29: by net name alone, the C3's GND picked up the UNO's GND pins)
        return sorted(cp['name'] for cp in tables.get('ConnectorPin', []) if cp.get('net') == net and (not board or cp.get('board') == board))
    return [ref]


def short(c):
    """One crossing in a sentence: 'series-resistor RN4B 1 kOhm -> consumed by ...'."""
    bits = [c['via']] + ([c['via_part']] if c['via_part'] else []) + ([c['via_value']] if c['via_value'] else [])
    return ' '.join(bits) + (' (%s)' % c['consumed_by'] if c['consumed_by'] else '')


def contact_refs_of_socpin(sp):
    return json.loads(sp.get('package_contacts_refs_json') or '[]')
