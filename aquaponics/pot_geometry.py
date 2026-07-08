"""
@cross-cutting
@module aquaponics.pot_geometry
@tags @xc:bindings

Pot geometry MATH (aqp-1) — validation of the gravity constraint +
placement generation, as pure functions over PotDefinition / PotHole
rows. Every finding is evidence-bearing and names the exact knob to
change (the scoring-engine honesty idiom): geometry is never silently
'fixed', it is diagnosed.

The self-watering invariant Dustin stated, checked here:
  - at least one INPUT (high) and one OUTPUT (low) hole;
  - every input sits ABOVE every output;
  - inputs and outputs on OPPOSITE sides of the wall;
  - every output drains by GRAVITY (bore angle downhill-out), and no
    bore angle exceeds the tunable limit;
  - holes stay inside the wall (not through the base or over the rim,
    not overlapping).

The maintained water level of a flow-through self-watering pot is set
by the LOWEST output's lower lip — water fills from the inputs and any
excess drains there. The report states it so the reader sees what the
geometry actually does.

@consumers
  - aquaponics.pot_api / aquaponics.selftest_pot
@see /AQUAPONICS_MODULE_PLAN.md
"""

import math

from aquaponics.pot_basis import (
    IDEAL_SIDE_SEPARATION_DEG, MAX_ABS_ANGLE_DEG,
    MIN_OUTPUT_DOWNHILL_DEG, MIN_SIDE_SEPARATION_DEG,
    RECOMMENDED_OUTPUT_DOWNHILL_DEG,
)

#: One input/output pair recommended per this much wall circumference
#: (mm) — a suggestion scaled to pot size, never enforced.
CIRCUMFERENCE_PER_PAIR_MM = 250.0


def _rows(manager, class_name):
    table = (manager.objectTables or {}).get(class_name, {})
    return list(table.values()) if isinstance(table, dict) else list(table)


def _f(row, attr, default=0.0):
    try:
        return float(getattr(row, attr, default))
    except (TypeError, ValueError):
        return default


def _holes_of(manager, pot_name):
    return [h for h in _rows(manager, 'PotHole')
            if getattr(h, 'pot_name', '') == pot_name]


def _circular_mean_deg(angles):
    """Mean direction of a set of azimuths (degrees), cycle-correct."""
    if not angles:
        return None
    x = sum(math.cos(math.radians(a)) for a in angles)
    y = sum(math.sin(math.radians(a)) for a in angles)
    if abs(x) < 1e-12 and abs(y) < 1e-12:
        return None  # antipodal cancel — no single mean side
    return math.degrees(math.atan2(y, x)) % 360.0


def _separation_deg(a, b):
    """Smallest angle between two azimuths (0-180)."""
    d = abs((a - b) % 360.0)
    return min(d, 360.0 - d)


def _lower_lip_mm(hole):
    """Height of a hole's lower edge (mm) — water drains to here."""
    return _f(hole, 'height_mm') - _f(hole, 'diameter_mm') / 2.0


def _upper_lip_mm(hole):
    return _f(hole, 'height_mm') + _f(hole, 'diameter_mm') / 2.0


def recommend_pair_count(pot):
    """Suggested input/output pair count for a pot's size."""
    mean_d = (_f(pot, 'outer_top_diameter_mm')
              + _f(pot, 'outer_base_diameter_mm')) / 2.0
    circumference = math.pi * mean_d
    return max(1, round(circumference / CIRCUMFERENCE_PER_PAIR_MM))


def validate_pot(manager, pot_name):
    """Full geometry + gravity validation for one pot. Returns a
    report with per-issue findings (each naming its knob) and the
    maintained water level the geometry implies. Never mutates."""
    pots = {getattr(p, 'name', ''): p
            for p in _rows(manager, 'PotDefinition')}
    pot = pots.get(pot_name)
    if pot is None:
        return {'ok': False,
                'error': f"no PotDefinition named '{pot_name}'",
                'knownPots': sorted(pots)}

    height = _f(pot, 'height_mm')
    base_th = _f(pot, 'base_thickness_mm')
    wall_th = _f(pot, 'wall_thickness_mm')
    holes = _holes_of(manager, pot_name)
    inputs = [h for h in holes if getattr(h, 'kind', '') == 'input']
    outputs = [h for h in holes if getattr(h, 'kind', '') == 'output']

    findings = []

    def finding(kind, hole, evidence, knob, action):
        findings.append({
            'kind': kind,
            'hole': getattr(hole, 'name', '') if hole is not None
            else None,
            'evidence': evidence,
            'suggestion': {'knob': knob, 'action': action}})

    # 1. The self-watering minimum: at least one input, one output.
    if not inputs:
        finding('no-input-hole', None,
                'a self-watering pot needs at least one high INPUT '
                'hole to fill from', 'PotHole.kind',
                "add a PotHole with kind 'input' near the top")
    if not outputs:
        finding('no-output-hole', None,
                'a self-watering pot needs at least one low OUTPUT '
                'hole to drain excess by gravity', 'PotHole.kind',
                "add a PotHole with kind 'output' near the bottom")

    # 2. Per-hole: inside the wall, angle within the tunable limit,
    #    outputs downhill.
    for h in holes:
        d = _f(h, 'diameter_mm')
        angle = _f(h, 'angle_deg')
        lower, upper = _lower_lip_mm(h), _upper_lip_mm(h)
        if lower < base_th:
            finding('breaches-base', h,
                    f'lower lip at {lower:.1f}mm is below the base '
                    f'thickness {base_th:.1f}mm — the bore would open '
                    'into the base', 'PotHole.height_mm / diameter_mm',
                    'raise the hole or shrink its diameter')
        if upper > height:
            finding('over-rim', h,
                    f'upper lip at {upper:.1f}mm exceeds the pot '
                    f'height {height:.1f}mm', 'PotHole.height_mm',
                    'lower the hole below the rim')
        if abs(angle) > MAX_ABS_ANGLE_DEG + 1e-9:
            finding('angle-exceeds-limit', h,
                    f'bore angle {angle:.1f} deg exceeds the +/-'
                    f'{MAX_ABS_ANGLE_DEG:.0f} deg limit (a slot this '
                    'steep loses gravity sense / breaches the wall)',
                    'PotHole.angle_deg',
                    f'clamp within +/- {MAX_ABS_ANGLE_DEG:.0f} deg')
        if getattr(h, 'kind', '') == 'output' \
                and angle < MIN_OUTPUT_DOWNHILL_DEG - 1e-9:
            finding('output-not-gravity-fed', h,
                    f'output bore angle {angle:.1f} deg is uphill-out '
                    '— water would be trapped instead of draining by '
                    'gravity', 'PotHole.angle_deg',
                    f'set angle >= {RECOMMENDED_OUTPUT_DOWNHILL_DEG:.0f}'
                    ' deg (downhill-out)')
        elif getattr(h, 'kind', '') == 'output' \
                and angle < RECOMMENDED_OUTPUT_DOWNHILL_DEG - 1e-9:
            finding('output-drains-weakly', h,
                    f'output angle {angle:.1f} deg drains only at the '
                    'lip; a slight downhill drains reliably',
                    'PotHole.angle_deg',
                    f'set angle ~ {RECOMMENDED_OUTPUT_DOWNHILL_DEG:.0f}'
                    ' deg')

    # 3. Overlap: two holes whose openings overlap on the wall.
    for i in range(len(holes)):
        for j in range(i + 1, len(holes)):
            a, b = holes[i], holes[j]
            sep = _separation_deg(_f(a, 'azimuth_deg'),
                                  _f(b, 'azimuth_deg'))
            mean_d = (_f(pot, 'outer_top_diameter_mm')
                      + _f(pot, 'outer_base_diameter_mm')) / 2.0
            arc_mm = math.radians(sep) * mean_d / 2.0
            dv = abs(_f(a, 'height_mm') - _f(b, 'height_mm'))
            min_gap = (_f(a, 'diameter_mm') + _f(b, 'diameter_mm')) / 2.0
            if arc_mm < min_gap and dv < min_gap:
                finding('holes-overlap', a,
                        f"'{getattr(a, 'name', '')}' and "
                        f"'{getattr(b, 'name', '')}' are closer than "
                        'their combined radii on the wall',
                        'PotHole.azimuth_deg / height_mm',
                        'separate them around or up the wall')

    # 4. Every input ABOVE every output (higher fill, lower drain).
    if inputs and outputs:
        lowest_input = min(_lower_lip_mm(h) for h in inputs)
        highest_output = max(_upper_lip_mm(h) for h in outputs)
        if lowest_input <= highest_output + 1e-9:
            finding('input-not-above-output', None,
                    f'the lowest input lip ({lowest_input:.1f}mm) is '
                    'not above the highest output lip '
                    f'({highest_output:.1f}mm) — inputs must sit '
                    'higher than outputs so the pot fills high and '
                    'drains low', 'PotHole.height_mm',
                    'raise the inputs or lower the outputs')

    # 5. Inputs and outputs on OPPOSITE sides.
    in_side = _circular_mean_deg([_f(h, 'azimuth_deg')
                                  for h in inputs])
    out_side = _circular_mean_deg([_f(h, 'azimuth_deg')
                                   for h in outputs])
    side_separation = None
    if in_side is not None and out_side is not None:
        side_separation = _separation_deg(in_side, out_side)
        if side_separation < MIN_SIDE_SEPARATION_DEG - 1e-9:
            finding('not-opposite-sides', None,
                    f'input side (~{in_side:.0f} deg) and output side '
                    f'(~{out_side:.0f} deg) are only '
                    f'{side_separation:.0f} deg apart — Dustin: holes '
                    f'on OPPOSITE sides (ideal '
                    f'{IDEAL_SIDE_SEPARATION_DEG:.0f} deg)',
                    'PotHole.azimuth_deg',
                    'move the output group toward the far side')

    # Maintained level: water fills to just below the lowest output.
    maintained_level = min((_lower_lip_mm(h) for h in outputs),
                           default=None)

    recommended_pairs = recommend_pair_count(pot)
    pair_count = min(len(inputs), len(outputs))
    pair_note = None
    if pair_count < recommended_pairs:
        pair_note = {
            'knob': 'PotHole (count)',
            'action': f'this pot ({(_f(pot, "outer_top_diameter_mm") + _f(pot, "outer_base_diameter_mm")) / 2.0:.0f}mm '
                      f'mean diameter) suggests ~{recommended_pairs} '
                      f'input/output pair(s); it has {pair_count} — '
                      'more even flow with additional pairs (a '
                      'suggestion, not required)'}

    return {
        'ok': True,
        'pot': pot_name,
        'displayName': getattr(pot, 'display_name', '') or pot_name,
        'holeCounts': {'input': len(inputs), 'output': len(outputs)},
        'inputSideDeg': round(in_side, 1) if in_side is not None
        else None,
        'outputSideDeg': round(out_side, 1) if out_side is not None
        else None,
        'sideSeparationDeg': round(side_separation, 1)
        if side_separation is not None else None,
        'maintainedWaterLevelMm': round(maintained_level, 1)
        if maintained_level is not None else None,
        'recommendedPairs': recommended_pairs,
        'findings': findings,
        'valid': not findings,
        'pairSuggestion': pair_note,
        'note': 'validation diagnoses geometry against the gravity '
                'self-watering invariant; it never edits the pot. The '
                'maintained water level is the lowest output lip — '
                'inputs fill above it, excess drains there.',
    }


def generate_holes(pot, n_pairs=1, input_diameter_mm=10.0,
                   output_diameter_mm=12.0, input_height_frac=0.8,
                   output_height_frac=0.15,
                   output_downhill_deg=RECOMMENDED_OUTPUT_DOWNHILL_DEG,
                   spread_deg=40.0):
    """Generate a VALID set of hole specs from tunable knobs (count,
    diameters, relative heights): n_pairs inputs clustered on one side
    (azimuth 0) and n_pairs outputs on the opposite side (180),
    outputs downhill. Returns a list of dicts ready to become PotHole
    rows — the 'tunable number' path that always satisfies the
    invariant. Does NOT persist."""
    height = _f(pot, 'height_mm')
    base_th = _f(pot, 'base_thickness_mm')
    usable = max(0.0, height - base_th)
    in_h = base_th + usable * input_height_frac
    out_h = base_th + usable * output_height_frac
    pot_name = getattr(pot, 'name', '')
    specs = []

    def place(kind, count, center_az, height_mm, diameter, angle):
        for i in range(count):
            offset = 0.0 if count == 1 else \
                (i - (count - 1) / 2.0) * (spread_deg / max(1, count))
            specs.append({
                'name': f'{pot_name}-{kind}-{i + 1}',
                'pot_name': pot_name, 'kind': kind,
                'diameter_mm': diameter,
                'height_mm': round(height_mm, 2),
                'azimuth_deg': round((center_az + offset) % 360.0, 2),
                'angle_deg': angle})
    place('input', n_pairs, 0.0, in_h, input_diameter_mm, 0.0)
    place('output', n_pairs, 180.0, out_h, output_diameter_mm,
          output_downhill_deg)
    return specs
