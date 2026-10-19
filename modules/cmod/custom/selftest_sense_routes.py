"""selftest_sense_routes - fgm-5b (MISSION_PROFILE_SOLVER_PLAN.md section 16): the sense-led-line isotopes as REAL Jinja2 templates, the sibling of selftest_button_routes (fgm-5a). Proves: the catom layout on
disk (catom.json / README / isotopes/<iso>/{isotope.json, substitutions.json, template.c.j2}) is complete and cross-refers to real catalogue rows and FirmwareVariants; each template renders
DETERMINISTICALLY with every register / bit / vector taken from the cited rows (and on other pins too); bad knobs are refused by name; each rendered variant COMPILES through the board engines seam (measured
flash/RAM, deterministic hex) and the existing variants' bytes did not change (the identical-hex gate); the iso-0 catalogue finds the new atoms (status compiles, measured costs) and climbs to proven-on-twin /
proven-on-hardware from a passing ScenarioRun of the route's own acceptance Scenario, falling back on a newer failure. The twin runs themselves (N toggles -> N edges, the negative controls) are in
board.board_variant_twin_selftest. Run by cmod_selftest.main() (sense_route_parts)."""
import json
import os
import tempfile
from types import SimpleNamespace

ROUTE_VARIANTS = {'poll': 'uno-light-sense-poll', 'pcint': 'uno-light-sense-pcint'}
ROUTE_ROWS = {'poll': 'sense-led-line:gpio-poll', 'pcint': 'sense-led-line:pin-change-interrupt'}
ROUTE_SCENARIOS = {'sense-led-line:gpio-poll': 'sense-poll-line-acceptance', 'sense-led-line:pin-change-interrupt': 'sense-pcint-line-acceptance'}
#: the hexes the identical-hex gate holds (the committed make-alone hex sha256 prefixes of the manifest) - hal.c's HAL_SENSE_ROUTE guard moved none of them; scl (led_follow_state) moved the light and button-clock hexes ON PURPOSE (same wire, same pins)
GATE = {'uno-button-clock': '0525a11f21b2c1f2', 'uno-light-unsensed': '1e75dab5ee7eb758', 'uno-sim-rig': '4188f6ae7d65bfc7', 'uno-light-pcint': 'e23a590496655b15', 'uno-light-analog': '3f8fbd0b742b03f9'}


def _engine():
    try:
        from board.custom import board_engines as be
        return be.resolve('avr-gcc')['how'] in ('local-binary', be.LOCAL_IMAGE)
    except Exception:  # noqa: BLE001
        return False


def sense_route_parts(check):
    def layout():
        _layout(check)

    def rendering():
        _rendering(check)

    def refusals():
        _refusals(check)

    def compiles():
        _compiles(check)

    def catalogue():
        _catalogue(check)

    def ladder():
        _ladder(check)

    return (layout, rendering, refusals, compiles, catalogue, ladder)


def _layout(check):
    from board.custom import sense_routes as SR
    from board.custom import variants as V
    from cmod.custom import isotope_variants as IV
    root = os.path.join(SR.CATOMS, SR.CATOM)
    need = ['catom.json', 'README.md', '_common.j2'] + [os.path.join('isotopes', SR.ROUTES[r][1], f) for r in SR.ROUTES for f in ('isotope.json', 'substitutions.json', 'template.c.j2')]
    check('the sense-led-line catom has the section 5b layout on disk (catom.json, README.md, a macro file, per isotope: isotope.json, substitutions.json, template.c.j2) - the JSON files are present (the repo ignores *.json: they are force-added)',
          all(os.path.isfile(os.path.join(root, f)) for f in need), [f for f in need if not os.path.isfile(os.path.join(root, f))])
    catom = json.load(open(os.path.join(root, 'catom.json')))
    fams = {h['family'] for h in catom['hal_contract']}
    check('catom.json names its HAL variables with the plan 5b families (drive / register / protocol / signal / execution) and its two functions',
          fams == {'drive', 'register', 'protocol', 'signal', 'execution'} and [f['function'] for f in catom['interface']] == ['hal_sense_init', 'hal_sense_read'] and catom['job'] == 'sense-led-line', sorted(fams))
    rows = {v['name'] for v in IV.variants()}
    names = {v['name'] for v in V.SEED_FIRMWARE_VARIANTS}
    for r, (code, iso, fname, variant_row) in SR.ROUTES.items():
        d = os.path.join(SR.CATOMS, SR.CATOM, 'isotopes', iso)
        meta = json.load(open(os.path.join(d, 'isotope.json')))
        sub = json.load(open(os.path.join(d, 'substitutions.json')))
        check('%s: isotope.json points at a REAL catalogue row, the file it renders, its route code and FirmwareVariants that exist' % iso,
              meta['variant_row'] == variant_row and variant_row in rows and meta['renders_to'] == fname and meta['hal_sense_route_code'] == code and meta['sense_route'] == r
              and set(meta['firmware_variants']) <= names and ROUTE_VARIANTS[r] in meta['firmware_variants'], meta)
        check('%s: substitutions.json says where every number comes from (knobs + derived-from-rows)' % iso, bool(sub['knobs']) and bool(sub['derived_from_rows']))
    rel = os.path.relpath(SR.CATOMS, os.path.dirname(SR.BR.HERE)).split(os.sep)
    check('the layout stays under custom/ beside read-button (the manifests selftest allows only objects/ custom/ initialData/ as module subfolders): board/%s' % '/'.join(rel),
          rel[0] == 'custom' and rel[-2:] == ['uno', 'catoms'] and os.path.isdir(os.path.join(SR.CATOMS, 'read-button')), rel)


def _knobs(variant):
    from board.custom import variants as V
    return V.resolve(V.find(variant))['knobs']


def _rendering(check):
    from board.custom import sense_routes as SR
    for r, variant in ROUTE_VARIANTS.items():
        k = _knobs(variant)
        a, b = SR.render(r, k), SR.render(r, k)
        check('%s: the template renders the SAME bytes twice (no timestamp)' % r, a['text'] == b['text'] and SR.sha256(a['text']) == SR.sha256(b['text']))
        check('%s: file %s, template sha256 recorded, no unresolved template syntax, cites present' % (r, a['file']),
              a['file'] == SR.ROUTES[r][2] and len(a['template_sha256']) == 64 and '{{' not in a['text'] and '{%' not in a['text'] and len(a['cites']) >= 2)
    pp = SR.render('poll', _knobs('uno-light-sense-poll'))
    check('poll on D3: PD3 read through PIND / DDRD, no interrupt and no pull-up in the file (the pin is a wire from the LED line), one look per hal_sense_read call',
          pp['plan']['soc_pin'] == 'PD3' and pp['plan']['pin_reg'] == 'PIND' and 'ISR(' not in pp['text'] and 'PORTD' not in pp['text'] and 'PCMSK' not in pp['text'], pp['plan'])
    p = SR.render('pcint', _knobs('uno-light-sense-pcint'))['plan']
    check('pcint on D8: PB0 -> PCMSK0.PCINT0, PCICR.PCIE0, PCIFR.PCIF0, vector PCINT0_vect (read off the SocPin + cited RegisterField rows)',
          (p['soc_pin'], p['mask_reg'], p['mask_bit'], p['enable_bit'], p['flag_bit'], p['vector']) == ('PB0', 'PCMSK0', 'PCINT0', 'PCIE0', 'PCIF0', 'PCINT0_vect'), p)
    other = {n: SR.pcint_plan(n) for n in (4, 14)}
    check('pcint on other pins: D4 -> PCMSK2.PCINT20/PCIE2/PCINT2_vect, A0 (14) -> PCMSK1.PCINT8/PCIE1/PCINT1_vect (port C: said uncited, never a made-up page)',
          (other[4]['mask_reg'], other[4]['mask_bit'], other[4]['vector']) == ('PCMSK2', 'PCINT20', 'PCINT2_vect') and (other[14]['mask_reg'], other[14]['mask_bit'], other[14]['vector']) == ('PCMSK1', 'PCINT8', 'PCINT1_vect')
          and any('no cited RegisterField row' in c for c in other[14]['cites']), other)
    t4 = SR.render('pcint', dict(_knobs('uno-light-sense-pcint'), sense_pin=4))['text']
    check('a different pin renders a different file, still deterministic', t4 != SR.render('pcint', _knobs('uno-light-sense-pcint'))['text'] and 'ISR(PCINT2_vect)' in t4
          and t4 == SR.render('pcint', dict(_knobs('uno-light-sense-pcint'), sense_pin=4))['text'])
    check('the generator environment is the strict one: a template asked for a key the context lacks fails by name', _strict_fails(SR))


def _strict_fails(SR):
    from cmod.custom.generator import env as E
    from cmod.custom.generator.filters import GenError
    try:
        E.render(SR.template_path('pcint'), {'file': 'x.c'}, templates_dir=SR.CATOMS)
        return False
    except GenError as e:
        return 'missing' in str(e)


def _refusals(check):
    from board.custom import sense_routes as SR
    from board.custom import variants as V

    def refused(variant, **knobs):
        v = dict(V.find(variant), knobs_json=json.dumps(dict(json.loads(V.find(variant)['knobs_json']), **knobs)))
        try:
            V.resolve(v)
            return ''
        except V.VariantRefused as e:
            return str(e)
    check('poll and pcint refuse D1 (the USB serial line) and D20 (no such pin), by name', 'D2..D13' in refused('uno-light-sense-pcint', sense_pin=1) and 'D2..D13' in refused('uno-light-sense-poll', sense_pin=1)
          and refused('uno-light-sense-pcint', sense_pin=20) != '', refused('uno-light-sense-pcint', sense_pin=1)[:120])
    check('the sense pin may not be the LED pin or the button pin', 'same pin' in refused('uno-light-sense-pcint', sense_pin=6) and 'same pin' in refused('uno-light-sense-poll', sense_pin=2),
          refused('uno-light-sense-pcint', sense_pin=6)[:120])
    check('a route other than int1 / poll / pcint is refused; a sense route without the sense feature is refused',
          'int1' in refused('uno-light-sense-poll', sense_route='adc')
          and 'without the sense feature' in refused('uno-light-unsensed', sense_route='poll'), refused('uno-light-unsensed', sense_route='poll')[:120])
    check('a sense route on an app not written for it (light_v2) is refused', 'without the sense feature' in refused('uno-light-v2', sense_route='pcint') or 'not written for it' in refused('uno-light-v2', sense_route='pcint'))
    check('the INT1 variant is unchanged: uno-button-clock still refuses any sense pin but D3', 'hardware-fixed to D3' in refused('uno-button-clock', sense_pin=8))
    cfg = {n: V.render_config(V.resolve(V.find(n))) for n in ('uno-light-unsensed', 'uno-button-clock', 'uno-sim-rig', 'uno-light-pcint')}
    check('the existing variants\' board_config.h carry no sense-route line at all (their bytes cannot have moved)', all('HAL_SENSE_ROUTE' not in t for t in cfg.values()))
    check('SR.check agrees with resolve (RouteRefused is the same refusal)', _raises(SR, 'pcint', {'sense_pin': 0}) and _raises(SR, 'poll', {'sense_pin': 1}))


def _raises(SR, route, knobs):
    try:
        SR.check(route, knobs)
        return False
    except SR.RouteRefused:
        return True


def _compiles(check):
    if not _engine():
        check('SKIP fgm-5b compile (no avr-gcc rung on this device)', True)
        return
    from board.custom import build as B, gen
    builds = {}
    for name in ('uno-button-clock', 'uno-light-sense-poll', 'uno-light-sense-pcint'):
        work = tempfile.mkdtemp(prefix='fgm5b-')
        try:
            gen.gen('uno', None, work, variant=name)
            builds[name] = B.build('uno', work)
            if name != 'uno-button-clock':
                gen.gen('uno', None, work, variant=name)
                builds[name + '#2'] = B.build('uno', work)
        finally:
            import shutil
            shutil.rmtree(work, ignore_errors=True)
    for name, hal in (('uno-light-sense-poll', 'hal_sense_poll'), ('uno-light-sense-pcint', 'hal_sense_pcint')):
        r = builds[name]
        check('%s compiles through the engines seam within the cited limits: flash %s B, static RAM %s B (avr-size; uno-button-clock: %s / %s)'
              % (name, r.get('flash_bytes'), r.get('ram_bytes'), builds['uno-button-clock'].get('flash_bytes'), builds['uno-button-clock'].get('ram_bytes')),
              r['state'] == 'built' and 0 < r['flash_bytes'] <= 32256 and 0 < r['ram_bytes'] <= 2048, r.get('notes'))
        check('%s builds deterministically (a second gen + build gives the same hex sha256)' % name, builds[name + '#2']['artifact_sha256'] == r['artifact_sha256'])
        repro = json.loads(r['repro_json'])
        labels = [i['label'] for i in repro['inputs']]
        check('%s records its isotope template + macros by sha256 in the repro block, and the rendered file as a project input' % name,
              'isotope template (jinja2)' in labels and 'isotope template macros (jinja2)' in labels and any(i['path'].endswith('%s.c' % hal) for i in repro['inputs']))
    check('uno-button-clock still builds to its committed hex 4cbe660a... (hal.c\'s sense-route guard changed no byte of it)', builds['uno-button-clock']['artifact_sha256'].startswith(GATE['uno-button-clock']),
          builds['uno-button-clock']['artifact_sha256'])
    check('the two sense hexes differ from uno-button-clock and from each other', len({builds[n]['artifact_sha256'] for n in ('uno-button-clock', 'uno-light-sense-poll', 'uno-light-sense-pcint')}) == 3)
    man = json.load(open(os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), 'board', 'custom', 'firmware', 'uno', 'polari-firmware.json')))
    got = {c['name']: c['make_alone']['hex_sha256'] for c in man['configurations'] if c['name'] in GATE or c['name'] in ROUTE_VARIANTS.values()}
    check('the identical-hex gate holds in the committed manifest: uno-sim-rig, uno-light-unsensed (the old uno-light), uno-button-clock, uno-light-pcint, uno-light-analog keep their hexes; the two sense variants are configurations of it',
          all(got.get(n, '').startswith(h) for n, h in GATE.items()) and {'uno-light-sense-poll', 'uno-light-sense-pcint'} <= set(got), got)


def _catalogue(check):
    from cmod.custom import isotope_variants as IV
    vs = {v['name']: v for v in IV.variants()}
    for r, row in ROUTE_ROWS.items():
        d = IV.variant_dict(vs[row])
        st = IV.status(vs[row])
        check('%s: the catalogue finds the rendered atoms - status compiles (no live instance, no run to read), flash/RAM/stack MEASURED from the build' % row,
              st['status'] == 'compiles' and d['costs']['flash_bytes']['kind'] == 'measured' and d['costs']['ram_bytes']['kind'] == 'measured'
              and d['costs']['stack_bytes']['kind'] == 'measured' and d['costs']['flash_bytes']['value'] > 0 and d['implemented'], (st, d['costs']['flash_bytes']))
    from firmwarefaults.custom import acceptance as ACC
    for row, scen in ROUTE_SCENARIOS.items():
        check('%s: its proof scenario %s is named by the route, exists, is an acceptance Scenario on the variant it restates, and has steps' % (row, scen),
              scen in json.loads(vs[row]['implemented_by_json']).get('proof_scenarios', []) and ACC.find(scen)['kind'] == 'acceptance' and ACC.VARIANT_PROOFS.get(scen) == ACC.find(scen)['before_variant']
              and bool(ACC.steps_of(scen)), scen)
    check('the INT1 route is unaffected: still named by its Purpose, no scenario', json.loads(vs['sense-led-line:ext-interrupt']['implemented_by_json']).get('proof_purposes') == ['button-clock-to-os'])


def _run(mgr, scenario, outcome, mode='digital-twin', at='2026-10-18T10:00:00'):
    n = len(mgr.objectTables.setdefault('ScenarioRun', {})) + 1
    mgr.objectTables['ScenarioRun'][n] = SimpleNamespace(name='run-%s-%s' % (scenario, at), scenario=scenario, outcome=outcome, ran_at=at, kind='measured',
                                                         repro_json=json.dumps({'mode': mode}), verdict_words=outcome)


def _ladder(check):
    from cmod.custom import isotope_variants as IV
    vs = {v['name']: v for v in IV.variants()}
    mgr = SimpleNamespace(objectTables={}, idList=[], db=None)
    for row, scen in ROUTE_SCENARIOS.items():
        v = vs[row]
        check('%s: with a manager but no ScenarioRun it stays at compiles' % row, IV.status(v, mgr)['status'] == 'compiles')
        _run(mgr, scen, 'failed')
        check('%s: a FAILED run lifts nothing' % row, IV.status(v, mgr)['status'] == 'compiles')
        _run(mgr, scen, 'undetermined', at='2026-10-18T10:30:00')
        check('%s: an engine refusal (undetermined) is not evidence either way' % row, IV.status(v, mgr)['status'] == 'compiles')
        _run(mgr, scen, 'passed', at='2026-10-18T11:00:00')
        st = IV.status(v, mgr)
        check('%s: a passing twin run of its own acceptance Scenario lifts it to proven-on-twin, naming the run' % row,
              st['status'] == 'proven-on-twin' and 'ScenarioRun' in st['proof'] and st['proof_purposes_used'] == [scen], st)
        _run(mgr, scen, 'passed', mode='hardware', at='2026-10-18T12:00:00')
        check('%s: a later passing HARDWARE run lifts it to proven-on-hardware' % row, IV.status(v, mgr)['status'] == 'proven-on-hardware')
        _run(mgr, scen, 'failed', at='2026-10-18T13:00:00')
        check('%s: a newer failing run takes the proof away again (no stale pass carried forward)' % row, IV.status(v, mgr)['status'] == 'compiles')
    _run(mgr, 'sense-poll-line-acceptance', 'passed', at='2026-10-18T14:00:00')
    check('one route\'s run lifts no other route (the pin-change route is still compiles while the polled one passes)',
          IV.status(vs['sense-led-line:gpio-poll'], mgr)['status'] == 'proven-on-twin' and IV.status(vs['sense-led-line:pin-change-interrupt'], mgr)['status'] == 'compiles')
    check('the shipped INT1 route is unaffected: still compiles with no run of its Purpose', IV.status(vs['sense-led-line:ext-interrupt'], mgr)['status'] == 'compiles')
