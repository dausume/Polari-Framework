"""hwnocode_schematic_selftest — cb-1 / cb-2 PROTOTYPE (AI-Notes/plans/COMPONENT_BINDING_PLAN.md): the schematic component rows and the
rough HardwareFeature model. Checks: every new class constructs from its seed rows with no stray field and is registered; the seed is
the user's drawing (2 solved, 2 unsolved; the solved ones carry their filter and guard parts, the unsolved only their core part) and is
internally consistent (every port and part names a component that exists, every part's port exists on its component, no value is
invented); "solved" in this prototype names the drawing, never a solver; the column model (every column known, required flags, the
narrowing names only real columns); the completeness reader (a seeded feature, an open one, one bound to an unsolved component, one
naming a component that does not exist); the two pages (each class a known class with the fields it names, the feature table's
columns taken from the column model, no new route); a feature is never converged by a re-seed.

    PYTHONPATH=.:modules python3 -m hwnocode.hwnocode_schematic_selftest      # from polari-framework/
"""
import inspect
import json
import sys

passed = total = 0


def check(label, cond, extra=''):
    global passed, total
    total += 1
    passed += bool(cond)
    print('  [%s] %s %s' % ('\033[0;32mPASS\033[0m' if cond else '\033[0;31mFAIL\033[0m', label, extra if not cond else ''))


NEW = ('SchematicComponent', 'SchematicComponentPort', 'SchematicComponentPart', 'HardwareFeature', 'SchematicComponentCheck')
#: the drawing's own rows (the solved rows of a HardwareSolution are checked by hwnocode_solve_selftest)
_DRAWN = lambda rows, key='name': [r for r in rows if not r.get('hardware_solution') and ':' not in r.get(key, '')]   # noqa: E731


def _pairs():
    from hwnocode.hwnocode_seed import HWNOCODE_SEED_PAIRS
    return {n: (c, rows) for n, c, rows in HWNOCODE_SEED_PAIRS if n in NEW}


def classes_and_seeds():
    from hwnocode.hwnocode_basis import HWNOCODE_CLASSES
    names = [c.__name__ for c in HWNOCODE_CLASSES]
    check('the five classes are registered in HWNOCODE_CLASSES', all(n in names for n in NEW), names)
    pairs = _pairs()
    check('each has a seed pair', sorted(pairs) == sorted(NEW), sorted(pairs))
    stray = []
    for n, (cls, rows) in pairs.items():
        params = set(inspect.signature(cls.__init__).parameters)
        for r in rows:
            extra = [k for k in r if k not in params and k != '_converge']
            if extra:
                stray.append('%s:%s:%s' % (n, r.get('name'), extra))
            cls(**{k: v for k, v in r.items() if k != '_converge'})     # constructs, manager-less
    check('every seed row constructs its class with no stray field', not stray, stray)
    for n, (cls, _rows) in pairs.items():
        check('%s says what it is (docstring "What it is:") and in plain words' % n,
              'What it is:' in (cls.__doc__ or '') and bool(getattr(cls, 'plain_words', '')))
    feats = _DRAWN(pairs['HardwareFeature'][1])
    check('a drawn HardwareFeature is a person\'s to edit: nothing on it converges on a re-seed', all(f['_converge'] == [] for f in feats),
          [f['_converge'] for f in feats])


def the_drawing():
    pairs = _pairs()
    comps = {r['name']: r for r in _DRAWN(pairs['SchematicComponent'][1])}
    ports = _DRAWN(pairs['SchematicComponentPort'][1], 'component')
    parts = _DRAWN(pairs['SchematicComponentPart'][1], 'component')
    states = sorted((c['title'], c['solve_state']) for c in comps.values())
    check('the drawing: LightComp and BtnSchematicComponent solved, a light and a button unsolved', states == [
        ('BtnSchematicComponent', 'solved'), ('Button (unsolved)', 'unsolved'), ('Light (unsolved)', 'unsolved'), ('LightComp', 'solved')], states)
    roles = {n: sorted(p['role'] for p in parts if p['component'] == n) for n in comps}
    check('solved components carry core + filter + guard + supply; unsolved ones only their core part', roles == {
        'light-comp': ['core', 'filter', 'guard', 'supply'], 'btn-comp': ['core', 'filter', 'guard', 'supply'],
        'light-unsolved': ['core'], 'button-unsolved': ['core']}, roles)
    pins = sorted('%s %s' % (p['chip'], p['pin']) for p in ports if p['component'] == 'btn-comp' and p['kind'] == 'signal')
    check('the button lands on chip1 GPIO3 and chip2 GPIO4, as drawn', pins == ['chip1 GPIO3', 'chip2 GPIO4'], pins)
    orphans = [r['name'] for r in ports + parts if r['component'] not in comps]
    check('every port and part names a component that exists', not orphans, orphans)
    port_names = {(p['component'], p['port']) for p in ports}
    bad_port = [p['name'] for p in parts if p['port'] and (p['component'], p['port']) not in port_names]
    check('every part sits on a port of its own component (or is the core part)', not bad_port, bad_port)
    check('no part value is invented: the drawing gives none, so every value is empty (shown as unverified)',
          all(p['value'] == '' for p in parts))
    honest = [c['name'] for c in comps.values() if c['solve_state'] == 'solved' and 'no solver has run' not in c['solved_by']]
    check('"solved" names the drawing, never a solver: no solver exists yet (cb-3)', not honest, honest)
    check('an unsolved component has no solved_by', all(not c['solved_by'] for c in comps.values() if c['solve_state'] == 'unsolved'))
    from hwnocode.objects.hwnocode.SchematicComponent import SchematicComponent
    from hwnocode.objects.hwnocode.SchematicComponentPart import SchematicComponentPart
    from hwnocode.objects.hwnocode.SchematicComponentPort import SchematicComponentPort
    check('every value is from its class\'s own list (solve_state, role, port kind)',
          all(c['solve_state'] in SchematicComponent.SOLVE_STATES for c in comps.values())
          and all(p['role'] in SchematicComponentPart.ROLES for p in parts) and all(p['kind'] in SchematicComponentPort.KINDS for p in ports))


def column_model():
    from hwnocode.custom import feature_columns as FC
    from hwnocode.objects.hwnocode.HardwareFeature import HardwareFeature
    params = set(inspect.signature(HardwareFeature.__init__).parameters)
    keys = [c['key'] for c in FC.COLUMNS]
    check('every column is a HardwareFeature field', all(k in params for k in keys), [k for k in keys if k not in params])
    bad = ['%s->%s' % (c['key'], n) for c in FC.COLUMNS for n in c['narrows'] if n not in keys]
    check('each column narrows only real columns, each with a reason in words', not bad and all(all(w for w in c['narrows'].values())
                                                                                               for c in FC.COLUMNS), bad)
    check('the UI control is optional; the struct field, no-code piece, HAL role, protocol, component, pins, solution, device and simulator are required',
          [c['key'] for c in FC.COLUMNS if not c['required']] == ['ui_control'])


def completeness():
    from hwnocode.custom import feature_columns as FC
    pairs = _pairs()
    comps = _DRAWN(pairs['SchematicComponent'][1])
    feats = {f['name']: f for f in _DRAWN(pairs['HardwareFeature'][1])}
    s = FC.state(feats['button-on'], comps)
    src = {c['key']: c['source'] for c in s['columns']}
    check('button-on: struct field, component and pins chosen; no-code piece, HAL role, protocol and the solution and its pair open; not complete, naming them',
          src['struct_field'] == 'chosen' and src['schematic_component'] == 'chosen' and src['pins'] == 'chosen'
          and src['nocode_variable'] == 'open' and not s['complete']
          and s['missing'] == ['No-code piece', 'HAL role', 'Protocol', 'Hardware solution', 'Device', 'Simulator pair'], s)
    full = dict(feats['light-on'], nocode_variable='LED_PIN', hal_role='led', protocol='active-high output', hardware_solution='a-solution',
                device='a-board', simulator='its twin')
    s = FC.state(full, comps)
    check('the same feature with every required column filled and a solved component is complete; the filled-in ones read suggested',
          s['complete'] and {c['key']: c['source'] for c in s['columns']}['protocol'] == 'suggested', s)
    s = FC.state(dict(full, schematic_component='light-unsolved'), comps)
    check('bound to an unsolved component it is not complete, and says why', not s['complete'] and 'unsolved' in s['words'], s['words'])
    s = FC.state(dict(full, schematic_component='no-such'), comps)
    check('naming a component that does not exist says missing', s['schematic'] == 'missing' and not s['complete'], s)
    s = FC.state({'name': 'empty'}, comps)
    check('an empty feature: every column open, none chosen', all(c['source'] == 'open' for c in s['columns']) and s['schematic'] == 'none')


def pages():
    from hwnocode.hwnocode_page import SEED_HWNOCODE_PAGE_DISPLAYS
    from hwnocode.hwnocode_basis import HWNOCODE_CLASSES
    from hwnocode.schematic_page import FEATURE_COLUMNS
    from hwnocode.custom import feature_columns as FC
    known = {c.__name__: c for c in HWNOCODE_CLASSES}
    by_route = {p['pageRoute']: p for p in SEED_HWNOCODE_PAGE_DISPLAYS}
    check('both pages are seeded', 'schematic-components' in by_route and 'hardware-features' in by_route, sorted(by_route))
    bad, comps = [], []
    for route in ('schematic-components', 'hardware-features'):
        for row in json.loads(by_route[route]['definition'])['rows']:
            for it in row['items']:
                inputs = it['componentProps']['inputs']
                comps.append(it['componentProps']['componentName'])
                if inputs.get('dataPath'):
                    bad.append('%s reads a door: %s' % (it['id'], inputs['dataPath']))
                for k in ('className', 'componentClass', 'portClass', 'partClass', 'featureClass', 'checkClass'):
                    cn = inputs.get(k)
                    if cn and cn not in known:
                        bad.append('%s.%s=%s unknown' % (it['id'], k, cn))
                cn = inputs.get('className')
                if cn in known:
                    params = set(inspect.signature(known[cn].__init__).parameters)
                    miss = [c for c in (inputs.get('columns') or '').split(',') if c and c not in params]
                    if miss:
                        bad.append('%s columns %s' % (it['id'], miss))
    check('every class named is a registered class with the columns asked for, and nothing reads a door (no new route)', not bad, bad)
    check('the pages use the two new generic components and configured tables only',
          sorted(set(comps)) == ['class-rows-table', 'feature-cards-table', 'schematic-component-cards'], sorted(set(comps)))
    from hwnocode.objects.hwnocode.HardwareFeature import HardwareFeature
    params = set(inspect.signature(HardwareFeature.__init__).parameters)
    bad = [c['key'] for c in FEATURE_COLUMNS if c['source_key'] not in params or any(v not in params for v in (c.get('fields') or {}).values())
           or (c['kind'] == 'schematic' and c.get('ref_field') not in params)]
    check('every feature-table card names HardwareFeature fields', not bad, bad)
    check('each card\'s required flag comes from the column model',
          all(c['required'] == bool(FC.column(c['source_key']) and FC.column(c['source_key'])['required']) for c in FEATURE_COLUMNS))


def manifest():
    with open(__file__.replace('hwnocode_schematic_selftest.py', 'polari-app.json')) as fh:
        m = json.load(fh)
    check('the manifest lists the classes, their files, the custom files, the page and this selftest',
          all(n in m['classes'] for n in NEW) and all('objects/hwnocode/' + n in m['files']['objects'] for n in NEW)
          and 'custom/feature_columns' in m['files']['custom'] and 'custom/schematic_seed' in m['files']['custom']
          and 'schematic_page' in m['files']['page'] and 'hwnocode_schematic_selftest' in m['selftests'])


def main():
    print('hwnocode schematic selftest (cb-1 / cb-2 prototype)')
    for part in (classes_and_seeds, the_drawing, column_model, completeness, pages, manifest):
        print('-- %s' % part.__name__)
        try:
            part()
        except Exception as e:  # noqa: BLE001 — a crash is a failed check, named
            import traceback
            traceback.print_exc()
            check('%s ran without raising' % part.__name__, False, '%s: %s' % (type(e).__name__, e))
    print('\n%d/%d checks passed' % (passed, total))
    return 0 if passed == total else 1


if __name__ == '__main__':
    sys.exit(main())
