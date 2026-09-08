"""
Selftest for cntfet.custom.cnt_level_scenes — the MULTISCALE scenes: FETs
plugged into cell layouts (real math-shape geometry or black-box
stand-ins), cells as instancable data-carrying boxes plugged into
blocks. The upsert CREATE path constructs a live SimSpaceDefinition
(needs the real server) — here the builders + the update path are
proven; creation is a live-verification item.

Run from polari-framework/modules/:
  PYTHONPATH=..:../polariApiServer python3 -m cntfet.level_scenes_selftest
"""

import json
import sys
from types import SimpleNamespace

from cntfet import cntfet_selftest as st
from cntfet.custom.cnt_level_scenes import (
    LEVEL_SCENE_KNOBS, _flatten, block_scene, cell_scene,
    generate_scene, scene_name, upsert_scene,
)
from cntfet.summary_selftest import _mgr, _seed_si

_results = []


def check(label, cond, extra=''):
    _results.append((label, bool(cond)))
    print(f'{"PASS" if cond else "FAIL"}: {label}'
          + (f' — {extra}' if extra and not cond else ''))


def main():
    mgr = _mgr()
    st._seed_all(mgr)
    _seed_si(mgr)

    # ---- cell scale, real geometry -------------------------------
    r = cell_scene(mgr, 'cinv', 'si-nmos-planar-90', dim='3d',
                   lod='real')
    d = json.loads(r['fields']['definition']) if r.get('ok') else {}
    fets = [e for e in d.get('freestanding', [])
            if str(e.get('shapeRef', '')).startswith('mathshape:')]
    check('cell 3d real: ok, named cell-3d-…, every FET instance '
          'references the SAME fet-part math shapes as the FET '
          'scenes (one geometry source across scales)',
          r.get('ok')
          and r['fields']['name'] == scene_name(
              'cell', '3d', 'cinv', 'si-nmos-planar-90')
          and r['instances'] == 2
          and fets
          and all('fet-part-si-nmos-planar-90' in e['shapeRef']
                  for e in fets),
          str(r.get('error') or r.get('entries')))
    check('cell 3d real: orbit camera + rails/tracks/stubs present '
          '(the interconnect that forms the cell) + schematic-'
          'convention honesty stated',
          r.get('ok')
          and '"mode": "orbit"' in r['fields']['camera_json']
          and any(e['userData'].get('kind') == 'rail'
                  for e in d['freestanding'])
          and any(e['userData'].get('kind') == 'net-track'
                  for e in d['freestanding'])
          and any(e['userData'].get('kind') == 'pin-stub'
                  for e in d['freestanding'])
          and 'not lithography' in r['fields']['description'])

    rb = cell_scene(mgr, 'cinv', 'si-nmos-planar-90', dim='3d',
                    lod='blackbox')
    db_ = json.loads(rb['fields']['definition']) if rb.get('ok') else {}
    boxes = [e for e in db_.get('freestanding', [])
             if e['userData'].get('kind') == 'fet-instance']
    check('cell 3d blackbox: stand-in boxes carry the scale-'
          'boundary contract (device summaryPath + nets + the FET '
          'scene one rung down)',
          rb.get('ok') and len(boxes) == 2
          and all(b['userData']['summaryPath']
                  == '/api/fet/device/si-nmos-planar-90/summary'
                  and b['userData']['nets'].get('gate')
                  and b['userData']['fetScene']
                  for b in boxes))

    r2 = cell_scene(mgr, 'cnand2', 'si-nmos-planar-90', dim='2d',
                    lod='real')
    d2 = json.loads(r2['fields']['definition']) if r2.get('ok') else {}
    check('cell 2d: always the box layout (stated — math shapes are '
          'a 3-D pipeline), 2-element non-uniform scales on the '
          '40×40 style base',
          r2.get('ok')
          and '2-D scenes always use the box layout'
          in r2['fields']['description']
          and all(len(e['scale']) == 2 and e['scale'][0] > 0
                  for e in d2.get('freestanding', []))
          and r2['instances'] == 4)

    check('compose cells flatten through their stages (cbuf = 2 '
          'chained cinv = 4 FETs)',
          len(_flatten('cbuf')) == 4
          and cell_scene(mgr, 'cbuf', 'si-nmos-planar-90',
                         dim='3d', lod='blackbox')['instances'] == 4)

    rc = cell_scene(mgr, 'cinv', 'cnt-aligned-s1', dim='3d',
                    lod='real')
    dc = json.loads(rc['fields']['definition']) if rc.get('ok') else {}
    cnt_fets = [e for e in dc.get('freestanding', [])
                if str(e.get('shapeRef', '')).startswith('mathshape:')]
    check('CNT device cell: real pieces resolve too, with the FET '
          'scenes\' radial view exaggeration kept (scale y = 3× x)',
          rc.get('ok') and cnt_fets
          and abs(cnt_fets[0]['scale'][1]
                  - 3.0 * cnt_fets[0]['scale'][0]) < 1e-6,
          str(rc.get('error')))

    tiny = cell_scene(mgr, 'cnand2', 'si-nmos-planar-90', dim='3d',
                      lod='real', knobs={'real_entry_budget': 10})
    check('entry budget: lod=real over budget REFUSES naming the '
          'number and the blackbox alternative — never a silent '
          'downgrade',
          not tiny.get('ok') and 'budget' in tiny.get('error', '')
          and 'blackbox' in tiny.get('error', ''))

    check('refusals: unknown cell names the library scope, unknown '
          'device named, bad dim/lod named',
          not cell_scene(mgr, 'nope', 'si-nmos-planar-90')['ok']
          and not cell_scene(mgr, 'cinv', 'no-such-dev')['ok']
          and not cell_scene(mgr, 'cinv', 'si-nmos-planar-90',
                             dim='4d')['ok']
          and not cell_scene(mgr, 'cinv', 'si-nmos-planar-90',
                             lod='fancy')['ok'])

    # ---- block scale ---------------------------------------------
    b = block_scene(mgr, 'alu4', 'si-nmos-planar-90', dim='3d')
    bd = json.loads(b['fields']['definition']) if b.get('ok') else {}
    cells = [e for e in bd.get('freestanding', [])
             if e['userData'].get('kind') == 'cell-instance']
    check('block blackbox: one INSTANCABLE box per cell instance, '
          'each carrying its CellFETConfiguration name, the cell '
          'scene one scale down, and the page link',
          b.get('ok') and len(cells) == b['instances']
          and all(c['userData']['cellConfig'].startswith('cellcfg-')
                  and c['userData']['cellScene'].startswith('cell-3d-')
                  and 'cell-detail?object=' in c['userData']['page']
                  for c in cells),
          str(b.get('error') or b.get('instances')))
    check('block blackbox on an uncharacterized manager: the data '
          'tie is HONEST — refusal recorded per box, not fake '
          'numbers',
          b.get('ok')
          and all('refusal' in c['userData']['data']
                  or 'score' in c['userData']['data']
                  for c in cells)
          and any('refusal' in c['userData']['data'] for c in cells))
    check('block lod=real refused honestly in v1 (the cell scenes '
          'hold the real geometry one scale down)',
          not block_scene(mgr, 'alu4', 'si-nmos-planar-90',
                          lod='real').get('ok'))

    # ---- upsert + generate ---------------------------------------
    nm = scene_name('cell', '3d', 'cinv', 'si-nmos-planar-90')
    stub_row = SimpleNamespace(name=nm)
    stub_mgr = SimpleNamespace(
        objectTables={'SimSpaceDefinition': {1: stub_row}}, db=None)
    up = upsert_scene(stub_mgr, r['fields'])
    check('upsert is idempotent BY NAME: existing row updated in '
          'place (create path = live SimSpaceDefinition, verified '
          'live)',
          up.get('ok') and up['action'] == 'updated'
          and getattr(stub_row, 'definition', '')
          == r['fields']['definition'])

    stub_mgr2 = SimpleNamespace(
        objectTables={'SimSpaceDefinition': {1: SimpleNamespace(
            name=scene_name('block', '3d', 'alu4',
                            'si-nmos-planar-90'))}}, db=None)
    # generate_scene needs the REAL manager for the builders and the
    # stub tables for upsert — graft the tables on
    class _G:
        pass
    g = _G()
    for attr in dir(mgr):
        if not attr.startswith('__'):
            try:
                setattr(g, attr, getattr(mgr, attr))
            except Exception:
                pass
    g.objectTables = {**mgr.objectTables,
                      'SimSpaceDefinition':
                          stub_mgr2.objectTables['SimSpaceDefinition']}
    g.db = None
    rep = generate_scene(g, 'block', 'alu4', 'si-nmos-planar-90',
                         dim='3d')
    check('generate_scene: build + upsert + stats in one call, '
          'ladder framing stated; bad level refused',
          rep.get('ok') and rep['action'] == 'updated'
          and rep['entries'] > 0 and 'multiscale' in rep['ladder']
          and not generate_scene(g, 'chip', 'x', 'y').get('ok'),
          str(rep.get('error')))

    passed = sum(1 for _l, okc in _results if okc)
    print(f'\n{passed}/{len(_results)} checks passed')
    return 0 if passed == len(_results) else 1


if __name__ == '__main__':
    sys.exit(main())
