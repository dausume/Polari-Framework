"""
@module motors.part_roles

mag-17: ACTIVE MECHANICAL ROLES — what a part DOES decides what it
must survive (Dustin 2026-07-30: "different parts perform different
kinds of generic active roles ... almost all moving parts we need to
account for almost all kinds of stresses and fatigues ... a
colliding part like a gear that hits another gear would be another
role ... being a mechanical part in a magnetic motor you need to try
and not interact with the magnetic or electric fields").

This is mag-2r's role taxonomy extended from MAGNETIC roles to
ACTIVE MECHANICAL ones, and it closes a real hole the fatigue work
exposed: substitution_search ranked materials by fatigue alone and
happily proposed a COPPER pinion — which passes fatigue and would
then wear away, and which is conductive so it would drag eddy
currents through the very gap it sits in. Fatigue was the only
question being asked. It is not the only question.

THE MODEL: a part declares the roles it ACTIVELY performs. Each role
brings REQUIRED PROPERTIES and PREDICATES. A material is viable for
the part only if it satisfies the UNION of its roles — and a
property nobody has measured makes the answer UNASSESSED, never a
pass. Same discipline as mag-2r: viability is DERIVED, never
stamped.

THE ROLES, and why each exists:

  moving          it accelerates and reverses, so it sees the whole
                  stress catalogue AND fatigue — Dustin's point
                  that almost all moving parts need almost all of
                  it. Requires a fatigue class.
  colliding       tooth strikes tooth. This is CONTACT stress
                  (Hertzian), not bending: the load lives in a tiny
                  patch and the surface fails before the body does.
                  Requires hardness. Softness here is the copper
                  pinion's second disqualification.
  field-transparent  a mechanical part inside a magnetic machine
                  must NOT participate. High mu steals flux from
                  the working gap; high sigma carries EDDY CURRENTS
                  that both drag and heat. Requires LOW mu_r AND
                  LOW sigma — and copper fails on sigma by ~13
                  orders of magnitude.
  sliding         rubs against another surface: wear and friction,
                  not strength, decide its life.
  press-fitted    assembled by force — and mag-15 found assembly is
                  what governs a clock-scale part, so this role
                  carries the handling load explicitly.
  static-structural  holds position and takes load without moving:
                  the ONE role that does not need fatigue data.

@consumers motors.motor_api, motors.motor_fatigue,
           motors.selftest_motors
"""

from magnetics.magnet_analysis import _named, _rows
# arch-2 (PART_ARCHETYPES_PLAN §3.3): the generic role engine moved
# DOWN into composition — motors consumes composition, never the
# reverse. Re-exported here so every existing import keeps working.
from composition.part_roles import (  # noqa: F401 — re-exports
    DOMAINS, ROLE_REQUIREMENTS, _check, role_viability,
)

#: Which roles each seeded Lavet part actually performs. This is
#: the join that was missing: the pinion is not merely "a part", it
#: is moving AND colliding AND field-transparent AND press-fitted,
#: and it must satisfy all four.
PART_ROLE_ASSIGNMENTS = {
    'lavet-v2-stator': ['static-structural',
                        'flux-carrying'],
    # The magnetic role was MISSING here, and its absence let a
    # search propose a COPPER rotor magnet — copper passed because
    # nothing was checking that a magnet must be magnetic.
    'lavet-v2-rotor-magnet': ['moving', 'press-fitted',
                              'torque-magnet-active'],
    # The pinion is mechanical FIRST and field-isolated by
    # GEOMETRY (it sits above the plate, clear of the gap) — the
    # intersectional case, and it must STATE its buffer.
    'lavet-v2-pinion': ['moving', 'colliding', 'field-buffered',
                        'press-fitted'],
    'lavet-v2-bobbin-flanges': ['static-structural',
                                'field-inert'],
    'lavet-v2-coil': ['static-structural',
                      'current-carrying'],
    'lavet-v2-leads': ['static-structural'],
}

def part_role_report(manager, part_name):
    """What this part DOES, what that demands, and whether its
    current material meets it."""
    part = _named(manager, 'MotorPartDefinition', part_name)
    if part is None:
        return {'ok': False,
                'refusal': f'no MotorPartDefinition named '
                           f'"{part_name}"'}
    roles = PART_ROLE_ASSIGNMENTS.get(part_name)
    if roles is None:
        return {'ok': False,
                'refusal': f'"{part_name}" has no active roles '
                           f'assigned — what a part DOES is what '
                           f'decides what it must survive, so this '
                           f'refuses rather than assuming',
                'suggestion': {'knob': 'PART_ROLE_ASSIGNMENTS',
                               'action': 'declare its roles'}}
    material = getattr(part, 'material_ref', '')
    via = role_viability(manager, material, roles,
                         part_row=part)
    return {
        'ok': True, 'part': part_name, 'material': material,
        'roles': [{'role': r,
                   'domain': ROLE_REQUIREMENTS[r].get('domain', ''),
                   'summary': ROLE_REQUIREMENTS[r]['summary'],
                   'analyses': ROLE_REQUIREMENTS[r]['analyses']}
                  for r in roles if r in ROLE_REQUIREMENTS],
        'viability': via,
        'honesty': 'a part is judged against the UNION of its '
                   'roles. Ranking candidates on ONE axis (fatigue) '
                   'is what proposed a copper pinion: it passes '
                   'fatigue, then wears away as a tooth face and '
                   'drags eddy currents through the gap it sits '
                   'in.',
    }


def screen_candidates(manager, part_name, candidates=None):
    """Filter a material list by the part's ROLES — the missing
    gate on substitution_search."""
    part = _named(manager, 'MotorPartDefinition', part_name)
    if part is None:
        return {'ok': False,
                'refusal': f'no MotorPartDefinition named '
                           f'"{part_name}"'}
    roles = PART_ROLE_ASSIGNMENTS.get(part_name, [])
    if not roles:
        return {'ok': False,
                'refusal': f'"{part_name}" has no active roles — '
                           f'nothing to screen against'}
    names = candidates or [getattr(o, 'name', '')
                           for o in _rows(manager,
                                          'MagneticMaterialOption')]
    out = []
    for n in names:
        v = role_viability(manager, n, roles, part_row=part)
        out.append({'material': n, 'verdict': v['verdict'],
                    'failedOn': v['failedOn'],
                    'unassessedOn': v['unassessedOn']})
    viable = [o for o in out if o['verdict'] == 'viable']
    return {
        'ok': True, 'part': part_name, 'roles': roles,
        'screened': out, 'count': len(out),
        'viable': [o['material'] for o in viable],
        'viableCount': len(viable),
        'note': 'run this BEFORE ranking by fatigue: a material '
                'that fails a role is not a candidate however good '
                'its fatigue number is.',
    }
