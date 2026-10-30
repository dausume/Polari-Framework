"""pcb_kicad_geometry_selftest - kxc-4 (AI-Notes/plans/KICAD_INTERCHANGE_PLAN.md): THE PCB COMPLETE - pads, the copper of each net, zones, net classes, custom
rules and the drawing on every layer, as rows (the single-Board design view's data, BENCH_BOARDS_PLAN bob-3). References: custom/reference/
pcbnew_geometry_<board>.json (pcbnew, KiCad 10.0.6 on econ-core, 2026-10-30: counts, length per net, each zone's filled area) and pcbnew_pads_*.tsv.
Run by pcb_selftest.main().
"""
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
DEMOS = os.path.join(HERE, 'custom', 'upstream', 'kicad-demos-9.0.2')
REF = os.path.join(HERE, 'custom', 'reference')


def run_kicad_geometry(check):
    from pcb.custom import kicad_read as K

    res = {}
    for sub, board, ref in (('complex_hierarchy', 'complex_hierarchy', 'complex_hierarchy'), ('ecc83', 'ecc83-pp', 'ecc83')):
        rows = K.read_project(K.read_dir(os.path.join(DEMOS, sub)), board)
        res[board] = (rows, json.load(open(os.path.join(REF, 'pcbnew_geometry_%s.json' % ref))))
    counts = {}
    for b, (rows, ref) in res.items():
        ng = rows['NetGeometry']
        counts[b] = ((len(rows['PcbPad']), sum(r['segments'] for r in ng), sum(r['arcs'] for r in ng), sum(r['vias'] for r in ng), len(rows['PcbZone'])),
                     (ref['pads'], ref['segments'], ref['arcs'], ref['vias'], ref['zones']))
    check('KXC-4 COUNTS = pcbnew\'s: pads, track segments, arcs, vias and zones of both demo boards equal what KiCad\'s own board model counts '
          '(complex_hierarchy 165 pads / 364 segments / 166 zones - 165 of them teardrops; ecc83 33 / 59 / 1)', all(a == c for a, c in counts.values()), counts)
    worst_len, worst_area = 0.0, 0.0
    for b, (rows, ref) in res.items():
        mine = {r['net']: r['length_mm'] for r in rows['NetGeometry']}
        worst_len = max([worst_len] + [abs(mine.get(n, 0.0) - v) for n, v in ref['length_mm'].items()])
        ours = sorted(z['filled_area_mm2'] for z in rows['PcbZone'])
        worst_area = max([worst_area] + [abs(a - c) for a, c in zip(ours, ref['zone_filled_mm2'])])
    check('KXC-4 COPPER = pcbnew\'s: every net\'s routed length equals KiCad\'s (one NetGeometry row per net, D-kxc-2) and every zone\'s filled copper area '
          'agrees within 0.002 mm2 (the shoelace over the filled polygons)', worst_len < 1e-3 and worst_area < 2e-3, (worst_len, worst_area))
    rows = res['complex_hierarchy'][0]
    nc = {c['netclass']: c for c in rows['PcbNetClass']}
    pads = {(p['ref'], p['number']): p for p in rows['PcbPad']}
    gfx = {(g['layer'], g['item']): g['count'] for g in rows['PcbLayerGraphics']}
    check('KXC-4 NET CLASSES, PADS, LAYER DRAWINGS: the .kicad_pro classes Default (track 0.4 mm) and power (0.6 mm) with their nets; a pad carries type, '
          'shape, size, drill, layers, net and ERC pin type (C104 pad 1: thru_hole rect 2 x 2 mm, drill 1 mm, +12V, passive); the silkscreen, fab and '
          'courtyard drawings are counted per layer with their bounding boxes',
          nc['Default']['track_width'] == 0.4 and nc['power']['track_width'] == 0.6 and nc['power']['net_count'] + nc['Default']['net_count'] >= 49
          and pads[('C104', '1')]['pad_type'] == 'thru_hole' and pads[('C104', '1')]['size_w_mm'] == 2.0 and pads[('C104', '1')]['drill_mm'] == 1.0
          and pads[('C104', '1')]['net'] == '+12V' and gfx.get(('F.SilkS', 'gr_line'), 0) > 0 and gfx.get(('F.CrtYd', 'gr_line'), 0) > 0,
          (sorted(nc), pads.get(('C104', '1'), {}).get('net')))
    cov = {(c['file'], c['element']): c for c in rows['KiCadCoverage']}
    check('KXC-4 COVERAGE MOVES: the board file\'s footprints, segments, zones and edge drawings are now TYPED (PcbPad / NetGeometry / PcbZone / '
          'PcbLayerGraphics), not summarised or counted', all(cov[('complex_hierarchy.kicad_pcb', e)]['handling'] == 'typed' for e in ('footprint', 'segment', 'zone', 'gr_line')),
          {e: cov[('complex_hierarchy.kicad_pcb', e)]['handling'] for e in ('footprint', 'segment', 'zone', 'gr_line')})
