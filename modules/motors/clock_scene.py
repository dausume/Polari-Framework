"""
@module motors.clock_scene

viz-1 (Dustin 2026-07-31): "specialized sim space displays on all of
the varying views ... changing through different 3D visualizations
and being able to overlap them as well." The clock views must LEAD
with 3D, not JSON — so the visualizations are LAYERS on one scene,
switchable per discipline and stackable in any combination.

THE SHAPE: a layer is a ClockSceneLayerDefinition ROW — a kind the
renderer already knows how to draw, the engine that feeds it, and
the mapping as params. Adding a visualization is an insert, not a
component. Kinds map 1:1 onto proven renderer capabilities
(sim-space three-renderer):

  part-coloring — per-body colorOverride computed from an engine
                  (mass fractions, stress SF thresholds, material
                  palette); carries a legend
  vector-field  — SnapshotVector arrows (rides the mag-fv field
                  view payloads unchanged)
  replay        — the solver-history animation; the layer carries
                  the GEOMETRY CONFIG (rotor bodies, axis, coil
                  styles) that previously lived hard-coded in the
                  Angular motor page
  markers       — extra builtin-shape bodies (the field-shells
                  idiom): interface joints, colored by whether
                  their failure modes are modelled

A layer that cannot answer REFUSES inside the payload with the
reason and the knob — never dropped, never a blank canvas. The
part→body map is DATA on the coloring layers (it also existed as a
buggy hard-coded table in clock-motor.component; this is the one
copy now).

@consumers motors.motor_api (/api/motors/clock-scene/{view}),
motors.selftest_motors, polariServer seed pass (upsert path, with
seed_clock_views)
"""

import json

from objectTreeDecorators import treeObject, treeObjectInit

from composition.data_refs import resolve_named, rows
from composition.seed_upsert import upsert_seed_pairs

LAYER_KINDS = ('part-coloring', 'vector-field', 'replay', 'markers')

#: The one part→scene-body map for the v2 Lavet scene
#: (motor-m0-lavet-v2-viz). Multi-body parts list every body.
V2_PART_BODIES = {
    'lavet-v2-stator': ['stator'],
    'lavet-v2-rotor-magnet': ['rotor-magnet'],
    'lavet-v2-coil': ['coil'],
    'lavet-v2-pinion': ['rotor-pinion'],
    'lavet-v2-bobbin-flanges': ['bobbin-flange-a',
                                'bobbin-flange-b'],
    'lavet-v2-leads': ['lead-a', 'lead-b'],
    'lavet-v2-index': ['rotor-index'],
}

#: Distinct, theme-safe palette for categorical coloring.
PALETTE = ('#4e9a63', '#c98a00', '#5b7fd4', '#b5525c', '#7a5bd4',
           '#3fa7a0', '#c46fb1', '#8a8f3f')


class ClockSceneLayerDefinition(treeObject):
    """One 3D visualization layer: kind + engine + mapping data."""

    @treeObjectInit
    def __init__(self, name='', display_name='',
                 kind='part-coloring', source='', params_json='{}',
                 style_json='{}', description='', is_prior=True,
                 provenance_id='', notes='', manager=None):
        self.name = name
        self.display_name = display_name
        self.kind = kind if kind in LAYER_KINDS else 'part-coloring'
        self.source = source
        self.params_json = params_json
        self.style_json = style_json
        self.description = description
        self.is_prior = is_prior
        self.provenance_id = provenance_id
        self.notes = notes


# ---------------------------------------------------------------
# Per-source layer data — every one an existing engine
# ---------------------------------------------------------------

def _ramp(fraction):
    """0..1 → green→amber→red hex (mass share, load share...)."""
    f = max(0.0, min(1.0, fraction))
    if f < 0.5:
        r, g = int(0x4e + (0xc9 - 0x4e) * (f * 2)), 0x9a
    else:
        r, g = 0xc9, int(0x9a - (0x9a - 0x52) * ((f - 0.5) * 2))
    return f'#{r:02x}{g:02x}45'


def mass_bodies(masses, part_bodies):
    """Pure coloring math: {part: massG} → per-body colors ramped
    by mass share (heaviest = full red end) + legend."""
    total = sum(masses.values()) or 1.0
    top = max((m / total for m in masses.values()), default=1.0)
    bodies, legend = {}, []
    for part, mass in sorted(masses.items(),
                             key=lambda kv: -kv[1]):
        frac = mass / total
        color = _ramp(frac / top)
        for body in part_bodies.get(part, []):
            bodies[body] = {'color': color, 'value': round(mass, 4),
                            'part': part}
        legend.append({'label': f'{part} — {mass:.3g} g '
                                f'({frac:.0%})', 'color': color})
    return bodies, legend


def _mass_coloring(manager, design, part_bodies):
    from motors.motor_parts import part_report
    rep = part_report(manager, design)
    if not rep.get('ok'):
        return {'ok': False,
                'refusal': rep.get('refusal', 'mass bill refused')}
    masses = {p['part']: p.get('massG') for p in rep.get('parts', [])
              if isinstance(p.get('massG'), (int, float))}
    if not masses:
        return {'ok': False,
                'refusal': 'no part masses resolve — the bill '
                           'derives mass from shape + material '
                           'rows, and none answered here'}
    bodies, legend = mass_bodies(masses, part_bodies)
    unmapped = [p['part'] for p in rep.get('parts', [])
                if p['part'] not in masses]
    return {'ok': True, 'bodies': bodies, 'legend': legend,
            'unit': 'g',
            'note': ('parts with no resolvable mass keep their '
                     'base material: ' + ', '.join(unmapped)
                     if unmapped else
                     'color ramps by mass share of the bill')}


def _stress_coloring(manager, design, part_bodies, style):
    from motors.motor_stress import part_stress
    warn = float(style.get('warnBelow', 4.0))
    fail = float(style.get('failBelow', 1.5))
    bodies, legend_rows = {}, []
    for part, mapped in part_bodies.items():
        try:
            rep = part_stress(manager, design, part)
        except Exception as e:
            rep = {'ok': False, 'refusal': f'raised: {e}'}
        if rep.get('ok'):
            sf = (rep.get('safetyFactor')
                  or rep.get('verdict', {}).get('safetyFactor'))
        else:
            sf = None
        if isinstance(sf, (int, float)):
            color = ('#b5525c' if sf < fail else
                     '#c98a00' if sf < warn else '#4e9a63')
            note = f'SF {sf:.2f}'
        else:
            color = '#6b7078'
            note = rep.get('refusal', 'no stress answer')[:80]
        for body in mapped:
            bodies[body] = {'color': color, 'value': sf,
                            'part': part, 'note': note}
        legend_rows.append({'label': f'{part} — {note}',
                            'color': color})
    return {'ok': True, 'bodies': bodies, 'legend': legend_rows,
            'unit': 'safety factor',
            'note': f'red < {fail}, amber < {warn}, green ≥ {warn}; '
                    f'gray = the engine refused (reason kept)'}


def _material_coloring(manager, design, part_bodies):
    parts = [p for p in rows(manager, 'MotorPartDefinition')
             if getattr(p, 'design_ref', '') == design]
    if not parts:
        return {'ok': False,
                'refusal': f'no MotorPartDefinition rows for '
                           f'"{design}" — motors seeds not booted?'}
    materials = sorted({getattr(p, 'material_ref', '') or
                        '(unresolved)' for p in parts})
    color_of = {m: PALETTE[i % len(PALETTE)]
                for i, m in enumerate(materials)}
    bodies = {}
    for p in parts:
        mat = getattr(p, 'material_ref', '') or '(unresolved)'
        for body in part_bodies.get(getattr(p, 'name', ''), []):
            bodies[body] = {'color': color_of[mat], 'value': mat,
                            'part': getattr(p, 'name', ''),
                            'route': f'/materials/{mat}'
                            if mat != '(unresolved)' else ''}
    legend = [{'label': m, 'color': c}
              for m, c in color_of.items()]
    return {'ok': True, 'bodies': bodies, 'legend': legend,
            'unit': 'material option',
            'note': 'same accountability chain as the sourcing '
                    'view; body click-through rides the part rows'}


def _vector_field(manager, params):
    view_name = params.get('field_view', '')
    try:
        from magnetics.field_views import dispersion_payload
    except ImportError:
        return {'ok': False,
                'refusal': 'magnetics module not importable here — '
                           'the field layer needs it enabled'}
    rep = dispersion_payload(manager, view_name)
    if not rep.get('ok'):
        return {'ok': False,
                'refusal': rep.get('refusal',
                                   f'field view "{view_name}" '
                                   f'refused')}
    legend = [{'label': f"{b.get('name')} "
                        f"({b.get('min')}–{b.get('max')} T)",
               'color': b.get('color')}
              for b in rep.get('bands', [])]
    return {'ok': True, 'vectors': rep.get('vectors', []),
            'legend': legend, 'fieldView': view_name,
            'note': rep.get('note', '')}


def _markers(manager, params):
    from motors.composition_splice import M0_INTERFACES
    fm_rows = {getattr(f, 'name', ''): f
               for f in rows(manager, 'FailureModeDefinition')}
    seeded = {m.get('interface'): m
              for m in params.get('markers', [])}
    out, legend = [], []
    for spec in M0_INTERFACES:
        mark = seeded.get(spec['name'])
        if not mark:
            continue
        modelled = [ref for ref in spec['failure_modes']
                    if fm_rows.get(ref) is not None
                    and getattr(fm_rows[ref], 'equation_ref', '')]
        unknown = [ref for ref in spec['failure_modes']
                   if fm_rows.get(ref) is None]
        color = '#4e9a63' if len(modelled) == len(
            spec['failure_modes']) else '#c98a00'
        out.append({
            'id': f"marker-{spec['name']}",
            'interface': spec['name'],
            'position': mark.get('position', [0, 0, 0]),
            'radius': mark.get('radius', 0.9),
            'color': color, 'alpha': 0.55,
            'between': [spec['member_a'], spec['member_b']],
            'failureModes': spec['failure_modes'],
            'modelled': modelled,
            'modeRowsMissing': unknown})
    legend = [
        {'label': 'every failure mode modelled', 'color': '#4e9a63'},
        {'label': 'unmodelled modes present (named in the marker)',
         'color': '#c98a00'}]
    return {'ok': True, 'markers': out, 'legend': legend,
            'note': 'positions are seeded approximations of the '
                    'joints, not derived geometry — the shape rows '
                    'carry absolute coords the markers do not read '
                    'yet'}


def layer_payload(manager, layer_row,
                  design='clock-lavet-m0'):
    kind = getattr(layer_row, 'kind', '')
    try:
        params = json.loads(getattr(layer_row, 'params_json', '')
                            or '{}')
        style = json.loads(getattr(layer_row, 'style_json', '')
                           or '{}')
    except ValueError:
        return {'ok': False, 'refusal': 'layer params do not parse'}
    part_bodies = params.get('part_bodies', V2_PART_BODIES)
    source = getattr(layer_row, 'source', '')
    try:
        if kind == 'part-coloring' and source == 'mass-bill':
            data = _mass_coloring(manager, design, part_bodies)
        elif kind == 'part-coloring' and source == 'part-stress':
            data = _stress_coloring(manager, design, part_bodies,
                                    style)
        elif kind == 'part-coloring' and source == 'materials':
            data = _material_coloring(manager, design, part_bodies)
        elif kind == 'vector-field':
            data = _vector_field(manager, params)
        elif kind == 'replay':
            data = {'ok': True, 'geometry': params,
                    'note': 'the page drives the animation from '
                            'the clock-sim step history — this '
                            'layer carries the geometry config '
                            'that used to live hard-coded in the '
                            'Angular motor page'}
        elif kind == 'markers':
            data = _markers(manager, params)
        else:
            data = {'ok': False,
                    'refusal': f'unknown layer kind/source '
                               f'"{kind}/{source}" — one of '
                               f'{LAYER_KINDS}'}
    except Exception as e:
        data = {'ok': False, 'refusal': f'layer raised: {e}'}
    return {'name': getattr(layer_row, 'name', ''),
            'displayName': getattr(layer_row, 'display_name', ''),
            'kind': kind, 'source': source,
            'description': getattr(layer_row, 'description', ''),
            **data}


def clock_scene_payload(manager, view_name,
                        design='clock-lavet-m0'):
    """The 3D assembly for one discipline view: base scene + every
    layer's render-ready data + which layers that view turns on by
    default. Stacking any combination is the caller's toggle."""
    view, refusal = resolve_named(manager, 'ClockViewDefinition',
                                  view_name)
    if refusal:
        return {'ok': False, **refusal}
    try:
        scene = json.loads(getattr(view, 'scene_json', '') or '{}')
    except ValueError:
        return {'ok': False, 'view': view_name,
                'refusal': 'scene_json does not parse'}
    if not scene.get('base'):
        return {'ok': False, 'view': view_name,
                'refusal': 'view has no scene_json — nav-4 gave it '
                           'leads/links; viz-1 needs base + layers',
                'suggestion': {'knob': 'ClockViewDefinition.'
                                       'scene_json'}}
    by_name = {getattr(r, 'name', ''): r
               for r in rows(manager, 'ClockSceneLayerDefinition')}
    layers = []
    for name in scene.get('layers', []):
        row = by_name.get(name)
        if row is None:
            layers.append({'name': name, 'ok': False,
                           'refusal': 'layer row not seeded'})
            continue
        payload = layer_payload(manager, row, design=design)
        payload['defaultOn'] = name in scene.get('defaultOn', [])
        layers.append(payload)
    return {'ok': True, 'view': view_name,
            'discipline': getattr(view, 'discipline', ''),
            'design': design,
            'baseScene': scene['base'],
            'layers': layers,
            'refusedLayers': [l['name'] for l in layers
                              if not l.get('ok')],
            'note': 'layers stack — any combination renders on the '
                    'one canvas; a refused layer stays listed with '
                    'its reason'}


# ---------------------------------------------------------------
# Seeds
# ---------------------------------------------------------------

PROV = 'viz-1'


def _j(o):
    return json.dumps(o)


SEED_CLOCK_SCENE_LAYERS = [
    {'name': 'layer-motion-replay',
     'display_name': 'Motion — solver replay',
     'kind': 'replay', 'source': 'clock-sim',
     'params_json': _j({
         'rotorBodies': ['rotor-magnet', 'rotor-pinion',
                         'rotor-index'],
         'rotorAxisX': -9.5,
         'coilBody': 'coil',
         'coilStyles': {'idle': 'motor-coil-idle',
                        'pos': 'motor-coil-pos',
                        'neg': 'motor-coil-neg'},
         'orientationOrigin': [-9.5, 0, 4.2],
         'orientationScale': 3.0,
         'fieldOrigin': [4.0, 0, 0], 'fieldAxis': [1, 0, 0],
         'fieldScale': 7.0}),
     'style_json': '{}',
     'description': 'Rotor rotation + coil polarity replayed from '
                    'the solver step history — motion is runtime, '
                    'never baked into the scene.',
     'is_prior': True, 'provenance_id': PROV, 'notes': ''},
    {'name': 'layer-mass-coloring',
     'display_name': 'Mass — share of the bill',
     'kind': 'part-coloring', 'source': 'mass-bill',
     'params_json': _j({'part_bodies': V2_PART_BODIES}),
     'style_json': '{}',
     'description': 'Bodies ramp green→red by mass share, from the '
                    'same shape rows the scene draws.',
     'is_prior': True, 'provenance_id': PROV, 'notes': ''},
    {'name': 'layer-stress-coloring',
     'display_name': 'Stress — governing safety factor',
     'kind': 'part-coloring', 'source': 'part-stress',
     'params_json': _j({'part_bodies': V2_PART_BODIES}),
     'style_json': _j({'failBelow': 1.5, 'warnBelow': 4.0}),
     'description': 'Bodies color by static stress SF under the '
                    'criterion their failure class demands; a '
                    'refusing engine grays the part with its '
                    'reason.',
     'is_prior': True, 'provenance_id': PROV, 'notes': ''},
    {'name': 'layer-material-coloring',
     'display_name': 'Materials — what each part is made of',
     'kind': 'part-coloring', 'source': 'materials',
     'params_json': _j({'part_bodies': V2_PART_BODIES}),
     'style_json': '{}',
     'description': 'One color per material option; the legend is '
                    'the sourcing story at a glance.',
     'is_prior': True, 'provenance_id': PROV, 'notes': ''},
    {'name': 'layer-field-dispersion',
     'display_name': 'B field — banded dispersion',
     'kind': 'vector-field', 'source': 'magnetics-fieldview',
     'params_json': _j({'field_view': 'dipole-b-dispersion'}),
     'style_json': '{}',
     'description': 'The mag-fv threshold-gated vector dispersion, '
                    'overlaid on the motor scene.',
     'is_prior': True, 'provenance_id': PROV, 'notes': ''},
    {'name': 'layer-interface-markers',
     'display_name': 'Interfaces — joints & failure modes',
     'kind': 'markers', 'source': 'composition-interfaces',
     'params_json': _j({'markers': [
         {'interface': 'ifm0-rotor-shaft',
          'position': [-9.5, 0, 0], 'radius': 1.0},
         {'interface': 'ifm0-working-gap',
          'position': [-6.2, 0, 0], 'radius': 0.9},
         {'interface': 'ifm0-coil-bobbin',
          'position': [4.0, 0, 0], 'radius': 1.0},
         {'interface': 'ifm0-bobbin-stator',
          'position': [4.0, 0, -2.0], 'radius': 0.9},
         {'interface': 'ifm0-leads-coil',
          'position': [9.5, 0, 0], 'radius': 0.8}]}),
     'style_json': '{}',
     'description': 'A sphere per M0 interface, green when every '
                    'failure mode is modelled, amber when not — '
                    'the composition splice made visible.',
     'is_prior': True, 'provenance_id': PROV, 'notes': ''},
]

#: Every view lists ALL layers (overlap is the point); defaultOn
#: is the discipline's opening statement.
ALL_LAYERS = [l['name'] for l in SEED_CLOCK_SCENE_LAYERS]
V2_BASE = 'motor-m0-lavet-v2-viz'
VIEW_SCENES = {
    'view-goal-explorer': ['layer-motion-replay'],
    'view-mechanical': ['layer-stress-coloring',
                        'layer-interface-markers'],
    'view-electrical': ['layer-motion-replay'],
    'view-magnetic': ['layer-field-dispersion',
                      'layer-motion-replay'],
    'view-materials-sourcing': ['layer-material-coloring'],
    'view-mass': ['layer-mass-coloring'],
    'view-motion': ['layer-motion-replay'],
    'view-cost': ['layer-material-coloring'],
}


def scene_json_for_view(view_name):
    default_on = VIEW_SCENES.get(view_name)
    if default_on is None:
        return ''
    return _j({'base': V2_BASE, 'layers': ALL_LAYERS,
               'defaultOn': default_on})


def seed_clock_scene(manager):
    """Layer rows via the upsert path (converge live rows)."""
    return upsert_seed_pairs(
        manager,
        [('ClockSceneLayerDefinition', ClockSceneLayerDefinition,
          SEED_CLOCK_SCENE_LAYERS)],
        tag='ClockSceneSeed')
