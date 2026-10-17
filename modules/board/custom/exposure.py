"""
@module board.custom.exposure

hsp-0: THE ENCLOSURE ROWS of a board, all derived from `tables` = {class: [dict]} (the seed's, or a live server's):
build(tables) -> {'EnclosureKind', 'HardwareEnclosure', 'EnclosureContact'}. The kinds are board.custom.enclosure_kinds, the enclosures
board.custom.enclosures, the E1 maps board.custom.exposure_e1, the E2 map board.custom.exposure_e2 (+ the cited typed paths). Nothing here is typed twice.
"""
from board.custom import enclosure_kinds as EK
from board.custom import enclosures as ENC
from board.custom import exposure_e1 as E1
from board.custom import exposure_e2 as E2
from board.custom.exposure_names import unique


def build(tables):
    encl = ENC.rows(tables)
    contacts = E1.rows(tables, encl)
    pkgs = {p['name']: p for p in tables.get('PackageDefinition', [])}
    for e in encl:
        if e['level'] != 'E2':
            continue
        u1 = next((c for c in tables.get('BoardComponent', []) if c['board'] == e['board'] and c.get('role') == 'mcu' and c.get('package') in pkgs), None)
        if u1 is not None:
            contacts += E2.rows(tables, e['board'], u1['package'])
    return {'EnclosureKind': EK.rows(), 'HardwareEnclosure': encl, 'EnclosureContact': unique(contacts)}
