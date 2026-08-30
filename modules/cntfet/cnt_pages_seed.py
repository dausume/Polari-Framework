"""
@module cntfet.cnt_pages_seed

The /display/cntfet page — pure no-code data over the generic
components: device/parameter/anchor tables + the capability and
citations panels + the seeded device's live state. Acts (derive/
iv/calibrate/equivalence) stay API-side; the page shows what IS,
with the capability panel naming what this instance refuses.

@consumers
  - polariServer DisplayDefinition seeds (guarded import)
"""

import json


def _table(item_id, index, segments, title, class_name, columns='',
           max_rows=0):
    return {
        'id': item_id, 'index': index, 'type': 'component',
        'rowSegmentsUsed': segments, 'gridColumnStart': None,
        'title': title, 'visible': True, 'collapsed': False,
        'cssClass': '',
        'componentProps': {
            'componentName': 'class-rows-table',
            'inputs': {'className': class_name, 'columns': columns,
                       'maxRows': max_rows},
        },
        'item': None, 'nestedRows': [],
    }


def _api(item_id, index, segments, title, path):
    return {
        'id': item_id, 'index': index, 'type': 'component',
        'rowSegmentsUsed': segments, 'gridColumnStart': None,
        'title': title, 'visible': True, 'collapsed': False,
        'cssClass': '',
        'componentProps': {
            'componentName': 'api-json-panel',
            'inputs': {'path': path},
        },
        'item': None, 'nestedRows': [],
    }


def _sapi(item_id, index, segments, title, path, pick=''):
    """A tabular API payload rendered as chips / tables (generic
    structured-payload reading) — never a raw JSON wall. `pick` is a
    dot-path into the payload (e.g. 'idealTable', 'ranking')."""
    return {
        'id': item_id, 'index': index, 'type': 'component',
        'rowSegmentsUsed': segments, 'gridColumnStart': None,
        'title': title, 'visible': True, 'collapsed': False,
        'cssClass': '',
        'componentProps': {
            'componentName': 'api-structured-panel',
            'inputs': {'path': path, 'pick': pick, 'title': ''},
        },
        'item': None, 'nestedRows': [],
    }


def _figure(item_id, index, segments, title, figure_id):
    """A figure-replica GRAPH panel (Dustin 2026-08-25: graphs,
    not JSON — and CONFIGURABLE ones riding the original graphs
    design: a seeded GraphDefinition row rendered by
    graph-renderer, editable on the Graphs page)."""
    return {
        'id': item_id, 'index': index, 'type': 'component',
        'rowSegmentsUsed': segments, 'gridColumnStart': None,
        'title': title, 'visible': True, 'collapsed': False,
        'cssClass': '',
        'componentProps': {
            'componentName': 'named-graph-panel',
            'inputs': {
                'graphName': f'cntfet-figure-{figure_id}',
                'dataPath': f'/api/cntfet/figures/{figure_id}'
                            f'/points',
            },
        },
        'item': None, 'nestedRows': [],
    }


def _device_graph(item_id, index, segments, title, device_name,
                  curve):
    """fet-viz: one device's curve family — the per-KIND seeded
    GraphDefinition (cnt-device-transfer/-output) fed by that
    device's own points path (per-object: another device's panel
    is the same graph with a different dataPath)."""
    return {
        'id': item_id, 'index': index, 'type': 'component',
        'rowSegmentsUsed': segments, 'gridColumnStart': None,
        'title': title, 'visible': True, 'collapsed': False,
        'cssClass': '',
        'componentProps': {
            'componentName': 'named-graph-panel',
            'inputs': {
                'graphName': f'cnt-device-{curve}',
                # fet, not cntfet: the generic per-device surface
                'dataPath': f'/api/fet/device/{device_name}'
                            f'/points?curve={curve}',
            },
        },
        'item': None, 'nestedRows': [],
    }


def _row(index, items, min_height=320):
    return {
        'index': index, 'rowSegments': 12,
        'minRowHeight': min_height, 'maxRowHeight': 0,
        'autoHeight': True, 'cssClass': '', 'items': items,
    }


def _cell_diagram(item_id, index, segments, title, component, cell,
                  drive=1):
    """fp-5: the d3 boolean-logic / transistor-schematic components
    (generic registry) for one cell — the proof you can step through."""
    return {
        'id': item_id, 'index': index, 'type': 'component',
        'rowSegmentsUsed': segments, 'gridColumnStart': None,
        'title': title, 'visible': True, 'collapsed': False,
        'cssClass': '',
        'componentProps': {'componentName': component,
                           'inputs': {'cell': cell, 'drive': drive}},
        'item': None, 'nestedRows': [],
    }


def _cells_page():
    """fp-5: /display/cntfet-cells — every cell's logic diagram +
    schematic (config only: one row per cell, two components), the
    library-wide switch-level proof, and the DFF state space."""
    rows = [
        # evidence: which cells are FREE to use — the library proof
        # table + the clickable evidence browser (patents, papers).
        _row(0, [_cell_diagram('cells-evidence-browser', 0, 12,
                               'Evidence + proof status for every cell, '
                               'FET and process (US) — click a row for '
                               'the chain, click an item for detail',
                               'evidence-browser', '', 0)],
             min_height=520),
        _row(100, [
            _sapi('cells-library-proof', 0, 6,
                 'Cell library: boolean vs switch-level PROOF per cell '
                 '(allProven, contention, floating) + DFF state space',
                 '/api/cntfet/cells/logic', pick='combinational'),
            _sapi('cells-library', 1, 6,
                 'Cell library (generated variants, drives, arcs)',
                 '/api/cntfet/cell-library', pick='cells'),
        ], min_height=360),
    ]
    for i, (cell, label) in enumerate((
            ('cinv', 'INV'), ('cnand2', 'NAND2'), ('cnor2', 'NOR2'),
            ('caoi21', 'AOI21'), ('coai21', 'OAI21'), ('cmux2', 'MUX2'),
            ('cxor2', 'XOR2'), ('cnand3', 'NAND3'), ('cand2', 'AND2'),
            # cells-2 (2026-08-27): the next set
            ('cxnor2', 'XNOR2'), ('cnand4', 'NAND4 (4-stack)'),
            ('caoi22', 'AOI22'), ('cmux4', 'MUX4'), ('cxor3', 'XOR3'),
            ('cha', 'Half adder (S, CO)'),
            ('cfa', 'Full adder — 28T mirror (S, CO)'),
            ('ctbuf', 'Tri-state buffer (Z when EN = 0)'),
            ('clatch', 'D latch (transparent, state space)'),
            ('cdff', 'DFF (sequential state space)'))):
        rows.append(_row(i + 1, [
            _cell_diagram(f'cells-{cell}-logic', 0, 6,
                          f'{label}: boolean logic diagram — click '
                          'inputs / step every vector; proven vs the '
                          'transistor netlist', 'cell-logic-diagram',
                          cell),
            _cell_diagram(f'cells-{cell}-schematic', 1, 6,
                          f'{label}: transistor-level schematic — '
                          'conducting path per vector',
                          'cell-schematic', cell),
        ], min_height=460))
    return {
        'name': 'cntfet-cells',
        'description': 'Standard cells as circuit + boolean logic '
                       'diagrams generated from the cell library '
                       '(no-code: one row per cell), with the switch-'
                       'level proof and state-space stepping.',
        'source_class': 'CNTCellDefinition',
        'isPage': True, 'pageRoute': 'cntfet-cells',
        'linkedSolutions': '[]',
        'definition': json.dumps({'rows': rows}),
    }


SEED_CNTFET_PAGE_DISPLAYS = [{
    'name': 'cntfet-home',
    'description': 'Aligned-CNT FET S1: the one-tube device rows, '
                   'role-tagged parameters, D18 calibration '
                   'anchors, capability refusals, and the '
                   'citation-linkage map.',
    'source_class': 'AlignedCNTFETDevice',
    'isPage': True,
    'pageRoute': 'cntfet',
    'linkedSolutions': '[]',
    'definition': json.dumps({'rows': [
        _row(0, [
            _table('cntfet-devices', 0, 6, 'Aligned CNT devices',
                   'AlignedCNTFETDevice',
                   'name,polarity,temperature_k,'
                   'manufacturing_regime,derived_at'),
            _api('cntfet-capability', 1, 6,
                 'Capability (honest refusals)',
                 '/api/cntfet/capability'),
        ]),
        _row(1, [
            _table('cntfet-parameters', 0, 6,
                   'Parameters by role (D8)', 'CNTFETParameterRow',
                   'parameter,value,unit,role,confidence'),
            _table('cntfet-anchors', 1, 6,
                   'Calibration + reference anchors (D18)',
                   'CNTCalibrationAnchor',
                   'name,value,unit,status,doi'),
        ]),
        _row(2, [
            _api('cntfet-citations', 0, 6,
                 'Citation linkage (source -> rows)',
                 '/api/cntfet/citations'),
            _table('cntfet-results', 1, 6, 'Sim results',
                   'CNTFETSimResult',
                   'name,kind,engine,verdict,ran_at'),
        ]),
        _row(3, [
            _api('cntfet-figures', 0, 4,
                 'Cited-figure replicas (proofing registry)',
                 '/api/cntfet/figures'),
            _figure('cntfet-figure-fig7a', 1, 8,
                    'Replica: [VS1] Fig.7(a) digitized vs model',
                    'vs1-fig7a'),
        ], min_height=430),
        _row(4, [
            _figure('cntfet-figure-vxo', 0, 6,
                    'v_xo vs Lg — anchors vs eq.(9)',
                    'fc10-vxo-vs-lg'),
            _figure('cntfet-figure-d13', 1, 6,
                    'D13: SCF barrier vs Laplace seed '
                    '(row-backed)',
                    'd13-scf-profile'),
        ], min_height=430),
        # fet-viz (2026-08-26): the S1 device's own curves +
        # characterization — refuses verbatim until the device is
        # derived (the affordance is named in the refusal).
        _row(5, [
            _device_graph('cntfet-device-transfer', 0, 4,
                          'S1 device: transfer Id(Vg), log Y',
                          'cnt-aligned-s1', 'transfer'),
            _device_graph('cntfet-device-output', 1, 4,
                          'S1 device: output Id(Vd)',
                          'cnt-aligned-s1', 'output'),
            _sapi('cntfet-device-characterization', 2, 4,
                 'S1 device: characterization (SS/DIBL/Ion/Ioff/'
                 'gm — refusals verbatim)',
                 '/api/cntfet/device/cnt-aligned-s1'
                 '/characterization', pick='metrics'),
        ], min_height=430),
        # fi-0/fi-1 (FET_INTUITION_PLAN): the states the device
        # passes through, what qualifies each (criteria as data),
        # shaded onto the curves they govern.
        _row(6, [
            _device_graph('cntfet-device-transfer-states', 0, 4,
                          'S1 device: operating states on Id(Vg) '
                          '(bands = states, guides = what qualifies)',
                          'cnt-aligned-s1', 'transfer-states'),
            _device_graph('cntfet-device-output-states', 1, 4,
                          'S1 device: linear vs saturation on '
                          'Id(Vd) (Vdsat locus)',
                          'cnt-aligned-s1', 'output-states'),
            _sapi('cntfet-device-states', 2, 4,
                 'S1 device: states, boundaries + sweep events '
                 '(criteria evaluated with their numbers)',
                 '/api/cntfet/device/cnt-aligned-s1/states'
                 '?vd=0.6&vg=0.3', pick='boundaries'),
        ], min_height=430),
        # fi-2/fi-3: scoring by characteristic equations — each
        # term against its computed ideal — and the best/worst
        # case from the process set's stochastic definitions.
        _row(7, [
            _device_graph('cntfet-device-score-terms', 0, 4,
                          'S1 device: figures of merit vs their '
                          'ideals (MC spread, best/worst case)',
                          'cnt-aligned-s1', 'score-terms'),
            _device_graph('cntfet-device-transfer-envelope', 1, 4,
                          'S1 device: stochastic Id(Vg) envelope '
                          '(p05–p95, min–max)',
                          'cnt-aligned-s1', 'transfer-envelope'),
            _sapi('cntfet-device-score', 2, 4,
                 'S1 device: score by characteristic equations '
                 '(ideal vs actual, MC best/worst)',
                 '/api/cntfet/device/cnt-aligned-s1/score'
                 '?samples=100', pick='idealTable'),
        ], min_height=430),
        # cells: the characterized library scored against the
        # driving FET's own intrinsic limits (refuses by name
        # until a library run exists).
        # evidence: is it free to use? — every FET / cell / process
        # with its proof status; click through to patents and papers.
        _row(9, [{
            'id': 'cntfet-evidence-browser', 'index': 0,
            'type': 'component', 'rowSegmentsUsed': 12,
            'gridColumnStart': None,
            'title': 'Free to use? Evidence (patents, papers, licences) '
                     '+ proof status per FET / cell / process (US)',
            'visible': True, 'collapsed': False, 'cssClass': '',
            'componentProps': {'componentName': 'evidence-browser',
                               'inputs': {}},
            'item': None, 'nestedRows': [],
        }], min_height=520),
        _row(8, [
            _device_graph('cntfet-device-cell-scores', 0, 6,
                          'S1 cells: score + terms vs intrinsic '
                          'limits (delay/τ, transition/τ, '
                          'energy/C·V², FETs/min)',
                          'cnt-aligned-s1', 'cell-scores'),
            _sapi('cntfet-device-cell-scores-json', 1, 6,
                 'S1 cells: scores (mid-grid point, ideal table)',
                 '/api/cntfet/device/cnt-aligned-s1/cell-scores',
                 pick='ranking'),
        ], min_height=430),
        # fg-2: the generic FET catalogue — every FET (CNT + Si)
        # with its /display/fet?object= pages and summary path.
        _row(10, [
            _sapi('cntfet-fet-catalogue', 0, 12,
                  'Every FET (CNT + Si): the generic score / detail '
                  'pages (?object=) + the one-payload summary',
                  '/api/fet/devices', pick='devices'),
        ], min_height=360),
    ]}),
}, _cells_page()]
