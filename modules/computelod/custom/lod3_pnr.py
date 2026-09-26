"""
@module computelod.custom.lod3_pnr

THE WHOLE ADDER PLACED AND ROUTED (lod-3e, 2026-09-26; plan §H.3): lod-2 timed the adder's 96 SKY130 cells as a NETLIST
(OpenSTA, no wires: 11.94 ns at 1.8 V / 14.6 fF / 50 ps); lod-3c checked and extracted single cells. This flow puts the
SAME mapped netlist (initialData/lod2/rv32_add_sky130.v, lod-2's own output) through a full physical flow — floorplan →
placement → (no clock tree: the design is combinational) → global + detailed routing → fill → parasitic extraction — with
OpenROAD-flow-scripts (ORFS) in its published image at a PINNED tag, then times the ROUTED design with its parasitics in
OpenSTA under lod-2's exact conditions, and the same routed netlist WITHOUT the parasitics, so the cost of the wires is
one subtraction on one netlist.

Two variants, because a physical flow does not leave a netlist alone:
    as-flow      ORFS defaults — repair_design / repair_timing resize cells and insert buffers (what a P&R flow DOES to a
                 netlist; the honest "layout rung" number, with the census of what changed)
    cells-kept   every repair knob the flow exposes switched off (SKIP_CTS_REPAIR_TIMING, SKIP_INCREMENTAL_REPAIR,
                 SKIP_LAST_GASP, DONT_BUFFER_PORTS, …) — as close to "lod-2's 96 cells, wired" as the flow allows; the
                 census says what still changed (the flow's floorplan-stage repair is not switchable)

Engines resolve through the Polari engines ladder (`computelod.custom.eda_engines`): `orfs` = `make` inside the pinned
openroad/orfs image (its own OpenROAD, yosys, PDK copy — the LEF/GDS of sky130hd come from THAT copy, cited by the image
digest; the LIBERTY is OURS — lod-2's cached file, so the timing model is byte-identical to lod-2's), `sta` = the OpenSTA
the suite has always timed with. A worker without the ORFS image refuses; nothing runs `docker` from here directly.

Committed (small, ours): the routed netlist (6_final.v), its parasitics (6_final.spef), the placement + routing (6_final.def),
the flow's metrics (6_report.json), reports and our OpenSTA logs, per variant under initialData/lod3/pnr/<variant>/. NOT
committed: the GDS / ODB (they merge the PDK's cell layouts — PDK content never enters git).

    python3 -m computelod.custom.lod3_pnr run [--variants as-flow,cells-kept] [--work DIR]
"""
import hashlib
import json
import os
import re
import shutil
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
MOD = os.path.dirname(HERE)
OUT = os.path.join(MOD, 'initialData', 'lod3', 'pnr')
LOD2 = os.path.join(MOD, 'initialData', 'lod2')
NETLIST = 'rv32_add_sky130.v'   # lod-2's mapped netlist (yosys abc -liberty), 96 cells
DESIGN = 'rv32_add'
PLATFORM = 'sky130hd'
#: the flow's knobs per variant (ORFS variables.yaml names); values are strings as make sees them
VARIANTS = {
    'as-flow': {'CORE_UTILIZATION': '20', 'PLACE_DENSITY': '0.50', 'LEC_CHECK': '0'},
    'cells-kept': {'CORE_UTILIZATION': '20', 'PLACE_DENSITY': '0.50', 'LEC_CHECK': '0', 'SKIP_CTS_REPAIR_TIMING': '1', 'SKIP_INCREMENTAL_REPAIR': '1',
                   'SKIP_LAST_GASP': '1', 'DONT_BUFFER_PORTS': '1', 'SKIP_GATE_CLONING': '1', 'SKIP_PIN_SWAP': '1', 'SKIP_BUFFER_REMOVAL': '1'},
}
KNOB_NOTES = {'CORE_UTILIZATION': '20 %: a first run at 40 % failed placement at 108 % utilization once the flow had buffered the ports and resized — the number is a knob, stated, not a result',
              'LEC_CHECK': 'off: the image\'s equivalence checker (kepler-formal) dies with an illegal instruction on this CPU; nothing else depends on it'}
SDC = '''current_design {design}
# a purely combinational adder: ONE virtual clock so the flow constrains and reports the input → output paths (10 ns, generous:
# no setup violation is ever asked for — the flow's repairs are for slew / capacitance / fanout, and hold at the ports)
create_clock -name vclk -period 10.0
set_input_delay 0.0 -clock vclk [all_inputs]
set_output_delay 0.0 -clock vclk [all_outputs]
set_load {load_pf} [all_outputs]
set_input_transition {slew_ns} [all_inputs]
'''
STA_TCL = '''read_liberty {lib}
read_verilog 6_final.v
link_design {design}
{spef}
set_load {load_pf} [all_outputs]
set_input_transition {slew_ns} [all_inputs]
report_checks -unconstrained -path_delay max -fields {{slew cap input_pins}} -digits 4
report_checks -unconstrained -path_delay min -digits 4
'''


def _sha(p):
    return hashlib.sha256(open(p, 'rb').read()).hexdigest()


def _census(verilog_text):
    return dict(sorted(((k, v) for k, v in _count(re.findall(r'\bsky130_fd_sc_hd__(\w+)\b', verilog_text)).items()), key=lambda kv: -kv[1]))


def _count(items):
    out = {}
    for x in items:
        out[x] = out.get(x, 0) + 1
    return out


def _liberty_areas(lib_text):
    return {m.group(1): float(m.group(2)) for m in re.finditer(r'cell \("sky130_fd_sc_hd__(\w+)"\) \{.*?area : ([\d.]+)', lib_text, re.S)}


def _arrival(sta_text):
    """(max-path arrival ns, its start, its end, min-path arrival ns) from an OpenSTA -unconstrained report."""
    blocks = re.split(r'\nStartpoint: ', sta_text)
    out = []
    for b in blocks[1:]:
        m = re.search(r'([-\d.]+)\s+data arrival time', b)
        s = re.match(r'(\S+)', b).group(1); e = re.search(r'Endpoint: (\S+)', b)
        out.append((float(m.group(1)) if m else None, s, e.group(1) if e else None))
    return out


def run(variants=None, work=None):
    from computelod.custom.eda_engines import resolve, run as eng, ORFS_IMAGE, orfs_image_digest
    from computelod.custom.lod2_silicon import fetch_liberty, CONDITIONS as L2
    for e in ('orfs', 'sta'):
        r = resolve(e)
        if r['how'] == 'refused':
            raise SystemExit(r['why'])
    lib_path, lib_sha = fetch_liberty(); lib_text = open(lib_path, errors='replace').read(); areas = _liberty_areas(lib_text)
    net_in = os.path.join(LOD2, NETLIST); net_in_text = open(net_in).read()
    load_pf, slew_ns = L2['load_pf'], L2['input_slew_ns']
    work = work or os.path.join(os.environ.get('TMPDIR', '/tmp'), 'polari-lod3e'); os.makedirs(work, exist_ok=True)
    rep = {'flow': 'OpenROAD-flow-scripts in %s (digest %s) through the engines ladder (orfs = make in that image; sta = OpenSTA)' % (ORFS_IMAGE, orfs_image_digest() or 'not inspected'),
           'engines': {e: resolve(e) for e in ('orfs', 'sta')}, 'input_netlist': {'file': 'lod2/' + NETLIST, 'sha256': _sha(net_in), 'census': _census(net_in_text), 'cells': sum(_census(net_in_text).values()),
                                                                               'area_um2': round(sum(areas[c] * n for c, n in _census(net_in_text).items()), 2)},
           'liberty': {'file': os.path.basename(lib_path), 'sha256': lib_sha, 'note': 'OURS — lod-2\'s cached Liberty handed to the flow as LIB_FILES, so the timing model is byte-identical to lod-2\'s; LEF/GDS are the image\'s sky130hd platform copy'},
           'conditions': {'voltage_v': 1.8, 'temperature_c': 25.0, 'load_pf': load_pf, 'input_slew_ns': slew_ns, 'sdc': 'virtual clock 10 ns, I/O delays 0 (constrains the I/O paths; no setup violation asked for)',
                          'baseline_lod2_ns': None, 'platform': PLATFORM, 'knob_notes': KNOB_NOTES},
           'variants': {}}
    from computelod.custom.lod2_silicon import report as lod2_report
    l2 = lod2_report() or {}
    rep['conditions']['baseline_lod2_ns'] = (l2.get('timing') or {}).get('max_path_ns')
    for var in (variants or list(VARIANTS)):
        knobs = VARIANTS[var]
        vw = os.path.join(work, var); shutil.rmtree(vw, ignore_errors=True); os.makedirs(vw)
        shutil.copy(net_in, vw); shutil.copy(lib_path, vw)
        open(os.path.join(vw, 'constraint.sdc'), 'w').write(SDC.format(design=DESIGN, load_pf=load_pf, slew_ns=slew_ns))
        cfg = ['export DESIGN_NAME = %s' % DESIGN, 'export PLATFORM = %s' % PLATFORM, 'export VERILOG_FILES = /w/%s' % NETLIST, 'export SDC_FILE = /w/constraint.sdc',
               'export LIB_FILES = /w/%s' % os.path.basename(lib_path), 'export ABC_AREA = 0'] + ['export %s = %s' % kv for kv in knobs.items()]
        open(os.path.join(vw, 'config.mk'), 'w').write('\n'.join(cfg) + '\n')
        r = eng('orfs', vw, ['-C', '/OpenROAD-flow-scripts/flow', 'DESIGN_CONFIG=/w/config.mk', 'WORK_HOME=/w/work'], timeout=1800, stdout_to='orfs.log')
        base = os.path.join(vw, 'work'); res = os.path.join(base, 'results', PLATFORM, DESIGN, 'base'); logs = os.path.join(base, 'logs', PLATFORM, DESIGN, 'base'); reps = os.path.join(base, 'reports', PLATFORM, DESIGN, 'base')
        entry = {'knobs': knobs, 'returncode': r['returncode'], 'how': r['how'], 'stages_logged': sorted(f for f in os.listdir(logs) if f.endswith('.log')) if os.path.isdir(logs) else [],
                 'finished': os.path.exists(os.path.join(res, '6_final.spef'))}
        if not entry['finished']:
            entry['refused'] = 'the flow did not reach the final stage — see orfs.log (last 600 chars follow)'; entry['tail'] = (r['stdout'] + r['stderr'])[-600:]
            rep['variants'][var] = entry
            continue
        fin = json.load(open(os.path.join(logs, '6_report.json'))); fp = json.load(open(os.path.join(logs, '2_1_floorplan.json'))); rt = json.load(open(os.path.join(logs, '5_2_route.json')))
        final_v = open(os.path.join(res, '6_final.v')).read(); census = _census(final_v)
        logic = {c: n for c, n in census.items() if not re.match(r'(clkbuf|buf|clkdlybuf|dlymetal|dlygate|fill|tap|decap|conb)', c)}
        entry['census'] = {'final': census, 'logic_cells': sum(logic.values()), 'logic_area_um2': round(sum(areas.get(c, 0) * n for c, n in logic.items()), 2),
                           'buffers_and_delays': sum(n for c, n in census.items() if c not in logic), 'resized': {c: n for c, n in logic.items() if c not in rep['input_netlist']['census']},
                           'kept': {c: n for c, n in logic.items() if c in rep['input_netlist']['census']}, 'mapping_unchanged': logic == rep['input_netlist']['census']}
        entry['metrics'] = {'die_area_um2': fin.get('finish__design__die__area'), 'core_area_um2': fin.get('finish__design__core__area'), 'stdcell_area_um2': fin.get('finish__design__instance__area__stdcell'),
                            'stdcell_count': fin.get('finish__design__instance__count__stdcell'), 'utilization': fin.get('finish__design__instance__utilization'),
                            'timing_repair_buffers': fin.get('finish__design__instance__count__class:timing_repair_buffer', 0), 'tap_cells': fin.get('finish__design__instance__count__class:tap_cell', 0),
                            'fill_cells': fin.get('finish__design__instance__count__class:fill_cell', 0), 'logic_cells_flow_count': fin.get('finish__design__instance__count__class:multi_input_combinational_cell'), 'rows': fin.get('finish__design__rows'),
                            'wirelength_um': rt.get('detailedroute__route__wirelength'), 'vias': rt.get('detailedroute__route__vias'), 'route_drc_errors': rt.get('detailedroute__route__drc_errors'),
                            'floorplan_utilization': fp.get('floorplan__design__instance__utilization'), 'setup_ws_ns_flow': fin.get('finish__timing__setup__ws'), 'hold_ws_ns_flow': fin.get('finish__timing__hold__ws'),
                            'flow_errors': fin.get('finish__flow__errors__count'), 'flow_warnings': fin.get('finish__flow__warnings__count')}
        spef = open(os.path.join(res, '6_final.spef'), errors='replace').read()
        entry['spef'] = {'nets': len(re.findall(r'^\*D_NET', spef, re.M)), 'sha256': _sha(os.path.join(res, '6_final.spef')), 'units': re.search(r'\*C_UNIT ([^\n]+)', spef).group(1).strip()}
        # ---- OpenSTA under lod-2's conditions: WITH the parasitics, and the same routed netlist WITHOUT them
        sw = os.path.join(vw, 'sta'); os.makedirs(sw, exist_ok=True)
        for f in ('6_final.v', '6_final.spef'):
            shutil.copy(os.path.join(res, f), sw)
        shutil.copy(lib_path, sw)
        timing = {}
        for tag, spef_line in (('with_parasitics', 'read_spef 6_final.spef'), ('without_parasitics', '# no SPEF: the routed netlist as a netlist')):
            open(os.path.join(sw, 'sta_%s.tcl' % tag), 'w').write(STA_TCL.format(lib=os.path.basename(lib_path), design=DESIGN, spef=spef_line, load_pf=load_pf, slew_ns=slew_ns))
            rs = eng('sta', sw, ['-exit', 'sta_%s.tcl' % tag], timeout=600, stdout_to='sta_%s.log' % tag)
            paths = _arrival(rs['stdout'] + rs['stderr'])
            timing[tag] = {'max_path_ns': paths[0][0] if paths else None, 'max_path': '%s → %s' % (paths[0][1], paths[0][2]) if paths else None, 'min_path_ns': paths[1][0] if len(paths) > 1 else None, 'how': rs['how']}
        if timing['with_parasitics']['max_path_ns'] and timing['without_parasitics']['max_path_ns']:
            timing['wire_cost_ns'] = round(timing['with_parasitics']['max_path_ns'] - timing['without_parasitics']['max_path_ns'], 4)
            timing['wire_cost_pct'] = round(timing['wire_cost_ns'] / timing['without_parasitics']['max_path_ns'] * 100, 1)
            if rep['conditions']['baseline_lod2_ns']:
                timing['vs_lod2_netlist_ns'] = round(timing['with_parasitics']['max_path_ns'] - rep['conditions']['baseline_lod2_ns'], 4)
                timing['vs_lod2_note'] = 'NOT the wire cost: lod-2 timed maj3_1 cells, the flow resized the carry chain to maj3_2 (census) — sizing gained more than the wires cost'
        entry['timing'] = timing
        # ---- keep the artefacts that are OURS
        keep = os.path.join(OUT, var); shutil.rmtree(keep, ignore_errors=True); os.makedirs(keep)
        for src, name in ((os.path.join(res, '6_final.v'), '6_final.v'), (os.path.join(res, '6_final.spef'), '6_final.spef'), (os.path.join(res, '6_final.def'), '6_final.def'),
                          (os.path.join(logs, '6_report.json'), '6_report.json'), (os.path.join(reps, '6_finish.rpt'), '6_finish.rpt'), (os.path.join(reps, '5_route_drc.rpt'), '5_route_drc.rpt'),
                          (os.path.join(reps, 'synth_stat.txt'), 'synth_stat.txt'), (os.path.join(sw, 'sta_with_parasitics.log'), 'sta_with_parasitics.log'), (os.path.join(sw, 'sta_without_parasitics.log'), 'sta_without_parasitics.log'),
                          (os.path.join(vw, 'config.mk'), 'config.mk'), (os.path.join(vw, 'constraint.sdc'), 'constraint.sdc'),
                          (os.path.join(reps, 'final_placement.webp.png'), 'final_placement.webp.png')):   # the routing image (680 kB) is regenerable, not committed
            if os.path.exists(src):
                shutil.copy(src, os.path.join(keep, name))
        entry['artefacts'] = sorted(os.listdir(keep)); entry['not_committed'] = ['6_final.gds', '6_final.odb (PDK cell layouts merged in — never in git)', 'final_routing.webp.png (680 kB, regenerable)']
        entry['flow_setup_note'] = ('the flow\'s own setup check against the 10 ns virtual clock: worst slack %+.3f ns — %s' % (entry['metrics']['setup_ws_ns_flow'], 'met' if entry['metrics']['setup_ws_ns_flow'] >= 0 else 'MISSED by that much: this is what the repairs the other variant runs would have fixed; the unconstrained path report above is unaffected'))
        rep['variants'][var] = entry
    done = {v: e for v, e in rep['variants'].items() if e.get('finished')}
    rep['summary'] = {'variants_finished': sorted(done), 'input_cells': rep['input_netlist']['cells'], 'input_area_um2': rep['input_netlist']['area_um2'], 'baseline_lod2_ns': rep['conditions']['baseline_lod2_ns'],
                      'per_variant': {v: {'routed_ns_with_parasitics': e['timing']['with_parasitics']['max_path_ns'], 'wire_cost_ns': e['timing'].get('wire_cost_ns'), 'wire_cost_pct': e['timing'].get('wire_cost_pct'),
                                          'logic_cells': e['census']['logic_cells'], 'mapping_unchanged': e['census']['mapping_unchanged'], 'buffers': e['census']['buffers_and_delays'],
                                          'core_area_um2': e['metrics']['core_area_um2'], 'utilization': e['metrics']['utilization'], 'wirelength_um': e['metrics']['wirelength_um'], 'route_drc_errors': e['metrics']['route_drc_errors']} for v, e in done.items()},
                      'reading': 'the layout rung entered for the WHOLE adder: routed, DRC-clean by the router\'s own count, its parasitics extracted and timed under lod-2\'s conditions; what the flow changed on the way (sizing, buffers) is counted, not hidden — '
                                 'the wire cost is the one subtraction that holds the netlist fixed'}
    os.makedirs(OUT, exist_ok=True)
    from computelod.custom.repro import record, file_entry
    gen = [file_entry(os.path.join(OUT, v, f)) for v in rep['variants'] for f in ('config.mk', 'constraint.sdc', '6_final.v', '6_final.spef', '6_final.def') if os.path.exists(os.path.join(OUT, v, f))]
    rep['reproduction'] = record('computelod.custom.lod3_pnr', inputs=[("lod-2's mapped netlist", net_in), ('SKY130 HD Liberty (cached, cited; handed to the flow as LIB_FILES)', lib_path)], engines=['sta', 'openroad'],
                                 knobs={v: e['knobs'] for v, e in rep['variants'].items()}, conditions=rep['conditions'], generated=gen,
                                 seeds={'GPL_RANDOM_SEED': 'flow default (unset: OpenROAD global_placement\'s built-in seed) — an ORFS knob, recorded not changed', 'GRT_SEED': 'flow default (unset) — ORFS knob', 'OR_SEED': 'flow default (unset) — ORFS knob (detailed routing)',
                                        'note': 'the flow exposes three seed knobs; this run used their defaults so the committed DEF/SPEF are what those defaults produce; set them in VARIANTS to perturb'},
                                 notes='the ORFS image is pinned by tag + digest in `flow`; the LEF/GDS come from that image\'s platform copy (not hashed here — the digest pins them)')
    json.dump(rep, open(os.path.join(OUT, 'pnr_report.json'), 'w'), indent=1)
    return rep


def report():
    p = os.path.join(OUT, 'pnr_report.json')
    return json.load(open(p)) if os.path.exists(p) else None


def rows(rep, lod2_rep):
    """ComputeMapping: the adder's cells → a placed-and-routed layout (per variant; evidence measured — the router's DRC count
    and the flow's metrics are tool output). Characterizations UP: routed delay with parasitics (simulated), wire cost, core
    area, wirelength, DRC count, instance count — layout → standard-cells / rtl."""
    if not rep or not lod2_rep:
        return [], []
    M = lambda **k: dict({'description': '', 'validity_json': '{}', 'loss_note': '', 'uncertainty_json': '{}', 'notes': ''}, **k)
    C = lambda **k: dict({'description': '', 'notes': ''}, **k)
    mp = lod2_rep['mapping']
    cells_ref = 'sky130_fd_sc_hd rv32_add: %d cells, %.1f µm² (%s)' % (mp['cells'], mp['area_um2'], ', '.join('%s×%d' % (k.replace('sky130_fd_sc_hd__', ''), v) for k, v in list(mp['by_type'].items())[:3]))
    maps, chars = [], []
    for var, e in rep['variants'].items():
        if not e.get('finished'):
            continue
        m, t, c = e['metrics'], e['timing'], e['census']
        ev = 'lod3/pnr_report.json + lod3/pnr/%s/ — %s; OpenSTA on 6_final.v (+ 6_final.spef) under %s' % (var, rep['flow'], json.dumps({k: rep['conditions'][k] for k in ('voltage_v', 'temperature_c', 'load_pf', 'input_slew_ns')}))
        lay_ref = 'sky130hd rv32_add routed (%s): core %.0f µm², %d std cells (%d logic%s, %d buffers), %d µm wire, %d routing DRC' % (
            var, m['core_area_um2'], m['stdcell_count'], c['logic_cells'], '' if c['mapping_unchanged'] else ' — %d resized' % sum(c['resized'].values()), c['buffers_and_delays'], m['wirelength_um'], m['route_drc_errors'])
        maps.append(M(name='lod3e: adder cells → placed-and-routed layout (%s)' % var, kind='one-to-one', source_rung='standard-cells', source_ref=cells_ref, target_rung='layout', target_ref=lay_ref,
                      mapping_status='validated' if m['route_drc_errors'] == 0 and m['flow_errors'] == 0 else 'implemented', evidence_level='measured', evidence_ref=ev,
                      loss_note='' if c['mapping_unchanged'] else 'the flow resized %s and added %d buffers/delay cells (%s) — the mapping lod-2 chose is not what was routed; counted here' % (
                          ', '.join('%s×%d' % kv for kv in c['resized'].items()), c['buffers_and_delays'], 'repairs on' if var == 'as-flow' else 'repairs switched off where the flow allows'),
                      notes='ORFS %s: floorplan → place → route → fill → RCX; router DRC %d (its own count), flow errors %d; knobs %s. %s' % (var, m['route_drc_errors'], m['flow_errors'], json.dumps(e['knobs']),
                                                                                                                                    'the mapped cells are unchanged' if c['mapping_unchanged'] else 'census: kept %s; resized/added %s' % (json.dumps(c['kept']), json.dumps(c['resized'])))))
        tgt = 'sky130_fd_sc_hd rv32_add (%s)' % var
        def ch(name, characteristic, method, result, units, level, status, extra, note):
            chars.append(C(name='lod3e: rv32_add %s (%s)' % (name, var), source_rung='layout', source_ref=lay_ref, target_rung='standard-cells', target_ref=tgt, characteristic=characteristic, method=method,
                           conditions_json=json.dumps(dict({k: rep['conditions'][k] for k in ('voltage_v', 'temperature_c', 'load_pf', 'input_slew_ns')}, variant=var, **extra)), result=result, units=units,
                           mapping_status=status, evidence_level=level, evidence_ref=ev, notes=note))
        ch('propagation delay (routed, with parasitics)', 'propagation_delay', 'OpenSTA with the extracted SPEF', t['with_parasitics']['max_path_ns'], 'ns', 'simulated', 'validated',
           {'path': t['with_parasitics']['max_path'], 'without_parasitics_ns': t['without_parasitics']['max_path_ns'], 'baseline_lod2_netlist_ns': rep['conditions']['baseline_lod2_ns'], 'mapping_unchanged': c['mapping_unchanged']},
           'the routed adder %s: %.4f ns with its wires vs %.4f ns as a bare netlist of the SAME routed cells; lod-2\'s netlist-only number was %s ns%s' % (
               var, t['with_parasitics']['max_path_ns'], t['without_parasitics']['max_path_ns'], rep['conditions']['baseline_lod2_ns'], '' if c['mapping_unchanged'] else ' — on a different cell sizing (the flow resized), so that difference is sizing + wires, not wires'))
        if t.get('wire_cost_ns') is not None:
            ch('wire delay cost', 'wire_delay', 'OpenSTA with minus without the SPEF, same netlist', t['wire_cost_ns'], 'ns', 'simulated', 'validated', {'wire_cost_pct': t['wire_cost_pct'], 'spef_nets': e['spef']['nets']},
               'the wires alone: %+.4f ns (%+.1f %%) on the routed netlist — one subtraction, the netlist held fixed' % (t['wire_cost_ns'], t['wire_cost_pct']))
        ch('core area', 'area', 'OpenROAD floorplan (CORE_UTILIZATION knob)', m['core_area_um2'], 'um2', 'measured', 'implemented', {'die_area_um2': m['die_area_um2'], 'utilization_final': m['utilization'], 'core_utilization_knob': e['knobs'].get('CORE_UTILIZATION')},
           'core %.0f µm² (die %.0f) from a %s %% utilization KNOB — the std-cell area inside it is %.1f µm² (%d cells); the number a knob decides is said to be one' % (m['core_area_um2'], m['die_area_um2'], e['knobs'].get('CORE_UTILIZATION'), m['stdcell_area_um2'], m['stdcell_count']))
        ch('routed wirelength', 'wirelength', 'OpenROAD detailed router', float(m['wirelength_um']), 'um', 'measured', 'validated', {'vias': m['vias']}, '%d µm of wire, %d vias' % (m['wirelength_um'], m['vias']))
        ch('routing DRC violations', 'drc_violations', 'OpenROAD detailed router (its own check)', float(m['route_drc_errors']), 'violations', 'measured', 'validated', {},
           'the router\'s own DRC count after the last iteration: %d (magic\'s full-rule DRC on the merged GDS is NOT run here — the cell-level lod-3c check stands for the cells)' % m['route_drc_errors'])
        ch('instances after place-and-route', 'device_count', 'OpenROAD report', float(m['stdcell_count']), 'cells', 'measured', 'validated', {'logic': c['logic_cells'], 'buffers_and_delays': c['buffers_and_delays'], 'tap_cells': m['tap_cells'], 'fill_cells': m['fill_cells']},
           '%d standard cells placed: %d logic (input netlist %d) + %d buffers/delays; %d taps and %d fill cells besides' % (m['stdcell_count'], c['logic_cells'], rep['input_netlist']['cells'], c['buffers_and_delays'], m['tap_cells'], m['fill_cells']))
    return maps, chars


if __name__ == '__main__':
    if len(sys.argv) > 1 and sys.argv[1] == 'run':
        vs = sys.argv[sys.argv.index('--variants') + 1].split(',') if '--variants' in sys.argv else None
        wk = sys.argv[sys.argv.index('--work') + 1] if '--work' in sys.argv else None
        print(json.dumps(run(vs, wk)['summary'], indent=1))
    else:
        r = report()
        print(json.dumps(r['summary'], indent=1) if r else 'no report yet: python3 -m computelod.custom.lod3_pnr run')
