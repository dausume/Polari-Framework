"""
@module motors.clock_views

view-1 (MOTOR_GOALS_PLAN goal-5 backend): SPECIALIZED VIEWS AS DATA.

Dustin 2026-07-31: views for clocks using the general M0 approach —
switch between scales, modulate goals and constraints, and SPLIT the
machine apart by discipline: a mechanical-engineering view (physical
failure conditions, stresses), an electrical-engineering view with
electrical and magnetic SEPARABLE, materials provenance/sourcing,
mass, movement simulation, cost from chosen provenance with
dependency tracing — at multiple scales, plus component-focused
views.

THE SHAPE: a view is a ClockViewDefinition ROW — discipline +
ordered sections, each section naming a SOURCE (an existing engine
entry point) and its args. The page renders rows; adding a view is
an insert, not a component. Sections that cannot answer REFUSE
inside the payload with the reason and the knob — a discipline view
never silently drops a panel.

Every source is an engine that already exists (stress, fatigue,
contact, winding, inductance+validity, accountability chain, bill,
clock sim, lifecycle cost, goal engine, composition splice). The one
that does not — the mechanical TENSOR field over a part — ships as a
NAMED GAP section, stating exactly what would wire it (fem_engine
elasticity export), never silently absent.

@consumers motors.motor_api, motors.selftest_motors,
polariServer seed passes (seed_clock_views — upsert path)
"""

import json

from objectTreeDecorators import treeObject, treeObjectInit

from composition.data_refs import resolve_named, rows
from composition.seed_upsert import upsert_seed_pairs

DISCIPLINES = ('goals', 'mechanical', 'electrical', 'magnetic',
               'materials-sourcing', 'mass', 'motion', 'cost',
               'component')


class ClockViewDefinition(treeObject):
    """One specialized view: discipline + ordered data sections."""

    @treeObjectInit
    def __init__(self, name='', display_name='', discipline='goals',
                 description='', sections_json='[]',
                 scale_support='m0-only', is_prior=True,
                 provenance_id='', notes='', manager=None):
        self.name = name
        self.display_name = display_name
        self.discipline = (discipline if discipline in DISCIPLINES
                           else 'goals')
        self.description = description
        #: [{'name', 'source', 'args': {...}}] — source is a key in
        #: SECTION_SOURCES; args merge under any caller overrides.
        self.sections_json = sections_json
        #: 'any-scale' = parameterized by goal/scale rows;
        #: 'm0-only' = the deep engines run on the built M0 today,
        #: and SAY so — per-scale depth is the growth path, not an
        #: assumption.
        self.scale_support = scale_support
        self.is_prior = is_prior
        self.provenance_id = provenance_id
        self.notes = notes


# ---------------------------------------------------------------
# Sources — every one an existing engine, bound late
# ---------------------------------------------------------------

def _failure_conditions(manager, a):
    """The PHYSICAL failure conditions: every failure mode carried
    by the design's interfaces and parts, with the observation that
    would show it (evidence_note) — what you would actually SEE."""
    from motors.composition_splice import M0_INTERFACES, \
        composition_view
    view = composition_view(manager, a['design'])
    if not view.get('ok'):
        return view
    fm_rows = {getattr(f, 'name', ''): f
               for f in rows(manager, 'FailureModeDefinition')}
    out = []
    for spec in M0_INTERFACES:
        for ref in spec['failure_modes']:
            fm = fm_rows.get(ref)
            out.append({
                'mode': ref, 'at': spec['name'],
                'locus': 'interface',
                'between': [spec['member_a'], spec['member_b']],
                'summary': getattr(fm, 'summary', '') if fm else
                'mode row not booted (composition off?)',
                'youWouldObserve': getattr(fm, 'evidence_note', '')
                if fm else '',
                'modelled': bool(fm and getattr(fm, 'equation_ref',
                                                '')),
            })
    return {'ok': True, 'design': a['design'], 'conditions': out,
            'count': len(out),
            'note': 'interface-locus modes from the stated M0 '
                    'joints; bulk modes attach per part and appear '
                    'in the component view. An unmodelled mode is '
                    'marked, never hidden.'}


def _stress_tensor_gap(manager, a):
    return {'ok': False,
            'refusal': 'the full stress TENSOR field over a part '
                       'is not wired yet — part_stress reports the '
                       'governing scalar checks (criterion chosen '
                       'by failure_class), and fem_engine solves '
                       '2D elasticity, but the per-element tensor '
                       'export from part geometry is the missing '
                       'seam',
            'suggestion': {'knob': 'fem_engine.solve_elasticity_2d',
                           'action': 'export the per-element '
                                     'stress tensor and bind it to '
                                     'the part shape rows'}}


def _src_design(module, fn):
    def call(manager, a):
        import importlib
        return getattr(importlib.import_module(module),
                       fn)(manager, a['design'])
    return call


def _src_part(module, fn):
    def call(manager, a):
        import importlib
        return getattr(importlib.import_module(module), fn)(
            manager, a['design'], a['part_name'])
    return call


SECTION_SOURCES = {
    # goals (any-scale)
    'scale-study': lambda m, a: __import__(
        'motors.scale_goals', fromlist=['scale_study']
    ).scale_study(m, a.get('policy', 'local-plus-imported-wire')),
    'goal-feasibility': lambda m, a: __import__(
        'motors.scale_goals', fromlist=['goal_feasibility']
    ).goal_feasibility(m, a['goal']),
    # mechanical
    'failure-conditions': _failure_conditions,
    'load-cases': _src_design('motors.motor_stress', 'load_cases'),
    'part-stress': _src_part('motors.motor_stress', 'part_stress'),
    'part-fatigue': _src_part('motors.motor_fatigue',
                              'part_fatigue'),
    'contact-stress': _src_part('motors.contact_wear',
                                'contact_stress'),
    'stress-tensor-field': _stress_tensor_gap,
    # electrical (separable from magnetic, per Dustin)
    'winding': _src_design('motors.motor_winding',
                           'winding_report'),
    'winding-gauge-sweep': _src_design('motors.motor_winding',
                                       'gauge_sweep'),
    'drive-pulse-response': _src_design('motors.inductance',
                                        'pulse_response'),
    # magnetic
    'inductance': _src_design('motors.inductance',
                              'solve_inductance'),
    'model-validity': _src_design('motors.inductance',
                                  'model_validity'),
    'torque-curve': _src_design('motors.motor_designer',
                                'torque_curve'),
    # materials + sourcing + dependency trace
    'materials-accountability': _src_design(
        'motors.motor_materials', 'material_accountability'),
    'composition-structure': _src_design(
        'motors.composition_splice', 'composition_view'),
    'promotion-candidates': _src_design(
        'motors.composition_splice', 'promotion_candidates'),
    # mass
    'mass-bill': _src_design('motors.motor_parts', 'part_report'),
    # motion
    'clock-sim': _src_design('motors.motor_designer', 'clock_sim'),
    'verification': _src_design('motors.motor_verify',
                                'verification_summary'),
    # cost (provenance-driven; the accountability chain carries the
    # cascaded make-vs-buy trace)
    'lifecycle-cost': _src_part('motors.lifecycle_cost',
                                'cost_per_lifespan_unit'),
    'cheapest-configuration': _src_part('motors.lifecycle_cost',
                                        'cheapest_configuration'),
}


def view_payload(manager, view_name, design='clock-lavet-m0',
                 goal='', component='', policy=''):
    """Assemble one view: run its sections, keep refusals IN the
    payload. Caller overrides (goal/component/policy) merge over
    each section's seeded args."""
    view, refusal = resolve_named(manager, 'ClockViewDefinition',
                                  view_name)
    if refusal:
        return {'ok': False, **refusal}
    try:
        sections = json.loads(getattr(view, 'sections_json', '')
                              or '[]')
    except ValueError:
        return {'ok': False, 'view': view_name,
                'refusal': 'sections_json does not parse'}
    out = []
    for s in sections:
        source = s.get('source', '')
        fn = SECTION_SOURCES.get(source)
        if fn is None:
            out.append({'section': s.get('name', source),
                        'ok': False,
                        'refusal': f'unknown source "{source}" — '
                                   f'one of '
                                   f'{sorted(SECTION_SOURCES)}'})
            continue
        args = {'design': design, **(s.get('args') or {})}
        if goal:
            args['goal'] = goal
        if component:
            args['part_name'] = component
        if policy:
            args['policy'] = policy
        try:
            payload = fn(manager, args)
        except Exception as e:
            payload = {'ok': False,
                       'refusal': f'section raised: {e}'}
        out.append({'section': s.get('name', source),
                    'source': source, 'args': {
                        k: v for k, v in args.items()
                        if k != 'design'},
                    **({'payload': payload} if payload.get('ok')
                       else {'ok': False,
                             'refusal': payload.get('refusal',
                                                    'refused'),
                             'suggestion': payload.get(
                                 'suggestion')})})
    return {
        'ok': True, 'view': view_name,
        'displayName': getattr(view, 'display_name', ''),
        'discipline': getattr(view, 'discipline', ''),
        'scaleSupport': getattr(view, 'scale_support', ''),
        'design': design,
        'sections': out,
        'refusedSections': [s['section'] for s in out
                            if not s.get('payload')],
        'note': 'a refused section is information: it names what '
                'would answer it. It is never dropped from the '
                'view.',
    }


def component_view(manager, part_name, design='clock-lavet-m0'):
    """The COMPONENT-focused view: one part, every discipline's
    answer about it, in one place."""
    from motors.part_roles import part_role_report
    sections = []

    def run(name, fn):
        try:
            payload = fn()
        except Exception as e:
            payload = {'ok': False, 'refusal': f'raised: {e}'}
        sections.append({'section': name,
                         **({'payload': payload}
                            if payload.get('ok') else
                            {'ok': False,
                             'refusal': payload.get('refusal',
                                                    'refused')})})
    run('roles-and-viability',
        lambda: part_role_report(manager, part_name))
    from motors.motor_stress import part_stress
    run('stress', lambda: part_stress(manager, design, part_name))
    from motors.motor_fatigue import part_fatigue
    run('fatigue', lambda: part_fatigue(manager, design, part_name))
    from motors.lifecycle_cost import cost_per_lifespan_unit
    run('lifecycle-cost',
        lambda: cost_per_lifespan_unit(manager, design, part_name))
    from motors.motor_parts import part_report
    def _mass():
        rep = part_report(manager, design)
        if not rep.get('ok'):
            return rep
        mine = [p for p in rep.get('parts', [])
                if p.get('part') == part_name]
        return {'ok': bool(mine),
                'part': mine[0] if mine else None,
                'refusal': '' if mine else
                f'"{part_name}" not in the {design} bill'}
    run('mass-and-geometry', _mass)
    return {'ok': True, 'component': part_name, 'design': design,
            'sections': sections,
            'refusedSections': [s['section'] for s in sections
                                if not s.get('payload')]}


# ---------------------------------------------------------------
# Seeds — the discipline split Dustin named, as rows
# ---------------------------------------------------------------

PROV = 'view-1'


def _j(o):
    return json.dumps(o)


SEED_CLOCK_VIEWS = [
    {'name': 'view-goal-explorer',
     'display_name': 'Goals & scales — what is possible',
     'discipline': 'goals', 'scale_support': 'any-scale',
     'description': 'switch scales, modulate goals/constraints; '
                    'verdicts with blockers and gaps named',
     'sections_json': _j([
         {'name': 'scale-study', 'source': 'scale-study',
          'args': {}},
         {'name': 'goal-detail', 'source': 'goal-feasibility',
          'args': {'goal': 'goal-local-wall-clock'}}]),
     'is_prior': True, 'provenance_id': PROV, 'notes': ''},
    {'name': 'view-mechanical',
     'display_name': 'Mechanical engineering',
     'discipline': 'mechanical', 'scale_support': 'm0-only',
     'description': 'physically observable failure conditions, '
                    'load cases, stress/fatigue/contact on the '
                    'governing parts; the tensor field is a NAMED '
                    'gap',
     'sections_json': _j([
         {'name': 'failure-conditions',
          'source': 'failure-conditions', 'args': {}},
         {'name': 'load-cases', 'source': 'load-cases', 'args': {}},
         {'name': 'pinion-stress', 'source': 'part-stress',
          'args': {'part_name': 'lavet-v2-pinion'}},
         {'name': 'pinion-fatigue', 'source': 'part-fatigue',
          'args': {'part_name': 'lavet-v2-pinion'}},
         {'name': 'pinion-contact', 'source': 'contact-stress',
          'args': {'part_name': 'lavet-v2-pinion'}},
         {'name': 'stress-tensor-field',
          'source': 'stress-tensor-field', 'args': {}}]),
     'is_prior': True, 'provenance_id': PROV, 'notes': ''},
    {'name': 'view-electrical',
     'display_name': 'Electrical engineering',
     'discipline': 'electrical', 'scale_support': 'm0-only',
     'description': 'winding electrics: R, V vs the cell, gauge '
                    'sweep, drive pulse — SEPARATE from the '
                    'magnetic view by design',
     'sections_json': _j([
         {'name': 'winding', 'source': 'winding', 'args': {}},
         {'name': 'gauge-sweep', 'source': 'winding-gauge-sweep',
          'args': {}},
         {'name': 'pulse-response',
          'source': 'drive-pulse-response', 'args': {}}]),
     'is_prior': True, 'provenance_id': PROV, 'notes': ''},
    {'name': 'view-magnetic',
     'display_name': 'Magnetics',
     'discipline': 'magnetic', 'scale_support': 'm0-only',
     'description': 'inductance by FEM with its validity regime, '
                    'and the torque curve',
     'sections_json': _j([
         {'name': 'inductance', 'source': 'inductance', 'args': {}},
         {'name': 'model-validity', 'source': 'model-validity',
          'args': {}},
         {'name': 'torque-curve-m1', 'source': 'torque-curve',
          'args': {'design': 'reluctance-6s4p-m1'}}]),
     'is_prior': True, 'provenance_id': PROV, 'notes': ''},
    {'name': 'view-materials-sourcing',
     'display_name': 'Materials, provenance & sourcing',
     'discipline': 'materials-sourcing', 'scale_support': 'm0-only',
     'description': 'the full accountability chain: part → option '
                    '→ per-value provenance → FEM/powder → dated '
                    'citations → cascaded make-vs-buy; plus the '
                    'composition structure',
     'sections_json': _j([
         {'name': 'accountability-chain',
          'source': 'materials-accountability', 'args': {}},
         {'name': 'composition-structure',
          'source': 'composition-structure', 'args': {}},
         {'name': 'promotion-candidates',
          'source': 'promotion-candidates', 'args': {}}]),
     'is_prior': True, 'provenance_id': PROV, 'notes': ''},
    {'name': 'view-mass', 'display_name': 'Mass & geometry',
     'discipline': 'mass', 'scale_support': 'm0-only',
     'description': 'per-part volumes and masses from the SAME '
                    'shape rows the 3D view renders',
     'sections_json': _j([
         {'name': 'mass-bill', 'source': 'mass-bill', 'args': {}}]),
     'is_prior': True, 'provenance_id': PROV, 'notes': ''},
    {'name': 'view-motion', 'display_name': 'Movement simulation',
     'discipline': 'motion', 'scale_support': 'm0-only',
     'description': 'the clock sim (steps vs time, the control '
                    'case) and the bench verification record',
     'sections_json': _j([
         {'name': 'clock-sim', 'source': 'clock-sim', 'args': {}},
         {'name': 'verification', 'source': 'verification',
          'args': {}}]),
     'is_prior': True, 'provenance_id': PROV, 'notes': ''},
    {'name': 'view-cost',
     'display_name': 'Cost & dependency trace',
     'discipline': 'cost', 'scale_support': 'm0-only',
     'description': 'cost per lifespan unit from CHOSEN provenance '
                    '+ the sourcing/business dependency trace the '
                    'accountability chain carries',
     'sections_json': _j([
         {'name': 'pinion-lifecycle-cost',
          'source': 'lifecycle-cost',
          'args': {'part_name': 'lavet-v2-pinion'}},
         {'name': 'cheapest-configuration',
          'source': 'cheapest-configuration',
          'args': {'part_name': 'lavet-v2-pinion'}},
         {'name': 'dependency-trace',
          'source': 'materials-accountability', 'args': {}}]),
     'is_prior': True, 'provenance_id': PROV,
     'notes': 'the accountability chain IS the dependency trace: '
              'supply sources, dated citations, make-vs-buy '
              'cascade, realization/business gates per material.'},
]


def seed_clock_views(manager):
    return upsert_seed_pairs(manager, [
        ('ClockViewDefinition', ClockViewDefinition,
         SEED_CLOCK_VIEWS),
    ], tag='ClockViewsSeed')
