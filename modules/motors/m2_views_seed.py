"""
@module motors.m2_views_seed

m2-3: M2's discipline views AS ROWS — the same ClockViewDefinition
class, the same view_payload assembler, new rows whose sections
carry `design: ferrite-pm-m2`. A rung's views are an INSERT, not a
component; the second time is when that promise gets tested, and
nothing in this file is a new mechanism.

What is new is only what M2 itself brings:
- rotation instead of stepping (m2-1), with the load angle and
  pull-out where M1 had missed steps and pull-in,
- a magnetics view whose FIRST card is still model validity, but
  whose second is the back-EMF constant — the one measurement
  that adjudicates the magnet prior on its own,
- electrics reusing m1_phase_electrics with M2's design row (200
  turns of 22 AWG instead of 300 of 26) — the function already
  took a design argument, so this is a call, not a copy,
- mechanical: the ring's BOND is the interesting stress, not a
  tooth,
- materials & sourcing: no construction fork here. The ring is
  press-and-sinter or bought — a ROUTE question (m2-6), and the
  role screen on a torque-magnet-active part is where a soft
  material gets refused outright,
- the LIFT proof (m2-5): the rung's product, a crucible off the
  floor and held there with the power off.

@consumers motors.motor_api (imports register the sources),
motors.m2_selftest, polariServer seed pass (seed_m2_views)
"""

import json

from moduleService.seed_upsert import upsert_seed_pairs

from motors.clock_views_basis import (
    ClockViewDefinition, SECTION_SOURCES,
)
# M2 views REUSE M1 sources (the drive card, the role screen, the
# materials chain) — importing m1_views is what puts those in the
# dispatch table. The reuse is the point of the rung, so the
# import says so rather than duplicating four source entries.
import motors.m1_views_seed  # noqa: F401,E402

M2_DESIGN = 'ferrite-pm-m2'
PROV = 'm2-3'


def _src_m2(module, fn):
    def call(manager, a):
        import importlib
        return getattr(importlib.import_module(module),
                       fn)(manager, a['design'])
    return call


M2_SECTION_SOURCES = {
    'm2-rotation': _src_m2('motors.custom.m2_rotation', 'rotation_sim'),
    'm2-pull-out': _src_m2('motors.custom.m2_rotation',
                           'pull_out_load_limit'),
    'm2-back-emf': _src_m2('motors.custom.m2_rotation',
                           'back_emf_constant'),
    'm2-lift-proof': _src_m2('motors.m2_lift_basis', 'lift_proof'),
    'm2-hoist-requirements': _src_m2('motors.m2_lift_basis',
                                     'hoist_report'),
    'm2-relations': _src_m2('motors.m2_composition_seed',
                            'm2_relation_report'),
    'm2-promotion-story': lambda m, a: __import__(
        'motors.m2_composition_seed', fromlist=['m2_promotion_story']
    ).m2_promotion_story(m),
    # The M1 electrics engine already takes a design argument —
    # so M2's electrics are a CALL, not a second implementation.
    'm2-phase-electrics': _src_m2('motors.m1_views_seed',
                                  'm1_phase_electrics'),
}

# One dispatch table for every view row — M2 sources register into
# clock_views' table at import, exactly as M1's do (motor_api
# imports this module, so registration precedes payload assembly).
SECTION_SOURCES.update(M2_SECTION_SOURCES)


def _j(o):
    return json.dumps(o)


def _s(name, source, lead, args=None, links=None):
    d = {'name': name, 'source': source,
         'args': {'design': M2_DESIGN, **(args or {})},
         'lead': lead}
    if links:
        d['links'] = links
    return d


_M2_SCENE_LINK = [{'label': 'M2 motor (3D)', 'kind': 'simspace',
                   'route': '/sim-spaces/motor-m2-viz'}]

SEED_M2_VIEWS = [
    {'name': 'view-m2-rotation',
     'display_name': 'M2 — rotation & drive',
     'discipline': 'motion', 'scale_support': 'm0-only',
     'description': 'the PM rung\'s control case: the magnet '
                    'follows the rotating field, lagging by '
                    'whatever angle makes the torque — until it '
                    'does not',
     'sections_json': _j([
         _s('rotation', 'm2-rotation',
            'Advance the commutation angle and the magnet '
            'follows. One electrical revolution is 180 deg of '
            'shaft (two pole pairs), the position error in '
            'synchronism is EXACTLY zero — a constant lag moves '
            'no position — and the scene replays THIS history. '
            'M1 walks and can miss a step; M2 spins and can fall '
            'out of step. Same ledger, opposite failure.',
            links=_M2_SCENE_LINK),
         _s('pull-out', 'm2-pull-out',
            'THE duty limit: the largest load the rotor stays in '
            'step under, bisected against the same sim that '
            'judges synchronism. Past it the machine does not '
            'droop — the lag walks past 90 deg electrical and '
            'the torque COLLAPSES. The peak is cross-checked '
            'against its closed form: two paths, one number.'),
         _s('drive-profile', 'drive-profile',
            'The SimpleFOC binding with pole pairs from the '
            'design row. M1 needed a three-phase driver; M2 '
            'needs the same driver to know WHERE THE ROTOR IS — '
            'which is the sensor line on the drive card.'),
         _s('bench-campaign', 'bench-campaign',
            'THE M2 BENCH SHEET (m2-7): six phase resistances '
            '(imbalance is a finding the model cannot make), the '
            'BACK-EMF CONSTANT against its prediction, the '
            'COGGING MAP the model says is zero, remanence, '
            'pull-out torque and a thermal rise no model '
            'predicts.')]),
     'is_prior': True, 'provenance_id': PROV, 'notes': ''},
    {'name': 'view-m2-magnetics',
     'display_name': 'M2 — magnetics',
     'discipline': 'magnetic', 'scale_support': 'm0-only',
     'description': 'the magnet is the machine now: the torque '
                    'curve with the PM term carrying it, k_e as '
                    'the adjudicating measurement, and the '
                    'cogging the model refuses to invent',
     'sections_json': _j([
         _s('model-validity', 'model-validity',
            'READ THIS FIRST: the lumped network still applies '
            'only as a ratio-grade estimate, and M2 adds a '
            'second prior on top — the magnet grade itself. '
            'Every torque number here rides a literature B_r '
            'until the press-sinter-magnetize experiment runs.',
            links=[{'label': 'Field views', 'kind': 'page',
                    'route': '/magnetics/fields'}]),
         _s('torque-curve', 'torque-curve',
            'Three-phase co-energy torque over one electrical '
            'period — and at saliency 1.0 the reluctance term is '
            'identically zero, so what is left IS the magnet. '
            'Compare it with M1\'s curve on the same frame: same '
            'stator, different physics.'),
         _s('m2-back-emf', 'm2-back-emf',
            'k_e, DERIVED from the same magnet MMF and loop '
            'reluctance the torque uses — never a second copy of '
            'the magnet math. Spin the rotor by hand and scope a '
            'phase: this is the one M2 measurement no other '
            'error can absorb, which is why it adjudicates the '
            'model. It also names the B_r / H_c slack the '
            'material rows carry.'),
         _s('m2-relations', 'm2-relations',
            'The air gap and the magnet thickness as CORRELATIONS '
            'between the parts\' own equations — and the gap '
            'relation spans two rungs (M1\'s tooth face against '
            'M2\'s ring), so M2 cannot drift away from the '
            'stator it claims to reuse.')]),
     'is_prior': True, 'provenance_id': PROV, 'notes': ''},
    {'name': 'view-m2-electrical',
     'display_name': 'M2 — electrical',
     'discipline': 'electrical', 'scale_support': 'm0-only',
     'description': 'six windings, three phases — the same '
                    'engine as M1 on a coarser wire, plus the '
                    'voltage the magnet generates back',
     'sections_json': _j([
         _s('m2-phase-electrics', 'm2-phase-electrics',
            'Per-phase R aggregated from the winding engine at '
            'M2\'s 200 turns of 22 AWG. The engine already took '
            'a design argument, so this is a CALL, not a second '
            'implementation — and the model still says the six '
            'coils are identical, which is why imbalance is a '
            'bench finding.'),
         _s('m2-back-emf', 'm2-back-emf',
            'The other half of the electrical story, and the one '
            'M1 could not have: a spinning magnet pushes voltage '
            'BACK into the drive. It sets the speed a given '
            'supply can reach, and it is measured with nothing '
            'but a hand and a scope.'),
         _s('drive-profile', 'drive-profile',
            'The drive card: three half-bridges and a rotor '
            'position sensor.')]),
     'is_prior': True, 'provenance_id': PROV, 'notes': ''},
    {'name': 'view-m2-mechanical',
     'display_name': 'M2 — mechanical',
     'discipline': 'mechanical', 'scale_support': 'm0-only',
     'description': 'the bonded rotor and the one designed gap — '
                    'plus the lift the rung exists to do',
     'sections_json': _j([
         _s('part-stress', 'part-stress',
            'Governing safety factor per part under the '
            'criterion each material\'s failure class demands. '
            'The ring is the one to read: a sintered ceramic '
            'spun on a bond line.',
            args={'part_name': 'm2-magnet-ring'}),
         _s('composition-structure', 'composition-structure',
            'M2 as a composition tree. ONE designed non-contact '
            'interface where M1 had two — a round rotor has no '
            'pole tips to swing past the coil bores — and the '
            'rotor is ALREADY PROMOTED, by bond rather than by '
            'mold.'),
         _s('m2-promotion-story', 'm2-promotion-story',
            'What promotion means on this rung: the bond that '
            'already happened, the gap that refuses, and the '
            'winding fork M2 INHERITS from M1 rather than '
            're-litigating.'),
         _s('m2-hoist-requirements', 'm2-hoist-requirements',
            'The hoist as ROWS: crucible mass, drum radius, worm '
            'ratio, pulley advantage — every prior naming the '
            'measurement that retires it.')]),
     'is_prior': True, 'provenance_id': PROV, 'notes': ''},
    {'name': 'view-m2-materials-sourcing',
     'display_name': 'M2 — materials & sourcing',
     'discipline': 'materials', 'scale_support': 'm0-only',
     'description': 'the first ACTIVE MAGNET above M0: a role '
                    'that refuses soft materials outright, and a '
                    'make-or-buy that is a route, not a '
                    'construction',
     'sections_json': _j([
         _s('role-screen', 'role-screen',
            'THE M2 DECISION: the rotor ring is '
            'torque-magnet-active, the role that refuses a soft '
            'material outright (the mag-2r predicate that once '
            'caught a proposed COPPER magnet). What passes is '
            'what we can press and sinter, or buy.',
            args={'part_name': 'm2-magnet-ring'}),
         _s('accountability-chain', 'materials-accountability',
            'Part -> option -> per-value provenance -> dated '
            'citations -> make-vs-buy, for every M2 material. '
            'The magnet is where the chain has a real gap, and '
            'it says so.'),
         _s('sourcing-routes', 'sourcing-routes',
            'The complete hoist-drive product, twice (m2-6): '
            'pure-local vs commercial, differing on THE MAGNET '
            'and NOT on the stator, because the stator is M1\'s '
            'and already routed. That is the ladder paying off.',
            links=[{'label': 'Business start', 'kind': 'page',
                    'route': '/business/start'}]),
         _s('m2-relations', 'm2-relations',
            'And the dimensional agreement underneath all of it: '
            'the magnet thickness the sourcing quotes is the '
            'same number the solver drives the MMF from.')]),
     'is_prior': True, 'provenance_id': PROV, 'notes': ''},
    {'name': 'view-m2-lift',
     'display_name': 'M2 — lifting (the product)',
     'discipline': 'mechanical', 'scale_support': 'm0-only',
     'description': 'M2\'s product is LIFT: a crucible off the '
                    'floor through a self-locking worm — and '
                    'still up there with the power off',
     'sections_json': _j([
         _s('m2-hoist-requirements', 'm2-hoist-requirements',
            'The crucible hoist as rows: mass, drum radius, worm '
            'ratio and its efficiency, pulley advantage, lift '
            'speed. The worm ratio and the self-locking claim '
            'are the SAME physics — a worm is lossy, and that is '
            'why it holds.'),
         _s('m2-lift-proof', 'm2-lift-proof',
            'THE proof this rung exists for: put the hoist duty '
            'on the motor and ask whether it stays in step. The '
            'motor-side torque demand is computed TWO ways — '
            'through the chain of ratios and through the power '
            'balance — and they must agree exactly. Then the '
            'answer that matters at 1200 C: with the power off, '
            'the load does not come down, and the reason is the '
            'WORM\'s geometry, never the motor\'s cogging.'),
         _s('rotation-under-load', 'm2-rotation',
            'The same solver the proof drives and the 3D scene '
            'replays — one engine, three consumers, no copies.',
            links=_M2_SCENE_LINK)]),
     'is_prior': True, 'provenance_id': PROV, 'notes': ''},
]

# viz-1 discipline: a view must decide its 3D scene deliberately —
# m2-3's m2_scene owns the M2 base + layers + defaultOn.
from motors.m2_scene_seed import m2_scene_json_for_view  # noqa: E402

for _view_seed in SEED_M2_VIEWS:
    _view_seed['scene_json'] = m2_scene_json_for_view(
        _view_seed['name'])


def seed_m2_views(manager):
    return upsert_seed_pairs(manager, [
        ('ClockViewDefinition', ClockViewDefinition,
         SEED_M2_VIEWS),
    ], tag='M2ViewsSeed')
