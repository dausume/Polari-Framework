"""
@cross-cutting
@module casting.nesting_wizard
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

import json

from casting.chain_analysis import chain_report
from casting.coatings import chain_full_report
from casting.demold import demold_plan
from casting.fill_sim import compute_fill_rows, persist_fill_rows
from casting.mold_geometry import (
    _mold_named, _resolve_imported_shape, derive_mold,
)
from casting.pour_loading import pour_loading_report
from casting.sprue_geometry import apply_sprue_strategy
from casting.wax_feasibility import _row_named, _rows, master_report
from mathshapes.shape_analysis import _named
from objectTreeDecorators import treeObject, treeObjectInit


class NestingPlanDefinition(treeObject):
    """One derived nesting plan: part × target material → chain +
    every step's verdict and viewable artifacts. DERIVED — re-runs
    reconverge."""

    @treeObjectInit
    def __init__(self, name: str = '', part_shape_ref: str = '',
                 target_material: str = '', chain_ref: str = '',
                 mold_ref: str = '', feedstock_ref: str = '',
                 verdict: str = '', steps_json: str = '[]',
                 report_json: str = '{}', is_prior: bool = True,
                 notes: str = '', provenance_id: str = '',
                 manager=None):
        self.name = name
        self.part_shape_ref = part_shape_ref
        self.target_material = target_material
        self.chain_ref = chain_ref
        self.mold_ref = mold_ref
        self.feedstock_ref = feedstock_ref
        self.verdict = verdict
        self.steps_json = steps_json
        self.report_json = report_json
        self.is_prior = is_prior
        self.notes = notes
        self.provenance_id = provenance_id


def _upsert(manager, class_name, cls, fields):
    table = manager.objectTables.setdefault(class_name, {})
    existing = next((r for r in table.values()
                     if getattr(r, 'name', '') == fields['name']),
                    None)
    if existing is not None:
        for k, v in fields.items():
            setattr(existing, k, v)
        return existing
    made = None
    try:
        made = cls(**fields, manager=manager)
    except Exception:
        made = None
    if made is None or fields['name'] not in {
            getattr(r, 'name', None) for r in table.values()}:
        class _Row:
            pass
        r = _Row()
        for k, v in fields.items():
            setattr(r, k, v)
        table[fields['name']] = r
        return r
    return made


#: Galvanized targets = a cast base metal + a hot-dip coating metal.
#: The dip is a CONVERSION (parity does not flip); temps are
#: literature-approximate with the claim named. Zinc consumption is
#: estimated off the part's MEASURED surface area.
GALVANIZE_TARGETS = {
    'galvanized-bio-steel': {
        'base': 'plain-bio-steel-cast', 'dip': 'zinc-cast',
        'dip_temp_c': 450.0, 'coating_um': 80.0,
        'zinc_density_kg_m3': 7140.0,
        'claim': 'literature-approximate: hot-dip galvanizing '
                 '~450°C bath, ~80µm typical coating — measure the '
                 'real bath/thickness'},
}


def _target_kind(manager, target_material):
    """(kind, row) — geopolymer | ceramic | metal | galvanized."""
    if target_material in ('geopolymer', 'geopolymer-slurry'):
        return 'geopolymer', None
    if target_material in GALVANIZE_TARGETS:
        spec = GALVANIZE_TARGETS[target_material]
        base = (_row_named(manager, 'CastingMaterialThermalProfile',
                           spec['base']))
        if base is not None:
            return 'galvanized', base
        return None, None
    ceramic = _row_named(manager, 'CeramicSample', target_material)
    if ceramic is not None:
        return 'ceramic', ceramic
    metal = (_row_named(manager, 'CastingMaterialThermalProfile',
                        target_material)
             or next((r for r in _rows(
                 manager, 'CastingMaterialThermalProfile')
                 if getattr(r, 'material_ref', '')
                 == target_material), None))
    if metal is not None:
        return 'metal', metal
    return None, None


#: The mold ceramic must out-survive the pour by this named margin.
FIRE_CERAMIC_SERVICE_MARGIN_C = 50.0
_TIER_RANK = {'household': 0, 'common-industrial': 1,
              'mined-nonlocal': 2, 'lab-reagent': 3}


def select_fire_ceramic(manager, pour_temp_c):
    """The PLUGGABLE steel-enabler (Dustin 2026-08-05): choose the
    mold ceramic FROM DATA — service ceiling ≥ pour + margin, firing
    reachable by a furnace rung — ranked most-local, most-accessible,
    coolest-kiln first. Nothing qualifying = a refusal naming the
    best available, never a silent fireclay default."""
    rungs = _rows(manager, 'LadderRung')
    best_rung = max((float(getattr(r, 'max_temp_c', 0.0) or 0.0)
                     for r in rungs), default=None)
    need = pour_temp_c + FIRE_CERAMIC_SERVICE_MARGIN_C
    candidates = []
    for c in _rows(manager, 'CeramicSample'):
        svc = float(getattr(c, 'max_service_temp_c', 0.0) or 0.0)
        fire = float(getattr(c, 'peak_firing_temp_c', 0.0) or 0.0)
        if svc < need:
            continue
        if best_rung is not None and fire > best_rung:
            continue
        candidates.append(c)
    if not candidates:
        have = max((float(getattr(c, 'max_service_temp_c', 0.0)
                          or 0.0)
                    for c in _rows(manager, 'CeramicSample')),
                   default=0.0)
        return None, (f'no mold ceramic serves {pour_temp_c:.0f}°C '
                      f'+ {FIRE_CERAMIC_SERVICE_MARGIN_C:.0f}°C '
                      f'margin with a reachable firing (best '
                      f'available service {have:.0f}°C, best rung '
                      f'{best_rung or 0:.0f}°C) — a capability gap, '
                      f'named')
    pick = sorted(candidates, key=lambda c: (
        getattr(c, 'track', '') != 'local',
        _TIER_RANK.get(getattr(c, 'accessibility_tier', ''), 9),
        float(getattr(c, 'peak_firing_temp_c', 0.0) or 0.0)))[0]
    choice = {'name': getattr(pick, 'name', ''),
              'fireTempC': float(getattr(pick, 'peak_firing_temp_c',
                                         0.0) or 0.0),
              'serviceC': float(getattr(pick, 'max_service_temp_c',
                                        0.0) or 0.0),
              'tier': getattr(pick, 'accessibility_tier', ''),
              'track': getattr(pick, 'track', ''),
              'claim': getattr(pick, 'temp_claim_status', ''),
              'evidence': f'lowest-firing local/accessible ceramic '
                          f'whose service ceiling covers the pour '
                          f'+ {FIRE_CERAMIC_SERVICE_MARGIN_C:.0f}°C '
                          f'margin (rung ceiling '
                          f'{best_rung or 0:.0f}°C respected)'}
    finding = None
    if choice['track'] != 'local' or choice['tier'] in (
            'mined-nonlocal', 'lab-reagent'):
        finding = (f"mold ceramic {choice['name']} is NOT fully "
                   f"local ({choice['tier']}/{choice['track']}) — "
                   f'carried honestly, not hidden')
    return choice, finding


def _stage_rows(kind, base, feedstock, target_material, ceramic_row,
                fire_ceramic=None):
    """The chain template parity demands for this target."""
    common = {'is_prior': True, 'provenance_id': 'nest-1'}
    if kind == 'geopolymer':
        return [dict(name=f'{base}-1-pour', chain_ref=base,
                     sequence=1, stage_kind='cast',
                     mold_material_ref=feedstock,
                     cast_material_ref='geopolymer-slurry',
                     fill_method='gravity-pour', cure_temp_c=40.0,
                     removal_route='melt-out', **common)]
    if kind == 'ceramic':
        fire_target = target_material
        fire_temp = float(getattr(ceramic_row, 'peak_firing_temp_c',
                                  0.0) or 0.0)
    else:
        fire_target = (fire_ceramic or {}).get('name',
                                               'fireclay-firebrick')
        fire_temp = (fire_ceramic or {}).get('fireTempC', 1300.0)
    stages = [
        dict(name=f'{base}-1-invest', chain_ref=base, sequence=1,
             stage_kind='cast', mold_material_ref=feedstock,
             cast_material_ref='geopolymer-slurry',
             fill_method='gravity-pour', cure_temp_c=40.0,
             removal_route='melt-out', **common),
        dict(name=f'{base}-2-press', chain_ref=base, sequence=2,
             stage_kind='cast', mold_material_ref='geopolymer',
             cast_material_ref='plastic-clay', fill_method='press',
             mold_disposable=True, removal_route='mechanical',
             **common),
        dict(name=f'{base}-3-fire', chain_ref=base, sequence=3,
             stage_kind='conversion', mold_material_ref='geopolymer',
             cast_material_ref='plastic-clay',
             target_material_ref=fire_target,
             process_temp_c=fire_temp, mold_disposable=True,
             removal_route='mechanical', **common)]
    if kind == 'metal':
        stages.append(
            dict(name=f'{base}-4-pour', chain_ref=base, sequence=4,
                 stage_kind='cast',
                 mold_material_ref=fire_target,
                 cast_material_ref=getattr(
                     ceramic_row, 'name', target_material),
                 fill_method='gravity-pour',
                 removal_route='mechanical', **common))
    return stages


def local_provenance(manager, fire_ceramic, target_row, galvanize):
    """Dustin 2026-08-05: 'where is the mullite coming from if
    local? can we genuinely do fully local steel?' — answered from
    ROWS, not assertion. Each leg names its feedstocks, its furnace
    rung (with the prerequisite climb), and its honest gates."""
    legs, gaps = [], []
    rungs = sorted(_rows(manager, 'LadderRung'),
                   key=lambda r: float(getattr(r, 'max_temp_c', 0.0)
                                       or 0.0))

    def _rung_for(temp_c):
        for r in rungs:
            if float(getattr(r, 'max_temp_c', 0.0) or 0.0) >= temp_c:
                return r
        return None

    def _climb(rung):
        chain = []
        seen = set()
        while rung is not None:
            nm = getattr(rung, 'name', '')
            if nm in seen:
                break
            seen.add(nm)
            chain.append(nm)
            pre = getattr(rung, 'prerequisite_rung', '')
            rung = next((r for r in rungs
                         if getattr(r, 'name', '') == pre), None)
        return list(reversed(chain))

    # -- the mold ceramic leg --
    if fire_ceramic:
        cer = _row_named(manager, 'CeramicSample',
                         fire_ceramic['name'])
        try:
            feeds = json.loads(getattr(cer, 'feedstocks_json', '[]')
                               or '[]') if cer is not None else []
        except (TypeError, ValueError):
            feeds = []
        fire_rung = _rung_for(fire_ceramic['fireTempC'])
        legs.append({
            'leg': f"mold ceramic ({fire_ceramic['name']})",
            'track': fire_ceramic.get('track'),
            'feedstocks': feeds,
            'firingRungClimb': _climb(fire_rung) if fire_rung
            else None,
            'notes': getattr(cer, 'notes', '') if cer else ''})
        for f in feeds:
            # a feedstock that IS another catalog ceramic carries
            # its own honesty note (alumina: 'refining is the real
            # accessibility gate') — follow the reference.
            ref_row = _row_named(manager, 'CeramicSample',
                                 str(f.get('material', '')
                                     ).split()[0].strip(','))
            note = ' '.join([f.get('note', '') or '',
                             getattr(cer, 'notes', '') if cer
                             else '',
                             getattr(ref_row, 'notes', '')
                             if ref_row is not None else ''])
            if 'refin' in note.lower() or f.get('tier') not in (
                    'household', 'common-industrial'):
                gaps.append(f"{fire_ceramic['name']} feedstock "
                            f"'{f.get('material')}': "
                            f'{note.strip()[:160]} — the honest '
                            f'accessibility gate')
        # BOOTSTRAP: if this ceramic IS a furnace lining, its first
        # firing must happen in that rung's PREREQUISITE.
        for r in rungs:
            lining = getattr(r, 'lining_options_json', '') or ''
            if fire_ceramic['name'] not in lining:
                continue
            pre_name = getattr(r, 'prerequisite_rung', '')
            pre = next((x for x in rungs
                        if getattr(x, 'name', '') == pre_name), None)
            pre_max = float(getattr(pre, 'max_temp_c', 0.0) or 0.0) \
                if pre else 0.0
            if fire_ceramic['fireTempC'] > pre_max > 0:
                gaps.append(
                    f"BOOTSTRAP: {fire_ceramic['name']} lines "
                    f"{getattr(r, 'name', '')}, but firing it at "
                    f"{fire_ceramic['fireTempC']:.0f}°C exceeds the "
                    f'prerequisite {pre_name} ({pre_max:.0f}°C) — '
                    f'the first lining is lower-grade fireclay '
                    f'fired at {pre_max:.0f}°C, then re-fired in '
                    f'place as the new furnace climbs (the '
                    f'thermal-strain ladder exists exactly for '
                    f'this)')
                break
    # -- the metal leg --
    if target_row is not None:
        mat_ref = getattr(target_row, 'material_ref', '')
        mat = _row_named(manager, 'MaterialsScienceMaterial', mat_ref)
        pour = float(getattr(target_row, 'recommended_pour_c', 0.0)
                     or 0.0)
        melt_rung = _rung_for(pour)
        legs.append({
            'leg': f'base metal ({mat_ref})',
            'route': (getattr(mat, 'notes', '') or '')[:200]
            if mat is not None else 'MaterialsScienceMaterial row '
                                    'absent',
            'meltRungClimb': _climb(melt_rung) if melt_rung
            else None,
            'liningGate': next(
                (getattr(r, 'lining_options_json', '')
                 for r in rungs
                 if getattr(r, 'name', '') == 'steelmaking-furnace'),
                '')})
    # -- the galvanizing zinc leg --
    if galvanize:
        zn_agent = _row_named(manager, 'BioextractionAgent',
                              'zinc-accumulating-microbe')
        zn_prod = _row_named(manager, 'BiomineralProduct',
                             'galvanized-phosphated-steel')
        if zn_agent is not None or zn_prod is not None:
            legs.append({
                'leg': 'zinc (bio-extraction route)',
                'route': 'biomining: zinc-accumulating microbe → '
                         'bio-zinc → hot-dip (the biomining module '
                         'rows carry yield/purity targets)',
                'purityGap': 'purity target ~0.9 UNMEASURED — a '
                             'first melt deserves an assay'})
        else:
            gaps.append('bio-zinc route rows not loaded on this '
                        'instance (biomining module) — zinc '
                        'sourcing unverified here')
    gaps.append('furnace-rung POSSESSION unverified — the ladder is '
                'the catalog of what CAN be built, not what this '
                'shop has built; the climb is the work')
    gaps.append('all temperatures literature-approximate (claims '
                'travel with each row)')
    return {'legs': legs, 'gaps': gaps,
            'verdict': 'local-as-claimed' if not any(
                'unverified here' in g for g in gaps[:-2])
            else 'gaps-named',
            'note': 'composed from CeramicSample feedstocks, the '
                    'LadderRung climb, bio-alloy notes, and '
                    'biomining rows — asserted by DATA, not by the '
                    'wizard'}


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
        from mathshapes.shape_analysis import shape_properties
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
