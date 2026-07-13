"""
@module aquaponics.aquaponics_pages_seed

Seeds: the aquaponics-pot-shape phase 2 DisplayDefinition PAGE (the
materials-science page pattern — isPage + pageRoute + a hosted
registered component):

  /display/pot-geometry — edit demo-herb-pot's wall/base thickness,
                          overall size, and per-hole diameter/
                          elevation/azimuth/bore-angle. CRUDE PUT on
                          the durable PotDefinition/PotHole rows,
                          validated before/after, then re-derives the
                          math-shape render via POST /api/shapes/
                          from-pot/{name}.

The component reads/writes live rows itself — this seed carries only
the page wiring, no data. Defaults to demo-herb-pot (the reference
pot); the editor's `potName` input can be repointed at any pot by
editing this Display or authoring a new one.
"""

import json

SEED_AQUAPONICS_PAGE_DISPLAYS = [
    {
        'name': 'pot-geometry',
        'description': (
            'Edit an aqp-1 self-watering pot: wall/base thickness, '
            'overall size, and per-hole diameter/elevation/azimuth/'
            'bore-angle. Every edit is validated against the gravity '
            'self-watering invariant before and after, then re-derives '
            'the math-defined render (aquaponics-pot-shape phase 2).'
        ),
        'source_class': 'PotDefinition',
        'isPage': True,
        'pageRoute': 'pot-geometry',
        'linkedSolutions': '[]',
        'definition': json.dumps({'rows': [{
            'index': 0, 'rowSegments': 12, 'minRowHeight': 480,
            'maxRowHeight': 0, 'autoHeight': True, 'cssClass': '',
            'items': [{
                'id': 'pot-geometry-item', 'index': 0,
                'type': 'component', 'rowSegmentsUsed': 12,
                'gridColumnStart': None,
                'title': 'Pot geometry — demo-herb-pot',
                'visible': True, 'collapsed': False, 'cssClass': '',
                'componentProps': {
                    'componentName': 'pot-geometry-editor',
                    'inputs': {'potName': 'demo-herb-pot'},
                },
                'item': None, 'nestedRows': [],
            }],
        }]}),
    },
]
