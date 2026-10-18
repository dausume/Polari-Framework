"""
@module cmod.custom.fsc_terms

fsc-0 (FIRMWARE_SCORE_PROFILES_PLAN.md section 4): the Firmware Score TERMS, seeded as `scoring.ScoreTerm` rows (category `firmware`) - no new score class. One term is one
measurable quantity of a solution (a Mission Solution, or a built Firmware Solution), with a direction (`is_positive`) and an EXPLICIT normalization:
  COMPETITIVE (his ruling 2026-10-18, plan 10b): every term is {"method": "min-max-auto"} over the compared set - the best solution on a term gets 100, the worst 0, the rest
  linearly between, direction from is_positive. Chip limits are NOT bounds; they stay in the basis text. The ONE exception is the stated "sol-0-compatible" mode of a profile
  (ABS_BOUNDS below), which feeds sol-0's raw fractions so today's ranking is reproduced exactly; it is never the default.

Every number a value carries has a KIND (measured | estimated | cited | stand-in) and a BASIS in words. A value nobody could determine is scored at a STATED stand-in, never zero.
The KNOBS below are knobs, not rulings; each is stated where it is used.
"""
import json

CATEGORY = 'firmware'
KINDS = ('measured', 'cited', 'estimated', 'stand-in')
#: how much a value of each kind counts toward the `confidence` term (measured/cited are evidence, an estimate is half, a stand-in none)
KIND_CONFIDENCE = {'measured': 1.0, 'cited': 1.0, 'estimated': 0.5, 'stand-in': 0.0}
#: D-fsc-5 knobs: a shared route's cost and time are split across the Purposes that use it, in proportion to these importance weights
IMPORTANCE_WEIGHTS = {'safety': 4.0, 'required': 3.0, 'important': 2.0, 'desired': 1.0}
#: D-fsc-1 knob: deadline-fit = 100 x min(1, budget / cycle) ** DEADLINE_EXPONENT (100 at or under budget; 1.0 = falls in proportion to the overrun)
DEADLINE_EXPONENT = 1.0
#: D-fsc-2 knobs (default yes, per profile): accept used offers, accept local (brick-and-mortar chain list price) offers
PRICE_KNOBS = {'accept_used': True, 'accept_local': True}
#: a value no one has (absent for a solution) is scored at this normalized midpoint, stated on the breakdown row - never zero
ABSENT_NORMALIZED = 0.5

AUTO = json.dumps({'method': 'min-max-auto'})
ABS_PCT = ABS_PARTS = AUTO      # competitive: no absolute bounds on a term row
#: sol-0-compatible mode only: the natural bounds of the terms sol-0's equation uses (fractions of what the chip has), so its raw weighted sum is reproduced
ABS_BOUNDS = {'pins-free': (0, 100), 'blocks-free': (0, 100), 'flash-free': (0, 100), 'ram-free': (0, 100), 'cpu-idle': (0, 100), 'parts-to-acquire': (0, 10), 'part-count': (0, 10)}
NORMALIZATIONS = ('competitive', 'sol-0-compatible')

# name, display, plain words, unit, value_type, is_positive, normalization, group, undetermined_now
_T = [
    ('bom-cost', 'Cost of everything', 'Money for every part the solution needs, the board included: the cheapest cited offer the profile accepts for each part class.', 'USD', 'currency', False, AUTO, 'cost'),
    ('cost-to-build-now', 'Cost to build now', 'Money for the parts the bench does NOT have yet (the board itself is already here): cited offers x the parts missing.', 'USD', 'currency', False, AUTO, 'cost'),
    ('parts-to-acquire', 'Parts to get', 'How many part classes the bench lacks for this solution (each counts one whole unit; 0 to 10 scale).', 'parts', 'count', False, ABS_PARTS, 'cost'),
    ('mission-cycle', 'Mission cycle time', 'One pass through every Purpose of the Mission, from each trigger to its last task, in microseconds.', 'us', 'custom', False, AUTO, 'speed'),
    ('worst-purpose-latency', 'Slowest Purpose', 'The longest single Purpose cycle (trigger to last task); in a Purpose context, that Purpose own cycle.', 'us', 'custom', False, AUTO, 'speed'),
    ('deadline-fit', 'Deadline fit', 'How well the stated deadline is met: 100 at or under the budget, falling as budget / cycle when over it (the curve exponent is a knob).', 'points', 'score', True, ABS_PCT, 'speed'),
    ('boot-to-ready', 'Boot to ready', 'Microseconds from reset until the initialization Purpose is done.', 'us', 'custom', False, AUTO, 'speed'),
    ('route-time', 'Route work time', 'Microseconds of route work (the atoms the routes run) attributed to a Purpose; a route two Purposes share is split by importance weight.', 'us', 'custom', False, AUTO, 'speed'),
    ('flash-free', 'Flash left', 'Percent of the chip flash still free after this solution (measured atom sizes where they exist, else labelled estimates).', '%', 'percentage', True, ABS_PCT, 'headroom'),
    ('ram-free', 'RAM left', 'Percent of the chip RAM still free after this solution.', '%', 'percentage', True, ABS_PCT, 'headroom'),
    ('pins-free', 'Pins left', 'Percent of the header pins this solution leaves unused.', '%', 'percentage', True, ABS_PCT, 'headroom'),
    ('blocks-free', 'Chip blocks left', 'Percent of the nine on-chip block kinds this solution leaves unclaimed.', '%', 'percentage', True, ABS_PCT, 'headroom'),
    ('cpu-idle', 'CPU left', 'One minus the CPU load class (0 hardware does the work .. 4 busy in a bit-timed exchange), as a percent.', '%', 'percentage', True, ABS_PCT, 'headroom'),
    ('active-current', 'Running current', 'Current drawn while running, in mA: datasheet-cited per block plus the LED. UNDETERMINED until figures are cited.', 'mA', 'custom', False, AUTO, 'power'),
    ('sleep-capable', 'Can sleep', 'Percent of the Purpose triggers that are interrupt or event driven, so the chip could sleep between them (polled = no).', '%', 'percentage', True, ABS_PCT, 'power'),
    ('risk-points', 'Open risks', 'Ladder rungs left unchecked or conditional for this plan (7 electrical, 9 claims, 10 requirements ...).', 'rungs', 'count', False, AUTO, 'robustness'),
    ('noise-immunity', 'Noise immunity', 'Debounce / threshold margin per route (an analog threshold is looser than a digital pin). UNDETERMINED: no basis yet.', 'points', 'score', True, ABS_PCT, 'robustness'),
    ('shared-resources', 'Shared resources', 'Pins, wires and chip blocks two needs share.', 'shared', 'count', False, AUTO, 'robustness'),
    ('confidence', 'Confidence', 'Share of this solution own figures that are measured or cited (an estimate counts half, a stand-in none).', '%', 'percentage', True, ABS_PCT, 'evidence'),
    ('proof-level', 'Proof level', 'How far the Purposes are proven: none 0, on the digital twin 50, on real hardware 100 (mean over the Purposes).', 'points', 'score', True, ABS_PCT, 'evidence'),
    ('part-count', 'Part classes used', 'How many different part classes the build needs (0 to 10 scale).', 'parts', 'count', False, ABS_PARTS, 'build'),
    ('wires', 'Wires and joints', 'Pins used, as the stated proxy for wires and joints on the bench.', 'pins', 'count', False, AUTO, 'build'),
    ('code-size', 'Code size', 'How many C atoms the chosen routes bring in.', 'atoms', 'count', False, AUTO, 'build'),
    ('also-runs-on', 'Also runs on', 'How many other hardware / package / tier combinations carry the same plan (portability).', 'targets', 'count', True, AUTO, 'portability'),
]
#: terms that have NO basis today: seeded, never given a value (a profile that weights them scores the midpoint and says so)
UNDETERMINED = ('active-current', 'noise-immunity')
TERM_NAMES = tuple(t[0] for t in _T)
TERM_GROUP = {t[0]: t[7] for t in _T}


def term_rows():
    rows = []
    for name, display, plain, unit, vtype, positive, norm, group in _T:
        rows.append({'name': name, 'display_name': display, 'description': plain, 'category': CATEGORY, 'value_type': vtype, 'unit': unit, 'is_positive': positive,
                     'normalization_json': norm, 'temporal_json': json.dumps({'nature': 'stock', 'resample': 'nearest'}), 'abstract_tags_json': json.dumps(['firmware', group]),
                     'source': 'FIRMWARE_SCORE_PROFILES_PLAN.md section 4', 'provenance_id': 'fsc-seed',
                     'notes': ('UNDETERMINED: no basis today; scored at the neutral midpoint and said so.' if name in UNDETERMINED else
                               'Group: %s. Higher is %s.' % (group, 'better' if positive else 'worse'))})
    return rows


def q(kind, value, basis):
    """A term value: {kind: measured|estimated|cited|stand-in, value, basis}."""
    assert kind in KINDS, kind
    return {'kind': kind, 'value': value, 'basis': basis}


def weakest(kinds):
    """The weakest kind among several (stand-in < estimated < cited < measured) - what a figure built from several parts can claim."""
    order = ('stand-in', 'estimated', 'cited', 'measured')
    ks = [k for k in kinds if k]
    return min(ks, key=order.index) if ks else 'stand-in'
