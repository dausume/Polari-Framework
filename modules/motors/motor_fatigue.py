"""
@module motors.motor_fatigue

mag-16: FATIGUE, and what to make the part out of instead.

The static check (mag-15) asks "does one load break it". A clock
asks a different question: it steps ONCE PER SECOND — 31.6 million
cycles a year — so the real question is whether the part survives
being loaded 3.2e8 times.

TWO MODELS, because the physics genuinely differs by class and
using the metal one on a ceramic is the same category of error as
using von Mises on it:

  ductile-endurance-limit      steel: below ~0.45 UTS life is
                               effectively infinite. A real limit.
  ductile-no-endurance-limit   copper/aluminium: NO limit — the
                               S-N curve keeps falling, so "it
                               survived 10^7" is not a promise.
  brittle-scg                  ceramics and cast geopolymers have
                               NO metal-style endurance limit at
                               all. They fail by SUBCRITICAL CRACK
                               GROWTH: a flaw grows slowly under
                               load until it reaches critical size.
                               Allowable stress falls as
                                   sigma(N) = sigma_static * N^(-1/n)
                               with n the crack-growth exponent —
                               and LOW n (cements ~15) is much
                               worse than high n (alumina ~45).

AND FOR BRITTLE MATERIALS, A SECOND DERATE THAT IS NOT OPTIONAL:
strength is WEIBULL-DISTRIBUTED. A brittle part fails from its
worst flaw, not its mean strength, so a design targets a SURVIVAL
PROBABILITY:
    sigma_design = sigma_char * (-ln(P_survive))^(1/m)
Low Weibull modulus m = wide scatter = large derate. Our cast
geopolymers are m~7-8; alumina is m~15.

The two derates MULTIPLY, and for a cast geopolymer over 10 years
of clock duty they remove ~85% of the strength. That is the finding
this module exists to make visible, and it changes the answer the
static check gave.

substitution_search() then answers the question that follows: if
this part cannot survive, what should it be made of? It ranks every
catalog material by whether it clears BOTH checks, and it is
allowed to conclude BUY IT — which is exactly what real clocks do
with pinions.

@consumers motors.motor_api, motors.selftest_motors
"""

import math

from magnetics.magnet_analysis import _named, _rows
from motors.motor_stress import (
    DEFAULT_SAFETY_FACTOR, _prop, failure_criterion,
)

SECONDS_PER_YEAR = 365.25 * 24 * 3600
#: Survival probability a design targets. 0.99 = one part in a
#: hundred is expected to fail — state it, because for brittle
#: materials there is no such thing as "safe", only a probability.
DEFAULT_SURVIVAL = 0.99

FATIGUE_VALIDITY = (
    'Fatigue by MATERIAL CLASS from literature-est parameters, not '
    'from testing: no S-N curve has been measured for any of our '
    'castings. Subcritical crack growth assumes a constant-amplitude '
    'load and an inert environment — MOISTURE accelerates crack '
    'growth in silicates sharply (that is stress-corrosion, and a '
    'clock lives in room air), so the real n is likely WORSE than '
    'the value used. Not modelled: crack initiation from casting '
    'voids, thermal cycling, and the fact that a single dropped '
    'part fails at once regardless of any of this.')


def cycles_for(manager, design_name, years=10.0):
    """How many load cycles the design's own drive rate implies."""
    design = _named(manager, 'MotorDesignDefinition', design_name)
    if design is None:
        return None
    import json
    try:
        drive = json.loads(getattr(design, 'drive_json', '') or '{}')
    except (TypeError, ValueError):
        drive = {}
    rate = float(drive.get('rate_hz', 0) or 0)
    if rate <= 0:
        return None
    return rate * SECONDS_PER_YEAR * float(years)


def fatigue_derate(manager, material, cycles,
                   survival=DEFAULT_SURVIVAL):
    """The fraction of static strength that survives `cycles`, and
    WHY — the two derates reported separately so neither hides."""
    crit = failure_criterion(manager, material)
    if not crit.get('ok'):
        return crit
    fclass, prov = _prop(manager, material, 'fatigue_class')
    if fclass is None:
        return {'ok': False,
                'refusal': f'"{material}" states no fatigue_class — '
                           f'a metal S-N model and a ceramic '
                           f'crack-growth model give different '
                           f'answers by a factor of several, so '
                           f'guessing is not acceptable',
                'suggestion': {
                    'knob': 'MagneticMaterialOption.properties_json',
                    'action': 'add fatigue_class + scg_exponent_n '
                              '(brittle) or endurance_limit_ratio '
                              '(ductile)'}}
    cycles = max(float(cycles or 1.0), 1.0)
    notes = []
    scg_factor = 1.0
    weibull_factor = 1.0

    if fclass == 'brittle-scg':
        n, _ = _prop(manager, material, 'scg_exponent_n')
        m, _ = _prop(manager, material, 'weibull_modulus')
        if not n:
            return {'ok': False,
                    'refusal': f'"{material}" is brittle-scg but '
                               f'states no scg_exponent_n'}
        scg_factor = cycles ** (-1.0 / float(n))
        notes.append(
            f'subcritical crack growth: allowable = strength x '
            f'N^(-1/n) with n={n} over {cycles:.3g} cycles => '
            f'{scg_factor:.3f}x. There is NO endurance limit here — '
            f'this keeps falling for as long as the clock runs.')
        if m:
            weibull_factor = (-math.log(float(survival))) ** (
                1.0 / float(m))
            notes.append(
                f'Weibull scatter: m={m} means a {survival:.0%} '
                f'survival target costs another {weibull_factor:.3f}'
                f'x — a brittle part fails from its WORST flaw, not '
                f'its mean strength.')
    elif fclass == 'ductile-endurance-limit':
        ratio, _ = _prop(manager, material, 'endurance_limit_ratio')
        scg_factor = float(ratio or 0.45)
        notes.append(
            f'true endurance limit at {scg_factor:.2f}x UTS: below '
            f'it, life is effectively infinite regardless of cycle '
            f'count.')
    else:                       # ductile-no-endurance-limit
        # No limit: use a conservative high-cycle knock-down. Copper
        # at 1e8 cycles runs roughly a third of UTS.
        scg_factor = 0.33
        notes.append(
            'NO endurance limit: the S-N curve keeps falling, so '
            'surviving 1e7 cycles is not a promise about 1e9. A '
            'conservative 0.33x high-cycle knock-down is used and '
            'it is a PRIOR, not a measurement.')

    total = scg_factor * weibull_factor
    return {
        'ok': True, 'material': material, 'fatigueClass': fclass,
        'provenance': prov, 'cycles': cycles,
        'survivalTarget': survival,
        'scgOrEnduranceFactor': round(scg_factor, 4),
        'weibullFactor': round(weibull_factor, 4),
        'totalDerate': round(total, 4),
        'strengthMpa': crit['tensileMpa'],
        'allowableMpa': (round(crit['tensileMpa'] * total, 4)
                         if crit['tensileMpa'] else None),
        'why': ' '.join(notes),
        'validity': FATIGUE_VALIDITY,
    }


def part_fatigue(manager, design_name, part_name, years=10.0,
                 survival=DEFAULT_SURVIVAL,
                 required_sf=DEFAULT_SAFETY_FACTOR, **stress_kw):
    """Static stress from mag-15, re-judged against the FATIGUE
    allowable instead of the static strength."""
    from motors.motor_stress import part_stress
    st = part_stress(manager, design_name, part_name, **stress_kw)
    if not st.get('ok'):
        return st
    cycles = cycles_for(manager, design_name, years=years)
    if cycles is None:
        return {'ok': False,
                'refusal': f'"{design_name}" states no drive rate — '
                           f'no cycle count, so no fatigue life'}
    de = fatigue_derate(manager, st['material'], cycles,
                        survival=survival)
    if not de.get('ok'):
        return de
    judged_mpa = st['stress']['judgedPa'] / 1e6
    allow = de['allowableMpa']
    sf = (allow / judged_mpa) if (allow and judged_mpa) else None
    passes = sf is not None and sf >= required_sf
    return {
        'ok': True, 'design': design_name, 'part': part_name,
        'material': st['material'], 'years': years,
        'cycles': cycles, 'criterion': st['criterion'],
        'staticSafetyFactor': st['safetyFactor'],
        'fatigueSafetyFactor': (round(sf, 2) if sf else None),
        'requiredSafetyFactor': required_sf,
        'derate': de, 'stressMpa': round(judged_mpa, 5),
        'allowableMpa': allow,
        'passes': passes,
        'verdict': (
            f'{"SURVIVES" if passes else "FAILS FATIGUE"}: '
            f'{cycles:.3g} cycles over {years:g} years derates the '
            f'{de["strengthMpa"]} MPa strength to {allow} MPa, so '
            f'the safety factor falls from '
            f'{st["safetyFactor"]} (static) to '
            f'{round(sf, 2) if sf else "n/a"} — against the '
            f'{required_sf} required'),
        'validity': FATIGUE_VALIDITY,
    }


def substitution_search(manager, design_name, part_name,
                        years=10.0, survival=DEFAULT_SURVIVAL,
                        required_sf=DEFAULT_SAFETY_FACTOR,
                        **stress_kw):
    """If the part cannot survive, WHAT SHOULD IT BE MADE OF?

    Re-runs the fatigue check against every catalog material,
    keeping the part's geometry and load fixed so only the material
    changes. Ranked by fatigue safety factor. Allowed to conclude
    that nothing castable works and the part should be BOUGHT —
    which is what real clocks do with pinions."""
    part = _named(manager, 'MotorPartDefinition', part_name)
    if part is None:
        return {'ok': False,
                'refusal': f'no MotorPartDefinition named '
                           f'"{part_name}"'}
    current = getattr(part, 'material_ref', '')
    original = current
    results, skipped = [], []
    for opt in _rows(manager, 'MagneticMaterialOption'):
        name = getattr(opt, 'name', '')
        try:
            part.material_ref = name
            r = part_fatigue(manager, design_name, part_name,
                             years=years, survival=survival,
                             required_sf=required_sf, **stress_kw)
        except Exception as exc:            # noqa: BLE001
            skipped.append({'material': name, 'reason': str(exc)})
            continue
        finally:
            part.material_ref = original
        if not r.get('ok'):
            skipped.append({'material': name,
                            'reason': r.get('refusal', '')[:120]})
            continue
        results.append({
            'material': name,
            'displayName': getattr(opt, 'display_name', ''),
            'realizationLevel': getattr(opt, 'realization_level',
                                        ''),
            'referenceOnly': bool(getattr(opt, 'reference_only',
                                          False)),
            'fatigueSafetyFactor': r['fatigueSafetyFactor'],
            'staticSafetyFactor': r['staticSafetyFactor'],
            'fatigueClass': r['derate']['fatigueClass'],
            'totalDerate': r['derate']['totalDerate'],
            'passes': r['passes'],
            'isCurrent': name == original,
        })
    results.sort(key=lambda x: -(x['fatigueSafetyFactor'] or 0))
    viable = [x for x in results if x['passes']]
    makeable = [x for x in viable
                if x['realizationLevel'] in ('recipe-seeded',
                                             'made-and-measured')]
    return {
        'ok': True, 'design': design_name, 'part': part_name,
        'currentMaterial': original, 'years': years,
        'candidates': results, 'count': len(results),
        'viableCount': len(viable),
        'best': (results[0] if results else None),
        'bestMakeable': (makeable[0] if makeable else None),
        'skipped': skipped,
        'recommendation': (
            f'nothing in the catalog clears {required_sf}x on '
            f'fatigue for this part — the honest move is to BUY it '
            f'(a steel or brass pinion, which is exactly what real '
            f'clock movements use) or to change the DESIGN: a '
            f'bigger tooth, a lower handling load, or a part that '
            f'is not asked to carry this stress'
            if not viable else
            f'"{viable[0]["material"]}" clears it at '
            f'{viable[0]["fatigueSafetyFactor"]}x'
            + ('' if makeable else
               ' — but nothing MAKEABLE does, so this is a '
               'buy-it-or-redesign answer, not a recipe')),
        'honesty': 'geometry and load are held FIXED — only the '
                   'material changes, so this compares materials '
                   'and not designs. A part that fails every '
                   'material is telling you the DESIGN is wrong, '
                   'not the shelf.',
        'validity': FATIGUE_VALIDITY,
    }
