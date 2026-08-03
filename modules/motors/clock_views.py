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
                 scene_json='', scale_support='m0-only',
                 is_prior=True, provenance_id='', notes='',
                 manager=None):
        self.name = name
        self.display_name = display_name
        self.discipline = (discipline if discipline in DISCIPLINES
                           else 'goals')
        self.description = description
        #: viz-1: {'base': <SimSpaceDefinition>, 'layers': [names],
        #: 'defaultOn': [names]} — the view's 3D assembly; layers
        #: are ClockSceneLayerDefinition rows, stackable.
        self.scene_json = scene_json
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
    from motors.composition_splice import composition_view, \
        interface_specs
    view = composition_view(manager, a['design'])
    if not view.get('ok'):
        return view
    fm_rows = {getattr(f, 'name', ''): f
               for f in rows(manager, 'FailureModeDefinition')}
    out = []
    for spec in interface_specs(a['design']):
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


#: Which registered display component renders a section's payload.
#: A section row may set its own 'renderer'; this is the default when
#: it does not, so the mapping is data in one place rather than a
#: switch statement in the template.
#:
#: The names resolve through the SAME frontend ComponentRegistry the
#: no-code displays use, so a section slot and a display slot are the
#: same kind of thing. Several of these payloads ALREADY had a
#: first-class renderer sitting unused in the magnetics folder while
#: the view JSON-dumped them — that is what this table fixes.
#:
#: A source with no entry renders as the named payload fallback, which
#: is an explicit last resort rather than the default.
SECTION_RENDERERS = {
    'winding': 'motor-winding-panel',
    'mass-bill': 'motor-parts-panel',
    'materials-accountability': 'motor-materials-panel',
    'drive-profile': 'motor-drive-panel',
}


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
    # as-1/3: the genuine assembly + the end-to-end time proof.
    'clock-assembly': lambda m, a: __import__(
        'motors.clock_assembly', fromlist=['clock_assembly_report']
    ).clock_assembly_report(m),
    'timekeeping-proof': lambda m, a: __import__(
        'motors.clock_assembly', fromlist=['timekeeping_proof']
    ).timekeeping_proof(m, pulses=int(a.get('pulses', 120))),
    # mp0: the product, twice-sourced.
    'sourcing-routes': lambda m, a: __import__(
        'motors.product_routes', fromlist=['product_routes']
    ).product_routes(m, design_name=a.get('design',
                                          'clock-lavet-m0b')),
    # bench-1: the W2 measurement protocol.
    'bench-campaign': lambda m, a: __import__(
        'motors.bench_campaign', fromlist=['bench_campaign']
    ).bench_campaign(m, design_name=a.get('design',
                                          'clock-lavet-m0b')),
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


def _derived_links(source, payload):
    """nav-4: links a section can only know from its LIVE payload —
    the mass bill links every part to its material's page. Seeded
    links stay data on the section; this adds what data can't."""
    links = []
    if source == 'mass-bill':
        for p in payload.get('parts', []):
            mat = p.get('material')
            if mat:
                links.append({'label': f"{p.get('part')} → {mat}",
                              'route': f'/materials/{mat}',
                              'kind': 'material'})
    return links


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
        # nav-4: sections LEAD with their seeded 2-3 line insight +
        # links INTO the visuals (simspaces, materials, tech nodes);
        # the payload is the expander, not the face.
        links = list(s.get('links') or [])
        if payload.get('ok'):
            links += _derived_links(source, payload)
        out.append({'section': s.get('name', source),
                    'source': source,
                    'lead': s.get('lead', ''),
                    'links': links,
                    #: HOW to draw it, not just where it came from.
                    #: Seeded override first, else the source's
                    #: default, else '' = the named payload fallback.
                    'renderer': (s.get('renderer')
                                 or SECTION_RENDERERS.get(source, '')),
                    'args': {
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

    def run(name, fn, renderer=''):
        try:
            payload = fn()
        except Exception as e:
            payload = {'ok': False, 'refusal': f'raised: {e}'}
        sections.append({'section': name,
                         #: Same contract as view_payload: the
                         #: section says how it draws. Every part
                         #: drill-in was raw JSON before this.
                         'renderer': (renderer
                                      or SECTION_RENDERERS.get(name, '')),
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
    run('mass-and-geometry', _mass, 'motor-parts-panel')
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
          'args': {},
          'lead': 'Which clock scales are OPEN with what we can '
                  'make today: a verdict per scale with its binding '
                  'blocker and measurement gap named — the design '
                  'matrix, not a wish list.',
          'links': [{'label': 'M0 running', 'kind': 'page',
                     'route': '/magnetics/motor'}]},
         {'name': 'goal-detail', 'source': 'goal-feasibility',
          'args': {'goal': 'goal-local-wall-clock'},
          'lead': 'One goal end-to-end: is the local wall clock '
                  'feasible, what blocks it, and which knob would '
                  'move the verdict.'}]),
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
          'source': 'failure-conditions', 'args': {},
          'lead': 'Every failure mode the M0 carries at its '
                  'interfaces, with what you would actually SEE '
                  'when it happens; unmodelled modes are marked, '
                  'never hidden.'},
         {'name': 'load-cases', 'source': 'load-cases', 'args': {},
          'lead': 'The loads the machine really sees. Operating '
                  'peaks are tiny — ASSEMBLY handling governs: it '
                  'will not break doing its job, it can break '
                  'being built.'},
         {'name': 'pinion-stress', 'source': 'part-stress',
          'args': {'part_name': 'lavet-v2-pinion'},
          'lead': 'The governing part under its worst load, judged '
                  'by the criterion its failure class demands '
                  '(max-principal for brittle, von Mises for '
                  'ductile).',
          'links': [{'label': 'Pinion in 3D', 'kind': 'simspace',
                     'route': '/sim-spaces/motor-m0-viz'}]},
         {'name': 'pinion-fatigue', 'source': 'part-fatigue',
          'args': {'part_name': 'lavet-v2-pinion'},
          'lead': 'A clock steps 3.2e8 times in ten years — '
                  'fatigue REVERSES the static answer for brittle '
                  'castings (SCG + Weibull derates multiply).'},
         {'name': 'pinion-contact', 'source': 'contact-stress',
          'args': {'part_name': 'lavet-v2-pinion'},
          'lead': 'The whole tooth load rides a micron-scale '
                  'patch; a brittle tooth is judged by trailing-'
                  'edge TENSION, not peak pressure.'},
         {'name': 'stress-tensor-field',
          'source': 'stress-tensor-field', 'args': {},
          'lead': 'The full tensor field over a part is a NAMED '
                  'gap — the refusal states the exact seam that '
                  'would wire it.'}]),
     'is_prior': True, 'provenance_id': PROV, 'notes': ''},
    {'name': 'view-electrical',
     'display_name': 'Electrical engineering',
     'discipline': 'electrical', 'scale_support': 'm0-only',
     'description': 'winding electrics: R, V vs the cell, gauge '
                    'sweep, drive pulse — SEPARATE from the '
                    'magnetic view by design',
     'sections_json': _j([
         {'name': 'winding', 'source': 'winding', 'args': {},
          'lead': 'Does the copper FIT and can a cell drive it: '
                  'fill factor, resistance, voltage against the '
                  'supply, dissipation as watts — never a guessed '
                  'temperature.'},
         {'name': 'gauge-sweep', 'source': 'winding-gauge-sweep',
          'args': {},
          'lead': 'GAUGE sets voltage, TURNS set battery life, '
                  'WINDOW sets turns — independent levers, so '
                  'coarse wire costs only bobbin size. Turns '
                  'CANCEL out of coil voltage.'},
         {'name': 'pulse-response',
          'source': 'drive-pulse-response', 'args': {},
          'lead': 'Does the 30 ms pulse reach final current '
                  'through the coil inductance — the time-constant '
                  'answer that retires the deep-turns risk.'}]),
     'is_prior': True, 'provenance_id': PROV, 'notes': ''},
    {'name': 'view-magnetic',
     'display_name': 'Magnetics',
     'discipline': 'magnetic', 'scale_support': 'm0-only',
     'description': 'inductance by FEM with its validity regime, '
                    'and the torque curve',
     'sections_json': _j([
         {'name': 'inductance', 'source': 'inductance', 'args': {},
          'lead': 'Inductance actually SOLVED by 2D FEM '
                  '(feature-aligned mesh, energy route cross-'
                  'checked by a real flux cut) — not asserted.',
          'links': [{'label': 'Field views', 'kind': 'page',
                     'route': '/magnetics/fields'}]},
         {'name': 'model-validity', 'source': 'model-validity',
          'args': {},
          'lead': 'Where the lumped reluctance model STOPS '
                  'APPLYING: low-mu cores do not confine flux, and '
                  'our locally producible materials are exactly '
                  'the low-mu ones.',
          'links': [{'label': 'Field views', 'kind': 'page',
                     'route': '/magnetics/fields'}]},
         {'name': 'torque-curve-m1', 'source': 'torque-curve',
          'args': {'design': 'reluctance-6s4p-m1'},
          'lead': 'The M1 torque curve from the reluctance '
                  'network — ratios survive the model caveat '
                  'better than absolutes.'}]),
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
          'source': 'materials-accountability', 'args': {},
          'lead': 'Part → option → per-value provenance → dated '
                  'citations → make-vs-buy: every material claim '
                  'traceable to where it came from.',
          'links': [{'label': 'Parts & materials (3D)',
                     'kind': 'page',
                     'route': '/magnetics/clock-motor'}]},
         {'name': 'composition-structure',
          'source': 'composition-structure', 'args': {},
          'lead': 'The M0 as a composition tree: components, '
                  'interfaces with their failure modes, and the '
                  'separability levels the arc established.'},
         {'name': 'promotion-candidates',
          'source': 'promotion-candidates', 'args': {},
          'lead': 'Where PROMOTION (processing an assembly into '
                  'one part) is on the table, and what each trade '
                  'buys and spends — repairability included.'}]),
     'is_prior': True, 'provenance_id': PROV, 'notes': ''},
    {'name': 'view-mass', 'display_name': 'Mass & geometry',
     'discipline': 'mass', 'scale_support': 'm0-only',
     'description': 'per-part volumes and masses from the SAME '
                    'shape rows the 3D view renders',
     'sections_json': _j([
         {'name': 'mass-bill', 'source': 'mass-bill', 'args': {},
          'lead': 'Per-part volume and mass from the SAME shape '
                  'rows the 3D scene draws — bill and picture '
                  'cannot disagree. Each part links to its '
                  'material below.',
          'links': [{'label': 'Motor scene (3D)',
                     'kind': 'simspace',
                     'route': '/sim-spaces/motor-m0-viz'}]},
         {'name': 'clock-assembly', 'source': 'clock-assembly',
          'args': {},
          'lead': 'The GENUINE assembly: motor + train gears + '
                  'hands, every mass from its own geometry x its '
                  'material density; each hand\'s imbalance torque '
                  'checked against what its shaft delivers through '
                  'the solved train. Absent members are NAMED.'}]),
     'is_prior': True, 'provenance_id': PROV, 'notes': ''},
    {'name': 'view-motion', 'display_name': 'Movement simulation',
     'discipline': 'motion', 'scale_support': 'm0-only',
     'description': 'the clock sim (steps vs time, the control '
                    'case) and the bench verification record',
     'sections_json': _j([
         {'name': 'timekeeping-proof', 'source': 'timekeeping-proof',
          'args': {},
          'lead': 'THE proof: the physics sim\'s (possibly missed) '
                  'steps carried through the solved ratios to the '
                  'hand angles, against true time. Zero missed '
                  'steps = EXACT agreement; every miss = exactly '
                  'one lost second, reported.'},
         {'name': 'clock-sim', 'source': 'clock-sim', 'args': {},
          'lead': 'The solver stepping the M0 — the control case '
                  'the whole arc rests on. The 3D scene replays '
                  'THIS step history, never a canned spin.',
          'links': [{'label': 'Motor scene (3D)',
                     'kind': 'simspace',
                     'route': '/sim-spaces/motor-m0-viz'}]},
         {'name': 'verification', 'source': 'verification',
          'args': {},
          'lead': 'What has actually been MEASURED vs replayed: '
                  'made-and-measured is earned by bench records '
                  'only; sim replays are provenance, not proof.'},
         {'name': 'bench-campaign', 'source': 'bench-campaign',
          'args': {},
          'lead': 'The W2 BENCH SHEET: five measurements in '
                  'order, each with its live-computed prediction '
                  '(both models where they disagree), its '
                  'instrument, what it adjudicates, and the exact '
                  'seam that records the result — the named next '
                  'advancement past M0, ready for the bench.'}]),
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
          'args': {'part_name': 'lavet-v2-pinion'},
          'lead': 'The TRUE price per year-of-timekeeping: the '
                  '1-cent cast pinion costs ~$1600/yr to own; '
                  'fired ceramic is 8x dearer to buy and five '
                  'orders cheaper to keep.'},
         {'name': 'cheapest-configuration',
          'source': 'cheapest-configuration',
          'args': {'part_name': 'lavet-v2-pinion'},
          'lead': 'Upfront vs lifetime orderings computed '
                  'SEPARATELY so they can disagree — and the '
                  'disagreement is the finding.'},
         {'name': 'dependency-trace',
          'source': 'materials-accountability', 'args': {},
          'lead': 'The same accountability chain read as a '
                  'dependency trace: supply sources, business '
                  'gates and dated citations under every cost.',
          'links': [{'label': 'Business start', 'kind': 'page',
                     'route': '/business/start'}]},
         {'name': 'sourcing-routes', 'source': 'sourcing-routes',
          'args': {},
          'lead': 'The COMPLETE PRODUCT, twice: pure-local (every '
                  'input made here, gaps named) vs commercial '
                  '(bought wire and magnet, cited) — both ending '
                  'at the same 24 h timekeeping QA gate and the '
                  'same sell-iteratively loop.',
          'links': [{'label': 'Business start', 'kind': 'page',
                     'route': '/business/start'},
                    {'label': 'Odoo business', 'kind': 'page',
                     'route': '/business/odoo'}]}]),
     'is_prior': True, 'provenance_id': PROV,
     'notes': 'the accountability chain IS the dependency trace: '
              'supply sources, dated citations, make-vs-buy '
              'cascade, realization/business gates per material.'},
]

# viz-1: every view gains its 3D assembly (base scene + stackable
# layers). Kept beside the seeds so a new view must decide its
# scene deliberately — scene_json_for_view returns '' for unknown
# names and the payload refuses honestly.
from motors.clock_scene import scene_json_for_view  # noqa: E402

for _view_seed in SEED_CLOCK_VIEWS:
    _view_seed['scene_json'] = scene_json_for_view(
        _view_seed['name'])


def seed_clock_views(manager):
    return upsert_seed_pairs(manager, [
        ('ClockViewDefinition', ClockViewDefinition,
         SEED_CLOCK_VIEWS),
    ], tag='ClockViewsSeed')
