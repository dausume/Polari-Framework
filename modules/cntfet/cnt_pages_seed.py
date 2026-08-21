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
    ]}),
}]
