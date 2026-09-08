"""
@cross-cutting
@module casting.nesting_wizard_basis
@tags @xc:bindings

The endgame (Dustin 2026-08-05): START with a math object or a
FreeCAD-defined object, CHOOSE the material you want it made of,
and AUTOMATE the whole simulation pipeline into a full mold-nesting
process — with EVERY intermediate step visible.

  plan_nesting(manager, part, target_material)
      → picks the chain template parity demands (geopolymer = 1
        stage; a ceramic = invest → press → fire; a metal = invest →
        press → fire-to-fireclay → pour), creates the mold + chain +
        stage rows (derived, converging), then runs the ENTIRE
        pipeline in order: derive → master feasibility → pour
        loading → sprues/vents → fill sim → demold → full chain
        report (economics + coatings + shrink).

Every step returns its VERDICT and its VIEWABLE artifacts — the
shape rows it derived (part, scaled part, stock, mold body, sprued
body, sprued master — all renderable via the existing
/api/shapes/{name}/surface viewer) and, for the fill, the SimSpace
run. The plan and its steps persist as NestingPlanDefinition rows
so the /casting page lists them and every step is click-through
inspectable (per-object displays, never raw JSON).

Blockers anywhere make the PLAN's verdict blocked — with the step
and the reason named; the steps after a blocker still run where
they can, so the report shows everything wrong at once, not one
error per attempt.

@see /WAX_MOLD_NESTING_PLAN.md (the §3 cast-6 endgame payoff)
"""
# sap-2c INDEX (design §7): the classes live one-per-file under objects/nesting_wizard/;
# this file re-exports them (imports keep working) and holds what they share.
# The original imports stay: names this file imported were re-exported implicitly.

import json
from casting.custom.chain_analysis import chain_report
from casting.coatings_basis import chain_full_report
from casting.demold_basis import demold_plan
from casting.fill_sim_basis import compute_fill_rows, persist_fill_rows
from casting.custom.mold_geometry import (
    _mold_named, _resolve_imported_shape, derive_mold,
)
from casting.custom.pour_loading import pour_loading_report
from casting.custom.sprue_geometry import apply_sprue_strategy
from casting.custom.wax_feasibility import _row_named, _rows, master_report
from mathshapes.custom.shape_analysis import _named
from objectTreeDecorators import treeObject, treeObjectInit

from casting.objects.nesting_wizard._shared import FIRE_CERAMIC_SERVICE_MARGIN_C, GALVANIZE_TARGETS, _TIER_RANK, _stage_rows, _target_kind, _upsert, local_provenance, select_fire_ceramic  # noqa: F401
from casting.objects.nesting_wizard.NestingPlanDefinition import NestingPlanDefinition  # noqa: F401

from mathshapes.custom.shape_analysis import _named
from casting.custom.mold_geometry import (
    _mold_named, _resolve_imported_shape, derive_mold,
)
from casting.custom.wax_feasibility import _row_named, _rows, master_report
from casting.custom.sprue_geometry import apply_sprue_strategy
from casting.coatings_basis import chain_full_report
from casting.custom.chain_analysis import chain_report
from casting.fill_sim_basis import compute_fill_rows, persist_fill_rows
from casting.demold_basis import demold_plan
import json
from casting.custom.pour_loading import pour_loading_report

def plan_nesting(manager, part_shape_ref, target_material,
                 feedstock_name=None, stock_margin_cm=1.0):
    """The one-call pipeline: part × material → full nesting plan
    with every intermediate step's verdict + viewable artifacts."""
    from casting.casting_basis import MoldDefinition
    from casting.chain_basis import (
        CastingStageDefinition, MoldNestingChain,
    )
    # -- resolve the part (math shape OR FreeCAD import) --
    part = _named(manager, part_shape_ref)
    part_source = 'mathshape'
    if part is None or getattr(part, 'family', '') == 'imported-mesh':
        imported, _rec = _resolve_imported_shape(manager,
                                                 part_shape_ref)
        if imported is not None:
            part = imported
            part_source = 'imported-cad'
            part_shape_ref = getattr(imported, 'name', part_shape_ref)
    if part is None:
        return {'ok': False,
                'error': f"'{part_shape_ref}' names no math shape "
                         f'and no imported CAD object'}
    kind, target_row = _target_kind(manager, target_material)
    if kind is None:
        known = (['geopolymer']
                 + sorted(GALVANIZE_TARGETS)
                 + sorted(getattr(r, 'name', '') for r in
                          _rows(manager, 'CeramicSample'))
                 + sorted(getattr(r, 'name', '') for r in
                          _rows(manager,
                                'CastingMaterialThermalProfile')))
        return {'ok': False,
                'error': f"'{target_material}' is not a castable "
                         f'target here — absent data is absent',
                'knownTargets': known}
    if feedstock_name is None:
        core = [f for f in _rows(manager, 'MasterFeedstockDefinition')
                if getattr(f, 'priority', '') == 'core']
        feedstock_name = getattr(core[0], 'name', '') if core else ''
    if not feedstock_name:
        return {'ok': False, 'error': 'no master feedstock '
                                      'resolvable — name one'}

    base = f'nest--{part_shape_ref}--{target_material}'
    steps, blockers = [], []
    plan_findings = []

    # metals (and galvanized bases): the mold ceramic is SELECTED
    # from data, never assumed.
    fire_ceramic = None
    galvanize = None
    if kind in ('metal', 'galvanized'):
        pour = float(getattr(target_row, 'recommended_pour_c', 0.0)
                     or 0.0)
        fire_ceramic, fc_finding = select_fire_ceramic(manager, pour)
        if fire_ceramic is None:
            return {'ok': False, 'verdict': 'blocked',
                    'error': fc_finding,
                    'targetMaterial': target_material}
        if fc_finding:
            plan_findings.append(fc_finding)
    if kind == 'galvanized':
        galvanize = dict(GALVANIZE_TARGETS[target_material])

    def _step(label, res, visuals=(), keys=None):
        verdict = res.get('verdict') or ('ok' if res.get('ok')
                                         else 'refused')
        entry = {'step': label, 'verdict': verdict,
                 'visualShapes': [v for v in visuals if v],
                 'key': keys or {},
                 'blockers': res.get('blockers', []),
                 'findings': res.get('findings', []),
                 'error': res.get('error', '')}
        steps.append(entry)
        blockers.extend(f'{label}: {b}'
                        for b in res.get('blockers', []))
        if not res.get('ok') and res.get('error'):
            blockers.append(f"{label}: {res['error']}")
        return res

    # 1. mold + inversion
    _upsert(manager, 'MoldDefinition', MoldDefinition, {
        'name': f'{base}--mold', 'part_shape_ref': part_shape_ref,
        'part_source': part_source,
        'stock_margin_cm': stock_margin_cm,
        'shrink_allowance_pct': 0.0, 'provenance_id': 'nest-1',
        'notes': f'derived by plan_nesting for {target_material} '
                 f'(pass 1: deliberately uncompensated — the shrink '
                 f'report suggests the oversize)'})
    derived = _step('derive-mold',
                    derive_mold(manager, f'{base}--mold'),
                    visuals=(part_shape_ref,
                             ),  # filled below when ok
                    keys={})
    if derived.get('ok'):
        steps[-1]['visualShapes'] = [
            part_shape_ref, derived.get('scaledPartShape', ''),
            derived.get('stockShape', ''),
            derived.get('bodyShape', '')]
        steps[-1]['key'] = {'mode': derived.get('mode', 'field'),
                            'volumeCheck': derived.get('volumeCheck')}

    # 2. chain + stages (the template parity demands)
    _upsert(manager, 'MoldNestingChain', MoldNestingChain, {
        'name': base, 'target_part_shape_ref': part_shape_ref,
        'mold_def_ref': f'{base}--mold', 'provenance_id': 'nest-1',
        'notes': f'auto-planned: {part_shape_ref} in '
                 f'{target_material}'})
    stage_kind = 'metal' if kind == 'galvanized' else kind
    for st in _stage_rows(stage_kind, base, feedstock_name,
                          target_material, target_row,
                          fire_ceramic=fire_ceramic):
        _upsert(manager, 'CastingStageDefinition',
                CastingStageDefinition, st)
    if galvanize is not None:
        # stage 5: the hot dip — a CONVERSION on the demolded part
        # (parity does not flip); the part's own solidus is the
        # ceiling it must not approach.
        _upsert(manager, 'CastingStageDefinition',
                CastingStageDefinition, dict(
                    name=f'{base}-5-galvanize', chain_ref=base,
                    sequence=5, stage_kind='conversion',
                    mold_material_ref=galvanize['base'],
                    cast_material_ref=galvanize['dip'],
                    target_material_ref=target_material,
                    process_temp_c=galvanize['dip_temp_c'],
                    removal_route='', is_prior=True,
                    provenance_id='nest-1',
                    notes=f"hot-dip {galvanize['dip']} at "
                          f"{galvanize['dip_temp_c']:.0f}°C "
                          f"({galvanize['claim']})"))
    gates = _step('chain-gates', chain_report(manager, base),
                  keys={})
    if gates.get('ok'):
        steps[-1]['key'] = {'parity': gates['parity'],
                            'stages': len(gates['stages'])}

    # 3. master feasibility (print/CNC + self-support + time)
    feas = _step('master-feasibility',
                 master_report(manager, f'{base}--mold',
                               feedstock_name=feedstock_name))
    if feas.get('ok'):
        steps[-1]['key'] = {
            'feedstock': feas.get('feedstock'),
            'route': feas.get('route'),
            'printHours': (feas.get('printTime') or {}).get(
                'estimatedHours')}

    # 4. pour loading (stage-1 survival)
    pour = _step('pour-loading',
                 pour_loading_report(manager, f'{base}--mold',
                                     feedstock_name=feedstock_name,
                                     cure_temp_c=40.0))
    if pour.get('ok'):
        steps[-1]['key'] = {
            'wallUtilization': (pour.get('wallBending') or {}).get(
                'utilization'),
            'exothermMarginC': (pour.get('exotherm') or {}).get(
                'marginC'),
            'buoyancyAnchorN': (pour.get('buoyancy') or {}).get(
                'anchorForceN')}

    # 5. sprues + vents (field molds; grid molds are a named seam)
    sprue = apply_sprue_strategy(manager, f'{base}--mold',
                                 'top-gate-default')
    _step('sprues-vents', sprue,
          visuals=(sprue.get('spruedBodyShape', ''),
                   sprue.get('spruedMasterShape', '')),
          keys={'removability': (sprue.get('removability') or {}).get(
              'worstWinsScore'),
                'vents': len(sprue.get('vents', []))})

    # 6. fill sim + its viewable run
    if sprue.get('ok'):
        run_name = f'{base}--fill'
        fill_rows = compute_fill_rows(manager, f'{base}--mold',
                                      run_name)
        if fill_rows.get('ok'):
            persist_fill_rows(manager, fill_rows['rows'])
        _step('fill-sim', fill_rows,
              keys=dict(fill_rows.get('summary') or {},
                        simulationRun=run_name,
                        scene='mold-fill-3d'))
    else:
        _step('fill-sim',
              {'ok': False,
               'error': 'skipped — no sprue set (grid-path molds '
                        'gain fill with the mesh-channel seam, '
                        'named)'})

    # 7. demold
    dm_method = 'melt-out' if kind != 'geopolymer' else 'mechanical'
    demold = _step('demold',
                   demold_plan(manager, f'{base}--mold',
                               method=dm_method,
                               cast_material='geopolymer-slurry'))
    if demold.get('ok'):
        steps[-1]['key'] = {'method': dm_method,
                            'parting': demold.get('parting')}

    # 8. the composed chain report (economics + coatings + shrink)
    full = _step('chain-full-report',
                 chain_full_report(manager, base))
    if full.get('ok'):
        steps[-1]['key'] = {
            'totalMoldMassKg': full.get('totalMoldMassKg'),
            'recyclingRoutes': full.get('recyclingRoutes'),
            'shrinkCompensationPct': ((full.get('shrink') or {}).get(
                'compensation') or {}).get('recommendedPct')}

    # galvanized: estimate the zinc the dip consumes off the part's
    # MEASURED surface area (grid/analytic, whichever the shape has).
    if galvanize is not None:
        from mathshapes.custom.shape_analysis import shape_properties
        props = shape_properties(manager, part_shape_ref)
        area_cm2 = float(props.get('surfaceAreaCm2') or 0.0) \
            if props.get('ok') else 0.0
        if area_cm2 > 0:
            zinc_g = (area_cm2 / 1.0e4) \
                * (galvanize['coating_um'] / 1.0e6) \
                * galvanize['zinc_density_kg_m3'] * 1000.0
            galvanize['zincMassG'] = round(zinc_g, 3)
            galvanize['surfaceAreaCm2'] = round(area_cm2, 2)
        else:
            plan_findings.append('galvanize zinc estimate '
                                 'unavailable — part surface area '
                                 'unmeasurable')

    verdict = 'blocked' if blockers else 'feasible'
    plan_fields = {
        'name': base, 'part_shape_ref': part_shape_ref,
        'target_material': target_material, 'chain_ref': base,
        'mold_ref': f'{base}--mold',
        'feedstock_ref': feedstock_name, 'verdict': verdict,
        'steps_json': json.dumps(steps),
        'report_json': json.dumps({'blockers': blockers}),
        'provenance_id': 'nest-1'}
    _upsert(manager, 'NestingPlanDefinition', NestingPlanDefinition,
            plan_fields)
    return {'ok': True, 'plan': base, 'verdict': verdict,
            'part': part_shape_ref, 'partSource': part_source,
            'targetMaterial': target_material, 'chainKind': kind,
            'feedstock': feedstock_name,
            'fireCeramic': fire_ceramic,
            'galvanize': galvanize,
            'localProvenance': (local_provenance(
                manager, fire_ceramic, target_row, galvanize)
                if kind in ('metal', 'galvanized') else None),
            'findings': plan_findings,
            'steps': steps, 'blockers': blockers,
            'note': 'every step lists its viewable shapes '
                    '(/api/shapes/{name}/surface) and the fill its '
                    'SimSpace run — the visual trail Dustin asked '
                    'for; polish lands on the /casting page.'}
