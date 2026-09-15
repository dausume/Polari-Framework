"""selftest_app_taxonomy — one primary category per app, N sub-categories (each belonging to one category; naming
another category's sub-category cross-lists), tags, search by name or properties; every module mapped; his rulings."""
import glob, json, os, sys

passed = total = 0


def check(label, cond, extra=''):
    global passed, total
    total += 1; passed += bool(cond)
    print('  [%s] %s %s' % ('PASS' if cond else 'FAIL', label, extra if not cond else ''))


def main():
    from moduleService.app_taxonomy import CATEGORIES, SUBCATEGORIES, DEFAULTS, classify, matches, problems
    check('three categories', tuple(CATEGORIES) == ('polari', 'network', 'hardware'))
    check('every sub-category belongs to a category', all(v[0] in CATEGORIES for v in SUBCATEGORIES.values()))
    mods = {os.path.basename(os.path.dirname(p)): json.load(open(p)).get('app', {}) for p in glob.glob('modules/*/polari-app.json')}
    check('every module is mapped (DEFAULTS) and every manifest declares a category', set(mods) <= set(DEFAULTS) and all(a.get('category') for a in mods.values()), sorted(set(mods) - set(DEFAULTS)))
    check('every manifest sub-category is in the vocabulary', all(not problems(a) for a in mods.values()), [(m, problems(a)) for m, a in mods.items() if problems(a)][:3])
    c = classify('isle_relay', mods['isle_relay'])
    check('isle_relay: primary network, cross-listed under hardware (a hardware sub-category named)', c['category'] == 'network' and 'hardware' in c['secondary'])
    check('his rulings: Business & Work = bizops, odooconnect, collab', sorted(m for m, a in mods.items() if 'business-work' in a.get('subcategories', [])) == ['bizops', 'collab', 'odooconnect'])
    check('his ruling: pspp under Materials & Devices first', mods['pspp']['subcategories'][0] == 'materials-devices')
    check('search by property: "wifi" finds the OpenWrt guests; "nutrition" finds nutrition; scope is the caller\'s (all vs a category)',
          matches('wifi', 'isle_relay', mods['isle_relay'], classify('isle_relay', mods['isle_relay'])) and matches('nutrition', 'nutrition', mods['nutrition'], classify('nutrition', mods['nutrition'])) and not matches('wifi', 'gears', mods['gears'], classify('gears', mods['gears'])))
    check('an undeclared manifest falls back to the kind (hardware kinds → hardware, else polari)', classify('x', {'kind': 'hardware-app'})['category'] == 'hardware' and classify('x', {'kind': 'polari-app'})['category'] == 'polari')
    print('\n%d/%d checks passed' % (passed, total))
    return 0 if passed == total else 1


if __name__ == '__main__':
    sys.exit(main())
