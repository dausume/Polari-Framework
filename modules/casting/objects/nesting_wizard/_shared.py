"""@module casting.objects.nesting_wizard._shared — what the nesting_wizard row classes share (constants, seeds, helpers); split from nesting_wizard_basis.py (sap-2c)."""
from casting.custom.wax_feasibility import _row_named, _rows, master_report
import json

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
