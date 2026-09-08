"""
@cross-cutting
@module casting.sim_seed
@tags @xc:render-3d, @xc:bindings

cast-9 (registration half): the mold-fill simulation as a VIEWABLE
sim space — the exact waxprint trigger-on-import pattern: importing
this module APPENDS the SimulationDefinition, the SimSpace3D scene,
the per-class binding, and the fill-state render materials to the
shared framework seed lists. The STATE ROWS themselves are computed
in the [CastingSeed] pass (they need the derived mold + sprue set —
derivation-as-seeding, like the molds); the run row seeded here
matches the run the pass computes.

Scene: the demo sphere mold's fill run — each domain voxel a cube
scaled by its real cell size, coloured by state (blue=fluid,
gray=channel, red=trapped air, orange=unfed, faint=empty), scrubbed
by fill level.

@consumers polariServer (imports this; adds the page display +
computes the rows in [CastingSeed])
@see /WAX_MOLD_NESTING_PLAN.md (PHASE cast-9)
"""

import json

from simSpace3D.seed_data import SEED_MATERIALS_3D
from simulations.seed_data import (
    SEED_PENDULUM_BINDINGS, SEED_PENDULUM_SIMSPACES,
    SEED_SIMULATION_DEFINITIONS, SEED_SIMULATION_RUNS,
)

SCENE = 'mold-fill-3d'
SIM = 'mold-fill'
_CLS = 'MoldFillSimState'
#: The run [CastingSeed] computes for the demo mold.
FILL_RUN = 'fill-demo-sphere'
FILL_RUN_STEPS = 3


def _mat(name, color, desc, opacity=1.0):
    return {'name': name, 'description': desc,
            'material_type': 'standard', 'color': color,
            'emissive': '#000000', 'emissive_intensity': 0.0,
            'metalness': 0.1, 'roughness': 0.7, 'opacity': opacity,
            'transparent': opacity < 1.0, 'double_sided': False,
            'flat_shading': False, 'wireframe': False}


SEED_MATERIALS_3D.extend([
    _mat('fill-empty', '#b0bec5', 'Unfilled cavity (faint gray).',
         opacity=0.15),
    _mat('fill-liquid', '#1565c0', 'Fluid (blue).'),
    _mat('fill-channel', '#78909c', 'Sprue/vent channel (gray).'),
    _mat('fill-trapped', '#c62828',
         'TRAPPED air — a void in the part (red).'),
    _mat('fill-unfed', '#ef6c00',
         'UNFED region — the gate never reaches it (orange).'),
])

SEED_PENDULUM_SIMSPACES.append({
    'name': SCENE,
    'description': 'Gravity fill of the demo sphere mold: fluid '
                   '(blue) climbs level by level through the cavity '
                   'and channels (gray); trapped air (red) and '
                   'unfed regions (orange) are the defects the '
                   'cast-5 sim exists to catch. Scrub the fill '
                   'level.',
    'dimensionality': '3d',
    'coordinate_system': 'math',
    'unit_scale': 1.0,
    'viewport_json': json.dumps({'center': [0, 0, 0],
                                 'extent': [6, 6, 6]}),
    'bound_classes_json': json.dumps([{'className': _CLS}]),
    'definition': json.dumps({'freestanding': []}),
    'owning_module': 'casting',
})

SEED_PENDULUM_BINDINGS.append({
    'name': f'{_CLS}-3d', 'class_name': _CLS, 'dimensionality': '3d',
    'enabled': True,
    'binding_json': json.dumps({
        'enabled': True, 'dimensionality': '3d', 'kind': 'object',
        'position': {'kind': 'fields',
                     'fields': {'x': 'pos_x', 'y': 'pos_y',
                                'z': 'pos_z'}},
        'visual': {'shapeRef': 'cube', 'styleRef': {
            'fromField': 'render_state',
            'map': {'0': 'fill-empty', '1': 'fill-liquid',
                    '2': 'fill-channel', '3': 'fill-trapped',
                    '4': 'fill-unfed'},
            'default': 'fill-empty'}},
        'scale': {'kind': 'uniform', 'field': 'cell_cm',
                  'factor': 1.0},
        'clickAction': 'navigate-to-instance', 'defaultVisible': True,
        'temporal': {'kind': 'time', 'field': 'step', 'unit': 'level',
                     'cumulative': False},
    }),
})

SEED_SIMULATION_DEFINITIONS.append({
    'name': SIM,
    'description': 'Quasi-static gravity mold fill on the occupancy '
                   'grid: feed at sprue mouths, level-by-level '
                   'flood, air-escape bookkeeping (trapped pockets, '
                   'unfed chambers, counterflow), fill time vs pot '
                   'life. Driven by the casting.fill_sim_basis engine.',
    'intent': 'feasibility',
    'participating_sim_state_classes_json': json.dumps([_CLS]),
    'time_step_seconds': 1.0,
    'duration_seconds': float(FILL_RUN_STEPS),
    'recording_interval_steps': 1,
    'initial_conditions_overrides_json': '{}',
    'parameters_json': json.dumps({
        'default_mold': 'demo-sphere-mold',
        'default_cast_material': 'geopolymer-slurry',
        'resolution': 24}),
})

SEED_SIMULATION_RUNS.append({
    'name': FILL_RUN, 'simulation_ref': SIM, 'status': 'completed',
    'total_steps': FILL_RUN_STEPS, 'recorded_steps': FILL_RUN_STEPS,
    'last_recorded_step': FILL_RUN_STEPS - 1,
    'label': 'demo sphere, geopolymer, top gate'})


# --------------------------------------------------------------------------
# the /casting page (exported for polariServer's display concat)
# --------------------------------------------------------------------------
SEED_CASTING_PAGE_DISPLAYS = [{
    'name': 'casting-page',
    'description': 'Casting & mold nesting: the fill simulation in '
                   '3D, the nesting chains with their derived '
                   'parity/thermal verdicts, and the mold catalog.',
    'source_class': 'MoldDefinition', 'isPage': True,
    'pageRoute': 'casting', 'linkedSolutions': '[]',
    'definition': json.dumps({'rows': [
        {'index': 0, 'rowSegments': 12, 'minRowHeight': 520,
         'maxRowHeight': 0, 'autoHeight': True, 'cssClass': '',
         'items': [{
             'id': 'mold-fill-scene-item', 'index': 0,
             'type': 'component', 'rowSegmentsUsed': 12,
             'gridColumnStart': None,
             'title': 'Mold fill — trapped air is red, unfed is '
                      'orange', 'visible': True, 'collapsed': False,
             'cssClass': '',
             'componentProps': {'componentName': 'sim-space-viewer',
                                'inputs': {'simSpaceName': SCENE}},
             'item': None, 'nestedRows': []}]},
        {'index': 1, 'rowSegments': 12, 'minRowHeight': 320,
         'maxRowHeight': 0, 'autoHeight': True, 'cssClass': '',
         'items': [
             {'id': 'chains-table-item', 'index': 0,
              'type': 'class-table', 'rowSegmentsUsed': 6,
              'gridColumnStart': None,
              'title': 'Nesting chains', 'visible': True,
              'collapsed': False, 'cssClass': '',
              'componentProps': {'className': 'MoldNestingChain'},
              'item': None, 'nestedRows': []},
             {'id': 'molds-table-item', 'index': 1,
              'type': 'class-table', 'rowSegmentsUsed': 6,
              'gridColumnStart': None,
              'title': 'Molds (derived negatives)', 'visible': True,
              'collapsed': False, 'cssClass': '',
              'componentProps': {'className': 'MoldDefinition'},
              'item': None, 'nestedRows': []}]},
        {'index': 2, 'rowSegments': 12, 'minRowHeight': 320,
         'maxRowHeight': 0, 'autoHeight': True, 'cssClass': '',
         'items': [{
             'id': 'plans-table-item', 'index': 0,
             'type': 'class-table', 'rowSegmentsUsed': 12,
             'gridColumnStart': None,
             'title': 'Nesting plans — part × material, every '
                      'derived step with its viewable shapes '
                      '(POST /api/casting/plan)',
             'visible': True, 'collapsed': False, 'cssClass': '',
             'componentProps': {'className': 'NestingPlanDefinition'},
             'item': None, 'nestedRows': []}]},
    ]}),
}]
