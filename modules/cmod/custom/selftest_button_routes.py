"""selftest_button_routes - fgm-5a (MISSION_PROFILE_SOLVER_PLAN.md 8.5): the read-button isotopes as REAL Jinja2 templates. Proves: the catom
layout on disk (catom.json / README / isotopes/<iso>/{isotope.json, substitutions.json, template.c.j2}) is complete and cross-refers to
real catalogue rows and FirmwareVariants; each template renders DETERMINISTICALLY (twice -> the same bytes) with every register / bit /
vector taken from the cited rows (and on other pins/channels too); each rendered variant COMPILES through the board engines seam
(measured flash/RAM from avr-size, deterministic hex) and the existing variants' bytes did not change (the gate also lives in
generator_parts); bad knobs are refused by name; the iso-0 catalogue finds the new atoms (status compiles, measured costs) and climbs to
proven-on-twin / proven-on-hardware from a passing ScenarioRun of the route's own acceptance Scenario, falling back on a newer failure.
The twin runs themselves are in board.board_variant_twin_selftest. Run by cmod_selftest.main() (button_route_parts)."""
import json
import os
import tempfile
from types import SimpleNamespace

ROUTE_VARIANTS = {'pcint': 'uno-light-pcint', 'adc': 'uno-light-analog'}
ROUTE_ROWS = {'pcint': 'read-button:pin-change-interrupt', 'adc': 'read-button:analog-threshold'}


def _engine():
    try:
        from board.custom import board_engines as be
        return be.resolve('avr-gcc')['how'] in ('local-binary', be.LOCAL_IMAGE)
    except Exception:  # noqa: BLE001
        return False


def button_route_parts(check):
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
    from board.custom import button_routes as BR
    from board.custom import variants as V
    from cmod.custom import isotope_variants as IV
    root = os.path.join(BR.CATOMS, BR.CATOM)
    need = ['catom.json', 'README.md', '_common.j2'] + [os.path.join('isotopes', BR.ROUTES[r][1], f)
                                                       for r in BR.ROUTES for f in ('isotope.json', 'substitutions.json', 'template.c.j2')]
    check('the read-button catom has the section 5b layout on disk (catom.json, README.md, a macro file, per isotope: isotope.json, substitutions.json, template.c.j2)',
          all(os.path.isfile(os.path.join(root, f)) for f in need), [f for f in need if not os.path.isfile(os.path.join(root, f))])
    catom = json.load(open(os.path.join(root, 'catom.json')))
    fams = {h['family'] for h in catom['hal_contract']}
    check('catom.json names its HAL variables with the plan 5b families (drive / register / protocol / signal / execution) and its three functions',
          fams == {'drive', 'register', 'protocol', 'signal', 'execution'} and [f['function'] for f in catom['interface']]
          == ['hal_button_init', 'hal_take_toggle_pending', 'hal_presses'], sorted(fams))
    rows = {v['name'] for v in IV.variants()}
    names = {v['name'] for v in V.SEED_FIRMWARE_VARIANTS}
    for r, (code, iso, fname, variant_row) in BR.ROUTES.items():
        d = os.path.join(BR.CATOMS, BR.CATOM, 'isotopes', iso)
        meta = json.load(open(os.path.join(d, 'isotope.json')))
        sub = json.load(open(os.path.join(d, 'substitutions.json')))
        check('%s: isotope.json points at a REAL catalogue row, the file it renders, its route code and FirmwareVariants that exist' % iso,
              meta['variant_row'] == variant_row and variant_row in rows and meta['renders_to'] == fname and meta['hal_button_route_code'] == code
              and meta['button_route'] == r and set(meta['firmware_variants']) <= names and ROUTE_VARIANTS[r] in meta['firmware_variants'], meta)
        check('%s: substitutions.json says where every number comes from (knobs + derived-from-rows)' % iso, bool(sub['knobs']) and bool(sub['derived_from_rows']))
    rel = os.path.relpath(BR.CATOMS, os.path.dirname(BR.HERE)).split(os.sep)
    check('the layout stays under custom/ (the manifests selftest allows only objects/ custom/ initialData/ as module subfolders): board/%s' % '/'.join(rel),
          rel[0] == 'custom' and rel[-2:] == ['uno', 'catoms'], rel)


def _knobs(variant):
    from board.custom import variants as V
    return V.resolve(V.find(variant))['knobs']


def _rendering(check):
    from board.custom import button_routes as BR
    for r, variant in ROUTE_VARIANTS.items():
        k = _knobs(variant)
        a, b = BR.render(r, k), BR.render(r, k)
        check('%s: the template renders the SAME bytes twice (no timestamp)' % r, a['text'] == b['text'] and BR.sha256(a['text']) == BR.sha256(b['text']))
        check('%s: file %s, template sha256 recorded, no unresolved template syntax, cites present' % (r, a['file']),
              a['file'] == BR.ROUTES[r][2] and len(a['template_sha256']) == 64 and '{{' not in a['text'] and '{%' not in a['text'] and len(a['cites']) >= 3)
    p = BR.render('pcint', _knobs('uno-light-pcint'))['plan']
    check('pcint on D4: PD4 -> PCMSK2.PCINT20, PCICR.PCIE2, PCIFR.PCIF2, vector PCINT2_vect (read off the SocPin + cited RegisterField rows)',
          (p['soc_pin'], p['mask_reg'], p['mask_bit'], p['enable_bit'], p['flag_bit'], p['vector']) == ('PD4', 'PCMSK2', 'PCINT20', 'PCIE2', 'PCIF2', 'PCINT2_vect'), p)
    other = {n: BR.pcint_plan(n) for n in (9, 14, 13)}
    check('pcint on other pins: D9 -> PCMSK0.PCINT1/PCIE0/PCINT0_vect, A0 (14) -> PCMSK1.PCINT8/PCIE1/PCINT1_vect, D13 -> PCMSK0.PCINT5',
          (other[9]['mask_reg'], other[9]['mask_bit'], other[9]['vector']) == ('PCMSK0', 'PCINT1', 'PCINT0_vect')
          and (other[14]['mask_reg'], other[14]['mask_bit'], other[14]['enable_bit'], other[14]['vector']) == ('PCMSK1', 'PCINT8', 'PCIE1', 'PCINT1_vect')
          and other[13]['mask_bit'] == 'PCINT5', other)
    t9 = BR.render('pcint', dict(_knobs('uno-light-pcint'), button_pin=9))['text']
    check('a different pin renders a different file, still deterministic', t9 != BR.render('pcint', _knobs('uno-light-pcint'))['text']
          and t9 == BR.render('pcint', dict(_knobs('uno-light-pcint'), button_pin=9))['text'] and 'ISR(PCINT0_vect)' in t9)
    pl = BR.render('adc', _knobs('uno-light-analog'))['plan']
    check('adc on A0: counts = mV x 1024 / 5000 (cited ADC = Vin * 1024 / Vref): 1500 mV -> 307, 3500 mV -> 716; DIDR0.ADC0D; PC0',
          (pl['press_below_counts'], pl['release_above_counts'], pl['didr_bit'], pl['soc_pin']) == (307, 716, 'ADC0D', 'PC0')
          and BR.counts_of(5000) == 1024, pl)
    check('the generator environment is the strict one: a template asked for a key the context lacks fails by name',
          _strict_fails(BR))


def _strict_fails(BR):
    from cmod.custom.generator import env as E
    from cmod.custom.generator.filters import GenError
    try:
        E.render('read-button/isotopes/pin-change-interrupt/template.c.j2', {'file': 'x.c'}, templates_dir=BR.CATOMS)
        return False
    except GenError as e:
        return 'missing' in str(e)


def _refusals(check):
    from board.custom import button_routes as BR
    from board.custom import variants as V

    def refused(variant, **knobs):
        v = dict(V.find(variant), knobs_json=json.dumps(dict(json.loads(V.find(variant)['knobs_json']), **knobs)))
        try:
            V.resolve(v)
            return ''
        except V.VariantRefused as e:
            return str(e)
    check('pcint refuses D1 (the USB serial line) and D20 (no such pin), by name', 'D2..D13' in refused('uno-light-pcint', button_pin=1)
          and refused('uno-light-pcint', button_pin=20) != '', refused('uno-light-pcint', button_pin=1)[:120])
    check('pcint refuses the button on the light\'s own pin', 'same pin' in refused('uno-light-pcint', button_pin=6), refused('uno-light-pcint', button_pin=6)[:120])
    check('adc refuses channel 6 and a press threshold above the release one', 'A0..A5' in refused('uno-light-analog', button_adc_channel=6)
          and 'hysteresis' in refused('uno-light-analog', adc_press_below_mv=4000, adc_release_above_mv=3000))
    check('a route other than int0 / pcint / adc is refused', 'int0' in refused('uno-light-pcint', button_route='spi'))
    check('a button route on an app not written for it (button-clock) is refused, naming the apps that are',
          'not written for it' in refused('uno-button-clock', button_route='pcint'), refused('uno-button-clock', button_route='pcint')[:120])
    check('the INT0 variants are unchanged: uno-light still refuses any button pin but D2', 'hardware-fixed to D2' in refused('uno-light', button_pin=4))
    cfg = {n: V.render_config(V.resolve(V.find(n))) for n in ('uno-light', 'uno-button-clock', 'uno-sim-rig')}
    check('the existing variants\' board_config.h carry no route line at all (their bytes cannot have moved)', all('HAL_BUTTON_ROUTE' not in t for t in cfg.values()))
    check('BR.check agrees with resolve (RouteRefused is the same refusal)', _raises(BR, 'pcint', {'button_pin': 0}))


def _raises(BR, route, knobs):
    try:
        BR.check(route, knobs)
        return False
    except BR.RouteRefused:
        return True


def _compiles(check):
    if not _engine():
        check('SKIP fgm-5a compile (no avr-gcc rung on this device)', True)
        return
    from board.custom import build as B, gen
    builds = {}
    for name in ('uno-light', 'uno-light-pcint', 'uno-light-analog'):
        work = tempfile.mkdtemp(prefix='fgm5a-')
        try:
            gen.gen('uno', None, work, variant=name)
            row = B.build('uno', work)
            builds[name] = row
            if name != 'uno-light':
                gen.gen('uno', None, work, variant=name)
                again = B.build('uno', work)
                builds[name + '#2'] = again
        finally:
            import shutil
            shutil.rmtree(work, ignore_errors=True)
    for name in ('uno-light-pcint', 'uno-light-analog'):
        r = builds[name]
        check('%s compiles through the engines seam within the cited limits: flash %s B, static RAM %s B (avr-size)' % (name, r.get('flash_bytes'), r.get('ram_bytes')),
              r['state'] == 'built' and 0 < r['flash_bytes'] <= 32256 and 0 < r['ram_bytes'] <= 2048, r.get('notes'))
        check('%s builds deterministically (a second gen + build gives the same hex sha256)' % name, builds[name + '#2']['artifact_sha256'] == r['artifact_sha256'])
        repro = json.loads(r['repro_json'])
        labels = [i['label'] for i in repro['inputs']]
        check('%s records its isotope template + macros by sha256 in the repro block, and the rendered file as a project input' % name,
              'isotope template (jinja2)' in labels and 'isotope template macros (jinja2)' in labels
              and any(i['path'].endswith('hal_button_%s.c' % ('pcint' if name.endswith('pcint') else 'adc')) for i in repro['inputs']))
    check('the existing uno-light still builds to its committed hex 94b9b77f... (hal.c\'s route guard changed no byte of it)',
          builds['uno-light']['artifact_sha256'].startswith('94b9b77f9f8c9b19'), builds['uno-light']['artifact_sha256'])
    check('uno-light-pcint and uno-light-analog hexes differ from uno-light and from each other',
          len({builds[n]['artifact_sha256'] for n in ('uno-light', 'uno-light-pcint', 'uno-light-analog')}) == 3)


def _catalogue(check):
    from cmod.custom import isotope_variants as IV
    vs = {v['name']: v for v in IV.variants()}
    for r, row in ROUTE_ROWS.items():
        d = IV.variant_dict(vs[row])
        st = IV.status(vs[row])
        check('%s: the catalogue finds the rendered atoms - status compiles (no live instance, no run to read), flash/RAM/stack MEASURED from the build' % row,
              st['status'] == 'compiles' and d['costs']['flash_bytes']['kind'] == 'measured' and d['costs']['ram_bytes']['kind'] == 'measured'
              and d['costs']['stack_bytes']['kind'] == 'measured' and d['costs']['flash_bytes']['value'] > 0 and d['implemented'], (st, d['costs']['flash_bytes']))
    check('the PWM route names its own acceptance Scenario as its proof', 'sim-rig-pwm-duty-acceptance' in vs['drive-led:pwm']['implemented_by_json'])
    from firmwarefaults.custom import acceptance as ACC
    for r, row in list(ROUTE_ROWS.items()) + [('pwm', 'drive-led:pwm')]:
        for scen in json.loads(vs[row]['implemented_by_json']).get('proof_scenarios', []):
            sc = ACC.find(scen)
            check('%s: proof scenario %s exists, is an acceptance Scenario on the variant it restates, and has steps' % (row, scen),
                  sc is not None and sc['kind'] == 'acceptance' and scen in ACC.VARIANT_PROOFS and ACC.steps_of(scen), scen)


def _run(mgr, scenario, outcome, mode='digital-twin', at='2026-10-18T10:00:00'):
    n = len(mgr.objectTables.setdefault('ScenarioRun', {})) + 1
    mgr.objectTables['ScenarioRun'][n] = SimpleNamespace(name='run-%s-%s' % (scenario, at), scenario=scenario, outcome=outcome, ran_at=at, kind='measured',
                                                         repro_json=json.dumps({'mode': mode}), verdict_words=outcome)


def _ladder(check):
    from cmod.custom import isotope_variants as IV
    vs = {v['name']: v for v in IV.variants()}
    mgr = SimpleNamespace(objectTables={}, idList=[], db=None)
    for row, scen in (('read-button:pin-change-interrupt', 'light-pcint-button-acceptance'), ('read-button:analog-threshold', 'light-analog-button-acceptance'),
                      ('drive-led:pwm', 'sim-rig-pwm-duty-acceptance')):
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
    _run(mgr, 'light-pcint-button-acceptance', 'passed', at='2026-10-18T14:00:00')
    check('one route\'s run lifts no other route (the analog route is still compiles while pcint passes)',
          IV.status(vs['read-button:pin-change-interrupt'], mgr)['status'] == 'proven-on-twin' and IV.status(vs['read-button:analog-threshold'], mgr)['status'] == 'compiles')
    check('the shipped INT0 route is unaffected: still compiles with no run of its Purposes', IV.status(vs['read-button:ext-interrupt'], mgr)['status'] == 'compiles')
