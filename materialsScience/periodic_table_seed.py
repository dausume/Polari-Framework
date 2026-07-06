"""
@module materialsScience.periodic_table_seed

Seeds generated from periodic_table_data:
  - 118 ChemicalElementDefinition rows (symbol-named, ions attached)
  - one Material3DDefinition per element CATEGORY (the color coding)
  - the `periodic-table-selector` scene: a fixed-camera, auto-fitting
    SELECTION SPACE — one tile per element on the standard 18-column
    layout (f-block dropped to its own rows), freestandingOnly, with a
    phone screen profile that relaxes the fit margin
  - PERIODIC_SELECTOR_ITEMS: the selector items config (element key,
    symbol label, ions as popup variants) consumed by the demo
    DisplayDefinition page seed

Proves the 3D selection machinery generalizes past materials (Dustin:
"ensure this kind of selection works for multiple use cases") and lays
the object-tree groundwork for the Materials Science Module.
"""

import json

from materialsScience.periodic_table_data import (
    CATEGORY_BY_CODE,
    ELEMENTS,
    common_ions_for,
    display_position,
)
from simSpace3D.seed_data import SEED_MATERIALS_3D
from simulations.seed_data import SEED_PENDULUM_SIMSPACES

PERIODIC_SCENE = 'periodic-table-selector'

# Tile spacing in scene units; tiles are cubes of edge TILE * 0.9.
_TILE = 0.3

# Category colors — deliberately close to common periodic-table prints.
_CATEGORY_COLORS = {
    'alkali-metal': '#ef5350',
    'alkaline-earth': '#ffa726',
    'transition-metal': '#ffd54f',
    'post-transition': '#9ccc65',
    'metalloid': '#26a69a',
    'reactive-nonmetal': '#42a5f5',
    'halogen': '#5c6bc0',
    'noble-gas': '#ab47bc',
    'lanthanide': '#8d6e63',
    'actinide': '#78909c',
    'unknown-properties': '#bdbdbd',
}

SEED_CHEMICAL_ELEMENTS = []
SEED_ELEMENT_CATEGORY_MATERIALS = [
    {
        'name': f'element-{category}',
        'description': f'Periodic-table category color: {category}.',
        'material_type': 'standard',
        'color': color,
        'metalness': 0.05,
        'roughness': 0.6,
    }
    for category, color in _CATEGORY_COLORS.items()
]

_FREESTANDING = []
PERIODIC_SELECTOR_ITEMS = []

for z, symbol, element_name, group, period, code, mass in ELEMENTS:
    category = CATEGORY_BY_CODE[code]
    row, col = display_position(z, group, period, code)
    ions = common_ions_for(symbol, code)
    SEED_CHEMICAL_ELEMENTS.append({
        'name': symbol,
        'symbol': symbol,
        'element_name': element_name,
        'atomic_number': z,
        'group': group,
        'period': period,
        'display_row': row,
        'display_col': col,
        'category': category,
        'common_ions_json': json.dumps(ions),
        'atomic_mass': mass,
    })
    _FREESTANDING.append({
        'id': f'element-{symbol}',
        # Centered: col 1-18 → x, row 1-9.5 → -y (period 1 on top).
        'position': [round((col - 9.5) * _TILE, 4),
                     round((5.25 - row) * _TILE, 4), 0.0],
        'shapeRef': 'cube',
        'styleRef': f'element-{category}',
        'scale': _TILE * 0.9,
        'label': f'{symbol} — {element_name}',
    })
    PERIODIC_SELECTOR_ITEMS.append({
        'key': symbol,
        'label': symbol,
        'objectId': f'element-{symbol}',
        'description': f'{element_name} · Z={z} · {category}'
                       + (f' · {mass:g} u' if mass else ''),
        'overlayRef': 'element-choice',
        'overlayInputs': {'atomicNumber': z, 'elementName': element_name},
        'popup': True,
        # Popup variants — picking one selects THE ION, not just the
        # element (published as {key, variant}).
        'variants': ions,
    })

# The demo surface: a seeded DisplayDefinition PAGE hosting the selector
# purely as configuration — proves "generally usable in any Display".
SEED_PERIODIC_DISPLAYS = [{
    'name': 'periodic-table-selection',
    'description': (
        'Element / ion selection demo page: the periodic-table selection '
        'space hosted in a plain Display — pick an element tile; its popup '
        'offers the common ions. Selections publish under the '
        "'selectedElement' display-context key."
    ),
    'source_class': 'ChemicalElementDefinition',
    'isPage': True,
    'pageRoute': 'periodic-table',
    'linkedSolutions': '[]',
    'definition': json.dumps({'rows': [{
        'index': 0, 'rowSegments': 12, 'minRowHeight': 480,
        'maxRowHeight': 0, 'autoHeight': True, 'cssClass': '',
        'items': [{
            'id': 'periodic-selector-item', 'index': 0, 'type': 'component',
            'rowSegmentsUsed': 12, 'gridColumnStart': None,
            'title': 'Periodic table — element / ion selection',
            'visible': True, 'collapsed': False, 'cssClass': '',
            'componentProps': {
                'componentName': 'sim-space-selector',
                'inputs': {
                    'simSpaceRef': PERIODIC_SCENE,
                    'items': PERIODIC_SELECTOR_ITEMS,
                    'contextKey': 'selectedElement',
                    # Disclaimer knob: authored for ≥320px hosts.
                    'supportedScreen': {'minWidth': 320},
                },
            },
            'item': None, 'nestedRows': [],
        }],
    }]}),
}]

SEED_PERIODIC_SIMSPACES = [{
    'name': PERIODIC_SCENE,
    'description': (
        'Periodic-table selection space — pick an element by clicking its '
        'tile (colors = categories); the popup offers its common IONS so a '
        'selection can be a specific charge state. Fixed camera with '
        'responsive auto-fit: the whole table stays visible on any screen.'
    ),
    'dimensionality': '3d',
    'coordinate_system': 'math',
    'unit_scale': 1.0,
    'viewport_json': json.dumps({
        'center': [0, 0, 0],
        # Half-extents of the 18 × 9.5 tile grid (plus margin).
        'extent': [round(9.0 * _TILE, 3), round(4.9 * _TILE, 3), 0.3],
    }),
    'camera_json': json.dumps({
        'mode': 'fixed',
        # Straight-on front view — auto-fit slides the distance.
        'position': [0.0, 0.0, 3.0],
        'target': [0.0, 0.0, 0.0],
        'up': [0, 1, 0],
        'projection': 'perspective',
        'fov': 45,
    }),
    'bound_classes_json': '[]',
    'definition': json.dumps({
        'freestandingOnly': True,
        'screenProfiles': [{
            'name': 'phone', 'maxWidth': 560,
            # Tighter margin: on a narrow screen the table is already
            # small — don't waste more pixels on breathing room.
            'camera': {'fitMargin': 1.03},
        }],
        'freestanding': _FREESTANDING,
    }),
}]

# Register into the shared seed lists (same in-place-extend pattern the
# other seed modules use; polariServer imports this module).
SEED_MATERIALS_3D.extend(SEED_ELEMENT_CATEGORY_MATERIALS)
SEED_PENDULUM_SIMSPACES.extend(SEED_PERIODIC_SIMSPACES)
