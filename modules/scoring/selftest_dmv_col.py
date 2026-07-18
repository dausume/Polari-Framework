"""
Selftest — col-1: the DMV cost-of-living vocabulary.

Run from polari-framework/:
    python3 -m scoring.selftest_dmv_col

Pins the vocabulary's promises: names unique and every statute value
resolvable against its term + subject + contexts; the deposit caps
read back per jurisdiction with their official-code citations
(VA=2 months across all five NoVA jurisdictions, MD=1, DC=1); the
DELIBERATE gap — no general lease-break-cap value exists anywhere in
the DMV, because no statute creates one (the gap is the finding);
the escape-cost categories extend the scr-12a walkthrough with their
guidance; and the cross-tree abstract tags make the abstraction
matcher suggest a longevity term for a plain-language longevity
intent.
"""

import json
import os
import sys
from types import SimpleNamespace

sys.path.insert(0, os.path.dirname(
    os.path.dirname(os.path.abspath(__file__))))

from scoring.abstraction import suggest_scores_for_assertion
from scoring.dmv_col_seed import (SEED_DMV_GEO_CONTEXTS,
                                  SEED_DMV_SUBJECTS,
                                  SEED_DMV_TERMS,
                                  SEED_DMV_TIMEFRAMES,
                                  SEED_ESCAPE_COST_CATEGORIES,
                                  SEED_ESCAPE_COST_TERMS,
                                  SEED_PERSONA_CONTEXTS,
                                  SEED_STATUTE_VALUES)
from scoring.survival_costs import (SEED_COST_CATEGORIES,
                                    SEED_COST_TERMS,
                                    survival_walkthrough)

PASS, FAIL = '\033[0;32mPASS\033[0m', '\033[0;31mFAIL\033[0m'
_results = []


def check(label, cond, extra=''):
    _results.append(bool(cond))
    print(f'  [{PASS if cond else FAIL}] {label}'
          f'{("  " + extra) if extra else ""}')


def _mgr():
    tables = {
        'ScoreTerm': SEED_DMV_TERMS + SEED_ESCAPE_COST_TERMS
        + SEED_COST_TERMS,
        'ScoreContext': SEED_DMV_GEO_CONTEXTS + SEED_DMV_TIMEFRAMES
        + SEED_PERSONA_CONTEXTS,
        'ScoreSubject': SEED_DMV_SUBJECTS,
        'ContextualizedValue': SEED_STATUTE_VALUES,
        'CostCategory': SEED_COST_CATEGORIES
        + SEED_ESCAPE_COST_CATEGORIES,
        'ScoreAssertion': [
            {'name': 'a-longevity-intent',
             'intent': 'improve how long housing lasts',
             'status': 'asserted'}],
        'ScoreConcept': [],
    }
    return SimpleNamespace(objectTables={
        cls: {row['name']: SimpleNamespace(**row) for row in rows}
        for cls, rows in tables.items()})


def _vocabulary():
    print('vocabulary integrity')
    for label, rows in (
            ('geo contexts', SEED_DMV_GEO_CONTEXTS),
            ('personas', SEED_PERSONA_CONTEXTS),
            ('terms', SEED_DMV_TERMS + SEED_ESCAPE_COST_TERMS),
            ('categories', SEED_ESCAPE_COST_CATEGORIES),
            ('statute values', SEED_STATUTE_VALUES)):
        names = [r['name'] for r in rows]
        check(f'{label}: names unique ({len(names)} rows)',
              len(names) == len(set(names)))
    check('13 geography contexts (11 jurisdictions + region + MSA)',
          len(SEED_DMV_GEO_CONTEXTS) == 13)
    check('8 persona contexts, each PUMS-reproducible',
          len(SEED_PERSONA_CONTEXTS) == 8
          and all('pums' in json.loads(p['value_json'])
                  for p in SEED_PERSONA_CONTEXTS))
    m = _mgr()
    terms = m.objectTables['ScoreTerm']
    contexts = m.objectTables['ScoreContext']
    subjects = m.objectTables['ScoreSubject']
    unresolved = [
        v['name'] for v in SEED_STATUTE_VALUES
        if v['term_name'] not in terms
        or v['subject_name'] not in subjects
        or any(c not in contexts
               for c in json.loads(v['context_names_json']))]
    check('every statute value resolves term + subject + contexts',
          unresolved == [], f'{unresolved}')
    check('categories reference terms that exist',
          all(c['term_name'] in terms
              for c in SEED_ESCAPE_COST_CATEGORIES))


def _statute_values():
    print('law-as-data (official code citations)')
    caps = {v['subject_name']: v for v in SEED_STATUTE_VALUES
            if v['term_name'] == 'security-deposit-cap-months'}
    va = [k for k in caps if k.startswith('va-')]
    md = [k for k in caps if k.startswith('md-')]
    check('deposit caps cover all 11 jurisdictions',
          len(caps) == 11 and 'dc' in caps
          and len(va) == 5 and len(md) == 5)
    check('VA = 2 months in all five NoVA jurisdictions '
          '(§55.1-1226)',
          all(caps[k]['pre_normalized_value'] == 2.0
              and '55.1-1226' in caps[k]['provenance_id']
              for k in va))
    check('MD = 1 month in all three counties (RP §8-203)',
          all(caps[k]['pre_normalized_value'] == 1.0
              and '8-203' in caps[k]['provenance_id'] for k in md))
    check('DC = 1 month (§42-3502.17)',
          caps['dc']['pre_normalized_value'] == 1.0
          and '42-3502.17' in caps['dc']['provenance_id'])
    check('every citation names an official code host URL',
          all(any(host in v['provenance_id'] for host in
                  ('code.dccouncil.gov', 'law.lis.virginia.gov',
                   'mgaleg.maryland.gov'))
              for v in SEED_STATUTE_VALUES))

    leasebreak_values = [v for v in SEED_STATUTE_VALUES
                         if v['term_name']
                         == 'leasebreak-liability-cap']
    check('the HONEST GAP: no general lease-break-cap value exists '
          'for any jurisdiction (none exists in statute)',
          leasebreak_values == [])
    term = next(t for t in SEED_DMV_TERMS
                if t['name'] == 'leasebreak-liability-cap')
    check('the gap is RECORDED on the term (VA uncapped named, '
          'carve-outs cited as carve-outs)',
          'NO GENERAL CAP' in term['description']
          and '8-212.1' in term['description']
          and 'never as general values' in term['notes'])


def _walkthrough():
    print('scr-12a walkthrough extension')
    result = survival_walkthrough(_mgr())
    steps = {s['category']: s for s in result['steps']}
    check('walkthrough serves the escape-cost reserve with its '
          'guidance',
          result['ok'] and 'escape-cost-reserve' in steps
          and 'ability to LEAVE'
          in steps['escape-cost-reserve']['guidance'])
    check('and the displacement-exposure step',
          'displacement-risk' in steps
          and 'eviction filing'
          in steps['displacement-risk']['guidance'])
    check('both are optional (baseline stays complete without '
          'them)',
          not steps['escape-cost-reserve']['required']
          and not steps['displacement-risk']['required'])
    check('original scr-12a categories still present around them',
          'housing' in steps and 'uncancellable-subscriptions'
          in steps)


def _interconnection():
    print('cross-tree interconnection')
    longevity = [t for t in SEED_DMV_TERMS
                 if 'longevity' in json.loads(
                     t['abstract_tags_json'])]
    check('longevity terms tag into household-economics '
          '(cross-tree by design)',
          len(longevity) >= 3
          and any('household-economics'
                  in json.loads(t['abstract_tags_json'])
                  for t in longevity))
    check('escape-cost terms tag into labor-mobility',
          any('labor-mobility' in json.loads(t['abstract_tags_json'])
              for t in SEED_DMV_TERMS
              if 'escape-cost' in json.loads(
                  t['abstract_tags_json'])))
    result = suggest_scores_for_assertion(_mgr(),
                                          'a-longevity-intent')
    names = [s['name'] for s in result.get('suggestions', [])]
    check("matcher suggests a longevity term for 'improve how long "
          "housing lasts'",
          result.get('ok', True)
          and any(n in names for n in ('housing-stock-median-age',
                                       'structural-problem-rate',
                                       'demolition-turnover')),
          f'top: {names[:3]}')


def main():
    _vocabulary()
    _statute_values()
    _walkthrough()
    _interconnection()
    passed, total = sum(_results), len(_results)
    print(f'\n{passed}/{total} checks passed')
    return 0 if passed == total else 1


if __name__ == '__main__':
    sys.exit(main())
