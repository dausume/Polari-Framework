"""
@cross-cutting
@module microalgae.integrated_analysis
@tags @xc:bindings

algae-2 model — the CHAINED balance of an excess-source + algae-reactor
loop, judged on BOTH balance and resilience (see integrated_basis).
Duck-typed manager (a lazy tanks read resolves live source surplus; a
source_surplus_override keeps selftests stdlib-only).

Same math serves both design modes (reactor-first / add-on) — they
differ only in the sizing RECOMMENDATION direction:
  base_surplus   = Σ source system net N (reactor NOT counted)
  reactor_need   = Σ reactor N need at its operating point
  draw           = min(base_surplus, reactor_need)   (can't pull N the
                   source doesn't make)
  composite_net  = base_surplus − draw               (with reactor)
  balanced       = |composite_net| ≤ band
  resilient      = base_surplus ≤ RESILIENCE_BAND     (passive crew holds
                   it if the reactor drops → fails safe)

Verdicts steer toward resilient-balanced:
  no-source-surplus   — nothing to feed the reactor (it'd deplete base)
  reactor-oversized   — reactors need more N than the source makes →
                        they starve/crash
  net-accumulating    — reactor too small → excess N remains
  reactor-load-bearing— balanced but base surplus too large → FRAGILE,
                        spikes toxic if the reactor stops
  resilient-balanced  — the target: modest base surplus, reactor sized
                        to it, fails safe

@consumers
  - microalgae.reactor_api (loop endpoints)
@see /SALTWATER_FOOD_FOREST_SPEC.md, [[microalgae-reactors]]
"""

import json

from microalgae.reactor_analysis import (
    STARVE_FRACTION, _f, _named, _operating_point, _rows,
)

#: Base surplus at/under this (mg N/day) is small enough for the passive
#: regulators + harvest to hold if the reactor goes offline (resilient).
#: A design knob — kept constant here, flagged as a prior.
RESILIENCE_BAND_MG_N = 250.0
BALANCE_FLOOR_MG_N = 100.0


def _parse(text, fallback='[]'):
    try:
        loaded = json.loads(text or fallback)
        return loaded if loaded is not None else json.loads(fallback)
    except Exception:
        return json.loads(fallback)


def _source_surplus(manager, source_names, source_kind, override):
    """Base net-N surplus summed over the source systems (reactor
    excluded). Positive = excess the reactors can consume."""
    if override is not None:
        return float(override), 'explicit override'
    total = 0.0
    detail = []
    for name in source_names:
        n = 0.0
        src = 'assumed 0 (unresolved)'
        if source_kind == 'tank':
            try:
                from tanks.tank_analysis import nutrient_balance
                bal = nutrient_balance(manager, name)
                if bal.get('ok'):
                    n = float(bal['netNitrogenMgPerDay'])
                    src = 'tank net N balance'
            except Exception:
                pass
        total += n
        detail.append({'source': name, 'netNMgPerDay': round(n, 2),
                       'resolvedBy': src})
    return total, detail


def _reactor_demand(manager, reactor_names):
    """Total N need + CO2 potential over the loop's reactors."""
    total_need = 0.0
    total_co2 = 0.0
    per = []
    for name in reactor_names:
        reactor = _named(manager, 'AlgaeReactorDefinition', name)
        if reactor is None:
            continue
        strain = _named(manager, 'AlgaeStrain',
                        getattr(reactor, 'strain_name', ''))
        if strain is None:
            continue
        op = _operating_point(strain, reactor)
        total_need += op['n_needed_mg_day']
        total_co2 += op['co2_g_day']
        per.append({'reactor': name,
                    'nNeedMgPerDay': round(op['n_needed_mg_day'], 2),
                    'co2PotentialGPerDay': round(op['co2_g_day'], 2)})
    return total_need, total_co2, per


def chained_balance(manager, loop_name, source_surplus_override=None):
    """The composite balance + resilience verdict for an integrated
    loop. Steers toward resilient-balanced regardless of design mode."""
    loop = _named(manager, 'IntegratedLoopDefinition', loop_name)
    if loop is None:
        return {'ok': False,
                'error': f"no IntegratedLoopDefinition named "
                         f"'{loop_name}'"}
    mode = getattr(loop, 'design_mode', 'reactor-first')
    sources = _parse(getattr(loop, 'source_system_names_json', '[]'))
    reactors = _parse(getattr(loop, 'reactor_names_json', '[]'))
    if not reactors:
        return {'ok': False,
                'error': f"loop '{loop_name}' has no reactors",
                'suggestion': {'knob': 'reactor_names_json',
                               'action': 'add AlgaeReactorDefinition names',
                               'evidence': 'the reactors do the '
                                           'consuming + decarbonizing'}}

    base_surplus, source_detail = _source_surplus(
        manager, sources, getattr(loop, 'source_kind', 'tank'),
        source_surplus_override)
    total_need, total_co2, reactor_detail = _reactor_demand(
        manager, reactors)

    draw = max(0.0, min(base_surplus, total_need))
    composite_net = base_surplus - draw
    supply_fraction = (draw / total_need) if total_need > 0 else 0.0
    co2_fixed = total_co2 * supply_fraction
    band = max(BALANCE_FLOOR_MG_N, 0.1 * abs(base_surplus))
    resilient = 0.0 < base_surplus <= RESILIENCE_BAND_MG_N

    suggestions = []
    if base_surplus <= 0:
        verdict = 'no-source-surplus'
        limiting = (f'the source produces no excess nitrogen '
                    f'(base surplus {base_surplus:.0f} mg N/day) — the '
                    f'reactor would draw the base into depletion')
        suggestions.append(_size_suggestion(mode, total_need,
                                             base_surplus))
    elif supply_fraction < STARVE_FRACTION:
        verdict = 'reactor-oversized'
        limiting = (f'reactors need {total_need:.0f} mg N/day but the '
                    f'source only makes {base_surplus:.0f} — the culture '
                    f'starves and crashes')
        suggestions.append(_size_suggestion(mode, total_need,
                                            base_surplus))
    elif composite_net > band:
        verdict = 'net-accumulating'
        limiting = (f'reactors consume {draw:.0f} of {base_surplus:.0f} '
                    f'mg N/day — {composite_net:.0f} excess remains and '
                    f'accumulates')
        suggestions.append(_size_suggestion(mode, total_need,
                                            base_surplus))
    elif not resilient:
        verdict = 'reactor-load-bearing'
        limiting = (f'composite balances, BUT the base surplus '
                    f'{base_surplus:.0f} mg N/day > resilience band '
                    f'{RESILIENCE_BAND_MG_N:.0f} — FRAGILE: it spikes '
                    f'toxic if the reactor stops')
        suggestions.append({
            'knob': 'reduce the source fish stock (or add passive '
                    'macroalgae / substrate denitrification)',
            'action': f'bring the base surplus down toward '
                      f'<= {RESILIENCE_BAND_MG_N:.0f} mg N/day so the '
                      f'passive crew holds it if the reactor drops',
            'evidence': 'a resilient design uses the reactor as a bonus '
                        'layer, not the load-bearing balance'})
    else:
        verdict = 'resilient-balanced'
        limiting = None

    return {
        'ok': True, 'loop': loop_name, 'designMode': mode,
        'verdict': verdict,
        'balanced': verdict in ('resilient-balanced',
                                'reactor-load-bearing'),
        'resilient': resilient,
        'baseSurplusMgNPerDay': round(base_surplus, 2),
        'reactorNeedMgNPerDay': round(total_need, 2),
        'reactorDrawMgNPerDay': round(draw, 2),
        'compositeNetMgNPerDay': round(composite_net, 2),
        'supplyFraction': round(supply_fraction, 3),
        'resilienceBandMgNPerDay': RESILIENCE_BAND_MG_N,
        'co2FixedGPerDay': round(co2_fixed, 2),
        'co2FixedKgPerYear': round(co2_fixed * 365.0 / 1000.0, 3),
        'failSafeNote': ('base surplus is within the resilience band — '
                         'the passive regulators hold it if the reactor '
                         'goes offline' if resilient else
                         'base surplus exceeds the resilience band — the '
                         'system is NOT fail-safe without the reactor'),
        'sourceDetail': source_detail, 'reactorDetail': reactor_detail,
        'limitingFactor': limiting, 'suggestions': suggestions,
        'priorsFlagged': True,
        'note': 'composite = source excess − reactor draw; resilient '
                'means the base alone stays safe if the reactor stops. '
                'RESILIENCE_BAND is a design prior.'}


def _size_suggestion(mode, total_need, base_surplus):
    """Mode-tailored sizing advice toward resilient-balanced."""
    # An over-large base is fragile no matter the mode — shrink it first.
    if base_surplus > RESILIENCE_BAND_MG_N:
        return {
            'knob': 'reduce the source fish stock toward the resilience '
                    'band',
            'action': f'bring base surplus down toward '
                      f'<= {RESILIENCE_BAND_MG_N:.0f} mg N/day (fewer '
                      f'fish / more passive macroalgae + substrate) — a '
                      f'resilient design never leans on the reactor to '
                      f'drain a large excess',
            'evidence': f'base surplus {base_surplus:.0f} > resilience '
                        f'band {RESILIENCE_BAND_MG_N:.0f} mg N/day'}
    target = min(total_need, RESILIENCE_BAND_MG_N) if total_need > 0 \
        else RESILIENCE_BAND_MG_N
    if mode == 'add-on':
        return {
            'knob': 'introduce a MODEST headroom surplus into the '
                    'balanced base (a few more fish) + size the reactor '
                    'to it',
            'action': f'add ~{target:.0f} mg N/day of surplus (stay '
                      f'<= {RESILIENCE_BAND_MG_N:.0f}) and match reactor '
                      f'capacity to it',
            'evidence': f'base surplus {base_surplus:.0f}, reactor need '
                        f'{total_need:.0f} mg N/day'}
    return {
        'knob': 'size the base fish stock to the reactor (reactor-first)',
        'action': f'stock the source to produce ~{total_need:.0f} mg '
                  f'N/day (keep <= {RESILIENCE_BAND_MG_N:.0f} for '
                  f'resilience) so the reactor runs at capacity',
        'evidence': f'base surplus {base_surplus:.0f}, reactor need '
                    f'{total_need:.0f} mg N/day'}
