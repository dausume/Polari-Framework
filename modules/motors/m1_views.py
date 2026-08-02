"""
@module motors.m1_views

m1-2: M1's discipline views AS ROWS — the same ClockViewDefinition
class, the same view_payload assembler, new rows whose sections
carry `design: reluctance-6s4p-m1`. Adding a rung's views is an
INSERT, not a component (the view-1 promise, kept).

What is new here is only what M1 itself brings:
- the sequencing sources (m1-1 solver, holding torque, the
  drive-current bisect with its pull-in physics),
- SIX COILS -> THREE PHASES electrics: per-phase R aggregated from
  the winding engine; per-phase L is a NAMED GAP until the bench
  (m1-7) measures six of them — the model predicts the phases
  EQUAL, so IMBALANCE is a thing only measurement can find,
- the positioning proof as a NAMED GAP section until m1-5 wires
  m1_positioning.py — the refusal states the exact seam,
- the stator materials fork (cast mu~2 vs bio-steel vs fired) led
  by the role screen — the m1-6 decision surfaced where materials
  are discussed, not buried in a route file.

Sections that today refuse (composition splice before m1-4, the
proof before m1-5) refuse BY NAME in the payload — the M0 rule
that a discipline view never silently drops a panel.

@consumers motors.motor_api (imports register the sources),
motors.selftest_m1, polariServer seed pass (seed_m1_views)
"""

import json

from composition.seed_upsert import upsert_seed_pairs

from motors.clock_views import (
    ClockViewDefinition, SECTION_SOURCES,
)

M1_DESIGN = 'reluctance-6s4p-m1'
PROV = 'm1-2'


def m1_phase_electrics(manager, design_name=M1_DESIGN):
    """Six coils -> three phases: per-phase R from the winding
    engine (two coils in series per phase), per-phase L refused by
    name. The MODEL says the phases are identical — so a measured
    IMBALANCE (m1-7 measures all six R and all six L) is a
    manufacturing finding, never a modeling output."""
    from motors.motor_winding import winding_report
    rep = winding_report(manager, design_name)
    if not rep.get('ok'):
        return rep
    r_coil = rep.get('resistanceOhm')
    if r_coil is None:
        return {'ok': False,
                'refusal': 'winding_report carries no '
                           'resistanceOhm — cannot aggregate '
                           'phases'}
    phases = [{'phase': p, 'coils': [f'tooth-{i}', f'tooth-{i+3}'],
               'rPhaseOhm': 2.0 * float(r_coil),
               'lPhaseH': None} for i, p in enumerate('ABC')]
    return {
        'ok': True, 'design': design_name,
        'coilCount': 6, 'phaseCount': 3,
        'perCoil': {'resistanceOhm': r_coil,
                    'source': 'winding_report (the same engine '
                              'that judged the M0 coil)'},
        'phases': phases,
        'imbalance': {
            'predicted': 0.0,
            'note': 'the model CANNOT predict imbalance — it '
                    'builds six identical coils. The bench (m1-7) '
                    'measures six R and six L; any spread is a '
                    'MANUFACTURING finding with a per-coil '
                    'paper trail.'},
        'inductanceGap': {
            'refusal': 'per-phase L is not solved here: the mag-23 '
                       'FEM solve is bound to the M0 bobbin '
                       'geometry, and the reluctance network at '
                       'mu~2 is outside its validity regime '
                       '(model-validity section)',
            'suggestion': {
                'knob': 'bench_campaign (m1-7)',
                'action': 'measure six per-phase inductances; '
                          'they feed the same mag-23 '
                          'adjudication the clock L did'}},
        'windingReport': rep}


def _positioning_gap(manager, a):
    return {'ok': False,
            'refusal': 'the POSITIONING PROOF is not wired yet — '
                       'm1_positioning.py (m1-5) turns printer-'
                       'axis requirement rows (leadscrew pitch -> '
                       'steps/mm, axis load, holding demand) plus '
                       'the m1-1 step history into position error '
                       'in mm vs commanded: EXACT when nothing '
                       'misses, every missed step a named error, '
                       'mm-error and missed-count pinned equal by '
                       'two paths',
            'suggestion': {'knob': 'motors.m1_positioning (m1-5)',
                           'action': 'build the proof on the m1-1 '
                                     'solver; it already carries '
                                     'thetaContinuousDeg and '
                                     'per-step shortfallDeg for '
                                     'exactly this'}}


def _src_m1(module, fn):
    def call(manager, a):
        import importlib
        return getattr(importlib.import_module(module),
                       fn)(manager, a['design'])
    return call


M1_SECTION_SOURCES = {
    'm1-sequence': _src_m1('motors.m1_sequencing', 'sequence_sim'),
    'm1-holding': _src_m1('motors.m1_sequencing', 'holding_torque'),
    'm1-min-current': lambda m, a: __import__(
        'motors.m1_sequencing',
        fromlist=['m1_minimum_drive_current']
    ).m1_minimum_drive_current(m, a['design'],
                               load_torque_nm=a.get('load')),
    'drive-profile': _src_m1('motors.motor_drive',
                             'simplefoc_config'),
    'm1-phase-electrics': _src_m1('motors.m1_views',
                                  'm1_phase_electrics'),
    'role-screen': lambda m, a: __import__(
        'motors.part_roles', fromlist=['screen_candidates']
    ).screen_candidates(m, a['part_name']),
    'm1-positioning-proof': _positioning_gap,
}

# One dispatch table for every view row — M1 sources register into
# clock_views' table at import (motor_api imports this module, so
# registration precedes any payload assembly).
SECTION_SOURCES.update(M1_SECTION_SOURCES)


def _j(o):
    return json.dumps(o)


def _s(name, source, lead, args=None, links=None):
    d = {'name': name, 'source': source,
         'args': {'design': M1_DESIGN, **(args or {})},
         'lead': lead}
    if links:
        d['links'] = links
    return d


_M1_SCENE_LINK = [{'label': 'M1 motor (3D)', 'kind': 'simspace',
                   'route': '/sim-spaces/motor-m1-viz'}]

SEED_M1_VIEWS = [
    {'name': 'view-m1-sequencing',
     'display_name': 'M1 — sequencing & drive',
     'discipline': 'motion', 'scale_support': 'm0-only',
     'description': 'the 6s/4p switched-reluctance control case: '
                    'phase sequencing at 30 deg/step, holding '
                    'torque, the drive card, and the derived (not '
                    'asserted) drive current',
     'sections_json': _j([
         _s('sequence', 'm1-sequence',
            'Excite a phase, the rotor settles aligned; sequence '
            'the phases and it walks 30 deg/step — 360/(3 phases '
            'x 4 poles). The scene replays THIS history. And the '
            'fact M0 never had to state: de-energized, a '
            'reluctance machine holds NOTHING.',
            links=_M1_SCENE_LINK),
         _s('holding-torque', 'm1-holding',
            'The torque one energized phase can hold against — '
            'honestly FEEBLE at mu~2, because the core barely '
            'beats air and saliency barely moves the loop. That '
            'is the rung: close the cast-wind-drive-spin loop, '
            'then earn better material.'),
         _s('drive-profile', 'drive-profile',
            'M0 was a bare alternating pulse; FOC starts HERE. '
            'The SimpleFOC binding with pole pairs from the '
            'design row — the drive card the bench wires up.'),
         _s('min-current', 'm1-min-current',
            'The current M1 NEEDS, bisected against the solver — '
            'refused until a load is stated (no magnet, no '
            'detent: against zero load the answer is zero). '
            'PULL-IN governs, not pull-out: the weakest torque '
            'along the travel decides, exactly like a stepper '
            'datasheet.')]),
     'is_prior': True, 'provenance_id': PROV, 'notes': ''},
    {'name': 'view-m1-magnetics',
     'display_name': 'M1 — magnetics',
     'discipline': 'magnetic', 'scale_support': 'm0-only',
     'description': 'the reluctance network outputs with the mu~2 '
                    'validity caveat LEADING — at this rung the '
                    'model caveat is the headline, not a footnote',
     'sections_json': _j([
         _s('model-validity', 'model-validity',
            'READ THIS FIRST at M1: at mu~2 the lumped network '
            'STOPS APPLYING — flux is not confined, FEM diverges '
            'from the network by ~4.7x. Every number below is a '
            'ratio-grade estimate, and says so.',
            links=[{'label': 'Field views', 'kind': 'page',
                    'route': '/magnetics/fields'}]),
         _s('torque-curve', 'torque-curve',
            'Three-phase co-energy torque over one electrical '
            'period — SMALL numbers stated as small; ratios '
            'survive the model caveat better than absolutes.'),
         _s('inductance', 'inductance',
            'The network\'s inductance for the M1 winding — '
            'carried WITH its validity regime; the bench (m1-7) '
            'measures six real ones and adjudicates.')]),
     'is_prior': True, 'provenance_id': PROV, 'notes': ''},
    {'name': 'view-m1-electrical',
     'display_name': 'M1 — electrical',
     'discipline': 'electrical', 'scale_support': 'm0-only',
     'description': 'six windings, three phases: per-phase R '
                    'aggregated from the winding engine, per-phase '
                    'L a named gap until the bench; imbalance is a '
                    'FINDING, not a parameter',
     'sections_json': _j([
         _s('phase-electrics', 'm1-phase-electrics',
            'Six coils in three series pairs: per-phase R from '
            'the same winding engine that judged the M0 coil. '
            'The model builds identical phases — IMBALANCE can '
            'only come from the bench, which is why m1-7 '
            'measures all six.'),
         _s('winding', 'winding',
            'One coil under the M0 questions: does the copper '
            'fit the window, what does it dissipate — 300 turns '
            'of 26 AWG is coarse-gauge territory, W2 wire, no '
            'converter drama.')]),
     'is_prior': True, 'provenance_id': PROV, 'notes': ''},
    {'name': 'view-m1-mechanical',
     'display_name': 'M1 — mechanical',
     'discipline': 'mechanical', 'scale_support': 'm0-only',
     'description': 'load cases + stress and fatigue on the parts '
                    'the phase forces actually work: stator teeth '
                    'and rotor poles',
     'sections_json': _j([
         _s('load-cases', 'load-cases',
            'What the machine really sees — and the M0 lesson '
            'carries: operating loads are tiny, ASSEMBLY and '
            'handling govern a cast mu~2 body.'),
         _s('tooth-stress', 'part-stress',
            'The stator tooth under its worst load, judged by '
            'the criterion its failure class demands — brittle '
            'castings answer to max-principal, not von Mises.',
            args={'part_name': 'm1-stator-teeth'},
            links=_M1_SCENE_LINK),
         _s('pole-stress', 'part-stress',
            'The rotor pole: the radial pull of an energized '
            'phase lands here, every step, forever.',
            args={'part_name': 'm1-rotor-poles'}),
         _s('pole-fatigue', 'part-fatigue',
            'Every step is a load cycle on a brittle casting — '
            'fatigue REVERSED the static verdict on the M0 '
            'pinion, so M1 asks the same question before '
            'trusting the same material.',
            args={'part_name': 'm1-rotor-poles'})]),
     'is_prior': True, 'provenance_id': PROV, 'notes': ''},
    {'name': 'view-m1-materials-sourcing',
     'display_name': 'M1 — materials & sourcing',
     'discipline': 'materials-sourcing', 'scale_support': 'm0-only',
     'description': 'the accountability chain for a machine with '
                    'NO magnet — the stator material fork (cast '
                    'mu~2 / bio-steel / fired) is the whole '
                    'sourcing question, led by the role screen',
     'sections_json': _j([
         _s('stator-role-screen', 'role-screen',
            'THE M1 DECISION: the stator tooth wants a SOFT '
            'magnetic conductor, and the screen ranks what we '
            'can actually make — cast geopolymer (mu~2, feeble, '
            'closes the loop TODAY) vs galvanized bio-steel vs '
            'fired ferrite. m1-6 turns this into routes; the '
            'screen is where the evidence lives.',
            args={'part_name': 'm1-stator-teeth'}),
         _s('accountability-chain', 'materials-accountability',
            'Part -> option -> per-value provenance -> dated '
            'citations -> make-vs-buy, for every M1 material. '
            'No magnet on the bill is the point of the rung.'),
         _s('composition-structure', 'composition-structure',
            'The M1 as a composition tree — interfaces, failure '
            'modes, separability. Refuses by name until the '
            'm1-4 splice states M1\'s joints.'),
         _s('promotion-candidates', 'promotion-candidates',
            'The promotion M1 actually poses: wind the teeth as '
            'separable bobbins, or PROMOTE wound teeth into the '
            'stator (sol-gel over the winding) and trade '
            'interface failures for bulk ones? m1-4 states both '
            'constructions as rows.')]),
     'is_prior': True, 'provenance_id': PROV, 'notes': ''},
    {'name': 'view-m1-positioning',
     'display_name': 'M1 — positioning (the product)',
     'discipline': 'motion', 'scale_support': 'm0-only',
     'description': 'M1\'s product is POSITION: the printer-axis '
                    'proof — steps to mm through a leadscrew, '
                    'exact-or-missed — as the view the rung is '
                    'FOR; the proof section refuses by name until '
                    'm1-5 builds it',
     'sections_json': _j([
         _s('positioning-proof', 'm1-positioning-proof',
            'THE proof this rung exists for: command N steps, '
            'land on the position or name exactly what was '
            'missed — "keeps time" become "lands on the '
            'commanded position". Refused BY NAME until m1-5 '
            'wires m1_positioning.py.'),
         _s('sequence-under-load', 'm1-sequence',
            'The solver the proof will drive — today unloaded; '
            'the axis rows (m1-5) bring the load torque, and '
            'the same history that replays in 3D becomes the '
            'position ledger.',
            links=_M1_SCENE_LINK)]),
     'is_prior': True, 'provenance_id': PROV, 'notes': ''},
]

# viz-1 discipline: a view must decide its 3D scene deliberately —
# m1-3's m1_scene owns the M1 base + layers + defaultOn.
from motors.m1_scene import m1_scene_json_for_view  # noqa: E402

for _view_seed in SEED_M1_VIEWS:
    _view_seed['scene_json'] = m1_scene_json_for_view(
        _view_seed['name'])


def seed_m1_views(manager):
    return upsert_seed_pairs(manager, [
        ('ClockViewDefinition', ClockViewDefinition,
         SEED_M1_VIEWS),
    ], tag='M1ViewsSeed')
