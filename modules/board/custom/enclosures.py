"""
@module board.custom.enclosures

hsp-0 (L2): THE HARDWARE ENCLOSURES that exist in today's models, DERIVED from the rows (never typed twice):
  * one E1 enclosure per BoardComponent that names a package (U1's 28-SPDIP, U2's 32-QFN), sitting inside the board's E2 enclosure;
  * one E1 enclosure per PackageDefinition no component carries but a component ALLOWS (the ATmega328P's 32-TQFP: modelled, on no UNO);
  * one E2 enclosure per board that has components (the UNO R3 itself).
The kind of an E1 package is read off its PackageDefinition.package_type (SPDIP -> E1:dip, TQFP -> E1:tqfp, QFN -> E1:qfn). The body of an enclosure
(heat, stress, ingress) is not modelled: this slice builds the pin side only.
"""
import json

from board.custom import uno_evidence as EV

PACKAGE_KIND = {'SPDIP': 'E1:dip', 'DIP': 'E1:dip', 'TQFP': 'E1:tqfp', 'QFN': 'E1:qfn'}
PINOUT_DOC = dict(document='Arduino UNO R3 (A000066) Full Pinout', datasheet='arduino-uno-r3-pinout', url='https://docs.arduino.cc/resources/pinouts/A000066-full-pinout.pdf')
SCH_CITE = dict(document=EV.SCH_DOC, datasheet='arduino-uno-r3-schematic', url=EV.SCH_URL)


def board_enclosure_name(board):
    return '%s:board' % board


def package_enclosure_name(board, ref):
    return '%s:%s:package' % (board, ref)


def variant_enclosure_name(package):
    return '%s:variant' % package


def rows(tables):
    comps = tables.get('BoardComponent', [])
    pkgs = {p['name']: p for p in tables.get('PackageDefinition', [])}
    out, placed = [], set()
    for board in sorted({c['board'] for c in comps}):
        bc = [c for c in comps if c['board'] == board]
        kids = []
        for c in sorted(bc, key=lambda c: c['ref']):
            pd = pkgs.get(c.get('package') or '')
            if pd is None:
                continue
            placed.add(pd['name'])
            nm = package_enclosure_name(board, c['ref'])
            kids.append(nm)
            out.append(_e1(nm, pd, board, c, parent=board_enclosure_name(board)))
        out.append({'name': board_enclosure_name(board), 'title': '%s board (E2)' % board, 'kind': 'E2:board', 'level': 'E2', 'parent': '',
                    'contains_json': json.dumps(['HardwareEnclosure:%s' % k for k in kids] + ['BoardComponent:%s' % c['name'] for c in sorted(bc, key=lambda c: c['ref'])]),
                    'board': board, 'component': '', 'package': '', 'status': 'modelled', 'verification': 'partial', **SCH_CITE,
                    'page_table': 'sheet 1 (rendered); pinout p.1 (headers); p.4 (ICSP)',
                    'undetermined': 'the header pin NUMBERS are ours (the pinout prints none except on ICSP); the board\'s body (heat, stress, ingress) is not modelled; '
                                    'each header line also has a test pad on the schematic (TP_0.. TP_13, TP_A0.. TP_A5): not modelled as crossings',
                    'notes': 'the board enclosure of the bought development board (stage S1 Breadboard): its exposure map is the EnclosureContact rows at level E2'})
    for name, pd in sorted(pkgs.items()):
        if name in placed:
            continue
        for c in comps:
            if name in json.loads(c.get('package_options_json') or '[]'):
                out.append(_e1(variant_enclosure_name(name), pd, '', None, parent='', status='variant-not-on-a-board',
                               extra='a package OPTION of %s (BoardComponent.package_options_json), modelled so ADC6 and ADC7 are not omitted; no UNO design here carries it' % c['name']))
                break
    return out


def _e1(name, pd, board, comp, parent, status='modelled', extra=''):
    kind = PACKAGE_KIND.get(pd['package_type'], '')
    return {'name': name, 'title': '%s package (%s%s)' % (pd['soc'], pd['package_type'], (' on ' + comp['ref']) if comp else ', variant'), 'kind': kind, 'level': 'E1', 'parent': parent,
            'contains_json': json.dumps(['SocDefinition:%s' % pd['soc']]), 'board': board, 'component': comp['name'] if comp else '', 'package': pd['name'], 'status': status,
            'verification': 'verified', 'document': pd['document'], 'datasheet': pd['datasheet'], 'page_table': pd['page_table'], 'url': pd['url'],
            'undetermined': ('which package is on the bench board is PENDING identification (his ruling 2026-10-15)' if comp else pd['undetermined']) +
                            '; the package body (heat, stress, ingress) is not modelled',
            'notes': extra or ('%s: the package as the board design models it (PackageDefinition %s)' % (comp['name'] if comp else 'variant', pd['name']))}
