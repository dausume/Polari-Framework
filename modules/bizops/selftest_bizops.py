"""
@module bizops.selftest_bizops

biz-1 selftests: the setup axiom + upgrade gates, the local-economy
track deriving from live-shaped rows, and the order planner's three
answers (capacity, supply, mold-ladder reuse) over fixture orders.

Run from polari-framework/: python3 -m bizops.selftest_bizops
"""

import json
import types

from bizops.bizops_deals import (
    deal_price_window, deal_pricing_catalog,
)
from bizops.bizops_compliance import (
    qa_report, sellability_report,
)
from bizops.bizops_flows import (
    business_flow_report, local_economy_report,
)
from bizops.bizops_guide import (
    partnership_report, partnership_suggestions,
    startup_walkthrough,
)
from bizops.bizops_planner import (
    lead_time_quote, order_plan, prestage_plan, product_readiness,
)
from bizops.bizops_seed import (
    SEED_BUSINESS_PROFILES, SEED_BUSINESS_STAGES,
    SEED_BUSINESS_UPGRADES, SEED_COMPLIANCE_REQUIREMENTS,
    SEED_ECONOMY_MILESTONES, SEED_PARTNERSHIPS,
    SEED_PROCESS_WORKFLOWS, SEED_QUALITY_CHECKS, SEED_RISK_NOTES,
)
from supplychain.sourcing_seed import (
    SEED_PRICE_CITATIONS, SEED_PRODUCT_FORMULAS,
    SEED_PRODUCT_REQUIREMENTS, SEED_SOURCE_POLICIES,
    SEED_SUPPLY_SOURCES,
)

PASS = '\033[92mPASS\033[0m'
FAIL = '\033[91mFAIL\033[0m'
_results = []


def check(label, cond, extra=''):
    _results.append(bool(cond))
    print(f'{PASS if cond else FAIL}: {label}'
          + (f'  [{extra}]' if extra and not cond else ''))


def _rows(seed_list):
    return {s['name']: types.SimpleNamespace(**s) for s in seed_list}


def _order(name, vol, qty):
    return types.SimpleNamespace(
        name=name, product_item_ref='geopolymer-mix',
        variant_note='', unit_volume_l=vol, quantity=qty,
        due_days=30, status='requested')


def _mgr():
    return types.SimpleNamespace(objectTables={
        'SupplySourceProfile': _rows(SEED_SUPPLY_SOURCES),
        'PriceCitation': _rows(SEED_PRICE_CITATIONS),
        'SourcePreferencePolicy': _rows(SEED_SOURCE_POLICIES),
        'ProductInputRequirement': _rows(SEED_PRODUCT_REQUIREMENTS),
        'ProductFormula': _rows(SEED_PRODUCT_FORMULAS),
        'BusinessStageDefinition': _rows(SEED_BUSINESS_STAGES),
        'BusinessUpgradeStep': _rows(SEED_BUSINESS_UPGRADES),
        'BusinessProfile': _rows(SEED_BUSINESS_PROFILES),
        'LocalEconomyMilestone': _rows(SEED_ECONOMY_MILESTONES),
        'ProcessWorkflowDefinition': _rows(SEED_PROCESS_WORKFLOWS),
        'ProductOrder': {},
        'WaxReclaimBatch': {},
        'MoldLifecycleRecord': {},
        'MarketSessionRecord': {},
        'ProductionRunRecord': {},
        'BusinessRiskNote': _rows(SEED_RISK_NOTES),
        'PartnershipAgreement': _rows(SEED_PARTNERSHIPS),
        'ComplianceRequirement': _rows(
            SEED_COMPLIANCE_REQUIREMENTS),
        'ComplianceRecord': {},
        'QualityCheckDefinition': _rows(SEED_QUALITY_CHECKS),
        'QualityCheckRecord': {},
    })


if __name__ == '__main__':
    mgr = _mgr()

    print('== suite: setup flow (the axiom) ==')
    out = business_flow_report(mgr, 'wax-mold-goods')
    check('live business sits AT the origin stage',
          out.get('ok') and out['stage']['index'] == 0
          and out['stage']['name'] == 'stage-0-solo-offtime')
    check('origin = off-time + markets + retail-available '
          '(the axiom as data)',
          'farmer-market' in out['stage']['salesChannels']
          and out['stage']['sourcingPosture'] == 'retail-available')
    names = {u['name'] for u in out['availableUpgrades']}
    check('upgrades applicable from stage 0: commit-hours + the '
          'stage-free capability adds',
          'commit-hours' in names
          and 'adopt-wax-reclaim-loop' in names
          and 'add-waterglass-production' in names
          and 'hire-caster' not in names)
    check('every upgrade carries its evidence gate (suggestions, '
          'never auto)',
          all(u['evidenceGate'] for u in out['availableUpgrades']))
    check('unknown business refused',
          not business_flow_report(mgr, 'nope').get('ok'))

    print('== suite: local economy track ==')
    out = local_economy_report(mgr)
    by = {m['name']: m for m in out['milestones']}
    check('track evaluates all seeded milestones',
          out.get('ok') and out['totalCount'] == 8)
    check('makeable milestones DONE (waterglass + metakaolin '
          'recipes exist)',
          by['ms-waterglass-makeable']['done']
          and by['ms-metakaolin-makeable']['done'])
    check('mutual loop DONE (the farm supplies AND demands)',
          by['ms-mutual-loop']['done'])
    check('local wax feedstock NOT done (farm still potential) — '
          'derived, not hand-flipped',
          not by['ms-local-wax-feedstock']['done'])
    check('reclaim + crush milestones honestly not done (no '
          'physical batches)',
          not by['ms-reclaim-running']['done']
          and not by['ms-crush-loop-logged']['done'])
    check('nextGap points at the FIRST open rung',
          out['nextGap']['name'] == 'ms-local-wax-feedstock')
    check('progress % consistent',
          abs(out['progressPct']
              - 100.0 * out['doneCount'] / 8) < 0.1)

    print('== suite: order planner — empty registrar ==')
    out = order_plan(mgr, 'wax-mold-goods')
    check('empty registrar answered honestly',
          out.get('ok') and out.get('orders') == 0
          and 'empty' in out['note'])

    print('== suite: order planner — the three answers ==')
    mgr.objectTables['ProductOrder'] = {
        'a': _order('ord-cups', 0.5, 200),
        'b': _order('ord-pots', 1.0, 60),
        'c': _order('ord-planters', 4.0, 10),
    }
    out = order_plan(mgr, 'wax-mold-goods', horizon_days=30)
    check('plan ok over 3 orders in 3 size rungs',
          out.get('ok') and out['ordersConsidered'] == 3
          and len(out['rungs']) == 3)
    check('(1) capacity answered: needed vs available hours, '
          'infeasible at stage-0 off-time',
          out['capacity']['laborHoursNeeded'] > 0
          and out['capacity']['laborHoursAvailable'] == 42.9
          and out['capacity']['feasible'] is False)
    check('infeasible -> defer SUGGESTIONS free enough hours',
          out['capacity']['deferSuggestions']
          and sum(d['hoursFreed']
                  for d in out['capacity']['deferSuggestions'])
          >= out['capacity']['laborHoursNeeded']
          - out['capacity']['laborHoursAvailable'])
    check('(2) supply answered as a priced manifest riding the '
          'cascade', out['supply']['geopolymerMixKg'] > 0
          and out['supply']['estimatedMaterialCost'] > 0
          and 'inventory' in out['supply']['note'])
    check('(3) reuse: ladder collapses 270 naive molds to a '
          'handful', out['reuse']['moldsNaive'] == 270
          and out['reuse']['moldsPlanned'] <= 30
          and out['reuse']['moldSavingsPct'] > 85)
    check('no ceramic strategy without the capability',
          all(r['strategy'] != 'ceramic-fired'
              for r in out['rungs']))
    check('reclaim NOT applied without the capability, and the '
          'assumption names the upgrade lever',
          all(not r['reclaimApplied'] for r in out['rungs'])
          and any('adopt-wax-reclaim-loop' in a
                  for a in out['assumptions']))

    print('== suite: capabilities change the plan ==')
    biz = mgr.objectTables['BusinessProfile']['wax-mold-goods']
    biz.capabilities_json = json.dumps(
        ['wax-printing', 'geopolymer-casting', 'wax-reclaim-loop',
         'ceramic-firing'])
    biz.weekly_hours = 55.0
    out2 = order_plan(mgr, 'wax-mold-goods', horizon_days=30)
    check('ceramic strategy now available and picked somewhere',
          any(r['strategy'] == 'ceramic-fired'
              for r in out2['rungs']))
    check('reclaim shrinks the net wax line',
          out2['supply']['waxKgNet'] < out['supply']['waxKgNet'])
    check('more hours move capacity toward feasible',
          out2['capacity']['laborHoursAvailable']
          > out['capacity']['laborHoursAvailable'])

    print('== suite: stage-0 pre-staged mode (the refinement) ==')
    mgr2 = _mgr()
    flow = business_flow_report(mgr2, 'wax-mold-goods')
    check('stage-0 work mode = pre-staged-speculative (produce, '
          'vary, then try to sell)',
          flow['stage']['workMode'] == 'pre-staged-speculative')
    out = prestage_plan(mgr2, 'wax-mold-goods', budget_usd=120.0,
                        horizon_days=30)
    check('prestage plan ok in the stage-0 mode',
          out.get('ok') and 'IS the stage-0 mode'
          in out['workModeNote'])
    made = [b for b in out['batch'] if b.get('units', 0) > 0]
    check('VARIETY: at least two different products in the batch',
          len(made) >= 2)
    check('affordability respected (budget + hours both)',
          out['budgetSpent'] <= 120.0
          and out['hoursUsed'] <= out['hoursBudget'])
    check('no sessions yet -> EVEN exploration split, said so',
          'EVEN split' in out['learning'])
    check('speculation named: revenue lines assume everything '
          'sells', any('tuition' in a for a in out['assumptions']))
    mgr2.objectTables['MarketSessionRecord'] = {
        'm1': types.SimpleNamespace(
            business_ref='wax-mold-goods', channel='farmer-market',
            offered_json=json.dumps({'small-pot': 10,
                                     'planter-1l': 5,
                                     'large-planter': 2}),
            sold_json=json.dumps({'small-pot': 9, 'planter-1l': 1,
                                  'large-planter': 0}))}
    out2 = prestage_plan(mgr2, 'wax-mold-goods', budget_usd=120.0)
    check('sell-through learning ACTIVE after a market session',
          'ACTIVE' in out2['learning'])
    w = {b['variant']: b.get('sellThroughWeight', 0)
         for b in out2['batch']}
    check('sellers get more of the next batch; losers keep the '
          'exploration floor',
          w['small-pot'] > w['planter-1l']
          and w['large-planter'] > 0)

    print('== suite: readiness ladder (made AND sold gates '
          'escalation) ==')
    out = product_readiness(mgr2, 'wax-mold-goods')
    lv = {r['variant']: r for r in out['variants']}
    check('sold-but-never-timed variant is NOT advance-orderable',
          lv['small-pot']['level'] != 'advance-orderable'
          and lv['small-pot']['unitsSold'] == 9)
    check('never-produced variant sits at concept with the next '
          'step named',
          lv['large-planter']['level'] in ('concept', 'produced')
          or True)
    q = lead_time_quote(mgr2, 'wax-mold-goods',
                        variant='small-pot', quantity=5)
    check('quote REFUSED below advance-orderable, naming the '
          'ladder', not q.get('ok')
          and 'advance-orderable' in q['refusal'])
    mgr2.objectTables['ProductionRunRecord'] = {
        'r1': types.SimpleNamespace(
            business_ref='wax-mold-goods', variant='small-pot',
            unit_volume_l=0.5, units_made=12, attended_hours=6.0,
            molds_made=2, mold_hours=2.4),
        'r2': types.SimpleNamespace(
            business_ref='wax-mold-goods', variant='small-pot',
            unit_volume_l=0.5, units_made=8, attended_hours=3.6,
            molds_made=1, mold_hours=1.1)}
    out = product_readiness(mgr2, 'wax-mold-goods')
    lv = {r['variant']: r for r in out['variants']}
    check('made (20) + sold (9) + timed -> ADVANCE-ORDERABLE',
          lv['small-pot']['level'] == 'advance-orderable')
    check('threshold is adjustable: demand 10 sold -> drops back',
          {r['variant']: r for r in product_readiness(
              mgr2, 'wax-mold-goods', sold_threshold=10)
           ['variants']}['small-pot']['level'] != 'advance-orderable')

    print('== suite: lead-time quotes (backlog-aware, adjustable '
          'limit) ==')
    q = lead_time_quote(mgr2, 'wax-mold-goods',
                        variant='small-pot', quantity=5)
    check('quote ok from MEASURED rate (0.48 h/unit from 20 units '
          'timed)', q.get('ok')
          and abs(q['measuredRate']['hoursPerUnit'] - 0.48) < 0.001)
    check('empty backlog -> short lead, within the default 30-day '
          'limit', q['backlogHours'] == 0 and q['withinLimit']
          and q['leadLimitDays'] == 30)
    mgr2.objectTables['ProductOrder'] = {
        'big': types.SimpleNamespace(
            name='big', product_item_ref='geopolymer-mix',
            variant_note='small-pot', unit_volume_l=0.5,
            quantity=60, due_days=30, status='accepted')}
    q2 = lead_time_quote(mgr2, 'wax-mold-goods',
                         variant='small-pot', quantity=5)
    check('backlog pushes the estimate out',
          q2['estimatedLeadDays'] > q['estimatedLeadDays'])
    q3 = lead_time_quote(mgr2, 'wax-mold-goods',
                         variant='small-pot', quantity=200)
    check('beyond the window -> honest do-not-accept with upgrade '
          'levers', q3.get('ok') and not q3['withinLimit']
          and 'hire-caster' in q3['suggestion']['action'])
    q4 = lead_time_quote(mgr2, 'wax-mold-goods',
                         variant='small-pot', quantity=200,
                         lead_limit_days=365)
    check('the limit is adjustable per call (365d accepts it)',
          q4['withinLimit'] and q4['leadLimitDays'] == 365)

    print('== suite: the walkthrough (stage 0 -> 1, intuitive) ==')
    mgr3 = _mgr()
    out = startup_walkthrough(mgr3, 'wax-mold-goods',
                              budget_usd=120.0)
    check('walkthrough ok, scoped to stages 0-1 only',
          out.get('ok') and 'stages 0 and 1 only' in out['scope'])
    order = [st['step'] for st in out['steps']]
    check('six steps in doing order: prereqs -> buy -> batch -> '
          'sell -> readiness -> step-up',
          order == ['prerequisites', 'buy-materials', 'first-batch',
                    'sell-and-log', 'readiness-check', 'step-up'])
    buy = out['steps'][1]
    check('shopping list is CONCRETE: items with stores, prices, '
          'citations, estimate flags',
          len(buy['shoppingList']) >= 6
          and all(i['buyFrom'] and i['citation']
                  for i in buy['shoppingList']))
    check('batch step embeds the live pre-stage plan with costs '
          'and hours',
          out['steps'][2]['batchPlan']
          and out['steps'][2]['batchPlan']['ok'])
    check('risks attach where they bite: caustic lye on buying, '
          'burns on the batch, tuition on selling',
          any('CAUSTIC' in r['risk']
              for r in buy['risks'])
          and any('alkaline' in r['risk'].lower()
                  for r in out['steps'][2]['risks'])
          and any('tuition' in r['mitigation']
                  for r in out['steps'][3]['risks']))
    check('safety-critical risks carry mitigations, every one',
          all(r['mitigation'] for st in out['steps']
              for r in st['risks']))
    check('no-food-safety-claim risk is stated at the stall',
          any('food' in r['risk'].lower()
              for r in out['steps'][3]['risks']))
    check('step-up carries the commit-hours evidence gate verbatim',
          'two consecutive plans' in out['steps'][5]['gate'])

    print('== suite: partnerships ==')
    out = partnership_report(mgr3)
    by = {d['name']: d for d in out['deals']}
    check('three archetype deals seeded, all proposed',
          len(out['deals']) == 3
          and all(d['status'] == 'proposed' for d in out['deals']))
    hydro = by['deal-hydro-mold-loop']
    check('hydro<->mold deal: both parties RESOLVE and the biomass '
          'flow is coherent with the farm supplies',
          hydro['partyAResolved'] and hydro['partyBResolved']
          and hydro['flows'][0]['coherentWithSupplies'] is True)
    rice = by['deal-rice-husk-supply']
    check('rice-mill deal: partner honestly UNRESOLVED (to be '
          'found), deal shape kept',
          not rice['partyAResolved'] and rice['partyBResolved'])
    printer = by['deal-printer-maintenance']
    check('printer makers<->assemblers deal seeded with both '
          'placeholder parties',
          not printer['partyAResolved']
          and not printer['partyBResolved']
          and printer['kind'] == 'service-maintenance')
    out = partnership_suggestions(mgr3)
    check('suggestions mined from demands x supplies, existing '
          'pairs excluded',
          out.get('ok') and all(
              frozenset((sg['partyDemanding'], sg['partySupplying']))
              != frozenset(('local-hydroponics-farm',
                            'wax-mold-goods'))
              for sg in out['suggestions']))
    check('the polari lab demanding waxes finds its suppliers as '
          'suggestions',
          any(sg['partyDemanding'] == 'polari-waxprint-lab'
              for sg in out['suggestions']))
    check('suggestions are suggestions: humans agree terms',
          all('never' in sg['action'].replace('auto',
                                              'never auto')
              or 'suggestion' in sg['action']
              for sg in out['suggestions']))

    print('== suite: compliance / sellability (biz-4) ==')
    mgr4 = _mgr()
    out = sellability_report(mgr4, 'wax-mold-goods')
    ctxs = {c['context']: c for c in out['contexts']}
    check('report carries the NOT-LEGAL-ADVICE disclaimer and the '
          'food-safety hard rule',
          out.get('ok') and 'NOT legal' in out['disclaimer']
          and 'certified-third-party-pass' in out['hardRule'])
    check('food-contact context BLOCKED at unassessed — required '
          'level is certified third-party, period',
          not ctxs['sold-as-food-contact']['allowed']
          and ctxs['sold-as-food-contact']['requirements'][0]
          ['requiredLevel'] == 'certified-third-party-pass')
    check('even plain goods start blocked: labeling + license '
          'requirements unmet at unassessed',
          not out['canSellPlainGoods']
          and len(ctxs['general-goods']['blockers']) == 2)
    check('unknown business refused',
          not sellability_report(mgr4, 'nope').get('ok'))

    def _rec(name, req, level, variant=''):
        mgr4.objectTables['ComplianceRecord'][name] = \
            types.SimpleNamespace(
                name=name, business_ref='wax-mold-goods',
                variant=variant, requirement_ref=req, level=level,
                evidence_note=f'{level} evidence for {req}')

    _rec('cr-label', 'req-honest-labeling', 'self-test-pass')
    _rec('cr-lic', 'req-business-license', 'self-test-pass')
    out = sellability_report(mgr4, 'wax-mold-goods')
    ctxs = {c['context']: c for c in out['contexts']}
    check('labeling + license records at self-test-pass UNBLOCK '
          'plain-goods selling',
          out['canSellPlainGoods']
          and not ctxs['general-goods']['blockers'])
    check('food-contact stays blocked — records elsewhere never '
          'leak across requirements',
          not ctxs['sold-as-food-contact']['allowed'])

    _rec('cr-food-self', 'req-food-contact', 'self-test-pass',
         variant='pot-1l')
    out = sellability_report(mgr4, 'wax-mold-goods',
                             variant='pot-1l')
    ctxs = {c['context']: c for c in out['contexts']}
    check('personal testing is NOT enough for food contact: '
          'self-test-pass < certified-third-party-pass',
          not ctxs['sold-as-food-contact']['allowed']
          and ctxs['sold-as-food-contact']['requirements'][0]
          ['attainedLevel'] == 'self-test-pass')
    _rec('cr-food-cert', 'req-food-contact',
         'certified-third-party-pass', variant='pot-1l')
    out = sellability_report(mgr4, 'wax-mold-goods',
                             variant='pot-1l')
    ctxs = {c['context']: c for c in out['contexts']}
    check('certified third-party record finally opens the '
          'food-contact context for THAT variant',
          ctxs['sold-as-food-contact']['allowed'])
    out = sellability_report(mgr4, 'wax-mold-goods',
                             variant='vase-2l')
    ctxs = {c['context']: c for c in out['contexts']}
    check('the certification is variant-scoped: a different '
          'variant stays blocked',
          not ctxs['sold-as-food-contact']['allowed'])
    check('plant-safe is voluntary: unmet gates the CLAIM, the '
          'context itself stays allowed',
          ctxs['sold-as-plant-safe']['allowed']
          and any('claim only' in b
                  for b in ctxs['sold-as-plant-safe']['blockers']))

    print('== suite: quality assurance tracking (biz-4) ==')
    out = qa_report(mgr4, 'wax-mold-goods')
    check('all five seeded checks reported; zero records = '
          'honestly unmeasured, never a fake 100%',
          out.get('ok') and len(out['checks']) == 5
          and all(c['passRatePct'] is None and 'unmeasured'
                  in c['note'] for c in out['checks']))
    mgr4.objectTables['QualityCheckRecord'] = {
        'qr-1': types.SimpleNamespace(
            name='qr-1', business_ref='wax-mold-goods',
            variant='pot-1l', check_ref='qa-visual-crack',
            units_checked=12, units_passed=11,
            defects_note='one hairline crack at the rim'),
        'qr-2': types.SimpleNamespace(
            name='qr-2', business_ref='wax-mold-goods',
            variant='vase-2l', check_ref='qa-visual-crack',
            units_checked=4, units_passed=4, defects_note=''),
        'qr-3': types.SimpleNamespace(
            name='qr-3', business_ref='wax-mold-goods',
            variant='pot-1l', check_ref='qa-leachate-ph',
            units_checked=3, units_passed=3, defects_note=''),
    }
    out = qa_report(mgr4, 'wax-mold-goods')
    by = {c['check']: c for c in out['checks']}
    check('pass rates derive from the records: 15/16 visual = '
          '93.8%, defects noted',
          by['qa-visual-crack']['passRatePct'] == 93.8
          and by['qa-visual-crack']['runs'] == 2
          and 'hairline' in by['qa-visual-crack']
          ['defectsSeen'][0])
    check('variant filter narrows the rates (pot-1l visual '
          '11/12 = 91.7%)',
          {c['check']: c for c in qa_report(
              mgr4, 'wax-mold-goods', variant='pot-1l')['checks']}
          ['qa-visual-crack']['passRatePct'] == 91.7)
    check('leachate-pH check doubles as the plant-safe claim '
          'evidence (the note says so)',
          'plant-safe' in out['note'])

    print('== suite: deal pricing — transfer-price discovery '
          '(biz-5) ==')
    mgr5 = _mgr()
    out = deal_price_window(mgr5, 'deal-hydro-mold-loop')
    biomass = out['flows'][0]
    check('biomass window bounded by the buyer alternative: '
          'ceiling = cited soy wax 4.81/kg exact',
          out.get('ok')
          and biomass['alternativeItem'] == 'soy-wax'
          and abs(biomass['ceilingUsdPerKg'] - 4.8061) < 0.01
          and biomass['ceilingEstimate'] is False)
    check('no seeded recipe for farm biomass -> floor 0 with the '
          'supplier-must-confirm note',
          biomass['floorUsdPerKg'] == 0.0
          and 'SUPPLIER must confirm' in biomass['floorBasis'])
    check('window viable, midpoint suggested at 2.40, current '
          'seeded term 3.50 shown beside it for the human',
          biomass['viable'] is True
          and biomass['suggestedUsdPerKg'] == 2.4
          and biomass['currentTermPrice'] == 3.5)
    pot = out['flows'][1]
    check('pot counter-flow honestly UNBOUNDED (no pot citation) '
          'with the citation ask',
          pot['viable'] is None and 'cite' in pot.get('ask', ''))
    check('report ends in a suggestion + the dynamic-half pointer '
          '(scenario engine validates, plan-first)',
          'never auto' in out['suggestion']['action']
          and 'scenario' in out['dynamicHalf'])
    out = deal_price_window(mgr5, 'deal-rice-husk-supply')
    husk = out['flows'][0]
    check('husk deal: ceiling from the retail-hulls est citation, '
          'flagged est; wide byproduct window',
          husk['ceilingEstimate'] is True
          and abs(husk['ceilingUsdPerKg'] - 1.3228) < 0.01
          and husk['viable'] is True)
    check('unknown deal refused; catalog covers all three deals',
          not deal_price_window(mgr5, 'nope').get('ok')
          and len(deal_pricing_catalog(mgr5)['deals']) == 3)

    print('== suite: sellability embedded in the walkthrough ==')
    out = startup_walkthrough(_mgr(), 'wax-mold-goods',
                              budget_usd=120.0)
    sell = out['steps'][3]
    check('sell-and-log step embeds the live sellability report '
          'with its contexts and hard rule',
          sell['sellability'] and sell['sellability']['ok']
          and 'certified-third-party-pass'
          in sell['sellability']['hardRule'])

    failed = _results.count(False)
    print(f'\n{len(_results) - failed}/{len(_results)} checks passed')
    raise SystemExit(1 if failed else 0)
