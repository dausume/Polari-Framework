"""
@module aquaponics.aquaponics_page

Seeds: the aquaponics-pot-shape phase 2 DisplayDefinition PAGE (the
materials-science page pattern — isPage + pageRoute + a hosted
registered component):

  /display/pot-geometry — edit demo-herb-pot's wall/base thickness,
                          overall size, and per-hole diameter/
                          elevation/azimuth/bore-angle. CRUDE PUT on
                          the durable PotDefinition/PotHole rows,
                          validated before/after, then re-derives the
                          math-shape render via POST /api/shapes/
                          from-pot/{name} — PLUS a bare sim-space-viewer
                          panel next to it so the re-derived scene is
                          actually visible on the page (2026-07-13: the
                          editor alone renders nothing, it only tells
                          the backend to re-derive and invalidates the
                          frontend mesh cache; something has to display
                          the scene it invalidated).

The editor component reads/writes live rows itself — this seed carries
only the page wiring, no data. Both items default to demo-herb-pot /
demo-herb-pot-viz (the reference pot + its scene); repoint either by
editing this Display or authoring a new one. The viewer is NOT wired
to follow the editor's potName dynamically — if you point the editor
at a different pot, update the viewer's simSpaceName to match
(<pot-name>-viz, per mathshapes.custom.pot_scene.ensure_pot_viz_scene).
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
            'items': [
                {
                    'id': 'pot-geometry-item', 'index': 0,
                    'type': 'component', 'rowSegmentsUsed': 5,
                    'gridColumnStart': None,
                    'title': 'Pot geometry — demo-herb-pot',
                    'visible': True, 'collapsed': False, 'cssClass': '',
                    'componentProps': {
                        'componentName': 'pot-geometry-editor',
                        'inputs': {'potName': 'demo-herb-pot'},
                    },
                    'item': None, 'nestedRows': [],
                },
                {
                    'id': 'pot-geometry-scene-item', 'index': 1,
                    'type': 'component', 'rowSegmentsUsed': 7,
                    'gridColumnStart': None,
                    'title': 'Rendered scene',
                    'visible': True, 'collapsed': False, 'cssClass': '',
                    'componentProps': {
                        'componentName': 'sim-space-viewer',
                        'inputs': {'simSpaceName': 'demo-herb-pot-viz'},
                    },
                    'item': None, 'nestedRows': [],
                },
            ],
        }]}),
    },
]
