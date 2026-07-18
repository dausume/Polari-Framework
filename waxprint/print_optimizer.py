"""
@cross-cutting
@module waxprint.print_optimizer
@tags @xc:bindings

wp-4 — the point of the whole module: iterate MANY trials over the
condition vector (two-zone temperatures, screw RPM, nozzle size,
ambient/bed, the fan wind vector, speed, layer height) across candidate
ASSEMBLIES (nozzle/bed/chamber/auger materials) and FEEDSTOCKS, and find
the print recipe that gives the finest REPEATABLE voxel that still passes
the wax thermal-safety gate and prints the standard movement patterns
(Dustin 2026-07-17: "identify ideal print approaches, nozzles, and
printing bed and nozzle and melt chamber/augur materials ... iterate
through many trials and see what the ideal resolutions are under what
conditions").

Trials are EPHEMERAL SimpleNamespaces (never persisted — a sweep is a
question, not data) fed through the rows-based cores in melt_analysis /
bead_analysis / movement_analysis. The objective rewards a fine voxel + a
small repeatability margin + printable movements and penalizes the fan
warp asymmetry; unsafe or unprintable trials are excluded, not scored.

A hard trial cap keeps a sweep bounded; truncation is LOGGED, never
silent (knobs-and-suggestions / no-silent-caps).

@consumers
  - waxprint.waxprint_api (/api/waxprint/optimize)
  - waxprint.selftest_optimizer
"""

from types import SimpleNamespace

from waxprint import melt_analysis, bead_analysis, movement_analysis

MAX_TRIALS = 600

#: Environment presets: (label, ambient_c, bed_c, convection_preset, wind_mm_s)
ENV_PRESETS = [
    ('room-still', 22.0, 22.0, 'still-air', 0.0),
    ('fridge-still', 4.0, 4.0, 'fridge-still', 0.0),
    ('room-ducted-fan', 22.0, 22.0, 'gentle-ducted', 800.0),
    ('fridge-ducted-fan', 4.0, 4.0, 'gentle-ducted', 800.0),
]

DEFAULT_SPEC = {
    'hotend_temp_c': [110.0, 130.0],
    'nozzle_diameter_mm': [0.25, 0.4],
    'print_speed_mm_s': [20.0, 40.0],
    'layer_height_mm': [0.15],
    'envs': ENV_PRESETS,
}

DEFAULT_WEIGHTS = {
    'fineness': 0.4,      # small voxel
    'repeatability': 0.3,  # small margin
    'movement': 0.2,      # patterns viable
    'warp': 0.1,          # penalty on fan asymmetry
}


def make_condition(hotend_temp_c, nozzle_diameter_mm, print_speed_mm_s,
                   layer_height_mm, ambient_c, bed_c, preset, wind_mm_s,
                   auger_offset_c=20.0):
    """Build one ephemeral trial condition (auger runs a fixed offset
    below the hotend by default)."""
    return SimpleNamespace(
        name='trial', auger_temp_c=max(40.0, hotend_temp_c - auger_offset_c),
        hotend_temp_c=hotend_temp_c, rpm=25.0,
        nozzle_diameter_mm=nozzle_diameter_mm, ambient_temp_c=ambient_c,
        bed_temp_c=bed_c, convection_preset=preset,
        fan_wind_vx_mm_s=wind_mm_s, fan_wind_vy_mm_s=0.0, fan_wind_vz_mm_s=0.0,
        print_speed_mm_s=print_speed_mm_s, layer_height_mm=layer_height_mm)


def _trial_conditions(spec):
    """Cross-product of the sweep spec → list of (env_label, condition)."""
    out = []
    for hot in spec['hotend_temp_c']:
        for nz in spec['nozzle_diameter_mm']:
            for spd in spec['print_speed_mm_s']:
                for lh in spec['layer_height_mm']:
                    for (label, amb, bed, preset, wind) in spec['envs']:
                        out.append((label, make_condition(
                            hot, nz, spd, lh, amb, bed, preset, wind)))
    return out


def evaluate_trial(manager, assembly, feedstock, env_label, condition):
    """One trial through melt → voxel → movements. Returns a flat record
    (no score yet — scoring is normalized across the batch)."""
    melt_result, voxel, movements = \
        movement_analysis.movements_for_condition(
            manager, assembly, feedstock, condition)
    return {
        'assembly': getattr(assembly, 'name', ''),
        'feedstock': getattr(feedstock, 'name', ''),
        'nozzle_material': getattr(assembly, 'nozzle_material_ref', ''),
        'bed_material': getattr(assembly, 'bed_material_ref', ''),
        'chamber_material': getattr(assembly, 'chamber_material_ref', ''),
        'auger_material': getattr(assembly, 'auger_material_ref', ''),
        'env': env_label,
        'hotend_temp_c': condition.hotend_temp_c,
        'auger_temp_c': condition.auger_temp_c,
        'nozzle_diameter_mm': melt_result['nozzle_diameter_mm'],
        'print_speed_mm_s': condition.print_speed_mm_s,
        'layer_height_mm': condition.layer_height_mm,
        'wind_mm_s': condition.fan_wind_vx_mm_s,
        'thermally_safe': melt_result['thermally_safe'],
        'printable': melt_result['printable'],
        'exit_temp_c': melt_result['exit_temp_c'],
        'voxel_xy_mm': voxel['voxel_xy_mm'],
        'voxel_z_mm': voxel['voxel_z_mm'],
        'voxel_volume_mm3': voxel['voxel_volume_mm3'],
        'margin_mm': voxel['margin_mm'],
        'warp_index': voxel['warp_index'],
        't_solidify_s': voxel['t_solidify_s'],
        'resolution_class': voxel['resolution_class'],
        'viable_count': movements['viable_count'],
        'movement_total': movements['total'],
        'movement_overall': movements['overall'],
    }


def _score_batch(records, weights):
    """Normalize + score the SAFE + printable trials in the batch. Unsafe
    trials get score None and an 'excluded' reason. Higher score better."""
    eligible = [r for r in records if r['thermally_safe'] and r['printable']]
    for r in records:
        if r not in eligible:
            r['score'] = None
            r['excluded_reason'] = (
                'thermally unsafe' if not r['thermally_safe']
                else 'not printable (under-melt / below margin)')
    if not eligible:
        return
    vmax = max(r['voxel_xy_mm'] for r in eligible) or 1.0
    vmin = min(r['voxel_xy_mm'] for r in eligible)
    mmax = max(r['margin_mm'] for r in eligible) or 1.0
    span_v = (vmax - vmin) or 1.0
    for r in eligible:
        fineness = (vmax - r['voxel_xy_mm']) / span_v            # 0..1
        repeatability = 1.0 - (r['margin_mm'] / mmax if mmax else 0.0)
        movement = r['viable_count'] / max(1, r['movement_total'])
        warp_pen = min(1.0, r['warp_index'])
        r['score'] = (weights['fineness'] * fineness
                      + weights['repeatability'] * repeatability
                      + weights['movement'] * movement
                      - weights['warp'] * warp_pen)
        r['score_components'] = {
            'fineness': fineness, 'repeatability': repeatability,
            'movement': movement, 'warp_penalty': warp_pen}


def _fan_verdict(records):
    """Compare safe trials with vs without a fan: does the resolution gain
    beat the warp cost? Answers Dustin's fan question with data."""
    safe = [r for r in records if r.get('score') is not None]
    fan = [r for r in safe if r['wind_mm_s'] > 0]
    nofan = [r for r in safe if r['wind_mm_s'] == 0]
    if not fan or not nofan:
        return {'verdict': 'insufficient data',
                'note': 'need both fan and no-fan safe trials'}
    mean = lambda xs, k: sum(x[k] for x in xs) / len(xs)
    dv = mean(nofan, 'voxel_xy_mm') - mean(fan, 'voxel_xy_mm')  # >0 = finer
    dw = mean(fan, 'warp_index') - mean(nofan, 'warp_index')    # warp added
    helps = dv > 0
    return {
        'verdict': ('a controlled fan HELPS resolution' if helps
                    else 'the fan does not improve resolution here'),
        'voxel_finer_by_mm': dv,
        'warp_added': dw,
        'note': 'controlled/ducted airflow trades a little warp asymmetry '
                'for a finer, faster-set bead; an uncontrolled fan would add '
                'the warp without the control — model it as a bigger '
                'warp_index before trusting it.'}


def _split_delta(records, key, low_pred, high_pred, low_label, high_label):
    """Mean voxel_xy for two subsets (e.g. fridge vs room)."""
    safe = [r for r in records if r.get('score') is not None]
    lo = [r for r in safe if low_pred(r)]
    hi = [r for r in safe if high_pred(r)]
    if not lo or not hi:
        return None
    mean = lambda xs: sum(x['voxel_xy_mm'] for x in xs) / len(xs)
    return {low_label: mean(lo), high_label: mean(hi),
            'finer_side': low_label if mean(lo) < mean(hi) else high_label,
            'delta_mm': abs(mean(lo) - mean(hi))}


def _rank_by(records, key):
    """Best (highest) score per value of `key`, ranked."""
    best = {}
    for r in records:
        if r.get('score') is None:
            continue
        v = r[key]
        if v not in best or r['score'] > best[v]['score']:
            best[v] = r
    return sorted(
        ({'value': v, 'best_score': r['score'],
          'best_voxel_xy_mm': r['voxel_xy_mm'], 'env': r['env'],
          'hotend_temp_c': r['hotend_temp_c']}
         for v, r in best.items()),
        key=lambda x: -x['best_score'])


def optimize(manager, assembly_names, feedstock_names, spec=None,
             weights=None, top_n=8):
    """Run the sweep and build the report. assembly_names / feedstock_names
    are lists of row names to compare; spec overrides DEFAULT_SPEC."""
    spec = {**DEFAULT_SPEC, **(spec or {})}
    weights = {**DEFAULT_WEIGHTS, **(weights or {})}

    assemblies = [melt_analysis.find_row(manager, 'PrinterAssemblyDefinition',
                                         n) for n in assembly_names]
    feedstocks = [melt_analysis.find_row(manager, 'WaxFeedstockDefinition', n)
                  for n in feedstock_names]
    missing = ([f'PrinterAssemblyDefinition:{n}'
                for n, a in zip(assembly_names, assemblies) if a is None]
               + [f'WaxFeedstockDefinition:{n}'
                  for n, f in zip(feedstock_names, feedstocks) if f is None])
    if missing:
        return {'ok': False, 'error': 'row(s) not found', 'missing': missing}

    conditions = _trial_conditions(spec)
    planned = len(assemblies) * len(feedstocks) * len(conditions)
    truncated = None
    combos = [(a, f, lbl, c) for a in assemblies for f in feedstocks
              for (lbl, c) in conditions]
    if len(combos) > MAX_TRIALS:
        truncated = {'planned': planned, 'ran': MAX_TRIALS,
                     'dropped': planned - MAX_TRIALS,
                     'note': f'trial cap {MAX_TRIALS} hit — ran the first '
                             f'{MAX_TRIALS} combinations; narrow the spec or '
                             f'raise MAX_TRIALS to cover the rest.'}
        combos = combos[:MAX_TRIALS]

    records = [evaluate_trial(manager, a, f, lbl, c)
               for (a, f, lbl, c) in combos]
    _score_batch(records, weights)

    scored = [r for r in records if r.get('score') is not None]
    scored.sort(key=lambda r: -r['score'])
    unsafe = len(records) - len(scored)

    # best per resolution class
    per_class = {}
    for r in scored:
        rc = r['resolution_class']
        if rc not in per_class or r['score'] > per_class[rc]['score']:
            per_class[rc] = r

    report = {
        'ok': True,
        'trials_run': len(records),
        'trials_scored': len(scored),
        'trials_excluded_unsafe_or_unprintable': unsafe,
        'truncated': truncated,
        'best_recipe': scored[0] if scored else None,
        'top_recipes': scored[:top_n],
        'best_per_resolution_class': {
            k: {'voxel_xy_mm': v['voxel_xy_mm'], 'env': v['env'],
                'assembly': v['assembly'], 'feedstock': v['feedstock'],
                'hotend_temp_c': v['hotend_temp_c'], 'score': v['score']}
            for k, v in per_class.items()},
        'finest_voxel_xy_mm': min((r['voxel_xy_mm'] for r in scored),
                                  default=None),
        'fan_verdict': _fan_verdict(records),
        'fridge_vs_room': _split_delta(
            records, 'env', lambda r: r['env'].startswith('fridge'),
            lambda r: r['env'].startswith('room'), 'fridge', 'room'),
        'nozzle_material_ranking': _rank_by(records, 'nozzle_material'),
        'bed_material_ranking': _rank_by(records, 'bed_material'),
        'feedstock_ranking': _rank_by(records, 'feedstock'),
        'assembly_ranking': _rank_by(records, 'assembly'),
    }
    return report
