"""pcb_selftest — pcb-0: the rows (13 classes), the s-expression reader/writer on a real small KiCad project (the stored
`ecc83-pp` demo, GPL-2.0-or-later, custom/upstream/kicad-demos-9.0.2/), DKRed's rules as cited rows, export naming, the
engines ladder's refusal (no engine reachable, offline), and the schematic writer on a tiny FAKE library (no engine: the
real official-library round trip is tests/pcb_probe.py, which needs PCB_ENGINES_URL).

    PYTHONPATH=.:modules python3 -m pcb.pcb_selftest      # from polari-framework/
"""
import json
import os
import sys

passed = total = 0
HERE = os.path.dirname(os.path.abspath(__file__))
ECC83 = os.path.join(HERE, 'custom', 'upstream', 'kicad-demos-9.0.2', 'ecc83')


def check(label, cond, extra=''):
    global passed, total
    total += 1
    passed += bool(cond)
    print('  [%s] %s %s' % ('\033[0;32mPASS\033[0m' if cond else '\033[0;31mFAIL\033[0m', label, extra if not cond else ''))


def classes():
    from pcb.pcb_basis import PCB_CLASSES
    from pcb.pcb_seed import PCB_SEED_PAIRS
    check('thirteen row classes (plan §2: Part, Symbol, Footprint, LandPattern, Schematic, SchematicSheet, PcbBoard, '
          'Placement, Route, DrcResult, FabricationExport, FabRuleSet, FabRule)', len(PCB_CLASSES) == 13)
    check('only the fab rules are code-owned seed rows; every design class seeds empty (observed, not asserted)',
          {n for n, _, rows in PCB_SEED_PAIRS if rows} == {'FabRuleSet', 'FabRule'}
          and all(not rows for n, _, rows in PCB_SEED_PAIRS if n not in ('FabRuleSet', 'FabRule')))


def sexpr_roundtrip():
    from pcb.custom import sexpr as S
    text = '(kicad_sch (version 20250114) (generator "polari_pcb") (uuid "x") (lib_symbols) (sheet_instances (path "/" (page "1"))))'
    tree = S.parse(text)
    check('parse → write round-trips a minimal kicad_sch', S.find(tree, 'version') and S.value(tree, 'version') == '20250114')
    check('check_kicad accepts a minimal-but-complete kicad_sch', S.check_kicad(tree, 'kicad_sch') == [])
    check('check_kicad rejects a pre-KiCad-6 version', S.check_kicad(['kicad_sch', ['version', 20200101], ['generator', '"x"'],
                                                                      ['lib_symbols']], 'kicad_sch') != [])
    check('check_kicad rejects the wrong top-level head', S.check_kicad(['kicad_pcb', ['version', 20250114]], 'kicad_sch') != [])


def fab_rules():
    from pcb.custom import fab_rules as FR
    rows = FR.rule_rows()
    check('twenty DKRed rules, each cited (source_text, url, retrieved)', len(rows) == 20
          and all(r['source_text'] and r['url'] == FR.URL and r['retrieved'] for r in rows))
    check('one FabRuleSet row names the fab and the accepted-extension table', len(FR.rule_set_rows()) == 1
          and FR.rule_set_rows()[0]['fab'] == 'DKRed (DigiKey)')
    d = FR.dru()
    check('.kicad_dru carries the length rules as KiCad constraints (clearance, track_width, hole_size, via)',
          all(c in d for c in ('constraint clearance', 'constraint track_width', 'constraint hole_size', 'constraint via_diameter'))
          and '0.1270mm' in d)   # 5 mil
    check('naming(): an accepted silkscreen extension', FR.naming('x-F_Silkscreen.gto', 'F.Silkscreen') == ('yes', '.gto', FR.naming('x.gto', 'F.Silkscreen')[2]))
    acc, name, note = FR.naming('x-top_cu.gtl', 'F.Cu')
    check('naming(): KiCad\'s Protel copper extension is the screenshot-only discrepancy, not the page text', acc == 'discrepancy' and name == '.gtl')
    acc, name, note = FR.naming('x-Edge_Cuts.gm1', 'Edge.Cuts')
    check('naming(): KiCad 9\'s Protel outline extension (.gm1) is not on DKRed\'s accepted-outline list (.gko/.outline/.profile)',
          acc == 'no' and name == '.gko')
    check('naming(): a layer DKRed does not group is n/a, never guessed', FR.naming('x.gbr', 'F.CrtYd')[0] == 'n/a')


def kicad_read_fixture():
    """The real small ecc83-pp project (GPL-2.0-or-later, stored under custom/upstream/) — no engine, no network."""
    from pcb.custom import kicad_read as K
    if not os.path.isdir(ECC83):
        check('the ecc83-pp fixture is present (custom/upstream/kicad-demos-9.0.2/ecc83)', False, '— directory missing')
        return
    files = K.read_dir(ECC83)
    check('the fixture carries the schematic, the board and both lib tables', all(k in files for k in
          ('ecc83-pp.kicad_sch', 'ecc83-pp.kicad_pcb', 'sym-lib-table', 'fp-lib-table')))
    rows = K.read_project(files, 'ecc83-pp')
    check('no read problems on a real KiCad 9 project', rows['problems'] == [])
    check('eleven Part rows (two mounting-hole / two 1.5K resistor groups collapse by refs)', len(rows['Part']) == 11)
    check('eight Symbol, six Footprint rows (the library references actually used)', len(rows['Symbol']) == 8 and len(rows['Footprint']) == 6)
    check('one PcbBoard row: 2 copper layers, 13 nets, byte-identical sha on a second read',
          len(rows['PcbBoard']) == 1 and rows['PcbBoard'][0]['copper_layers'] == 2 and rows['PcbBoard'][0]['nets'] == 13
          and rows['PcbBoard'][0]['sha256'] == K.read_project(files, 'ecc83-pp')['PcbBoard'][0]['sha256'])
    check('fifteen Placement rows (every footprint on the board, including the four mounting holes)', len(rows['Placement']) == 15)
    check('thirteen BoardNet + thirteen Route rows (one per net, routes summarised, never per-segment)',
          len(rows['BoardNet']) == 13 and len(rows['Route']) == 13)
    check('a licence-bearing provenance: the stored copy cites GPL-2.0-or-later (SOURCE.json), compatible with this GPL-3.0 project',
          json.load(open(os.path.join(HERE, 'custom', 'upstream', 'kicad-demos-9.0.2', 'SOURCE.json')))['licence'] == 'GPL-2.0-or-later')
    rows['FabRuleSet'], rows['FabRule'] = __import__('pcb.custom.fab_rules', fromlist=['x']).rule_set_rows(), \
        __import__('pcb.custom.fab_rules', fromlist=['x']).rule_rows()
    from pcb.custom import fab_rules as FR
    drc = FR.check_board(rows['PcbBoard'][0], files['ecc83-pp.kicad_pcb'])
    check('the DKRed row check runs over the real board with no violations (all-THT, 2-layer, within DKRed\'s limits)',
          all(d['severity'] in ('none', 'info') for d in drc), str([d for d in drc if d['severity'] not in ('none', 'info')]))


def ingest_offline():
    """pol pcb ingest with engines=False: rows only, no kicad-cli reachable needed."""
    from pcb.custom import ingest as I
    if not os.path.isdir(ECC83):
        return
    res = I.ingest(ECC83, board='ecc83-pp', engines=False)
    check('ingest(engines=False) returns rows with no record and no refusal (the engine step never ran)',
          res['record'] is None and res['refused'] == '' and res['rows']['Part'])
    check('ingest seeds FabRuleSet/FabRule and the DKRed DrcResult rows even with no engine',
          res['rows'].get('FabRuleSet') and res['rows'].get('FabRule') and res['rows'].get('DrcResult'))
    # naming fix (his browser pass): ecc83-pp showed up as a bare board name with nothing to say what it was. The
    # ingest must read the real title block ("ECC Push-Pull", no company/comment fields on this project) and the
    # sibling SOURCE.json (licence + package) onto BOTH rows — never left blank, never invented.
    sch_row, board_row = res['rows']['Schematic'][0], res['rows']['PcbBoard'][0]
    check('ingest reads the .kicad_sch title block\'s own title onto both Schematic and PcbBoard ("ECC Push-Pull", '
          'not the bare directory name)', sch_row['title'] == 'ECC Push-Pull' and board_row['title'] == 'ECC Push-Pull')
    check('ingest fills description + licence from the sibling SOURCE.json on both rows — non-empty, and the words '
          'are SOURCE.json\'s own ("what" + licence + package), nothing invented',
          bool(sch_row['description']) and bool(board_row['description']) and board_row['licence'] == 'GPL-2.0-or-later'
          and 'kicad-demos' in board_row['description'] and 'GPL-2.0-or-later' in board_row['description'])


def artifact_urls():
    """arturl fix: POLARI_PUBLIC_BASE_URL unset (the staging case that hid every drawing — every row stored
    artifact_url='') must still yield a USABLE url, relative to the API root, and GET /api/pcb/svgs must still
    list that row — both straight from a fresh export (artifact_url populated) and from a row stored BEFORE the
    fix (artifact_url='', only artifact_path set)."""
    from pcb.custom import ingest as I
    from pcb.pcb_api import resolved_artifact_url, svg_items
    old = os.environ.pop('POLARI_PUBLIC_BASE_URL', None)
    try:
        want = '/api/pcb/artifacts/ecc83-pp/layers/ecc83-pp-F_Cu.svg'
        check('artifact_url() with POLARI_PUBLIC_BASE_URL unset is relative to the API root (no public base URL '
              'needed — this is the bug: staging never set it, so every row stored artifact_url=\'\')',
              I.artifact_url('ecc83-pp', 'layers/ecc83-pp-F_Cu.svg') == want)
        rec = {'exports': [{'export_set': 'layers', 'kind': 'svg-layer', 'layer': 'F.Cu', 'filename': 'ecc83-pp-F_Cu.svg',
                            'path': 'layers/ecc83-pp-F_Cu.svg', 'extension': '.svg', 'sha256': 'abc123', 'bytes': 10,
                            'accepted': 'n/a', 'fab_name': '', 'naming_note': '', 'argv': 'kicad-cli pcb export svg'}],
               'engine': {'version': 'x'}, 'source_date': '2020-01-01T00:00:00Z'}
        rows = I.export_rows('ecc83-pp', rec)
        check('export_rows() with the env var unset gives the FabricationExport row a relative artifact_url (the '
              'same the live server will now store on ingest)', len(rows) == 1 and rows[0]['artifact_url'] == want
              and rows[0]['artifact_path'] == 'ecc83-pp/layers/ecc83-pp-F_Cu.svg')
    finally:
        if old is not None:
            os.environ['POLARI_PUBLIC_BASE_URL'] = old

    from pcb.objects.pcb.FabricationExport import FabricationExport
    fresh = FabricationExport(manager=None, name='ecc83-pp:layers:fresh', board='ecc83-pp', export_set='layers',
                              kind='svg-layer', layer='F.Cu', filename='ecc83-pp-F_Cu.svg',
                              artifact_path='ecc83-pp/layers/ecc83-pp-F_Cu.svg', artifact_url=want)
    stale = FabricationExport(manager=None, name='ecc83-pp:layers:stale', board='ecc83-pp', export_set='layers',
                              kind='svg-layer', layer='B.Cu', filename='ecc83-pp-B_Cu.svg',
                              artifact_path='ecc83-pp/layers/ecc83-pp-B_Cu.svg', artifact_url='')
    check('resolved_artifact_url() passes a stored (fresh) artifact_url through unchanged',
          resolved_artifact_url(fresh.artifact_url, fresh.artifact_path) == want)
    check('resolved_artifact_url() derives the url from artifact_path alone for a STALE row (artifact_url=\'\', '
          'stored before the arturl fix) — the already-ingested rows on the live stack work without re-ingesting',
          resolved_artifact_url(stale.artifact_url, stale.artifact_path) == '/api/pcb/artifacts/ecc83-pp/layers/ecc83-pp-B_Cu.svg')

    items = svg_items([fresh, stale], 'svg-layer')
    check('GET /api/pcb/svgs (via svg_items — the same function the endpoint calls) lists BOTH the fresh row and '
          'the stale artifact_url=\'\' row — neither is dropped for lack of a url', {it['url'] for it in items} ==
          {want, '/api/pcb/artifacts/ecc83-pp/layers/ecc83-pp-B_Cu.svg'}, str(items))


def engines_refusal():
    from pcb.custom import pcb_engines as E
    old = os.environ.pop(E.KNOB, None)
    old_img = os.environ.pop(E.IMAGE_KNOB, None)
    try:
        msg = E.refusal()
        check('the refusal names the knob, the default image and the provider module (never silent)',
              E.KNOB in msg and E.DEFAULT_IMAGE in msg and E.PROVIDER_MODULE in msg)
        r = E.resolve()
        if r['how'] == 'refused':
            check('resolve() with no knob, no local binary, no local image, no reachable provider is refused', True)
        else:
            check('resolve() found a local kicad-cli / image / provider on THIS host (not the no-engine path; informational)', True,
                  '— found %s at %s' % (r['how'], r['where']))
    finally:
        if old is not None:
            os.environ[E.KNOB] = old
        if old_img is not None:
            os.environ[E.IMAGE_KNOB] = old_img


#: a tiny FAKE library (no engine, no network) — just enough for schematic_writer's mechanics
_FAKE_R = '(symbol "Device:R" (pin passive line (at 0 2.54 270) (length 2.54) (name "~") (number "1")) ' \
          '(pin passive line (at 0 -2.54 90) (length 2.54) (name "~") (number "2")))'
_FAKE_PWR5 = '(symbol "power:+5V" (power) (pin power_in line (at 0 0 90) (length 0) (name "+5V") (number "1")))'
_FAKE_GND = '(symbol "power:GND" (power) (pin power_in line (at 0 0 270) (length 0) (name "GND") (number "1")))'
_FAKE_FLAG = '(symbol "power:PWR_FLAG" (power) (pin power_in line (at 0 0 90) (length 0) (name "pwr") (number "1")))'


def schematic_writer_offline():
    from pcb.custom import schematic_writer as W
    d = {'board': 'fixture', 'components': [{'ref': 'R1', 'lib_id': 'Device:R', 'value': '220', 'footprint': 'Resistor_THT:R',
                                             'role': 'resistor', 'pins': {'1': '+5V', '2': 'GND'}}],
        'nets': {'+5V': [('R1', '1')], 'GND': [('R1', '2')]}, 'unconnected': []}
    libs = {'Device:R': _FAKE_R, 'power:+5V': _FAKE_PWR5, 'power:GND': _FAKE_GND, 'power:PWR_FLAG': _FAKE_FLAG}
    text, report = W.write(d, libs, title='fixture')
    from pcb.custom import sexpr as S
    check('the written schematic passes its own check_kicad', S.check_kicad(S.parse(text), 'kicad_sch') == [])
    check('every wired pin on a power net becomes a power symbol (2 pins → 2 power symbols + 2 PWR_FLAGs, one per net)',
          report['power_symbols'] == 2 and len(report['connections']) == 2 and not report['unconnected_pins'])
    text2, _ = W.write(d, libs, title='fixture')
    check('deterministic: the same rows give the same bytes (uuid5, no dates)', text == text2)
    try:
        W.write({'board': 'x', 'components': [{'ref': 'R1', 'lib_id': 'Device:R', 'value': '1', 'footprint': '', 'role': 'r',
                                               'pins': {'9': 'GND'}}], 'nets': {}, 'unconnected': []}, libs)
        check('a pin number the library does not have is refused, not silently dropped', False)
    except W.WriterRefused:
        check('a pin number the library does not have is refused, not silently dropped', True)


def page():
    from pcb.pcb_page import SEED_PCB_PAGE_DISPLAYS as P
    names = {p['pageRoute'] for p in P}
    check('four pages: board-schematic, board-layout, board-bom, board-fab',
          names == {'board-schematic', 'board-layout', 'board-bom', 'board-fab'})
    # demo1b: board-schematic + board-layout each draw FIRST (the generic api-svg-panel), tables below; board-bom
    # and board-fab stay configured tables only (no drawing exists for a BOM or a fab profile).
    drawn = {'board-schematic', 'board-layout'}
    for p in P:
        rows = json.loads(p['definition'])['rows']
        items = [it for row in rows for it in row['items']]
        comps = [it['componentProps']['componentName'] for it in items]
        allowed = {'class-rows-table', 'api-svg-panel'} if p['pageRoute'] in drawn else {'class-rows-table'}
        check('/display/%s is configured tables (+ the generic svg panel on the drawn pages) only — no JSON panel' % p['pageRoute'],
              comps and set(comps) <= allowed, str(comps))
        if p['pageRoute'] in drawn:
            check('/display/%s: the FIRST item is the drawing (api-svg-panel)' % p['pageRoute'], comps[0] == 'api-svg-panel', str(comps))
        check('/display/%s: every item carries a non-empty description' % p['pageRoute'],
              all(it.get('description') for it in items), str([it['id'] for it in items if not it.get('description')]))


def main():
    classes()
    sexpr_roundtrip()
    fab_rules()
    kicad_read_fixture()
    ingest_offline()
    artifact_urls()
    engines_refusal()
    schematic_writer_offline()
    page()
    print('\n%d/%d checks passed' % (passed, total))
    return 0 if passed == total else 1


if __name__ == '__main__':
    sys.exit(main())
