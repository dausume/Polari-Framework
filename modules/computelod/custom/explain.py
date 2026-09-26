"""
@module computelod.custom.explain

EACH ROW OF THE LADDER, EXPLAINED (bp-3, his ask 2026-09-25: "source ref and other refs and conditions don't really
make coherent sense to me … per row we likely need a human explainable row and an understanding of what was done and
how to duplicate it"). Read by GET /api/explain (polariApiServer/explainAPI.py) and shown on /object/:class/:name.

A CharacterizationMapping row is a MEASUREMENT: at the `source_rung`, the thing named by `source_ref` (a synthesized
netlist, a cell's transistor netlist, a layout) was measured for one `characteristic` with one `method` (a tool),
under `conditions_json` (which are load-bearing: change them and the number changes), and the number characterizes
the `target_ref` at the `target_rung` — "reading upward" through the ladder. The flow that produced it is named by
the row's prefix (lod1 / lod2 / lod2-cnt / lod3 / lod3-cnt / lod3c) and re-runs with one command.
"""
import json
from urllib.parse import quote


FLOWS = {
    'lod1': ('computelod.custom.lod1_chain', 'c = a + b followed down: gcc → RISC-V assembly → PicoRV32 → yosys synthesis → iverilog simulation', 'lod1/report.json'),
    'lod2': ('computelod.custom.lod2_silicon', 'the adder technology-mapped onto SKY130 standard cells (yosys abc -liberty) and timed with OpenSTA', 'lod2/report.json'),
    'lod2-cnt': ('computelod.custom.lod2_cnt', 'the same adder mapped onto OUR CNT cell library (the Liberty characterized here) and timed with OpenSTA', 'lod2/cnt/report.json'),
    'lod3': ('computelod.custom.lod3_cells', 'the standard cells opened: their transistor netlists and LEF footprints read from the PDK', 'lod3/report.json'),
    'lod3b': ('computelod.custom.lod3_devices', 'the cells\' transistor netlists RUN in ngspice against the PDK\'s device models', 'lod3/devices_report.json'),
    'lod3-cnt': ('computelod.custom.lod2_cnt', 'our CNT cell library\'s device lists, counted', 'lod2/cnt/report.json'),
    'lod3c': ('computelod.custom.lod3_layout', 'the cells\' layouts checked (magic DRC), parasitics extracted, LVS-matched (netgen), and re-simulated on the extracted netlist', 'lod3/layout_report.json'),
    'lod4': ('computelod.custom.lod4_process', 'the layout\'s layers read as process steps and materials', 'lod4/report.json'),
    'lod4c': ('computelod.custom.lod4_devices', 'the process node\'s own device numbers (Ion, Ioff, Vt, DIBL, subthreshold swing) RUN as DC sweeps on the PDK\'s BSIM4 models', 'lod4/devices_report.json'),
}

CHARACTERISTIC_WORDS = {
    'gate_count': 'how many logic cells the design needs', 'propagation_delay': 'how long a signal takes to get through',
    'dynamic_power': 'the power it burns while switching', 'leakage': 'the power it leaks while idle', 'area': 'how much silicon it occupies',
    'latency': 'how long one operation takes', 'throughput': 'how many operations per second', 'transistor_count': 'how many transistors it takes',
    'cycles': 'how many clock cycles it takes', 'device_count': 'how many devices it takes',
    'on_current': 'how much current one micron of transistor width carries when fully on', 'off_current': 'how much current leaks through when it is switched off',
    'threshold_voltage': 'the gate voltage at which the transistor starts to conduct', 'dibl': 'how much the drain voltage lowers the threshold (drain-induced barrier lowering)',
    'subthreshold_swing': 'how many millivolts of gate voltage it takes to change the leakage tenfold',
}


def _flow_for(name):
    prefix = str(name).split(':')[0].strip()
    if prefix in FLOWS:
        return FLOWS[prefix]
    return None


def _flow_key(name, method):
    prefix = str(name).split(':')[0].strip()
    # lod3 rows come from two flows: the READ ones (LEF/netlists) and the ngspice RUN ones (lod-3b)
    if prefix == 'lod3' and 'ngspice' in str(method).lower():
        return 'lod3b'
    return prefix


def _conditions(row):
    try:
        c = json.loads(getattr(row, 'conditions_json', '{}') or '{}')
    except Exception:
        c = {}
    return c if isinstance(c, dict) else {'conditions': c}


def _words(v):
    if isinstance(v, dict):
        return '; '.join('%s %s' % (k.replace('_', ' '), _words(x)) for k, x in v.items())
    if isinstance(v, (list, tuple)):
        return ', '.join(_words(x) for x in v)
    if isinstance(v, float):
        return '%g' % v
    return str(v)


def explain_characterization(manager, row):
    name = str(row.name)
    key = _flow_key(name, getattr(row, 'method', ''))
    flow = FLOWS.get(key)
    ch = str(getattr(row, 'characteristic', '') or '')
    ch_words = CHARACTERISTIC_WORDS.get(ch, ch.replace('_', ' '))
    conditions = _conditions(row)
    result = ('%s %s' % (_words(getattr(row, 'result', '')), str(getattr(row, 'units', '') or ''))).strip()
    src_rung, tgt_rung = str(getattr(row, 'source_rung', '')), str(getattr(row, 'target_rung', ''))
    src, tgt = str(getattr(row, 'source_ref', '')), str(getattr(row, 'target_ref', ''))
    method = str(getattr(row, 'method', '') or 'an unstated method')
    level = str(getattr(row, 'evidence_level', '') or 'none')
    status = str(getattr(row, 'mapping_status', '') or '')
    trust = {'measured': 'MEASURED: a tool produced this number on this instance (or a recorded run of it); re-running the flow reproduces it',
             'simulated': 'SIMULATED: a simulator produced it under the stated conditions; it is as good as the models it used',
             'analytical': 'ANALYTICAL: derived by a formula, not run',
             'none': 'no evidence recorded: a placeholder until a flow produces it'}.get(level, level)
    steps = ['cd polari-rf-node/polari-framework']
    if flow:
        steps += ['# the toolchain runs in the polari-eda-tools image (nothing installed on the host); build it once:',
                  '(cd ../polari-eda-tools && docker build -t polari-eda-tools:noble . && ./fetch-pdk.sh)',
                  'PYTHONPATH=.:modules python3 -m %s run      # %s' % (flow[0], flow[1]),
                  '# then read %s — this row\'s number is the %r entry' % (flow[2], ch)]
        if key in ('lod3b', 'lod3c'):
            # the cell is the TARGET of these upward rows ('sky130_fd_sc_hd inv_1'); lod-3c's source also starts with it
            cell = (tgt.split(' ')[-1] if tgt.startswith('sky130_fd_sc_hd ') else (src.split(' ')[0] if src else '')) or '<cell>'
            steps.append('# one cell only: add --cells %s' % cell)
    else:
        steps.append('# no flow is registered for the prefix %r — the evidence field names the report it was read from' % name.split(':')[0])
    steps.append('# the same reading through the API: GET /api/computelod/walk/%s/%s' % (quote(src_rung), quote(src)))
    sentence = ('At the %s rung, %s was measured for %s (%s) with %s; the answer is %s. That number characterizes %s at the %s rung.'
                % (src_rung, src, ch.replace('_', ' '), ch_words, method, result or 'not recorded', tgt or 'its target', tgt_rung))
    done = ('%s. Conditions the number depends on: %s.' % (flow[1][0].upper() + flow[1][1:] if flow else 'The flow that produced this row is not registered by prefix',
                                                            _words(conditions) or 'none recorded'))
    return {'in one sentence': sentence, 'what was done': done,
            'inputs': {'measured thing (source ref)': src, 'at the rung': src_rung, 'characteristic': '%s — %s' % (ch, ch_words), 'tool (method)': method,
                       'conditions': {k.replace('_', ' '): _words(v) for k, v in conditions.items()} or 'none recorded',
                       'what it characterizes (target ref)': tgt, 'at the rung ': tgt_rung},
            'result': result or 'not recorded', 'how to reproduce': steps,
            'evidence': str(getattr(row, 'evidence_ref', '') or 'none recorded'),
            'how far to trust it': '%s%s' % (trust, (' · status: %s' % status) if status else ''),
            'related': [{'class': 'ComputeLOD', 'name': src_rung}, {'class': 'ComputeLOD', 'name': tgt_rung}]}


def explain_compute_mapping(manager, row):
    kind = str(getattr(row, 'kind', '') or '')
    kind_words = {'one-to-one': 'each thing at the source becomes exactly one thing at the target', 'one-to-many': 'one thing at the source becomes several at the target',
                  'many-to-one': 'several things at the source become one at the target', 'approximate': 'the target only approximates the source',
                  'alternative': 'one of several ways the source could be realised', 'unresolved': 'not yet worked out', 'partial': 'only part of the source is covered'}.get(kind, kind)
    src_rung, tgt_rung = str(getattr(row, 'source_rung', '')), str(getattr(row, 'target_rung', ''))
    src, tgt = str(getattr(row, 'source_ref', '')), str(getattr(row, 'target_ref', ''))
    level = str(getattr(row, 'evidence_level', '') or 'none')
    try:
        validity = json.loads(getattr(row, 'validity_json', '{}') or '{}')
    except Exception:
        validity = {}
    return {'in one sentence': 'Going DOWN the ladder: %s (at the %s rung) is implemented as %s (at the %s rung) — a %s mapping: %s.' % (src, src_rung, tgt, tgt_rung, kind, kind_words),
            'what was done': str(getattr(row, 'description', '') or 'the link between the two rungs was recorded') + ('. What is lost on the way: %s' % getattr(row, 'loss_note') if getattr(row, 'loss_note', '') else ''),
            'inputs': {'source (what)': src, 'source rung': src_rung, 'target (implemented as)': tgt, 'target rung': tgt_rung, 'valid where': _words(validity) or 'not stated'},
            'how to reproduce': ['cd polari-rf-node/polari-framework', 'PYTHONPATH=.:modules python3 -m computelod.custom.computelod_walk %s %s      # walk the ladder from this row' % (src_rung, src),
                                 '# or GET /api/computelod/path?rung=%s&ref=%s' % (quote(src_rung), quote(src))],
            'evidence': str(getattr(row, 'evidence_ref', '') or 'none recorded'),
            'how far to trust it': '%s · status %s' % (level, getattr(row, 'mapping_status', '')),
            'related': [{'class': 'ComputeLOD', 'name': src_rung}, {'class': 'ComputeLOD', 'name': tgt_rung}]}


EXPLAINERS = {'CharacterizationMapping': explain_characterization, 'ComputeMapping': explain_compute_mapping}
