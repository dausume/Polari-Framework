"""
@module board.custom.exposure_e2

hsp-0 (L3): THE E2 (BOARD) EXPOSURE MAP of a board with an ATmega328P-class chip — DERIVED:
  * every I/O leg whose SocPin a BoardPin carries -> one `direct` crossing per ConnectorPin that BoardPin is wired to (D13 -> its DIGITAL_H pin AND its ICSP pin;
    A4 -> ANALOG:5 AND the SDA pin ...), read from the ConnectorPin.board_pin rows;
  * VCC / GND / AREF legs and PC6 (RESET) -> the board's rail net of that name (the headers reach it through the ConnectorPin.net rows);
  * everything else the headers do not say (the 1 kOhm to the 16U2, C5 from DTR, the LMV358 buffer, the clock part, the 16U2's own legs) comes from the
    cited typed table board.custom.uno_schematic_paths.
The schematic read (every I/O line leaves the 328P pin and goes straight to its IOn / ADn header net) is the rendered sheet 1; the header NUMBERS are ours.
"""
import json

from board.custom import uno_evidence as EV
from board.custom import uno_schematic_paths as SP
from board.custom.enclosures import SCH_CITE, board_enclosure_name
from board.custom.exposure_names import row

RAIL_OF_LEG = {'VCC': '+5V', 'GND': 'GND', 'AREF': 'AREF'}


def rows(tables, board, u1_package):
    enc = board_enclosure_name(board)
    contacts = [c for c in tables.get('PackageContact', []) if c['package'] == u1_package]
    bpins = {b['soc_pin']: b for b in tables.get('BoardPin', []) if b['board'] == board}
    cpins = [c for c in tables.get('ConnectorPin', []) if c['board'] == board]
    out = []
    for c in sorted(contacts, key=lambda c: c['number']):
        leg = 'PackageContact:%s' % c['name']
        if c['kind'] == 'io' and c['label'] in bpins:
            bp = bpins[c['label']]
            for cp in [x for x in cpins if x.get('board_pin') == bp['canonical']]:
                out.append(row(enc, 'E2', leg, 'ConnectorPin:%s' % cp['name'], 'direct', exposed=True,
                               label='%s: %s (%s) -> header %s pin %d' % (c['label'], bp['canonical'], bp['net'], cp['connector'], cp['number']),
                               verification='verified', **SCH_CITE, page_table='sheet 1 (rendered): the 328P pin -> its IO/AD net -> the header; pinout p.1 (pin <-> port)',
                               fact=json.loads(bp['facts_json'] or '[]')[0] if json.loads(bp['facts_json'] or '[]') else '',
                               notes='header pin numbers are ours; a test pad is drawn on each header line (not modelled as a crossing)'))
            continue
        net = 'RESET' if c['label'] == 'PC6' else RAIL_OF_LEG.get(c['label'])
        if net:
            und = ('the render does not trace pin 22 (named AGND on the symbol) to the GND rail: read from its name' if c['number'] == 22 and c['label'] == 'GND' else '')
            out.append(row(enc, 'E2', leg, 'BoardNet:%s:%s' % (board, net), 'direct', exposed=True, label='%s -> rail %s' % (c['label'], net),
                           verification='partial' if und else 'verified', **SCH_CITE, page_table='sheet 1 (rendered): %s leg to the %s net' % (c['label'], net),
                           fact='%s:pinout.power_header' % board, undetermined=und,
                           notes='the header pins on net %s are the ConnectorPin rows with that net; bypass capacitors (C4, C6, C10 100 nF) are drawn, not modelled as crossings' % net))
    for p in SP.paths():
        out.append(row(enc, 'E2', p['inner_ref'], p['outer_ref'], p['via'], via_part=p['via_part'], via_value=p['via_value'], exposed=p['exposed'],
                       consumed_by=p['consumed_by'], label=p['label'], verification=p['verification'], **SCH_CITE, page_table=p['where'] or SP.SCH,
                       fact=p['fact'], undetermined=p['undetermined'], notes=p['notes']))
    return out
