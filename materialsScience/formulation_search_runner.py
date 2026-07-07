"""
@module materialsScience.formulation_search_runner

Execution + persistence for FormulationSearchDefinition rows: the seam
that turns the stateless composite_search / batch_refine engines into
object-tree runs ([[object-coherence]]), and the home of the
STAGED-FIDELITY ladder:

  screening (always)  — rules of mixtures + thermal gate: IS the search.
  verify (knob)       — FEM homogenization on the top shortlistN
                        candidates; per-candidate honest refusals when
                        inputs are missing or the engine ladder is
                        down. Never blocks or alters screening scores.
  evidence (knob)     — NEVER auto-runs (autoRun=false): emits
                        suggestions naming the winners' components'
                        level-4 MaterialScaleDefinition rows that
                        /api/msci/scale-definitions/execute can mark as
                        DFT evidence.

Persistence realism: only min(results_keep_top_n, ranked) candidates +
every winner + every FEM-shortlist member become rows; the run row
keeps the honest totals; the FULL report is returned to the caller.

promote_winner_to_scale_definition is the EXPLICIT Track-C lineage
knob: a chosen candidate becomes a level-1 MaterialScaleDefinition row
derived from the base material — a button, never automatic.
"""

import json
from datetime import datetime, timezone

from materialsScience.composite_search import (
    load_legacy_seed_data, normalize_targets, search_composites,
)
from materialsScience.batch_refine import refine_formulation


def _now():
    return datetime.now(timezone.utc).isoformat(timespec='seconds')


def _rows(manager, class_name):
    table = (manager.objectTables or {}).get(class_name, {}) or {}
    return list(table.values()) if isinstance(table, dict) else list(table)


def _row_by_name(manager, class_name, name):
    return next((r for r in _rows(manager, class_name)
                 if getattr(r, 'name', '') == name), None)


def _parse(blob, default):
    try:
        parsed = json.loads(blob or '')
        return parsed if isinstance(parsed, type(default)) else default
    except (TypeError, ValueError):
        return default


# ---------------------------------------------------------------------
# Fidelity rung 2 — FEM homogenization over the shortlist.
# ---------------------------------------------------------------------

def verify_shortlist_fem(candidates, verify_cfg, additives_by_id):
    """Run fem.effective-conductivity per shortlisted candidate.

    `verify_cfg`: {"engine": "fem.effective-conductivity",
                   "shortlistN": 5, "property": "thermalConductivity",
                   "matrixK": <base k>, "inclusionK": {name-or-id: k},
                   "refine": 5}

    Mutates each candidate dict with a `femVerify` entry — 'verified'
    with the computed k_eff (and the Voigt/Reuss window), or 'refused'
    with the exact missing knob / engine failure. Screening scores are
    never altered. Returns the per-candidate summaries."""
    engine_key = verify_cfg.get('engine', 'fem.effective-conductivity')
    shortlist_n = int(verify_cfg.get('shortlistN', 5) or 5)
    matrix_k = verify_cfg.get('matrixK')
    inclusion_k = verify_cfg.get('inclusionK') or {}
    refine = int(verify_cfg.get('refine', 5) or 5)
    summaries = []
    for cand in candidates[:shortlist_n]:
        entry = {'engine': engine_key}
        if matrix_k is None:
            entry.update(status='refused',
                         reason="verify.matrixK missing — the base "
                                "material's thermal conductivity is a "
                                "manual-entry knob")
        else:
            entry.update(_fem_verify_candidate(
                cand, engine_key, float(matrix_k), inclusion_k,
                additives_by_id, refine))
        cand['femVerify'] = entry
        summaries.append(entry)
    for cand in candidates[shortlist_n:]:
        cand.setdefault('femVerify', {'status': 'skipped',
                                      'reason': f'outside the top '
                                                f'{shortlist_n} shortlist'})
    return summaries


def _fem_verify_candidate(cand, engine_key, matrix_k, inclusion_k,
                          additives_by_id, refine):
    from materialsScience.scale_execution import ENGINE_REGISTRY
    runner = ENGINE_REGISTRY.get(engine_key)
    if runner is None:
        return {'status': 'refused',
                'reason': f"engine '{engine_key}' not in ENGINE_REGISTRY"}
    per_component = []
    for comp in cand.get('components', []):
        mat_id = comp.get('materialId', '')
        additive = additives_by_id.get(mat_id, {})
        name = additive.get('name', mat_id)
        k = inclusion_k.get(name, inclusion_k.get(mat_id))
        if k is None:
            per_component.append({
                'component': name, 'status': 'refused',
                'reason': f"verify.inclusionK['{name}'] missing — "
                          "inclusion conductivity is a manual-entry "
                          "knob"})
            continue
        # wt% ≈ vol% is an explicit ASSUMPTION (densities of waxes and
        # their additives are same-order); flagged on the result.
        vf = float(comp.get('weightPercent', 0.0)) / 100.0
        try:
            result = runner({'matrixK': matrix_k, 'inclusionK': float(k),
                             'volumeFraction': vf, 'refine': refine})
        except Exception as e:                       # engine crash =
            result = {'ok': False, 'error': str(e)}  # honest refusal
        if result.get('ok'):
            per_component.append({
                'component': name, 'status': 'verified',
                'volumeFraction': vf,
                'assumption': 'wt% treated as vol%',
                **{k2: v for k2, v in result.items() if k2 != 'ok'}})
        else:
            per_component.append({
                'component': name, 'status': 'refused',
                'reason': result.get('error', 'engine refused'),
                **{k2: v for k2, v in result.items()
                   if k2 in ('suggestion', 'suggestions')}})
    verified = [c for c in per_component if c['status'] == 'verified']
    return {'status': 'verified' if verified and len(verified)
                      == len(per_component)
                      else ('partial' if verified else 'refused'),
            'components': per_component}


# ---------------------------------------------------------------------
# Fidelity rung 3 — DFT evidence SUGGESTIONS (never auto-run).
# ---------------------------------------------------------------------

def suggest_dft_evidence(manager, winners, evidence_cfg, additives_by_id):
    """For each winner component, name the level-4
    MaterialScaleDefinition row a DFT run could mark as evidence — or
    the honest gap that no such row exists yet. Suggestions only."""
    if evidence_cfg.get('autoRun'):
        # The knob exists but stays suggestion-only by design; say so
        # instead of silently executing ([[knobs-and-suggestions]]).
        return [{'action': 'autoRun=true is not honored',
                 'reason': 'DFT evidence stays an explicit per-row '
                           'action (POST /api/msci/scale-definitions/'
                           'execute); flip it there',
                 'evidence': {'evidence_cfg': evidence_cfg}}]
    scale_rows = _rows(manager, 'MaterialScaleDefinition') if manager else []
    l4_by_material = {}
    for row in scale_rows:
        if int(getattr(row, 'scale_level', -1) or -1) == 4:
            l4_by_material.setdefault(
                getattr(row, 'material_name', ''), []).append(
                getattr(row, 'name', ''))
    suggestions = []
    seen = set()
    for winner in winners:
        for comp in winner.get('components', []):
            mat_id = comp.get('materialId', '')
            if mat_id in seen:
                continue
            seen.add(mat_id)
            name = additives_by_id.get(mat_id, {}).get('name', mat_id)
            slug = name.lower().replace(' ', '-')
            rows = l4_by_material.get(slug) or l4_by_material.get(name)
            if rows:
                suggestions.append({
                    'action': f"POST /api/msci/scale-definitions/execute "
                              f"{{'name': '{rows[0]}'}}",
                    'reason': f"attach quantum-level evidence to winner "
                              f"component '{name}'",
                    'evidence': {'l4Rows': rows,
                                 'engine': evidence_cfg.get('engine', '')},
                })
            else:
                suggestions.append({
                    'action': f"create a level-4 MaterialScaleDefinition "
                              f"for '{name}' (EngineComputation, engine="
                              f"'{evidence_cfg.get('engine', 'dft.molecular-energy')}')",
                    'reason': 'no quantum-level row exists for this '
                              'winner component yet — an honest gap, '
                              'not an error',
                    'evidence': {'material': name, 'l4Rows': []},
                })
    return suggestions


# ---------------------------------------------------------------------
# The run itself.
# ---------------------------------------------------------------------

def run_formulation_search(manager, search_def_name, *,
                           continue_after_winner=None, attempt_tag='',
                           knob_overrides=None, seed_data=None):
    """Execute a FormulationSearchDefinition end to end: resolve config,
    run the mode engine, run the fidelity ladder, persist the run +
    top-N candidate rows, return the FULL report (report['run'] names
    the persisted row)."""
    definition = _row_by_name(
        manager, 'FormulationSearchDefinition', search_def_name)
    if definition is None:
        return {'ok': False,
                'error': f"no FormulationSearchDefinition named "
                         f"'{search_def_name}'"}
    if not getattr(definition, 'enabled', True):
        return {'ok': False,
                'error': f"'{search_def_name}' is disabled (enabled=False "
                         "is a knob on the row)"}

    data = seed_data or load_legacy_seed_data()
    additives = data['additives']
    pool = _parse(getattr(definition, 'additive_pool_json', ''), [])
    if pool:
        wanted = set(pool)
        additives = [a for a in additives
                     if a.get('name') in wanted or a.get('id') in wanted]
    base_properties = _parse(
        getattr(definition, 'base_properties_json', ''), {})
    inline_targets = _parse(getattr(definition, 'targets_json', ''), [])
    if inline_targets:
        targets = normalize_targets(inline_targets)
    else:
        profile_id = getattr(definition, 'target_profile_id', '')
        target_rows = [t for t in data['targets']
                       if t['profileId'] == profile_id]
        if not target_rows:
            return {'ok': False,
                    'error': f"no PropertyTargets for profile "
                             f"'{profile_id}' and no inline targets",
                    'knownProfiles': sorted(
                        {t['profileId'] for t in data['targets']})}
        targets = normalize_targets(target_rows)

    knobs = _parse(getattr(definition, 'knobs_json', ''), {})
    knobs.update(knob_overrides or {})
    if continue_after_winner is not None:
        knobs['continueAfterWinner'] = bool(continue_after_winner)
    mode = getattr(definition, 'mode', 'grid') or 'grid'
    process = getattr(definition, 'process', '') or None
    thermal_knobs = _parse(
        getattr(definition, 'thermal_knobs_json', ''), {})
    thermal_profiles = None
    if process:
        from materialsScience.thermal_windows import profiles_from_rows
        thermal_profiles = profiles_from_rows(
            _rows(manager, 'ThermalProcessingProfile')) if manager else {}

    common = dict(
        base_material_name=getattr(definition, 'base_material_name', ''),
        process=process, thermal_profiles=thermal_profiles,
        thermal_knobs=thermal_knobs or None, raws=data['raws'],
        sourcingPolicy=getattr(definition, 'sourcing_policy',
                               'fossil-free-local'),
    )
    started = _now()
    try:
        if mode == 'refine':
            refine_knobs = {k: v for k, v in knobs.items()
                            if k in ('start_components', 'loadingStep',
                                     'minLoadingStep', 'perAdditiveCap',
                                     'maxTotalLoad', 'maxBatches')}
            report = refine_formulation(
                base_properties, targets, additives, data['effects'],
                **refine_knobs, **common)
            report['ok'] = True
            ranked = [report['best']] if report.get('best') else []
            winners = [c for c in ranked if c.get('meets')]
        else:
            grid_knobs = {k: v for k, v in knobs.items()
                          if k in ('maxAdditives', 'loadingStep',
                                   'perAdditiveCap', 'maxTotalLoad',
                                   'stopPolicy', 'continueAfterWinner',
                                   'maxCandidates')}
            report = search_composites(
                base_properties, targets, additives, data['effects'],
                data['compatibilizers'], **grid_knobs, **common)
            report['ok'] = True
            ranked = report.get('ranked', [])
            winners = report.get('winners', [])
    except Exception as e:
        report = {'ok': False, 'error': f'{mode} engine failed: {e}'}
        _persist_run(manager, definition, mode, attempt_tag,
                     status='failed', outcome='', report=report,
                     ranked=[], winners=[], started=started)
        return report

    # --- Fidelity ladder ------------------------------------------------
    fidelity_cfg = _parse(
        getattr(definition, 'fidelity_stages_json', ''), {})
    additives_by_id = {a['id']: a for a in data['additives']}
    fidelity_summary = {
        'screening': {'status': 'scored',
                      'engine': (fidelity_cfg.get('screening') or {}).get(
                          'engine', 'rules-of-mixtures')},
    }
    verify_cfg = fidelity_cfg.get('verify')
    if verify_cfg:
        summaries = verify_shortlist_fem(ranked, verify_cfg,
                                         additives_by_id)
        statuses = [s.get('status') for s in summaries]
        fidelity_summary['verify'] = {
            'engine': verify_cfg.get('engine', ''),
            'shortlistN': verify_cfg.get('shortlistN', 5),
            'statuses': statuses,
        }
    evidence_cfg = fidelity_cfg.get('evidence')
    if evidence_cfg:
        dft_suggestions = suggest_dft_evidence(
            manager, winners, evidence_cfg, additives_by_id)
        report['dftEvidenceSuggestions'] = dft_suggestions
        fidelity_summary['evidence'] = {
            'engine': evidence_cfg.get('engine', ''),
            'autoRun': False,
            'suggestions': len(dft_suggestions),
        }
    report['fidelity'] = fidelity_summary

    run_name = _persist_run(
        manager, definition, mode, attempt_tag, status='complete',
        outcome=report.get('outcome')
        or ('met' if winners else
            ('exhausted' if report.get('searchComplete', True)
             else 'first-winner')),
        report=report, ranked=ranked, winners=winners, started=started)
    report['run'] = run_name
    return report


def _persist_run(manager, definition, mode, attempt_tag, *, status,
                 outcome, report, ranked, winners, started):
    """Create the FormulationSearchRun + top-N FormulationCandidateResult
    rows. Returns the run row's name ('' when no manager, e.g. dry
    selftests)."""
    if manager is None:
        return ''
    from materialsScience.formulation_search_run import FormulationSearchRun
    from materialsScience.formulation_candidate_result import (
        FormulationCandidateResult,
    )
    search_name = getattr(definition, 'name', '')
    existing = [r for r in _rows(manager, 'FormulationSearchRun')
                if getattr(r, 'search_ref', '') == search_name]
    tag = f'{attempt_tag}-' if attempt_tag else ''
    run_name = f'{search_name}-run-{tag}{len(existing) + 1}'
    keep_n = int(getattr(definition, 'results_keep_top_n', 25) or 25)
    winner_ids = {json.dumps(w.get('components')) for w in winners}
    to_persist = list(ranked[:keep_n])
    for w in winners:
        if json.dumps(w.get('components')) not in {
                json.dumps(c.get('components')) for c in to_persist}:
            to_persist.append(w)
    run = FormulationSearchRun(
        name=run_name, search_ref=search_name, mode=mode, status=status,
        outcome=outcome,
        evaluated=int(report.get('evaluated', 0)
                      or report.get('batches', 0) or 0),
        sweep_capped=bool(report.get('sweepCapped', False)),
        winners_count=len(winners),
        assumptions_json=json.dumps(report.get('assumptions', [])),
        gap_analysis_json=json.dumps(report.get('gapAnalysis', [])),
        trajectory_json=json.dumps(report.get('trajectory', [])),
        sourcing_policy=report.get(
            'sourcingPolicy',
            getattr(definition, 'sourcing_policy', '')),
        excluded_by_sourcing_json=json.dumps(
            report.get('excludedBySourcingPolicy', [])),
        predictable_properties_json=json.dumps(
            report.get('predictableProperties', [])),
        fidelity_summary_json=json.dumps(report.get('fidelity', {})),
        started_at=started, finished_at=_now(),
        error=report.get('error', ''),
        manager=manager)
    cand_rows = []
    for rank, cand in enumerate(to_persist, start=1):
        cand_rows.append(FormulationCandidateResult(
            name=f'{run_name}-cand-{rank}',
            run_ref=run_name, rank=rank,
            components_json=json.dumps(cand.get('components', [])),
            predicted_properties_json=json.dumps(cand.get('predicted', {})),
            score=float(cand.get('score', 0.0) or 0.0),
            meets_targets=bool(cand.get('meets', False)),
            violations_json=json.dumps(cand.get('violations', [])),
            unpredicted_json=json.dumps(cand.get('unpredicted', [])),
            thermal_verdict_json=json.dumps(cand.get('thermal', {})),
            fidelity_json=json.dumps(
                {'screening': {'status': 'scored'},
                 'femVerify': cand.get('femVerify',
                                       {'status': 'skipped'}),
                 'dftEvidence': {'status': 'suggested'
                                 if json.dumps(cand.get('components'))
                                 in winner_ids and report.get(
                                     'dftEvidenceSuggestions')
                                 else 'none'}}),
            is_winner=json.dumps(cand.get('components')) in winner_ids,
            manager=manager))
    # Explicitly write BOTH the run row and every candidate row — a row
    # only survives a backend restart if saveInstanceInDB ran for it
    # (run-2's candidate was lost live because only the run was saved;
    # run-1's survived only because the PROMOTION flow saved it).
    try:
        manager.db.saveInstanceInDB(run)
        for row in cand_rows:
            manager.db.saveInstanceInDB(row)
    except Exception:
        pass
    report['persistedCandidates'] = len(to_persist)
    return run_name


# ---------------------------------------------------------------------
# The explicit promotion knob (Track C lineage).
# ---------------------------------------------------------------------

def promote_winner_to_scale_definition(manager, run_name, candidate_name):
    """EXPLICIT knob: a chosen candidate becomes a level-1
    MaterialScaleDefinition row derived from the search's base material.
    Never called by the search itself."""
    run = _row_by_name(manager, 'FormulationSearchRun', run_name)
    if run is None:
        return {'ok': False,
                'error': f"no FormulationSearchRun named '{run_name}'"}
    cand = _row_by_name(
        manager, 'FormulationCandidateResult', candidate_name)
    if cand is None or getattr(cand, 'run_ref', '') != run_name:
        return {'ok': False,
                'error': f"no candidate '{candidate_name}' on run "
                         f"'{run_name}'"}
    if getattr(cand, 'promoted_scale_def', ''):
        return {'ok': True, 'alreadyPromoted': True,
                'scaleDefinition': cand.promoted_scale_def}
    definition = _row_by_name(manager, 'FormulationSearchDefinition',
                              getattr(run, 'search_ref', ''))
    base_name = (getattr(definition, 'base_material_name', '')
                 if definition else '') or 'base'
    base_slug = base_name.lower().replace(' ', '-')
    fem = (_parse(getattr(cand, 'fidelity_json', ''), {})
           .get('femVerify', {}) or {})
    fem_verified = fem.get('status') == 'verified'
    scale_def_name = f'{candidate_name}@L1'
    # Lineage: derived from the base material's L1 row when one exists,
    # else its L0 row, else the base name itself (still honest lineage).
    base_rows = {f'{base_slug}@L1', f'{base_slug}@L0'}
    existing_base = next(
        (getattr(r, 'name', '') for r in
         _rows(manager, 'MaterialScaleDefinition')
         if getattr(r, 'name', '') in base_rows), base_slug)
    from materialsScience.materials_basis import MaterialScaleDefinition
    row = MaterialScaleDefinition(
        name=scale_def_name,
        material_name=f'{base_slug}-formulation',
        scale_level=1, scale_category='continuum',
        definition_class='FormulationCandidateResult',
        definition_ref=candidate_name,
        status='defined' if fem_verified else 'partial',
        derived_from_name=existing_base,
        derivation_method='rules-of-mixtures'
                          + (' + fem-verified' if fem_verified else ''),
        parameters_json=json.dumps({
            'components': _parse(
                getattr(cand, 'components_json', ''), []),
            'predicted': _parse(
                getattr(cand, 'predicted_properties_json', ''), {}),
            'score': getattr(cand, 'score', 0.0),
        }),
        notes=f'Promoted from formulation run {run_name} (explicit '
              'user action).',
        manager=manager)
    cand.promoted_scale_def = scale_def_name
    try:
        manager.db.saveInstanceInDB(row)
        manager.db.saveInstanceInDB(cand)
    except Exception:
        pass
    return {'ok': True, 'scaleDefinition': scale_def_name,
            'status': row.status,
            'derivationMethod': row.derivation_method,
            'derivedFrom': existing_base}
