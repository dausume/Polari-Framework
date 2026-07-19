"""
@module pspp.network_stepping

pspp-8 FULL: the reaction network STEPS — rules consume and produce
species, with the Q-distribution as a DYNAMIC RESOURCE seeded from the
measured book data (never invented).

What stepping honestly means without kinetics (invariant I5 stands —
no rule in the library carries a calibrated rate law yet):

- `solution_inventory` — the initial species pool of an activated mix,
  its Q0-Q4 motif amounts read from the MEASURED Table 5.6 solution
  rows (Na; listed MRs only — between-MR queries refuse upstream).
  Unquantified-but-present species (water, ions) carry amount None:
  present, honestly unmeasured.
- `applicable_rules` — which rules CAN fire here: reactants present
  (with multiplicity), site constraint compatible (Fig 8.21 transport
  selection), and every condition-gate window open (the p.188 MR<1.20
  Q0 threshold is a ThresholdReactionWindow row, not code).
- `step_once` — apply ONE named rule stoichiometrically: quantified
  reactant amounts decrement, products increment, in rule-application
  units. This is TOPOLOGY bookkeeping a scientist drives by hand
  ('what if this fires?'), never a time integration.
- `reachable_frameworks` — the kinetics-free closure: which framework
  families the open pathways can reach from this inventory, each with
  its rule pathway, the hypothesis floor of that pathway (a chain is
  only as standing as its weakest rule), sites traversed, and which
  rules stayed blocked and WHY. Competing hypotheses are surfaced,
  never resolved.

Time-resolved simulation still refuses through rule_rate until a
cited calibration row arrives — a scientist extends this engine by
ENTERING DATA (kinetics_ref + calibration), not by editing code.

@consumers
  - pspp.pspp_api (GET /api/pspp/pathways)
  - pspp.experiment_guidance (open-routes section)
"""

import json

from pspp.q_distribution import glass_to_solution_q
from pspp.reaction_network import (
    HYPOTHESIS_STATUSES, SEED_CHEMICAL_SPECIES, SEED_REACTION_RULES,
)
from pspp.threshold_windows import (
    SEED_THRESHOLD_WINDOWS, banded_window_dict, grade_value_banded,
)

#: Pathway standing = the WEAKEST hypothesis on the chain
#: (book-supported > mechanistic-proposal > contested).
_STANDING_ORDER = {status: i for i, status
                   in enumerate(HYPOTHESIS_STATUSES)}

_STEP_ASSUMPTIONS = [
    'kinetics-free: no rule carries a calibrated rate law '
    '(invariant I5) — stepping is stoichiometric/topological, '
    'never time-resolved',
    'amounts are in rule-application units; species with amount '
    'None are present but unquantified (honest absence of measure)',
    'transport partitioning beyond the site_constraint flag '
    '(Fig 8.21) is not modeled',
]


def _get(row, key, default=''):
    return row.get(key, default) if isinstance(row, dict) \
        else getattr(row, key, default)


def _loads(row, key, fallback='[]'):
    raw = _get(row, key, fallback) or fallback
    try:
        return raw if isinstance(raw, list) else json.loads(raw)
    except Exception:
        return json.loads(fallback)


def solution_inventory(cation, mr, datasets=None):
    """The starting species pool of an activated (cation)-silicate +
    MK-750 mix at one MR — Q motifs from the MEASURED solution data,
    everything else present-unquantified."""
    if cation != 'Na':
        return {'ok': False,
                'refusal': f'no glass-to-solution Q table for cation '
                           f'family {cation!r} — Table 5.6 is Na only',
                'suggestion': 'enter the K solution distribution as a '
                              'DigitizedDataset row (it does not '
                              'transfer from Na), or pass an explicit '
                              'inventory to the stepper'}
    solution = glass_to_solution_q(mr, datasets=datasets)
    if not solution.get('ok'):
        return solution
    inventory = {f'siloxonate-q{n}':
                 float(solution['solution'].get(f'Q{n}', 0))
                 for n in range(5)}
    inventory = {k: v for k, v in inventory.items() if v > 0}
    # Present but unmeasured in this table: the aqueous environment
    # and the reactant particle the mix supplies.
    for name in ('water', 'hydroxide-ion', 'sodium-ion',
                 'metakaolin-layer'):
        inventory[name] = None
    if inventory.get('siloxonate-q1') is not None:
        # Q1 sites of the waterglass ARE the di-siloxonate reactant
        # of the surface route (p.184) — same measured amount.
        inventory['di-siloxonate'] = inventory['siloxonate-q1']
    return {
        'ok': True,
        'cation': cation,
        'MR': mr,
        'inventory': inventory,
        'assumptions': solution['assumptions'] + [
            'Q amounts are the Table 5.6 SOLUTION percentages of Si '
            'sites, used as rule-application units',
            'water/ions/metakaolin present unquantified (None) — the '
            'table does not measure them',
            'di-siloxonate mirrors the Q1 amount (Q1 sites ARE the '
            'waterglass di-siloxonate, p.184) — one resource under '
            'two names, not double-counted mass'],
        'evidence': solution['evidence'],
    }


def _gate_verdicts(rule, conditions, windows=None):
    """Evaluate one rule's condition-gate windows against the caller's
    conditions ({descriptor: value}). Returns (open?, verdicts) —
    a missing window row or an unprovided descriptor BLOCKS the rule
    with the reason recorded (never silently passes)."""
    gates = _loads(rule, 'condition_windows_json')
    if not gates:
        return True, []
    banded = {w['name']: w for w in
              (banded_window_dict(x) for x in
               (windows if windows is not None
                else SEED_THRESHOLD_WINDOWS))}
    verdicts = []
    open_ = True
    for gateName in gates:
        window = banded.get(gateName)
        if window is None:
            verdicts.append({'gate': gateName, 'open': False,
                             'reason': f'gate window {gateName!r} row '
                                       'is missing',
                             'suggestion': 'restore/enter the '
                                           'ThresholdReactionWindow '
                                           'row'})
            open_ = False
            continue
        value = (conditions or {}).get(window['descriptor'])
        if value is None:
            verdicts.append({'gate': gateName, 'open': False,
                             'reason': f"condition "
                                       f"{window['descriptor']!r} not "
                                       'provided — gate undetermined',
                             'suggestion': 'pass the descriptor value '
                                           'in conditions (honest '
                                           'absence blocks, never '
                                           'assumes)'})
            open_ = False
            continue
        verdict = grade_value_banded(window, value)
        gateOpen = verdict.get('ok') and verdict['grade'] != 'failure'
        verdicts.append({'gate': gateName, 'open': bool(gateOpen),
                         'value': value,
                         'grade': verdict.get('grade'),
                         'reason': verdict.get('behaviorNote',
                                               verdict.get('refusal',
                                                           ''))})
        open_ = open_ and gateOpen
    return open_, verdicts


def _site_compatible(rule, site):
    constraint = _get(rule, 'site_constraint', '')
    if not constraint or site is None:
        # site None = both sites exist in the mix (Fig 8.21: surface
        # and interior phases coexist) — every rule finds its site.
        return True
    return constraint == f'{site}-only'


def _cation_compatible(rule, cation):
    family = _get(rule, 'cation_family', '')
    # cation None = caller declines to scope (explicit inventories);
    # a scoped mix never fires the other alkali's routes (§8.5 vs
    # §8.6 — a Na mix cannot regenerate KOH).
    return not family or cation is None or family == cation


def _reactant_counts(rule):
    counts = {}
    for name in _loads(rule, 'reactants_json'):
        counts[name] = counts.get(name, 0) + 1
    return counts


def _has_reactants(inventory, rule):
    for name, needed in _reactant_counts(rule).items():
        amount = inventory.get(name, 0 if name not in inventory
                               else None)
        if name not in inventory:
            return False, name
        if amount is not None and amount < needed:
            return False, name
    return True, None


def applicable_rules(inventory, rules=None, site=None, conditions=None,
                     windows=None, cation=None):
    """Which rules CAN fire from this inventory — and, for each that
    cannot, exactly why (missing species / wrong site / wrong alkali /
    closed gate). Refusal reasons are the guidance."""
    rules = rules if rules is not None else SEED_REACTION_RULES
    applicable, blocked = [], []
    for rule in rules:
        name = _get(rule, 'name')
        if not _cation_compatible(rule, cation):
            blocked.append({'rule': name,
                            'reason': f'rule is the '
                                      f"{_get(rule, 'cation_family')} "
                                      f'route; the mix is {cation} '
                                      '(§8.5 Na routes vs §8.6 K '
                                      'analogues)'})
            continue
        ok, missing = _has_reactants(inventory, rule)
        if not ok:
            blocked.append({'rule': name,
                            'reason': f'reactant {missing!r} absent '
                                      'or exhausted'})
            continue
        if not _site_compatible(rule, site):
            blocked.append({'rule': name,
                            'reason': f'site constraint '
                                      f"{_get(rule, 'site_constraint')!r}"
                                      f' incompatible with site '
                                      f'{site!r} (Fig 8.21 transport '
                                      'selection)'})
            continue
        open_, verdicts = _gate_verdicts(rule, conditions, windows)
        if not open_:
            blocked.append({'rule': name,
                            'reason': 'condition gate closed',
                            'gates': verdicts})
            continue
        applicable.append({'rule': name,
                           'stage': _get(rule, 'stage'),
                           'hypothesisStatus':
                               _get(rule, 'hypothesis_status'),
                           'siteConstraint':
                               _get(rule, 'site_constraint'),
                           'competingWith':
                               _loads(rule, 'competing_with_json'),
                           'gates': verdicts})
    return {'ok': True, 'applicable': applicable, 'blocked': blocked,
            'assumptions': list(_STEP_ASSUMPTIONS)}


def step_once(inventory, rule_name, rules=None, site=None,
              conditions=None, windows=None, cation=None, times=1):
    """Apply ONE named rule stoichiometrically `times` times —
    scientist-driven topology bookkeeping, never time integration.
    Returns the new inventory + the delta, or an evidence-bearing
    refusal naming what blocked it."""
    rules = rules if rules is not None else SEED_REACTION_RULES
    rule = next((r for r in rules if _get(r, 'name') == rule_name),
                None)
    if rule is None:
        return {'ok': False,
                'refusal': f'unknown rule {rule_name!r}',
                'suggestion': 'GET /api/pspp/network for the rule '
                              'library'}
    if not _cation_compatible(rule, cation):
        return {'ok': False,
                'refusal': f'rule {rule_name!r} is the '
                           f"{_get(rule, 'cation_family')} route; the "
                           f'mix is {cation}',
                'suggestion': 'use the matching alkali route (§8.5 Na '
                              'vs §8.6 K analogues) or an unscoped '
                              'explicit inventory'}
    if not _site_compatible(rule, site):
        return {'ok': False,
                'refusal': f'rule {rule_name!r} is '
                           f"{_get(rule, 'site_constraint')!r} but the "
                           f'step is sited {site!r}',
                'suggestion': 'step at the compatible site — Fig 8.21 '
                              'transport selection is physical, not '
                              'advisory'}
    open_, verdicts = _gate_verdicts(rule, conditions, windows)
    if not open_:
        return {'ok': False,
                'refusal': f'condition gate closed for {rule_name!r}',
                'gates': verdicts,
                'suggestion': 'change the gated condition (see each '
                              'gate reason) — the threshold is cited '
                              'data, not a tunable'}
    new = dict(inventory)
    consumed, produced = {}, {}
    for name, needed in _reactant_counts(rule).items():
        need = needed * times
        amount = new.get(name)
        if name not in new or (amount is not None and amount < need):
            return {'ok': False,
                    'refusal': f'reactant {name!r} absent or exhausted '
                               f'(need {need}, have '
                               f'{new.get(name, 0)})',
                    'suggestion': 'lower times, replenish the '
                                  'inventory, or fire the producing '
                                  'rule first'}
        if amount is not None:
            new[name] = amount - need
        consumed[name] = need
    for name in _loads(rule, 'products_json'):
        amount = new.get(name)
        new[name] = (times if name not in new
                     else (None if amount is None else amount + times))
        produced[name] = produced.get(name, 0) + times
    return {'ok': True, 'rule': rule_name, 'times': times,
            'inventory': new,
            'consumed': consumed, 'produced': produced,
            'gates': verdicts,
            'assumptions': list(_STEP_ASSUMPTIONS)}


def reachable_frameworks(inventory, rules=None, site=None,
                         conditions=None, windows=None,
                         species=None, cation=None):
    """Kinetics-free closure: which framework families the OPEN
    pathways can reach from this inventory. Presence-only (amounts
    ignored — without rates, exhaustion ordering would be invented).
    Each reachable species records the rule that first produced it, so
    every framework carries a concrete rule pathway + the hypothesis
    floor of that pathway. Competing branches all appear."""
    rules = rules if rules is not None else SEED_REACTION_RULES
    species = species if species is not None else SEED_CHEMICAL_SPECIES
    present = {name for name, amount in inventory.items()
               if amount is None or amount > 0}
    producedBy = {}
    fired = []
    blockedFinal = []
    changed = True
    while changed:
        changed = False
        verdicts = applicable_rules(
            {name: None for name in present}, rules, site=site,
            conditions=conditions, windows=windows, cation=cation)
        blockedFinal = verdicts['blocked']
        for entry in verdicts['applicable']:
            rule = next(r for r in rules
                        if _get(r, 'name') == entry['rule'])
            products = set(_loads(rule, 'products_json'))
            new = products - present
            if not new:
                continue
            for name in new:
                producedBy[name] = entry['rule']
            present |= new
            fired.append(entry['rule'])
            changed = True

    ruleByName = {_get(r, 'name'): r for r in rules}

    def pathway(speciesName, _seen=None):
        _seen = _seen or set()
        ruleName = producedBy.get(speciesName)
        if ruleName is None or ruleName in _seen:
            return []
        _seen.add(ruleName)
        chain = []
        for reactant in _loads(ruleByName[ruleName], 'reactants_json'):
            chain += pathway(reactant, _seen)
        return chain + [ruleName]

    frameworks = []
    for s in species:
        name = _get(s, 'name')
        if _get(s, 'species_kind') != 'framework' \
                or name not in present:
            continue
        if name not in producedBy and name in inventory:
            continue  # was an input, not a product — not 'reached'
        if name not in producedBy:
            continue
        chain = []
        for ruleName in pathway(name):
            if ruleName not in chain:
                chain.append(ruleName)
        statuses = [_get(ruleByName[r], 'hypothesis_status')
                    for r in chain]
        floor = max(statuses, key=lambda st:
                    _STANDING_ORDER.get(st, len(_STANDING_ORDER)),
                    default='')
        frameworks.append({
            'framework': name,
            'pathway': chain,
            'hypothesisFloor': floor,
            'sites': sorted({_get(ruleByName[r], 'site_constraint')
                             for r in chain} - {''}),
            'competingWith': sorted({
                c for r in chain
                for c in _loads(ruleByName[r], 'competing_with_json')}),
        })
    return {
        'ok': True,
        'reachableFrameworks': sorted(frameworks,
                                      key=lambda f: f['framework']),
        'firedRules': fired,
        'blockedRules': blockedFinal,
        'reachableSpecies': sorted(present),
        'assumptions': _STEP_ASSUMPTIONS + [
            'reachability is presence-only closure — which routes are '
            'OPEN, never which wins (framework selection is genuinely '
            'competitive, p.185)'],
    }
