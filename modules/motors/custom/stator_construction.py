"""
@module motors.custom.stator_construction

mag-26: STATOR CONSTRUCTION VARIANTS — the worked example of the
part-composition model, and the case that settles whether PROMOTION
can be partial.

Dustin 2026-07-31: "variations like having a direct spool with just
an enameled wire over a spool (simple stator) vs a bound stator
(wire put on a spool and covered by sol-gel or another covering) and
layered bound stators, where we have grooves the wire is layed into
at each level and it is covered by sol-gel to keep it in place and
then layered again on another grooved spool concentric circle layer
that snaps on."

Three constructions of the SAME functional part, and they are not a
difficulty ranking — they sit at different points on separability,
and the third one answers an open question from
PART_COMPOSITION_HANDOVER.md §5.2: promotion is NOT all-or-nothing.
A layered bound stator is internally promoted PER LAYER (wire into
sol-gel, irreversible) while the layers themselves remain SEPARABLE
(they snap). One object, mixed separability, so promotion has to
attach to a NAMED INTERFACE SET rather than to a whole assembly.

WHAT THE LAYERING IS ACTUALLY FOR, since it is easy to read as mere
tidiness: FILL FACTOR. Grooves force each turn into a defined
position, and ordered packing beats scramble winding — the close
packed ceiling is pi/(2*sqrt(3)) = 0.907 against roughly 0.60 for
scramble. Fill enters the mag-25 equations directly (turns =
f*W/A_wound), so a better fill is either more turns in the same coil
or the same turns in a smaller one.

AND THE CATCH, which is the same square-law that ruled out cotton
covering in mag-24: the groove WALLS consume window. Ordered packing
only wins if the walls are thin relative to the wire, and at fine
gauge they cannot be. The crossover is sharp and it is derived, not
asserted — see groove_viability().

@consumers motors.motor_api, motors.motors_selftest
"""

import math

# arch-3 (PART_ARCHETYPES_PLAN §3.3): fill is a property of the
# CONSTRUCTION, so the packing geometry moved DOWN into composition
# (same extraction as part_roles). Re-exported here so existing
# imports keep working.
from composition.custom.fill_models import (  # noqa: F401 — re-exports
    CLOSE_PACKED_CEILING, SCRAMBLE_FILL, groove_viability,
)

PROV = 'mag-26'

#: The three constructions. `promotedInterfaces` is the field that
#: matters: it names WHICH interfaces the process fuses, leaving the
#: rest separable.
VARIANTS = [
    {
        'name': 'stator-simple',
        'display_name': 'Simple — enamelled wire on a spool',
        'level': 'assembly',
        'promotedInterfaces': [],
        'separable': ['wire from spool'],
        'fillModel': 'scramble',
        'repairable': True,
        'process': ['wind'],
        'processCount': 1,
        'gains': [],
        'losses': [],
        'failureModesPresent': [
            'turn-to-turn FRETTING — the wire can move, and a clock '
            'runs 3.2e8 cycles',
            'enamel abrasion at crossovers, which is a turn-to-turn '
            'short',
            'the winding carries no load, so the bobbin flanges '
            'must carry all of it',
        ],
        'why': 'the honest baseline: one operation, no chemistry '
               'after winding, and you can unwind it to recover the '
               'wire. Everything below is measured against this.',
    },
    {
        'name': 'stator-bound',
        'display_name': 'Bound — wound, then sol-gel or varnish over',
        'level': 'part (promoted from assembly)',
        'promotedInterfaces': ['wire-to-wire', 'wire-to-spool'],
        'separable': [],
        'fillModel': 'scramble',
        'repairable': False,
        'process': ['wind', 'impregnate', 'cure'],
        'processCount': 3,
        'gains': [
            'wire CANNOT move — fretting and crossover abrasion are '
            'deleted outright, not reduced',
            'the coil becomes STRUCTURAL, so the bobbin no longer '
            'has to carry the winding alone and its flanges can be '
            'thinner — which gives back some of the window the '
            'coating cost',
            'a continuous solid conducts heat better than the air '
            'gaps of a loose winding (marginal for us: this coil '
            'dissipates ~12 mW)',
        ],
        'losses': [
            'REPAIRABILITY. The wire is not recoverable, so the '
            'whole cost amortises over one life — a lifecycle_cost '
            'term, not a footnote',
            'a BULK failure mode replaces the interface ones: '
            'sol-gel silica is BRITTLE (mag-24), and a crack in a '
            'potted winding is a short',
        ],
        'failureModesPresent': [
            'crack propagation through the potting compound',
            'cure shrinkage stressing the winding',
            'thermal expansion mismatch, now internal stress rather '
            'than clearance',
        ],
        'why': 'THE canonical promotion: an assembly processed '
               'irreversibly into a part. It trades interface '
               'failure modes for bulk ones and spends '
               'repairability to do it.',
    },
    {
        'name': 'stator-layered-bound',
        'display_name': 'Layered bound — grooved layers, bound per '
                        'layer, snapped concentrically',
        'level': 'part with SEPARABLE sub-parts',
        'promotedInterfaces': ['wire-to-groove (within each layer)'],
        'separable': ['layer from layer (snap fit)'],
        'fillModel': 'ordered',
        'repairable': False,
        'processCount': 4,
        'process': ['form grooved layer', 'lay wire into grooves',
                    'impregnate + cure', 'snap on next layer'],
        'gains': [
            'ORDERED PACKING. Grooves fix each turn, so fill can '
            'approach the close-packed ceiling instead of scramble '
            '— and fill is a direct multiplier on turns, hence on '
            'battery life',
            'a KNOWN mean turn length per layer, so resistance is '
            'predicted rather than estimated',
            'inter-layer insulation is a designed feature, which '
            'matters for any higher-voltage descendant of this '
            'design (not for a clock at under a volt)',
            'layers are separately made and separately inspectable '
            '— a defective layer is discarded, not a whole coil',
        ],
        'losses': [
            'the grooves must be MADE, at a pitch near the wire '
            'diameter — a mould feature, not a machining one, at '
            'our sizes',
            'groove WALLS consume window, and this is the whole '
            'trade (see groove_viability)',
            'four process steps per layer instead of one',
        ],
        'failureModesPresent': [
            'SNAP FIT IN A BRITTLE MATERIAL. A snap needs elastic '
            'deflection to engage; fired ceramic and geopolymer are '
            'brittle and will crack instead of flexing. This is a '
            'genuine conflict with the field-inert ceramic the '
            'spool otherwise wants, and it is not resolved here.',
            'per-layer bond failure at the snap interface',
        ],
        'why': 'the case that proves promotion is PARTIAL: wire is '
               'fused into each layer irreversibly, while the '
               'layers stay separable. One object, two '
               'separability regimes.',
    },
]

_BY_NAME = {v['name']: v for v in VARIANTS}


def variant_catalog():
    """The three constructions, with what each promotion costs."""
    return {
        'ok': True, 'variants': VARIANTS, 'count': len(VARIANTS),
        'separabilityIsTheAxis': (
            'these are not a difficulty ranking. They sit at '
            'different points on SEPARABILITY: simple is an '
            'assembly, bound is a part promoted from one, and '
            'layered-bound is a part whose sub-parts remain '
            'separable while their contents do not.'),
        'partialPromotionFinding': (
            'the layered variant settles an open question: promotion '
            'is NOT all-or-nothing. Wire is fused into each layer '
            'irreversibly while the layers themselves snap apart, so '
            'promotion must attach to a NAMED INTERFACE SET rather '
            'than to a whole assembly.'),
        'provenance': PROV,
    }


def compare_variants(manager=None, awg=32, wall_mm=0.03,
                     window_mm2=606.0, mmf=21.45, nested=False):
    """Run all three through the mag-25 winding relations, so the
    comparison is in turns and years rather than adjectives."""
    from motors.custom.simple_first import (
        AWG_MM, ENAMEL_MM, coil_voltage,
    )
    if awg not in AWG_MM:
        return {'ok': False,
                'refusal': f'no wire table entry for {awg} AWG — '
                           f'one of {sorted(AWG_MM)}'}
    d_wound = AWG_MM[awg] + ENAMEL_MM
    a_wound = math.pi * (d_wound / 2.0) ** 2
    groove = groove_viability(d_wound, wall_mm, nested=nested)
    nested_alt = groove_viability(d_wound, wall_mm,
                                  nested=not nested)
    volts = coil_voltage(mmf, awg)
    rows = []
    for v in VARIANTS:
        fill = (groove['orderedFill'] if v['fillModel'] == 'ordered'
                else SCRAMBLE_FILL)
        turns = fill * window_mm2 / a_wound
        amps = mmf / turns if turns else None
        avg_ma = amps * 1000.0 * 0.030 if amps else None
        rows.append({
            'variant': v['name'],
            'displayName': v['display_name'],
            'level': v['level'],
            'fillModel': v['fillModel'], 'fill': round(fill, 4),
            'turns': round(turns),
            'averageCurrentMa': round(avg_ma, 5) if avg_ma else None,
            'aaYears': round(2500.0 / avg_ma / 24 / 365, 2)
            if avg_ma else None,
            'processSteps': v['processCount'],
            'repairable': v['repairable'],
            'promotedInterfaces': v['promotedInterfaces'],
        })
    best = max(rows, key=lambda r: r['turns'])
    simple = rows[0]
    return {
        'ok': True, 'awg': awg, 'wallMm': wall_mm,
        'windowMm2': window_mm2, 'coilVoltageV': round(volts, 3),
        'groove': groove, 'nestedAlternative': nested_alt,
        'nestingCostsThisMuch': round(
            abs(nested_alt['orderedFill'] - groove['orderedFill'])
            / groove['orderedFill'], 3),
        'rows': rows,
        'finding': (
            f'at {awg} AWG with a {wall_mm * 1000:.0f} um groove '
            f'wall, the layered variant reaches fill '
            f'{groove["orderedFill"]} against scramble '
            f'{SCRAMBLE_FILL} — {groove["gainVsScramble"]}x the '
            f'turns, so {best["aaYears"]} years against '
            f'{simple["aaYears"]}. It costs '
            f'{best["processSteps"]} process steps per layer '
            f'instead of {simple["processSteps"]}, and the '
            f'repairability of all three is already gone by the '
            f'second variant.'
            if groove['beatsScramble'] else
            f'at {awg} AWG a {wall_mm * 1000:.0f} um groove wall '
            f'gives fill {groove["orderedFill"]}, WORSE than '
            f'scramble at {SCRAMBLE_FILL}. The walls cost more '
            f'window than the ordering gains. Grooving is not '
            f'justified at this gauge and wall thickness — go '
            f'coarser or make thinner walls.'),
        'snapOnVerdict': (
            f'the SNAP-ON construction specifically costs '
            f'{round(abs(nested_alt["orderedFill"] - groove["orderedFill"]) / groove["orderedFill"] * 100)}% '
            f'of the fill a NESTED ordered winding would reach, '
            f'because a layer that snaps on is a rigid floor and '
            f'rigid floors forbid nesting. Choose it for '
            f'PER-LAYER INSPECTABILITY and yield — a defective '
            f'layer is discarded instead of a whole coil — not for '
            f'packing. If packing is the goal, offset the grooves '
            f'and let the layers nest instead of snapping.'),
        'convergence': (
            'grooving pays at COARSE gauge and loses at fine, '
            'because the wall is a fixed thickness against a '
            'shrinking wire. mag-25 already pointed at coarse gauge '
            'for an entirely different reason — a cell cannot supply '
            'the voltage fine wire needs. Two independent arguments '
            'landing in the same design region is worth more than '
            'either alone.'),
        'provenance': PROV,
    }
