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
                'dataPath': f'/api/cntfet/device/{device_name}'
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
            _api('cntfet-device-characterization', 2, 4,
                 'S1 device: characterization (SS/DIBL/Ion/Ioff/'
                 'gm — refusals verbatim)',
                 '/api/cntfet/device/cnt-aligned-s1'
                 '/characterization'),
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
            _api('cntfet-device-states', 2, 4,
                 'S1 device: states, boundaries + sweep events '
                 '(criteria evaluated with their numbers)',
                 '/api/cntfet/device/cnt-aligned-s1/states'
                 '?vd=0.6&vg=0.3'),
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
            _api('cntfet-device-score', 2, 4,
                 'S1 device: score by characteristic equations '
                 '(ideal vs actual, MC best/worst)',
                 '/api/cntfet/device/cnt-aligned-s1/score'
                 '?samples=100'),
        ], min_height=430),
        # cells: the characterized library scored against the
        # driving FET's own intrinsic limits (refuses by name
        # until a library run exists).
        _row(8, [
            _device_graph('cntfet-device-cell-scores', 0, 6,
                          'S1 cells: score + terms vs intrinsic '
                          'limits (delay/τ, transition/τ, '
                          'energy/C·V², FETs/min)',
                          'cnt-aligned-s1', 'cell-scores'),
            _api('cntfet-device-cell-scores-json', 1, 6,
                 'S1 cells: scores (mid-grid point, ideal table)',
                 '/api/cntfet/device/cnt-aligned-s1/cell-scores'),
        ], min_height=430),
    ]}),
}]
