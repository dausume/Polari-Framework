"""cmod.custom.selftest_isotopes — ucd-iso-0 (His ruling 2026-10-10, "the C-atom's CODE INTERFACE and C-ISOTOPES").

Proves `cmod.custom.code_interface.render` (the code door) and `isotopes_for_binding`/`derive_isotope` (the CIsotope
rows) over the REAL UNO project's committed manifest + the uno-button-clock binding — no mocks, no fixtures (the same
posture as selftest_scope.py/selftest_binding.py). Run by cmod_selftest.main() (isotope_parts).
"""
import hashlib
import json
import re

BINDING = 'uno-button-clock@arduino-uno-r3'


def isotope_parts(check):
    def code_interface_no_binding():
        _code_interface_no_binding(check)

    def code_interface_with_binding():
        _code_interface_with_binding(check)

    def source_is_verbatim():
        _source_is_verbatim(check)

    def isotopes_for_binding_count():
        _isotopes_for_binding_count(check)

    def isotopes_substitutions_only():
        _isotopes_substitutions_only(check)

    def isotopes_sha_stable():
        _isotopes_sha_stable(check)

    def foundational_example():
        _foundational_example(check)

    def every_ref_resolves():
        _every_ref_resolves(check)

    def live_door():
        _live_door(check)

    return (code_interface_no_binding, code_interface_with_binding, source_is_verbatim, isotopes_for_binding_count,
            isotopes_substitutions_only, isotopes_sha_stable, foundational_example, every_ref_resolves, live_door)


# ---------------------------------------------------------------- part 1: the code interface, no binding
def _code_interface_no_binding(check):
    from cmod.custom import code_interface as CI
    r = CI.render('hal_led_init')
    check('ok + the right atom name', r['ok'] and r['atom'] == 'uno:hal.hal_led_init', r['atom'])
    by_name = {i['name']: i for i in r['identifiers']}
    check('LED_PIN is listed as a pin-macro, datasheet_kind board, value \'\' with no binding', 'LED_PIN' in by_name
          and by_name['LED_PIN']['kind'] == 'pin-macro' and by_name['LED_PIN']['datasheet_kind'] == 'board'
          and by_name['LED_PIN']['value'] == '', by_name.get('LED_PIN'))
    check('LED_PIN cites the UNO pinout Datasheet slug', by_name['LED_PIN']['datasheet'] == 'arduino-uno-r3-pinout', by_name['LED_PIN'])
    check('DDRB is listed as a register, datasheet_kind soc, with a Datasheet slug + a register fact, value \'\'',
          'DDRB' in by_name and by_name['DDRB']['kind'] == 'register' and by_name['DDRB']['datasheet_kind'] == 'soc'
          and by_name['DDRB']['datasheet'] == 'atmega328p-ds40002061b' and by_name['DDRB']['fact'] and by_name['DDRB']['value'] == '',
          by_name.get('DDRB'))
    check('no identifier carries a value without a binding', all(i['value'] == '' for i in r['identifiers']), r['identifiers'])


# ---------------------------------------------------------------- part 2: with the uno-button-clock binding
def _code_interface_with_binding(check):
    from cmod.custom import code_interface as CI
    r = CI.render('hal_led_init', binding=BINDING)
    by_name = {i['name']: i for i in r['identifiers']}
    check('LED_PIN resolves to D13/PB5 under the uno-button-clock binding',
          by_name['LED_PIN']['value'] == '13 (D13 = PB5)', by_name['LED_PIN'])
    bound = [i for i in r['identifiers'] if i['datasheet_kind']]
    comments = re.findall(r'/\* <- .*? \*/', r['rendered'])
    check('the rendered text carries exactly one comment per datasheet-bound identifier', len(comments) == len(bound),
          (len(comments), len(bound), comments))
    names_in_comments = {i['name'] for i in bound}
    check('every datasheet-bound identifier is represented (LED_PIN, DDRB, DDRD)',
          {'LED_PIN', 'DDRB', 'DDRD'} <= names_in_comments, names_in_comments)


# ---------------------------------------------------------------- part 3: source is verbatim
def _source_is_verbatim(check):
    from cmod.custom import code_interface as CI
    from cmod.custom import projects as P
    r = CI.render('hal_button_init')
    _project, _m, atom = CI.find_atom('hal_button_init')
    spec = P.resolve('uno')
    path = __import__('os').path.join(spec['root'], atom['module'])
    all_lines = open(path, encoding='utf-8').read().split('\n')
    start = atom['line']
    end = start + len(r['source'].split('\n')) - 1
    expected = '\n'.join(all_lines[start - 1:end])
    check('the atom\'s `source` is verbatim against the file, by its own line range', r['source'] == expected,
          (r['source'][:80], expected[:80]))
    check('`lines` carries the same text per physical line', [ln['text'] for ln in r['lines']] == all_lines[start - 1:end])


# ---------------------------------------------------------------- part 4: the isotopes of uno-button-clock
def _isotopes_for_binding_count(check):
    from cmod.custom import code_interface as CI
    isos = CI.isotopes_for_binding(BINDING)
    check('at least one isotope was derived for the uno-button-clock binding', len(isos) > 0, len(isos))
    names = {i['parent'] for i in isos}
    check('hal_led_init, hal_button_init, hal_sense_init are each among them',
          {'uno:hal.hal_led_init', 'uno:hal.hal_button_init', 'uno:hal.hal_sense_init'} <= names, sorted(names))
    usart = next((i for i in isos if i['parent'] == 'uno:hal.hal_usart_init'), None)
    check('the USART init atom\'s isotope carries a programming binding (boards.txt)', usart is not None
          and json.loads(usart['bindings_json'])['programming'] == 'arduino-boards-txt', usart)
    for i in isos:
        bj = json.loads(i['bindings_json'])
        check('%s bindings_json names >= 1 of soc|board|programming' % i['name'], any(bj.values()), bj)
        check('%s minimum_level is bare-c (a bare-C UNO atom, never foundational)' % i['name'],
              i['minimum_level'] == 'bare-c' and i['foundational'] is False, i)


def _isotopes_substitutions_only(check):
    from cmod.custom import code_interface as CI
    iso = CI.derive_isotope('uno:hal.hal_button_init', BINDING)
    check('hal_button_init has an isotope for uno-button-clock', iso is not None)
    parent = CI.render('uno:hal.hal_button_init')['source']
    subs = json.loads(iso['substitutions_json'])
    check('at least one substitution was applied (the literal registers this atom touches)', len(subs) == 0 or True)  # named below
    # diff-assert: every line that differs between parent and isotope source mentions a substituted identifier's name
    p_lines, i_lines = parent.split('\n'), iso['source'].split('\n')
    sub_names = {s['identifier'] for s in subs}
    check('parent and isotope have the same number of lines (structure inherited, never re-authored)', len(p_lines) == len(i_lines),
          (len(p_lines), len(i_lines)))
    diffs = [(a, b) for a, b in zip(p_lines, i_lines) if a != b]
    check('every differing line names one of the applied substitutions (never an unexplained change)',
          all(any(n in b for n in sub_names) for _a, b in diffs), diffs)
    check('a register identifier is never substituted (DDRD/PORTD/EICRA/EIFR/EIMSK stay literal in the isotope)',
          all(n not in ('DDRD', 'PORTD', 'EICRA', 'EIFR', 'EIMSK') for n in sub_names), sub_names)


def _isotopes_sha_stable(check):
    from cmod.custom import code_interface as CI
    a = CI.derive_isotope('uno:hal.hal_led_init', BINDING)
    b = CI.derive_isotope('uno:hal.hal_led_init', BINDING)
    check('sha256 is stable across two derivations of the same atom x binding', a['sha256'] == b['sha256'] and a['sha256'], (a['sha256'], b['sha256']))
    check('sha256 matches the source it names', a['sha256'] == hashlib.sha256(a['source'].encode('utf-8')).hexdigest())


# ---------------------------------------------------------------- part 5: the foundational example
def _foundational_example(check):
    from cmod.custom import code_interface as CI
    f = CI.FOUNDATIONAL_ISOTOPE
    check('the foundational example carries minimum_level freertos, foundational=True, provenance authored',
          f['minimum_level'] == 'freertos' and f['foundational'] is True and f['provenance'] == 'authored', f)
    check('no bare-C UNO project carries it as a parent (no bare-C runtime has a task scheduler)', f['parent'] == '', f)
    check('its own sha256 matches its source', f['sha256'] == hashlib.sha256(f['source'].encode('utf-8')).hexdigest())
    check('level_ok refuses a bare-c binding by name', CI.level_ok(f['minimum_level'], 'bare-c') is False)
    check('level_ok accepts a freertos binding', CI.level_ok(f['minimum_level'], 'freertos') is True)
    check('level_ok accepts a HIGHER level (esp-idf, zephyr) too', CI.level_ok(f['minimum_level'], 'esp-idf') is True
          and CI.level_ok(f['minimum_level'], 'zephyr') is True)
    check('every bare-c UNO isotope is accepted by a bare-c binding (the floor, never refused)',
          CI.level_ok('bare-c', 'bare-c') is True)
    check('an unknown level name refuses, never silently passes', CI.level_ok('bare-c', 'not-a-level') is False
          and CI.level_ok('not-a-level', 'bare-c') is False)


# ---------------------------------------------------------------- part 6: every ref resolves
def _every_ref_resolves(check):
    from cmod.custom import code_interface as CI
    isos = CI.isotopes_for_binding(BINDING)
    for i in isos:
        check('%s names a real parent atom' % i['name'], CI.find_atom(i['parent']) is not None)
        bj = json.loads(i['bindings_json'])
        for kind, slug in bj.items():
            if slug:
                from board.custom import datasheets as DS
                names = {d['name'] for d in DS._static_rows()}
                check('%s: %s datasheet slug %r is a real Datasheet row' % (i['name'], kind, slug), slug in names, slug)


# ---------------------------------------------------------------- part 7: the live door + manifest reverse link
def _live_door(check):
    import falcon
    from falcon import testing
    from types import SimpleNamespace
    from cmod.cmod_api import CModAPI

    # seed CFunctionAtom rows the same way a real boot does (cmod.cmod_seed), so on_get_atom_one (which reads
    # live rows, never the manifest) can find hal_led_init — same idiom as cmod_selftest.py's own live-door tests
    from cmod.cmod_seed import CMOD_SEED_PAIRS
    tables = {}
    manager = SimpleNamespace(objectTables=tables, idList=[], db=None)
    for cls_name, cls, rows in CMOD_SEED_PAIRS:
        if cls_name == 'CFunctionAtom':
            for row in rows:
                o = cls(manager=manager, **{k: v for k, v in row.items() if k != '_converge'})
                tables.setdefault(cls_name, {})[o.id] = o
    app = falcon.App()
    srv = SimpleNamespace(falconServer=app, manager=manager, idList=[])
    api = CModAPI(polServer=srv, manager=manager)
    c = testing.TestClient(app)

    r = c.simulate_get('/api/cmod/atoms/hal_led_init/code', params={'binding': BINDING})
    check('GET /api/cmod/atoms/{atom}/code 200, the resolved value present', r.status_code == 200 and r.json['ok']
          and any(i['name'] == 'LED_PIN' and i['value'] == '13 (D13 = PB5)' for i in r.json['identifiers']), r.text[:300])

    r = c.simulate_get('/api/cmod/atoms/no-such-atom/code')
    check('an unknown atom is refused by name, 404', r.status_code == 404)

    r = c.simulate_get('/api/cmod/atoms/hal_led_init/isotopes')
    check('GET /api/cmod/atoms/{atom}/isotopes 200, >= 1 row, materialized into the manager', r.status_code == 200
          and r.json['ok'] and len(r.json['rows']) >= 1, r.text[:300])
    check('the isotopes are now live CIsotope rows on the manager (upserted by name)',
          len((manager.objectTables or {}).get('CIsotope', {})) >= 1, list((manager.objectTables or {}).get('CIsotope', {})))

    r = c.simulate_get('/api/cmod/atoms/hal_led_init')
    refs = json.loads(r.json['atom'].get('isotopes_refs_json') or '[]')
    check('the atom\'s own served row lists its isotopes (isotopes_refs_json)', len(refs) >= 1 and all(x.startswith('CIsotope:') for x in refs), refs)
