"""
@module bizops.bizops_guide

The INTUITIVE walkthrough (biz-3, Dustin): walk a NEW business maker
through exactly what to do at stage 0 and the step up to stage 1 —
what each step is, why, what it costs on the cited prices, and the
risks/dangers stated before they bite. Plus partnerships: agreement
rows coherence-checked against the supply/demand data, and deal
SUGGESTIONS mined from complementary supplies/demands.

Scope honesty: stages 0 and 1 only for now — later rungs exist in
the ladder but are not walked here.
"""

from supplychain.formula_analysis import requirement_coverage
from bizops.bizops_compliance import sellability_report
from bizops.bizops_flows import _loads, _named, _rows
from bizops.bizops_planner import prestage_plan, product_readiness


def _risks_for(manager, step_ref):
    return [{'severity': getattr(r, 'severity', ''),
             'risk': getattr(r, 'risk', ''),
             'mitigation': getattr(r, 'mitigation', '')}
            for r in _rows(manager, 'BusinessRiskNote')
            if getattr(r, 'step_ref', '') == step_ref]


def _shopping_list(manager):
    """Concrete buy-list from the CITED coverage of the two core
    recipes — store names, prices, citation URLs. Stage-0 posture
    is retail-available: BUY everything; self-made intermediaries
    are later-stage upgrades."""
    items = []
    for product in ('geopolymer-mix', 'natural-print-wax-blend'):
        cov = requirement_coverage(manager, product)
        if not cov.get('ok'):
            continue
        for role in cov['roles']:
            cited = [c for c in role['candidates']
                     if c.get('cited')]
            if not cited:
                continue
            best = min(cited, key=lambda c: c['usdPerKg'])
            items.append({
                'for': product, 'role': role['role'],
                'item': best['item'],
                'usdPerKg': best['usdPerKg'],
                'buyFrom': best['source'],
                'citation': best['citation'],
                'estimateFlagged': best['isEstimate']})
    # dedupe by item, keep the cheapest listing
    seen = {}
    for item in items:
        prev = seen.get(item['item'])
        if prev is None or item['usdPerKg'] < prev['usdPerKg']:
            seen[item['item']] = item
    return sorted(seen.values(), key=lambda i: -i['usdPerKg'])


def startup_walkthrough(manager, business_name='wax-mold-goods',
                        budget_usd=120.0):
    """The whole stage-0 route, in order, in plain language, with
    live numbers and the risk register attached per step."""
    biz = _named(manager, 'BusinessProfile', business_name)
    if biz is None:
        return {'ok': False,
                'refusal': f'no BusinessProfile named '
                           f'"{business_name}"'}
    batch = prestage_plan(manager, business_name,
                          budget_usd=budget_usd)
    sellability = sellability_report(manager, business_name)
    readiness = product_readiness(manager, business_name)
    commit = _named(manager, 'BusinessUpgradeStep', 'commit-hours')
    steps = [
        {'step': 'prerequisites', 'order': 1,
         'title': 'What you need before day one',
         'what': 'A working wax 3D printer (the standing '
                 'assumption of this whole route), mixing tubs, '
                 'a scale, gloves + goggles, and a selling table.',
         'cost': 'printer assumed owned (the open-hardware build '
                 'is its own track); consumable safety gear '
                 '~$30-60 one-time',
         'why': 'everything downstream prints molds and casts '
                'into them',
         'risks': _risks_for(manager, 'prerequisites')},
        {'step': 'buy-materials', 'order': 2,
         'title': 'Buy your starting materials (retail — that is '
                  'the stage-0 posture)',
         'what': 'The shopping list below, from the cheapest '
                 'CITED listing per material.',
         'shoppingList': _shopping_list(manager),
         'cost': f'bounded by your batch budget '
                 f'(${budget_usd:.0f} here); flagged~ prices are '
                 'estimates — keep receipts and re-cite',
         'why': 'buying available retail beats waiting on bulk '
                'tiers or self-made intermediaries you do not '
                'have yet',
         'risks': _risks_for(manager, 'buy-materials')},
        {'step': 'first-batch', 'order': 3,
         'title': 'Make your first speculative batch — VARIED on '
                  'purpose',
         'what': 'The pre-stage plan below: different products, '
                 'sized to what your budget and off-time hours '
                 'actually afford.',
         'batchPlan': batch if batch.get('ok') else None,
         'cost': (f"~${batch.get('budgetSpent', 0)} materials + "
                  f"{batch.get('hoursUsed', 0)}h of your time"
                  if batch.get('ok') else 'plan unavailable'),
         'why': 'you do not know what sells yet — variety IS the '
                'strategy; TIME every run (ProductionRunRecord) '
                'because measured speed unlocks advance orders '
                'later',
         'risks': _risks_for(manager, 'first-batch')},
        {'step': 'sell-and-log', 'order': 4,
         'title': 'Sell at farmer/maker markets + online — and '
                  'LOG every session',
         'what': 'Offer everything; write down per product what '
                 'was offered and what sold (MarketSessionRecord).',
         'sellability': sellability
         if sellability.get('ok') else None,
         'cost': 'market stall fees vary locally (typically '
                 '$10-40/day — uncited, ask your market)',
         'why': 'sell-through is the ONLY signal that tunes your '
                'next batch, and made+sold is what earns a '
                'product its escalation',
         'risks': _risks_for(manager, 'sell-and-log')},
        {'step': 'readiness-check', 'order': 5,
         'title': 'Check what your products have EARNED',
         'what': 'The readiness ladder below — concept, produced, '
                 'market-proven, advance-orderable.',
         'readiness': readiness if readiness.get('ok') else None,
         'cost': 'free — it derives from the rows you logged',
         'why': 'only advance-orderable products may quote '
                'delivery promises; everything else sells from '
                'stock',
         'risks': _risks_for(manager, 'readiness-check')},
        {'step': 'step-up', 'order': 6,
         'title': 'When (and only when) to step up to stage 1',
         'what': 'The commit-hours upgrade: same person, real '
                 'committed hours, bulk-tier sourcing, standing '
                 'orders.',
         'gate': getattr(commit, 'evidence_gate', '')
         if commit else '',
         'cost': 'the 15 extra weekly hours are the real price; '
                 'bulk buys need more cash up front but drop '
                 'unit costs (the 40-bag metakaolin tier: 2.04 '
                 'vs 2.91/kg)',
         'why': 'stepping up on one good market day is how '
                'businesses burn out — the gate wants the '
                'evidence twice',
         'risks': _risks_for(manager, 'step-up')},
    ]
    return {'ok': True, 'business': business_name,
            'scope': 'stages 0 and 1 only — later rungs exist in '
                     'the ladder but are not walked here yet',
            'budgetUsd': budget_usd,
            'steps': steps,
            'partnershipsNote': 'partner deals (see /partnerships) '
                                'usually start making sense at '
                                'stage 1 — byproduct supply deals '
                                'first, they are the cheapest '
                                'wins'}


def _party_exists(manager, party):
    return (_named(manager, 'BusinessProfile', party) is not None
            or _named(manager, 'SupplySourceProfile', party)
            is not None)


def partnership_report(manager):
    """Every agreement row, with each flow coherence-checked
    against what the parties actually supply/demand where the
    party rows exist — placeholders are honest gaps."""
    deals = []
    for deal in _rows(manager, 'PartnershipAgreement'):
        flows = []
        for f in _loads(deal, 'flows_json', []):
            src = _named(manager, 'SupplySourceProfile', f.get(
                'from', ''))
            coherent = None
            if src is not None:
                coherent = f.get('item_ref', '') in _loads(
                    src, 'supplies_json', [])
            flows.append({**f, 'fromResolved': _party_exists(
                manager, f.get('from', '')),
                'toResolved': _party_exists(manager,
                                            f.get('to', '')),
                'coherentWithSupplies': coherent})
        deals.append({
            'name': getattr(deal, 'name', ''),
            'displayName': getattr(deal, 'display_name', ''),
            'kind': getattr(deal, 'kind', ''),
            'status': getattr(deal, 'status', ''),
            'partyA': getattr(deal, 'party_a', ''),
            'partyAResolved': _party_exists(
                manager, getattr(deal, 'party_a', '')),
            'partyB': getattr(deal, 'party_b', ''),
            'partyBResolved': _party_exists(
                manager, getattr(deal, 'party_b', '')),
            'flows': flows,
            'termsNote': getattr(deal, 'terms_note', ''),
            'notes': getattr(deal, 'notes', '')})
    return {'ok': True, 'deals': deals,
            'note': 'unresolved parties are partners TO BE FOUND '
                    '— the deal shape is the point; activate a '
                    'deal only when both parties resolve'}


def partnership_suggestions(manager):
    """Mine the supply/demand rows for complementary pairs that
    have NO agreement yet — suggested deals with the evidence,
    never auto-created."""
    existing_pairs = set()
    for deal in _rows(manager, 'PartnershipAgreement'):
        existing_pairs.add(frozenset((getattr(deal, 'party_a', ''),
                                      getattr(deal, 'party_b', ''))))
    suggestions = []
    sources = _rows(manager, 'SupplySourceProfile')
    for a in sources:
        demands_a = set(_loads(a, 'demands_json', []))
        if not demands_a:
            continue
        for b in sources:
            if a is b:
                continue
            supplies_b = set(_loads(b, 'supplies_json', []))
            overlap = demands_a & supplies_b
            if not overlap:
                continue
            pair = frozenset((getattr(a, 'name', ''),
                              getattr(b, 'name', '')))
            if pair in existing_pairs:
                continue
            existing_pairs.add(pair)
            suggestions.append({
                'partyDemanding': getattr(a, 'name', ''),
                'partySupplying': getattr(b, 'name', ''),
                'items': sorted(overlap),
                'evidence': f'{a.name} demands what {b.name} '
                            'supplies — a deal shape exists in '
                            'the rows',
                'action': 'draft a PartnershipAgreement if the '
                          'terms make sense — suggestion, never '
                          'auto'})
    return {'ok': True, 'suggestions': suggestions,
            'note': 'mined from demands_json x supplies_json; '
                    'deals only form when humans agree terms'}
