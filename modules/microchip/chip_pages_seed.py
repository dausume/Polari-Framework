"""
@module microchip.chip_pages_seed

The /display/microchip page: the interactive microchip-ladder
component (design picker + level rail + click-to-traverse nodes)
above the raw node/level tables — one DisplayDefinition row, no
Angular routing work (module_pages_seed pattern, component
registered in generic-display-components.ts).

@consumers
  - polariServer DisplayDefinition seeds (guarded import)
"""

import json


def _component(item_id, index, segments, title, name, inputs):
    return {
        'id': item_id, 'index': index, 'type': 'component',
        'rowSegmentsUsed': segments, 'gridColumnStart': None,
        'title': title, 'visible': True, 'collapsed': False,
        'cssClass': '',
        'componentProps': {'componentName': name, 'inputs': inputs},
        'item': None, 'nestedRows': [],
    }


def _row(index, items, min_height=320):
    return {
        'index': index, 'rowSegments': 12,
        'minRowHeight': min_height, 'maxRowHeight': 0,
        'autoHeight': True, 'cssClass': '', 'items': items,
    }


SEED_MICROCHIP_PAGE_DISPLAYS = [{
    'name': 'microchip-home',
    'description': 'Microchip design-level ladder: traverse '
                   'device -> standard-cell -> functional-block '
                   '-> core -> chip across the seeded designs '
                   '(our CNT ladder + the RV16X-NANO precedent).',
    'source_class': 'MicrochipDesignNode',
    'isPage': True,
    'pageRoute': 'microchip',
    'linkedSolutions': '[]',
    'definition': json.dumps({'rows': [
        _row(0, [
            _component('microchip-ladder-main', 0, 12,
                       'Design-level traversal', 'microchip-ladder',
                       {'design': ''}),
        ], min_height=480),
        _row(1, [
            _component('microchip-levels-table', 0, 6,
                       'Ladder levels (rows)', 'class-rows-table',
                       {'className': 'DesignLevelDefinition',
                        'columns': 'name,rank,status,plan_pointer',
                        'maxRows': 0}),
            _component('microchip-nodes-table', 1, 6,
                       'Design nodes (rows)', 'class-rows-table',
                       {'className': 'MicrochipDesignNode',
                        'columns': 'name,design,level,parent,'
                                   'status',
                        'maxRows': 0}),
        ]),
        _row(2, [
            _component('microchip-families-table', 0, 6,
                       'Rank-1 device families (fet live; shells '
                       'carry their contract as data — plan §2c)',
                       'class-rows-table',
                       {'className': 'DeviceFamilyDefinition',
                        'columns': 'name,status,first_target,'
                                   'plan_pointer',
                        'maxRows': 0}),
            _component('microchip-families-api', 1, 6,
                       'Families report (live artifact counts + '
                       'contracts)', 'api-json-panel',
                       {'path': '/api/microchip/families'}),
        ]),
    ]}),
}]
