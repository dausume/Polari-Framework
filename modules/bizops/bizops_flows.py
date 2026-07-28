"""
@module bizops.bizops_flows

Setup/Upgrade flow reports + the Local Economy track (biz-1).
Everything DERIVES from live rows: upgrade steps surface as
evidence-gated SUGGESTIONS (never auto-taken); milestone status is
computed from the sourcing/business/reclaim tables, never
hand-flipped. Stdlib, duck-typed.
"""

import json


def _rows(manager, class_name):
    return list(getattr(manager, 'objectTables', {}).get(
        class_name, {}).values())


def _named(manager, class_name, name):
    for row in _rows(manager, class_name):
        if getattr(row, 'name', None) == name:
            return row
    return None


def _loads(row, attr, default):
    try:
        return json.loads(getattr(row, attr, '') or '')
    except ValueError:
        return default


def business_flow_report(manager, business_name):
    """Where a business sits on the ladder and which upgrade edges
    apply, each with its evidence gate stated."""
    biz = _named(manager, 'BusinessProfile', business_name)
    if biz is None:
        return {'ok': False,
                'refusal': f'no BusinessProfile named '
                           f'"{business_name}"'}
    stage = _named(manager, 'BusinessStageDefinition',
                   getattr(biz, 'current_stage', ''))
    caps = set(_loads(biz, 'capabilities_json', []))
    applicable = []
    for step in _rows(manager, 'BusinessUpgradeStep'):
        from_stage = getattr(step, 'from_stage', '')
        if from_stage and from_stage != getattr(biz,
                                                'current_stage', ''):
            continue
        effects = _loads(step, 'effects_json', {})
        added = set(effects.get('capabilities_added', []))
        if added and added <= caps:
            continue  # already has it
        applicable.append({
            'name': getattr(step, 'name', ''),
            'displayName': getattr(step, 'display_name', ''),
            'kind': getattr(step, 'kind', ''),
            'roleOrCapability': getattr(step,
                                        'role_or_capability', ''),
            'toStage': getattr(step, 'to_stage', ''),
            'evidenceGate': getattr(step, 'evidence_gate', ''),
            'effects': effects,
            'suggestion': 'take this step ONLY when the evidence '
                          'gate holds — the planner supplies the '
                          'numbers'})
    return {'ok': True, 'business': business_name,
            'businessModel': getattr(biz, 'business_model_ref', ''),
            'stage': {
                'name': getattr(stage, 'name', '?'),
                'index': getattr(stage, 'stage_index', -1),
                'weeklyHours': getattr(biz, 'weekly_hours', 0.0),
                'headcount': getattr(biz, 'headcount', 0),
                'salesChannels': _loads(stage, 'sales_channels_json',
                                        []) if stage else [],
                'sourcingPosture': getattr(stage, 'sourcing_posture',
                                           '?') if stage else '?',
            } if stage else {'name': getattr(biz, 'current_stage',
                                             '?')},
            'capabilities': sorted(caps),
            'availableUpgrades': applicable,
            'axiom': 'every business starts as one person, '
                     'off-time, buying whatever is available — '
                     'stages only move on evidence'}


def _milestone_status(manager, ms):
    kind = getattr(ms, 'kind', '')
    target = getattr(ms, 'target_ref', '')
    if kind == 'local-available-source-for':
        for s in _rows(manager, 'SupplySourceProfile'):
            if (getattr(s, 'is_local', False)
                    and getattr(s, 'availability', '') == 'available'
                    and target in _loads(s, 'supplies_json', [])):
                return True, f'local available source: {s.name}'
        return False, ('no LOCAL AVAILABLE source supplies '
                       f'"{target}" yet (potential ones may exist)')
    if kind == 'makeable-intermediary':
        for f in _rows(manager, 'ProductFormula'):
            if getattr(f, 'product_item_ref', '') == target:
                return True, f'recipe exists: {f.name}'
        return False, f'no ProductFormula makes "{target}"'
    if kind == 'mutual-loop-exists':
        for s in _rows(manager, 'SupplySourceProfile'):
            if (_loads(s, 'supplies_json', [])
                    and _loads(s, 'demands_json', [])):
                return True, (f'{s.name} both supplies and demands '
                              '(the loop)')
        return False, 'no source both supplies and demands yet'
    if kind == 'business-at-stage':
        want = int(target or 1)
        for b in _rows(manager, 'BusinessProfile'):
            st = _named(manager, 'BusinessStageDefinition',
                        getattr(b, 'current_stage', ''))
            if st and getattr(st, 'stage_index', 0) >= want:
                return True, f'{b.name} at {st.name}'
        return False, f'no business at stage index >= {want}'
    if kind == 'business-count':
        count = len(_rows(manager, 'BusinessProfile'))
        want = int(target or 2)
        return count >= want, f'{count} business profile(s)'
    if kind == 'reclaim-active':
        n = len(_rows(manager, 'WaxReclaimBatch'))
        return n > 0, f'{n} reclaim batch(es) logged'
    if kind == 'crush-loop-logged':
        for m in _rows(manager, 'MoldLifecycleRecord'):
            if getattr(m, 'crushed_kg_recovered', 0.0) > 0:
                return True, f'{m.name}: crushed kg recovered'
        return False, 'no mold has been crushed back yet'
    return False, f'unknown milestone kind "{kind}" — honest no'


def local_economy_report(manager):
    """The Local Economy Setup track: every milestone evaluated
    from live rows, progression % toward the functioning baseline,
    and the next gap as the suggested focus."""
    milestones = sorted(_rows(manager, 'LocalEconomyMilestone'),
                        key=lambda m: getattr(m, 'track_order', 0))
    if not milestones:
        return {'ok': False,
                'refusal': 'no LocalEconomyMilestone rows — seed '
                           'the track first'}
    rows = []
    done = 0
    next_gap = None
    for ms in milestones:
        ok, evidence = _milestone_status(manager, ms)
        done += 1 if ok else 0
        row = {'name': getattr(ms, 'name', ''),
               'displayName': getattr(ms, 'display_name', ''),
               'order': getattr(ms, 'track_order', 0),
               'done': ok, 'evidence': evidence,
               'description': getattr(ms, 'description', '')}
        rows.append(row)
        if not ok and next_gap is None:
            next_gap = row
    return {'ok': True,
            'milestones': rows,
            'doneCount': done,
            'totalCount': len(rows),
            'progressPct': round(100.0 * done / len(rows), 1),
            'nextGap': next_gap,
            'note': 'the track toward a functioning local economic '
                    'baseline (OSEB) — status is DERIVED from live '
                    'rows, never hand-flipped'}
