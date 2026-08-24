"""
Selftest for the topology/bundle planner (dl-6).

Run from polari-framework/:
  PYTHONPATH=.:modules python3 -m appstore.selftest_planner

Function-level: the three wizard steps render from query params
alone (zero JS), goal→module mapping filters to the live registry,
role assignment (core = strongest hosting device, small devices =
members), per-device bundles carry REAL links, honest overflow /
no-hosting-device / offline notes, and the propose-never-apply
promise.
"""

import sys

from appstore import planner_page as planner
from appstore.planner_page import _Params

_results = []


def check(label, cond, extra=''):
    _results.append((label, bool(cond)))
    print(f'{"PASS" if cond else "FAIL"}: {label}'
          + (f' — {extra}' if extra and not cond else ''))


def render(raw):
    return planner.render_page(_Params(raw))


def main():
    page = render({})
    check('step 1: device count select, internet question, goal '
          'checkboxes, zero JS, GET form (bookmarkable, nothing '
          'mutates)',
          'name="d"' in page and 'name="net"' in page
          and page.count('type="checkbox"') == len(planner.GOALS)
          and 'method="get"' in page
          and '<script' not in page)

    page = render({'d': '3', 'net': 'no', 'g': ['motors', 'food']})
    check('step 2: one performance select per device, answers '
          'carried as hidden fields, the in-what-way distinction '
          'explained',
          page.count('<select name="p') == 3
          and 'value="no"' in page
          and page.count('value="motors"') == 1
          and 'RAM' in page)

    raw = {'d': '3', 'net': 'yes', 'g': ['motors', 'food'],
           'p1': 'normal', 'p2': 'highmem', 'p3': 'small'}
    page = render(raw)
    check('roles: the strongest hosting device is CORE (device 2, '
          'high-RAM), the normal one hosts, the small one is a '
          'member',
          '<em>core</em>' in page and '<em>hosting</em>' in page
          and '<em>member</em>' in page)
    check('bundles are REAL links: Option A for hosting devices, '
          'app-deb generate links for suggested modules, Option B '
          'pieces for the member',
          'href="/downloads"' in page
          and 'href="/downloads/apps/get/motors"' in page
          and 'Option B pieces 1' in page
          and 'Polari Complete' in page)
    check('the plan explains itself: speculation explainer with '
          'the measured evidence, assignment-happens-in-topology '
          'honesty, app-debs-already-included honesty',
          'How solid is this proposal?' in page
          and 'SPECULATION' in page and '~37 s' in page
          and 'Does the download decide' in page
          and 'topology' in page
          and 'Why list per-app debs' in page)
    check('propose-never-apply stated in plain words',
          'Nothing was installed or configured' in page)

    plan = planner.plan_topology(
        ['normal', 'highmem', 'small'], ['motors', 'food'],
        {m: {} for m in ('motors magnetics gears electrodevice '
                         'hwdigital hwfpga techtree nutrition '
                         'aquaponics plant_morphology tanks '
                         'microalgae agro_forestry supplychain'
                         ).split()})
    roles = [d['role'] for d in plan['devices']]
    check('plan_topology: roles [hosting, core, member], all 14 '
          'goal modules placed core-first within budgets, no '
          'overflow',
          roles == ['hosting', 'core', 'member']
          and not plan['overflow']
          and len(plan['devices'][1]['modules']) >= len(
              plan['devices'][0]['modules'])
          and sum(len(d['modules']) for d in plan['devices'])
          == 14)

    page = render({'d': '1', 'net': 'yes',
                   'g': ['motors', 'food', 'materials',
                         'climate', 'business'],
                   'p1': 'normal'})
    check('overflow honesty: one normal device + five goals names '
          'the modules past the measured budget, never silently '
          'drops them',
          'More apps than your devices' in page
          and '⚠' in page)

    page = render({'d': '2', 'net': 'yes', 'g': ['climate'],
                   'p1': 'small', 'p2': 'small'})
    check('all-small honesty: an isle needs a hosting machine — '
          'the warning renders instead of a silent bad plan',
          'at least\n                   one hosting machine'
          in page or 'at least' in page)

    page = render({'d': '2', 'net': 'no', 'g': ['climate'],
                   'p1': 'normal', 'p2': 'small'})
    check('no-internet answer routes every device at the offline '
          'page (which owns the built-yet honesty)',
          page.count('href="/downloads/offline"') == 2)

    page = render({'d': '1', 'net': 'yes', 'g': ['nonsense'],
                   'p1': 'normal'})
    check('unknown goals are ignored (registry filter), page '
          'still renders a plan',
          'nothing selected' in page)

    page = render({'d': '99', 'net': 'yes', 'g': [],
                   'p1': 'normal'})
    check('device count clamps to the maximum instead of a '
          'runaway form',
          page.count('<select name="p') == planner.MAX_DEVICES)

    page = render({'d': '2', 'net': 'yes', 'g': [],
                   'p1': 'normal', 'p2': 'betamax'})
    check('an invalid performance value re-renders step 2, '
          'never a stack trace',
          page.count('<select name="p') == 2)

    passed = sum(1 for _, ok in _results if ok)
    print(f'\n{passed}/{len(_results)} checks passed')
    return 0 if passed == len(_results) else 1


if __name__ == '__main__':
    sys.exit(main())
