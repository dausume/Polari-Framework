"""
Selftest for the computerparts module (ai-8).

Run from polari-framework/:
    python3 -m computerparts.computerparts_selftest

Stdlib-only. Pins: every price is DATED with a source; build cost
derives from part rows (missing parts stated, oldest date
surfaced); assembly checks derive from declared specs with
'unverified' — never guessed — for undeclared ones; break-even is
None when either side is unknown.
"""

import json

from computerparts.custom.parts_assembly import assembly_check
from computerparts.parts_basis import (
    CONDITIONS, PART_KINDS, break_even_months, build_report,
)
from computerparts.parts_seed import (
    SEED_COMPUTER_BUILDS, SEED_COMPUTER_PARTS,
)

_results = []


def check(label, cond, extra=''):
    _results.append((label, bool(cond)))
    print(f'{"PASS" if cond else "FAIL"}: {label}'
          + (f' — {extra}' if extra and not cond else ''))


if __name__ == '__main__':
    print('== suite: dated-price parts ==')
    check('every part price is dated with a source (the ai-7 '
          'rule) and uses known kind/condition',
          all(p['price_as_of'] and p['price_source']
              and p['price_amount'] > 0
              and p['kind'] in PART_KINDS
              and p['condition'] in CONDITIONS
              for p in SEED_COMPUTER_PARTS))
    check('estimate prices SAY they are estimates (build-guide-'
          'sourced rows; listing-sourced rows stand on their '
          'listing)',
          all('estimate' in p['price_note']
              for p in SEED_COMPUTER_PARTS
              if 'ai-pc-build-guide' in p['price_source']))

    parts_by_name = {p['name']: p for p in SEED_COMPUTER_PARTS}

    print('== suite: derived build cost ==')
    reports = {b['name']: build_report(b, parts_by_name)
               for b in SEED_COMPUTER_BUILDS}
    check('example builds seeded (3 generic + the owned-6338N '
          'machine), totals derived from part rows',
          set(reports) == {'build-used-3090', 'build-5060ti-16gb',
                           'build-used-4090', 'build-xeon-6338n'}
          and all(r['total_usd'] > 0 and not r['missing_parts']
                  for r in reports.values()))
    check('owned-chip build: LGA4189 socket + DDR4 checks answer '
          'ok; valuation is priced but marked a VALUATION',
          assembly_check(
              [b for b in SEED_COMPUTER_BUILDS
               if b['name'] == 'build-xeon-6338n'][0],
              parts_by_name)['feasible'] is True
          and 'VALUATION' in parts_by_name[
              'cpu-xeon-6338n-owned']['price_note'])
    r3090 = reports['build-used-3090']
    expected = sum(parts_by_name[p]['price_amount']
                   for p in json.loads(
                       [b for b in SEED_COMPUTER_BUILDS
                        if b['name'] == 'build-used-3090'
                        ][0]['parts_json']))
    check('total is exactly the sum of its parts',
          abs(r3090['total_usd'] - expected) < 0.01,
          f"{r3090['total_usd']} vs {expected}")
    check('oldest price date surfaced (freshness of the stalest '
          'part)', r3090['price_as_of_oldest'] == '2026-08-16')
    ghost = build_report({'name': 'x', 'parts_json':
                          '["gpu-rtx3090-used", "no-such-part"]',
                          'specs_json': '{}'}, parts_by_name)
    check('missing parts are STATED, cost still sums the rest',
          ghost['missing_parts'] == ['no-such-part']
          and ghost['total_usd'] == 700.0)

    print('== suite: assembly feasibility (derived, honest) ==')
    asm = assembly_check(SEED_COMPUTER_BUILDS[0], parts_by_name)
    by_check = {c['check']: c for c in asm['checks']}
    check('socket + ram-type + psu checks ANSWER from declared '
          'specs (AM5/DDR5/850W seeds)',
          by_check['socket']['verdict'] == 'ok'
          and by_check['ram-type']['verdict'] == 'ok'
          and by_check['psu-wattage']['verdict'] == 'ok')
    check('undeclared clearance stays UNVERIFIED, never guessed',
          by_check['gpu-clearance']['verdict'] == 'unverified'
          and 'not declared' in by_check['gpu-clearance']['detail'])
    check('feasible = every ANSWERED check passes',
          asm['feasible'] is True)
    # a deliberate mismatch: DDR4 ram on the DDR5 board
    bad_parts = dict(parts_by_name)
    bad_parts['ram-ddr4'] = {'name': 'ram-ddr4', 'kind': 'ram',
                             'specs_json':
                             '{"ram_type": "DDR4"}'}
    bad = assembly_check(
        {'parts_json': '["cpu-ryzen7-7700", "mb-am5-b650", '
                       '"ram-ddr4"]'}, bad_parts)
    check('a real mismatch is CAUGHT and named',
          bad['feasible'] is False
          and any(c['verdict'] == 'mismatch'
                  and 'DDR4' in c['detail']
                  for c in bad['checks']))
    none_declared = assembly_check({'parts_json': '[]'}, {})
    check('no declared specs -> feasible None + the affordance '
          'named', none_declared['feasible'] is None
          and 'declare' in none_declared['note'])

    print('== suite: break-even ==')
    check('break-even months derive from the two costs',
          break_even_months(1655.0, 555.0) == 3.0
          and break_even_months(1655.0, 248.0) == 6.7)
    check('unknown either side -> None, never a guess',
          break_even_months(0, 555) is None
          and break_even_months(1655, 0) is None)

    passed = sum(1 for _, ok in _results if ok)
    print(f'{passed}/{len(_results)} checks passed')
    raise SystemExit(0 if passed == len(_results) else 1)
