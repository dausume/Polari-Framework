"""
@cross-cutting
@module casting.chain_analysis
@tags @xc:bindings

cast-3: the two derived correctness properties, computed and refusing
— never stored, never hand-set:

  PARITY    every 'cast' stage inverts the geometry; 'conversion'
            stages (firing clay to ceramic) transform in place. The
            wax master is a NEGATIVE (it IS the mold) when the count
            of inverting stages is odd, a POSITIVE when even. Derived
            from the stage rows; there is no field to hand-set.
  THERMAL   each stage's mold material must survive that stage's
            process temperature (geopolymer cure EXOTHERM PEAK is
            derived from the cure temp via the measured pspp points,
            never typed in; firing temps are declared and checked
            against the furnace rungs). A DISPOSABLE mold (Dustin
            2026-08-05: sacrificing the geopolymer in the firing is
            fine) turns the thermal blocker into a named finding —
            sacrificed, not silently survived.

Plus the fill gate (slip-casting into geopolymer is REFUSED — the
supplychain.mold_analysis rule: no proven capillarity) and cast-3's
SHRINK COMPENSATION two-pass (Dustin 2026-08-05): pass 1 derives
deliberately UNCOMPENSATED; the cumulative linear shrink across the
chain (measured values beat priors, per stage) then yields the exact
master oversize as an evidence-bearing SUGGESTION — applied only on
explicit confirmation (apply=True), never silently. Warp is a named
gap until anisotropy data exists.

Duck-typed manager, stdlib.
@see /WAX_MOLD_NESTING_PLAN.md (PHASE cast-3)
"""

import json

from casting.pour_loading import EXOTHERM_MEASURED, EXOTHERM_SOURCE
from casting.wax_feasibility import _row_named, _rows

#: Cured-geopolymer stability ceiling: the measured crystallization
#: onset — above this the amorphous gel starts becoming ceramic.
GEOPOLYMER_STABLE_C = 1000.0
GEOPOLYMER_BASIS = ('pspp geopolymer→ceramic transition (measured, '
                    'Table 8.8 lineage): amorphous stable to 1000°C '
                    'crystallization onset')
#: Linear shrink priors per cast material (%), literature-
#: approximate; a stage's measured_shrink_pct REPLACES its prior.
STAGE_SHRINK_PRIORS = {
    'geopolymer-slurry': {
        'linear_shrink_pct': 1.0,
        'claim': 'literature-approximate: geopolymer cure/drying '
                 'linear shrinkage ~0.1–1%+ (mix-dependent) — '
                 'CONSERVATIVE-HIGH prior, measure the real mix'},
    'plastic-clay': {
        'linear_shrink_pct': 11.0,
        'claim': 'literature-approximate: pressed earthenware clay, '
                 'drying (~5–6%) + firing (~5–6%) combined linear — '
                 'body-dependent, measure the real body'},
    'water-test': {'linear_shrink_pct': 0.0, 'claim': 'exact'},
}
WARP_GAP = ('warp/anisotropy unmodelled — compensation is a UNIFORM '
            'scalar; measure warp on the first-pass article (clamped '
            'drying, symmetric wall thickness reduce it)')


def _stages_of(manager, chain_name):
    stages = [s for s in _rows(manager, 'CastingStageDefinition')
              if getattr(s, 'chain_ref', '') == chain_name]
    return sorted(stages, key=lambda s: getattr(s, 'sequence', 0))


def _exotherm_peak(cure_temp_c):
    """Peak from the measured points; refuses outside 40–85°C."""
    lo, hi = EXOTHERM_MEASURED[0][0], EXOTHERM_MEASURED[-1][0]
    if cure_temp_c is None or cure_temp_c <= 0:
        return {'ok': True, 'peakC': EXOTHERM_MEASURED[0][1],
                'basis': f'lowest measured peak (cure {lo:.0f}°C)'}
    if not lo <= cure_temp_c <= hi:
        return {'ok': False,
                'refusal': f'cure {cure_temp_c:.0f}°C outside the '
                           f'measured {lo:.0f}–{hi:.0f}°C validity — '
                           f'refusing to extrapolate '
                           f'({EXOTHERM_SOURCE})'}
    for (c0, p0), (c1, p1) in zip(EXOTHERM_MEASURED,
                                  EXOTHERM_MEASURED[1:]):
        if c0 <= cure_temp_c <= c1:
            f = (cure_temp_c - c0) / (c1 - c0)
            return {'ok': True, 'peakC': p0 + f * (p1 - p0),
                    'basis': f'interpolated at cure '
                             f'{cure_temp_c:.0f}°C '
                             f'({EXOTHERM_SOURCE})'}
    return {'ok': False, 'refusal': 'exotherm interpolation failed'}


def _thermal_profile(manager, material_ref):
    """(ceiling_c, basis) a mold material survives to — feedstock
    soften, cured geopolymer stability, or a ceramic's service temp.
    None = data absent (a refusal, never a default)."""
    feed = _row_named(manager, 'MasterFeedstockDefinition',
                      material_ref)
    if feed is not None:
        soften = float(getattr(feed, 'soften_temp_c', 0.0) or 0.0)
        if soften > 0:
            return {'ceilingC': soften,
                    'basis': f'MasterFeedstockDefinition '
                             f'{material_ref} soften_temp_c '
                             f'({getattr(feed, "claim_status", "")})'}
        return None
    if material_ref in ('geopolymer', 'geopolymer-cured'):
        return {'ceilingC': GEOPOLYMER_STABLE_C,
                'basis': GEOPOLYMER_BASIS}
    ceramic = _row_named(manager, 'CeramicSample', material_ref)
    if ceramic is not None:
        svc = float(getattr(ceramic, 'max_service_temp_c', 0.0)
                    or 0.0)
        if svc > 0:
            claim = getattr(ceramic, 'temp_claim_status', '')
            return {'ceilingC': svc,
                    'basis': f'CeramicSample {material_ref} '
                             f'max_service_temp_c ({claim})'}
    return None


def _process_temp(stage):
    """What the mold must survive at this stage — DERIVED where the
    data allows, declared only for conversions."""
    kind = getattr(stage, 'stage_kind', 'cast')
    cast = getattr(stage, 'cast_material_ref', '')
    if kind == 'conversion':
        t = float(getattr(stage, 'process_temp_c', 0.0) or 0.0)
        if t <= 0:
            return {'ok': False,
                    'refusal': f"conversion stage "
                               f"'{getattr(stage, 'name', '')}' "
                               f'declares no process_temp_c'}
        return {'ok': True, 'tempC': t, 'basis': 'declared firing '
                'temperature (checked against furnace rungs)'}
    if cast in ('geopolymer-slurry', 'geopolymer'):
        peak = _exotherm_peak(float(getattr(stage, 'cure_temp_c',
                                            0.0) or 0.0) or None)
        if not peak.get('ok'):
            return {'ok': False, 'refusal': peak['refusal']}
        return {'ok': True, 'tempC': peak['peakC'],
                'basis': f"cure exotherm peak — {peak['basis']}"}
    if cast == 'plastic-clay':
        return {'ok': True, 'tempC': 25.0,
                'basis': 'pressed plastic at ambient'}
    if cast == 'water-test':
        return {'ok': True, 'tempC': 25.0, 'basis': 'ambient'}
    return {'ok': False,
            'refusal': f"no process-temperature data for cast "
                       f"material '{cast}' — molten metals need "
                       f'CastingMaterialThermalProfile rows (cast-3b, '
                       f'not yet seeded); absent data is absent'}


def _furnace_check(manager, temp_c):
    rungs = _rows(manager, 'LadderRung')
    if not rungs:
        return {'ok': None, 'gap': 'no LadderRung furnace data '
                                   'loaded — reachability unassessed'}
    best = max((float(getattr(r, 'max_temp_c', 0.0) or 0.0)
                for r in rungs), default=0.0)
    if temp_c > best:
        return {'ok': False, 'bestRungC': best,
                'blocker': f'firing at {temp_c:.0f}°C exceeds the '
                           f'best furnace rung ({best:.0f}°C) — a '
                           f'capability blocker, not a material one'}
    return {'ok': True, 'bestRungC': best}


def _stage_shrink(stage):
    """Measured beats prior; absent both = 0 with a named gap."""
    measured = float(getattr(stage, 'measured_shrink_pct', 0.0)
                     or 0.0)
    if measured > 0:
        return {'pct': measured, 'basis': 'MEASURED on a first-pass '
                                          'article (replaces prior)'}
    cast = getattr(stage, 'cast_material_ref', '')
    prior = STAGE_SHRINK_PRIORS.get(cast)
    if prior:
        return {'pct': prior['linear_shrink_pct'],
                'basis': prior['claim']}
    return {'pct': 0.0, 'basis': f"no shrink prior for '{cast}' — "
                                 f'carried as 0 with this gap named'}


def chain_report(manager, chain_name):
    """Parity + thermal ordering + fill gates for a chain, every
    verdict carrying its basis. Blockers decide."""
    chain = _row_named(manager, 'MoldNestingChain', chain_name)
    if chain is None:
        return {'ok': False,
                'error': f"no MoldNestingChain named '{chain_name}'"}
    stages = _stages_of(manager, chain_name)
    if not stages:
        return {'ok': False,
                'error': f"chain '{chain_name}' has no "
                         f'CastingStageDefinition rows'}
    blockers, gaps, findings = [], [], []

    # -- PARITY: derived, nowhere stored --
    inversions = sum(1 for s in stages
                     if getattr(s, 'stage_kind', 'cast') == 'cast')
    conversions = len(stages) - inversions
    wax_parity = 'negative' if inversions % 2 == 1 else 'positive'
    parity = {
        'invertingStages': inversions,
        'conversionStages': conversions,
        'waxMasterParity': wax_parity,
        'meaning': ('the wax IS the mold — print the cavity'
                    if wax_parity == 'negative'
                    else 'the wax is a POSITIVE master — print the '
                         'part; the first mold forms around it'),
        'rule': 'derived from stage rows; conversion stages do not '
                'flip. There is no field to hand-set.'}

    # -- per-stage thermal + fill gates --
    stage_records = []
    for st in stages:
        st_name = getattr(st, 'name', '')
        kind = getattr(st, 'stage_kind', 'cast')
        mold_ref = getattr(st, 'mold_material_ref', '')
        cast_ref = getattr(st, 'cast_material_ref', '')
        fill = getattr(st, 'fill_method', '')
        disposable = bool(getattr(st, 'mold_disposable', False))
        rec = {'stage': st_name, 'sequence': getattr(st, 'sequence',
                                                     0),
               'kind': kind, 'moldMaterial': mold_ref,
               'castMaterial': cast_ref, 'fillMethod': fill,
               'disposable': disposable}

        if kind == 'cast' and fill not in ('gravity-pour', 'inject',
                                           'press', 'in-place'):
            blockers.append(f"stage '{st_name}': unknown fill method "
                            f"'{fill}'")
        if (fill == 'slip-cast'
                or (fill not in ('gravity-pour', 'inject', 'press',
                                 'in-place') and 'slip' in fill)):
            blockers.append(
                f"stage '{st_name}': slip-casting into a geopolymer "
                f'mold is REFUSED — no proven capillarity '
                f'(supplychain.mold_analysis rule); press plastic '
                f'clay instead')

        ceiling = _thermal_profile(manager, mold_ref)
        proc = _process_temp(st)
        if ceiling is None:
            blockers.append(f"stage '{st_name}': no thermal data for "
                            f"mold material '{mold_ref}' — absent "
                            f'data is absent')
        if not proc.get('ok'):
            blockers.append(f"stage '{st_name}': {proc['refusal']}")
        if ceiling is not None and proc.get('ok'):
            rec['moldCeilingC'] = ceiling['ceilingC']
            rec['moldCeilingBasis'] = ceiling['basis']
            rec['processTempC'] = round(proc['tempC'], 1)
            rec['processTempBasis'] = proc['basis']
            margin = ceiling['ceilingC'] - proc['tempC']
            rec['marginC'] = round(margin, 1)
            if margin <= 0:
                if disposable:
                    findings.append(
                        f"stage '{st_name}': {mold_ref} is "
                        f'SACRIFICED — process '
                        f"{proc['tempC']:.0f}°C exceeds its "
                        f"{ceiling['ceilingC']:.0f}°C ceiling, "
                        f'allowed because mold_disposable is set '
                        f'(the mold does not survive; plan on '
                        f'break-out, not reuse)')
                    rec['sacrificed'] = True
                else:
                    blockers.append(
                        f"stage '{st_name}': {cast_ref} at "
                        f"{proc['tempC']:.0f}°C "
                        f"({proc['basis']}) exceeds {mold_ref} "
                        f"ceiling {ceiling['ceilingC']:.0f}°C "
                        f"({ceiling['basis']}) — the offending "
                        f'pair, named')
            elif margin < 15:
                findings.append(f"stage '{st_name}': only "
                                f'{margin:.0f}°C thermal margin '
                                f'({mold_ref} vs {cast_ref})')
        if kind == 'conversion' and proc.get('ok'):
            furnace = _furnace_check(manager, proc['tempC'])
            rec['furnace'] = furnace
            if furnace.get('blocker'):
                blockers.append(f"stage '{st_name}': "
                                f"{furnace['blocker']}")
            if furnace.get('gap'):
                gaps.append(furnace['gap'])
            # gap thm-steam-firing (modelled): fired geopolymer
            # releases its bound water as steam.
            if mold_ref in ('geopolymer', 'geopolymer-cured'):
                findings.append(
                    f"stage '{st_name}': fired geopolymer releases "
                    f'bound water as STEAM — slow the ramp and/or '
                    f'pre-dry the mold or it cracks (and takes the '
                    f'part with it)')
            # gap thm-thermal-shock (modelled): surface the target
            # ceramic's ramp tolerance on the record.
            target = getattr(st, 'target_material_ref', '')
            ceramic = _row_named(manager, 'CeramicSample', target)
            if ceramic is not None:
                rec['targetThermalShock'] = getattr(
                    ceramic, 'thermal_shock', '')
        stage_records.append(rec)

    verdict = 'blocked' if blockers else 'feasible'
    return {'ok': True, 'chain': chain_name, 'verdict': verdict,
            'parity': parity, 'stages': stage_records,
            'blockers': blockers, 'findings': findings, 'gaps': gaps,
            'note': 'parity and thermal ordering are DERIVED — '
                    'blockers name the offending pair; disposable '
                    'molds are sacrificed loudly, never silently '
                    'survived.'}


def shrink_compensation_report(manager, chain_name, apply=False):
    """The two-pass shrink workflow (Dustin 2026-08-05). Pass 1 is
    the UNCOMPENSATED derivation (the mold as-designed — deliberate).
    This report multiplies each stage's linear shrink (measured beats
    prior) into the expected final scale and yields the exact master
    oversize as a SUGGESTION with evidence. apply=True (explicit
    confirmation — never the default) writes the compensation onto
    the chain's MoldDefinition and re-derives, so the post-shrink
    part lands exact."""
    chain = _row_named(manager, 'MoldNestingChain', chain_name)
    if chain is None:
        return {'ok': False,
                'error': f"no MoldNestingChain named '{chain_name}'"}
    stages = _stages_of(manager, chain_name)
    if not stages:
        return {'ok': False,
                'error': f"chain '{chain_name}' has no stages"}
    factor = 1.0
    per_stage = []
    for st in stages:
        if getattr(st, 'stage_kind', 'cast') == 'conversion':
            # firing shrink is folded into the cast material's
            # COMBINED prior (drying + firing) on its cast stage —
            # counting the conversion again would double it.
            per_stage.append({'stage': getattr(st, 'name', ''),
                              'castMaterial': getattr(
                                  st, 'cast_material_ref', ''),
                              'linearShrinkPct': 0.0,
                              'basis': 'conversion — shrink already '
                                       'folded into the cast '
                                       "material's combined prior"})
            continue
        sh = _stage_shrink(st)
        f = 1.0 - sh['pct'] / 100.0
        factor *= f
        per_stage.append({'stage': getattr(st, 'name', ''),
                          'castMaterial': getattr(
                              st, 'cast_material_ref', ''),
                          'linearShrinkPct': sh['pct'],
                          'basis': sh['basis']})
    comp_pct = (1.0 / factor - 1.0) * 100.0 if factor > 0 else None
    if comp_pct is None:
        return {'ok': False,
                'error': 'cumulative shrink ≥ 100% — nonsensical'}
    suggestion = {
        'knob': 'MoldDefinition.shrink_allowance_pct on '
                f"'{getattr(chain, 'mold_def_ref', '')}'",
        'recommendedPct': round(comp_pct, 3),
        'evidence': f'expected final scale ×{factor:.4f} '
                    f'(uncompensated part comes out '
                    f'{(1 - factor) * 100.0:.1f}% undersize); '
                    f'master oversize ×{1.0 / factor:.4f} makes the '
                    f'post-shrink part exact',
        'applied': False}
    result = {'ok': True, 'chain': chain_name,
              'passOne': 'derive with shrink_allowance_pct = 0 — '
                         'DELIBERATELY uncompensated; measure the '
                         'article, write measured_shrink_pct on the '
                         'stages, re-run this report',
              'stages': per_stage,
              'expectedFinalScale': round(factor, 5),
              'compensation': suggestion,
              'gaps': [WARP_GAP,
                       'waxprint fabrication shrink is upstream '
                       '(the waxprint sim owns it) — not double-'
                       'counted here'],
              'note': 'measured values REPLACE priors per stage; '
                      'apply=True is the explicit-confirmation knob '
                      '(never auto-applied)'}
    if apply:
        from casting.mold_geometry import _mold_named, derive_mold
        mold = _mold_named(manager, getattr(chain, 'mold_def_ref',
                                            ''))
        if mold is None:
            result['compensation']['applyError'] = (
                f"chain names no derivable MoldDefinition "
                f"('{getattr(chain, 'mold_def_ref', '')}')")
            return result
        mold.shrink_allowance_pct = round(comp_pct, 4)
        derived = derive_mold(manager, getattr(mold, 'name', ''))
        result['compensation']['applied'] = bool(derived.get('ok'))
        result['compensation']['derivation'] = {
            'ok': derived.get('ok'),
            'scaleFactor': derived.get('scaleFactor'),
            'error': derived.get('error', '')}
    return result
