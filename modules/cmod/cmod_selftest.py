"""cmod_selftest — cmod-0 + cmod-1 (C_MODULARIZATION_PLAN.md §10). cmod-1 (custom/selftest_glue.py): the seeded graph → a
deterministic render equal to the committed project, the refusals (cycle, unbound port, type mismatch, free C, …), idempotence +
the hand-edit guard, the Makefile with a fake avr-gcc, the compiler seam, the committed twin proof and its rows, the cost. cmod-0: the atom parser on FIXTURES (an ISR, volatile globals shared with it,
a torn read and its atomic twin, a read-modify-write lost update, a function touching a register, a pure function, a pointer
written through, both annotation forms), the REFUSALS (a malformed POLARI_NODE never guessed), the preprocessor fixes, the AVR
type widths, the manifest's idempotence and hand-set preservation on a plain project; then (custom/selftest_uno.py) the UNO:
34 atoms, the committed manifest matching the sources, every atom with ports/resources/cost, the torn build's verdict, the
macro expanding to nothing, the seeds/page/API, `manifests conform cmod`. No engine is run here except a host gcc when present
(tests/cmod_liveboot_probe.py proves the byte-identical .hex and the live boot).

    PYTHONPATH=.:modules python3 -m cmod.cmod_selftest      # from polari-framework/
"""
import json
import os
import shutil
import sys
import tempfile

passed = total = 0

FX_H = '''#ifndef FX_H
#define FX_H
#include <stdint.h>
#ifndef POLARI_NODE
#define POLARI_NODE(...)
#endif
uint32_t read_torn(void);
#endif
'''
FX_C = '''#include <avr/io.h>
#include <avr/interrupt.h>
#include <util/atomic.h>
#include "fx.h"

static volatile uint32_t g_count;   /* 4 bytes the ISR writes */
static volatile uint8_t g_small;    /* 1 byte the ISR writes */
static uint8_t g_plain;             /* nobody else touches it */

ISR(TIMER1_COMPA_vect) { g_count++; g_small++; }

uint32_t read_torn(void) { return g_count; }

uint32_t read_safe(void)
{
    uint32_t v;
    ATOMIC_BLOCK(ATOMIC_RESTORESTATE) { v = g_count; }
    return v;
}

void bump(void) { g_small++; }

uint8_t peek(void) { return g_small; }

/* @polari-node(led_on, uses(D13), role("the LED on D13")) */
void led_on(void) { PORTB |= _BV(PB5); }

POLARI_NODE(add, in(a, "mV"), in(b, "mV"), out(return, "mV", "the sum"))
int16_t add(int16_t a, int16_t b) { return a + b; }

void fill(uint8_t *out, uint8_t n) { while (n--) out[n] = 0; g_plain = n; }

#define KICK() bump()
void kicker(void) { KICK(); }

#if 3 != 4 && 010 == 8
int lives(void) { return add(1, 2); }
#endif
'''
FX_MK = 'CC = gcc\nCFLAGS = -Os -std=gnu99 -Wall -DPOLARI_HOST -Ihostinc\nLDFLAGS =\nall:\n\t$(CC) $(CFLAGS) -c fx.c\n'


def check(label, cond, extra=''):
    global passed, total
    total += 1
    passed += bool(cond)
    print('  [%s] %s %s' % ('\033[0;32mPASS\033[0m' if cond else '\033[0;31mFAIL\033[0m', label, extra if not cond else ''))


def fixture_dir(c_text=FX_C):
    d = tempfile.mkdtemp(prefix='cmod-fx-')
    open(os.path.join(d, 'fx.c'), 'w').write(c_text)
    open(os.path.join(d, 'fx.h'), 'w').write(FX_H)
    open(os.path.join(d, 'Makefile'), 'w').write(FX_MK)
    return d


def parser_on_fixtures():
    from cmod.custom import analyse as AN
    d = fixture_dir()
    p = AN.parse_project(d)
    a = p['atoms']
    check('plain project: the directory as it is is ONE configuration; atoms = the functions of its .c, the ISR by its vector',
          p['spec']['kind'] == 'plain' and [c['name'] for c in p['configs']] == ['default']
          and sorted(a) == ['fx.TIMER1_COMPA_vect', 'fx.add', 'fx.bump', 'fx.fill', 'fx.kicker', 'fx.led_on', 'fx.lives', 'fx.peek', 'fx.read_safe',
                            'fx.read_torn'],
          sorted(a))
    isr = a['fx.TIMER1_COMPA_vect']
    check('ISR(TIMER1_COMPA_vect) is detected through the macro: kind isr, vector 11 from avr-libc\'s own table, writes g_count + g_small',
          isr['isr'] == 'TIMER1_COMPA_vect' and isr['isr_safe'] == 'isr' and isr['globals']['g_count']['w'] and isr['globals']['g_small']['w']
          and any(r['detail'] == 'vector 11' for r in AN.resources(isr)))
    check('the torn read: a 4-byte volatile the ISR writes, read outside an atomic block → isr_safe no, naming the tear',
          a['fx.read_torn']['isr_safe'] == 'no' and 'tears' in a['fx.read_torn']['isr_safe_why'] and 'g_count (4 B' in a['fx.read_torn']['isr_safe_why'])
    check('its ATOMIC_BLOCK twin → isr_safe yes, atomic_block true, the access recorded inside the block',
          a['fx.read_safe']['isr_safe'] == 'yes' and a['fx.read_safe']['atomic'] and a['fx.read_safe']['globals']['g_count']['inside_atomic']
          and not a['fx.read_safe']['globals']['g_count']['outside_atomic'])
    check('a 1-byte RMW (g_small++) outside an atomic block while the ISR writes it → isr_safe no (a lost update)',
          a['fx.bump']['isr_safe'] == 'no' and 'lost update' in a['fx.bump']['isr_safe_why'])
    check('a 1-byte read of the same global (one lds) → isr_safe yes', a['fx.peek']['isr_safe'] == 'yes', a['fx.peek']['isr_safe_why'])
    res = AN.resources(a['fx.led_on'])
    check('a function touching a register: PORTB (read-modify-write) → peripheral GPIO PORTB; the comment-form annotation\'s uses(D13) kept',
          any(r['kind'] == 'register' and r['name'] == 'PORTB' and r['access'] == 'rw' and r['peripheral'] == 'GPIO PORTB' for r in res)
          and any(r['kind'] == 'declared' and r['name'] == 'D13' for r in res) and a['fx.led_on']['annotation']['form'] == 'comment')
    add = a['fx.add']
    check('a pure function: no global, no register, no resource → pure; its ports from the signature + the macro annotation\'s units',
          add['pure'] and [(x['name'], x['direction'], x['polari_type'], x['unit']) for x in add['ports']]
          == [('a', 'in', 'int64', 'mV'), ('b', 'in', 'int64', 'mV'), ('return', 'out', 'int64', 'mV')] and add['annotation']['form'] == 'macro')
    check('lives() calls the pure add() and nothing else → pure through the closure; read_torn → not pure (touches g_count)',
          a['fx.lives']['pure'] and not a['fx.read_torn']['pure'] and 'g_count' in a['fx.read_torn']['pure_why'])
    fill = a['fx.fill']
    check('a pointer only written through → out (derived), polari type bytes; the file-scope g_plain write is a global, not shared with the ISR',
          fill['ports'][0]['direction'] == 'out' and fill['ports'][0]['polari_type'] == 'bytes' and fill['globals']['g_plain']['w']
          and not fill['globals']['g_plain'].get('shared_with_isr') and fill['isr_safe'] == 'yes')
    check('the preprocessor: a function-like macro with NO parameters (`#define KICK() bump()`) consumes its () — kicker calls bump, '
          'nothing indirect; and inherits bump\'s verdict (isr_safe no)', a['fx.kicker']['calls'] == ['bump'] and a['fx.kicker']['isr_safe'] == 'no',
          a['fx.kicker']['calls'])
    check('the preprocessor: `#if 3 != 4 && 010 == 8` is TRUE (PLY rewrote `!=` into a syntax error; octal 010 = 8) → lives() exists',
          'fx.lives' in a)
    shutil.rmtree(d, ignore_errors=True)


def refusals():
    from cmod.custom import analyse as AN
    from cmod.custom.annotation import AnnotationRefused
    bad = {
        'an unknown clause': ('POLARI_NODE(add, in(a), weight(3))', 'unknown clause'),
        'a port the signature does not have': ('POLARI_NODE(add, in(c))', 'names port'),
        'out() on a by-value parameter': ('POLARI_NODE(add, out(a))', 'passed by value'),
        'a parenthesis left open': ('POLARI_NODE(add, in(a)', 'not closed'),
        'a port declared twice': ('POLARI_NODE(add, in(a), in(a))', 'twice'),
        'the return as an input': ('POLARI_NODE(add, in(return))', 'return value'),
    }
    for what, (ann, needle) in bad.items():
        d = fixture_dir(FX_C.replace('POLARI_NODE(add, in(a, "mV"), in(b, "mV"), out(return, "mV", "the sum"))', ann))
        try:
            AN.parse_project(d)
            check('refused: %s' % what, False, 'parsed without complaint')
        except AnnotationRefused as e:
            check('refused: %s — "%s"' % (what, str(e)[:90]), needle in str(e) and 'fx.c:' in str(e), str(e))
        shutil.rmtree(d, ignore_errors=True)
    d = fixture_dir(FX_C.replace('void fill(', 'POLARI_NODE(bump)\nvoid fill('))
    try:
        AN.parse_project(d)
        check('refused: an annotation that does not sit right above the function it names', False)
    except AnnotationRefused as e:
        check('refused: an annotation that does not sit right above the function it names (names bump, next is fill)', 'next function is fill' in str(e), str(e))
    shutil.rmtree(d, ignore_errors=True)


def types_and_preprocess():
    from pycparser import c_parser
    from cmod.custom.c_types import TypeTable, polari_type
    from cmod.custom import preprocess as PP
    src = ('typedef unsigned char uint8_t; typedef unsigned long uint32_t; typedef struct { uint8_t a; uint32_t b; char n[8]; } S_t;'
           'int i; long l; double d; char *s; uint8_t *bp; S_t st; const S_t *sp; _Bool f; uint32_t arr[2 + 2];')
    ast = c_parser.CParser().parse(src)
    tt = TypeTable(ast)
    got = {e.name: tt.describe(e.type) for e in ast.ext if getattr(e, 'name', None) and not e.name.endswith('_t')}
    check('AVR widths: int 2, long 4, double 4 (= float), pointer 2, a struct = the sum of its members (no padding on the AVR), an array dim '
          'from a constant expression', (got['i']['width'], got['l']['width'], got['d']['width'], got['s']['width'], got['st']['width'], got['arr']['width'])
          == (2, 4, 4, 2, 13, 16), {k: v['width'] for k, v in got.items()})
    check('Polari types: int → int64, double → double, char* → string, uint8_t* → bytes, struct → ref:S_t, const S_t* → ref:S_t, _Bool → bool',
          [polari_type(got[k]) for k in ('i', 'd', 's', 'bp', 'st', 'sp', 'f')] == ['int64', 'double', 'string', 'bytes', 'ref:S_t', 'ref:S_t', 'bool'])
    check('the fake headers are pinned by sha (part of every manifest\'s parser block) and declare the AVR fixed-width types',
          len(PP.fake_headers_sha()) == 64 and 'typedef unsigned long uint32_t' in PP.FAKE_HEADERS['stdint.h'])


def manifest_idempotence():
    from cmod.custom import manifest as MF
    d = fixture_dir()
    r1 = MF.conform(d, measure=False)
    r2 = MF.conform(d, measure=False)
    check('plain project: conform writes polari-firmware.json beside the Makefile; a SECOND conform changes nothing (not even a timestamp)',
          r1['written'] and not r2['changed'] and not r2['written'] and os.path.isfile(os.path.join(d, 'polari-firmware.json')), (r1['written'], r2['changed']))
    m = json.load(open(os.path.join(d, 'polari-firmware.json')))
    check('the manifest validates and carries the parser block (pycparser, its version, the fake-header sha, avr-libc\'s register snapshot)',
          not MF.validate(m) and m['parser']['engine'] == 'pycparser' and m['parser']['registers']['count'] == 96, MF.validate(m))
    m['title'], m['notes'] = 'my fx project', 'hand notes'
    next(a for a in m['atoms'] if a['name'] == 'fx.add')['notes'] = 'adds millivolts'
    json.dump(m, open(os.path.join(d, 'polari-firmware.json'), 'w'), indent=1)
    open(os.path.join(d, 'fx.c'), 'a').write('\nint16_t twice(int16_t x) { return add(x, x); }\n')
    r3 = MF.conform(d, measure=False)
    m3 = json.load(open(os.path.join(d, 'polari-firmware.json')))
    check('a source change → re-derived (added: fx.twice); the HAND-SET title / notes / atom notes survive (like manifests._preserve_hand_set)',
          r3['written'] and r3['added'] == ['fx.twice'] and m3['title'] == 'my fx project' and m3['notes'] == 'hand notes'
          and next(a for a in m3['atoms'] if a['name'] == 'fx.add')['notes'] == 'adds millivolts', (r3['added'], m3['title']))
    shutil.rmtree(d, ignore_errors=True)


def host_measure():
    """The cost path on THIS host's gcc (the engine rung is the probe's): a host project with its own Makefile flags."""
    from cmod.custom import measure as M
    if not shutil.which('gcc') or not shutil.which('nm'):
        print('  [SKIP] no host gcc/nm — the engine rung is proven by tests/cmod_liveboot_probe.py')
        return
    d = tempfile.mkdtemp(prefix='cmod-host-')
    open(os.path.join(d, 'm.c'), 'w').write('int add(int a, int b) { return a + b; }\nstatic int sq(int x) { return x * x; }\n'
                                             'int main(void) { return add(1, 2) + sq(3); }\n')
    open(os.path.join(d, 'Makefile'), 'w').write('CC = gcc\nOPT = -Os\nCFLAGS = $(OPT) -std=gnu99 -Wall\nLDFLAGS =\n')
    r = M.measure(d, ['m.c'])
    sh, ni = r['modes']['shipped'], r['modes']['noinline']
    check('makefile_vars expands $(OPT) into CFLAGS; the measurement runs with the Makefile\'s OWN flags',
          r['cc'] == 'gcc' and r['cflags'][:2] == ['-Os', '-std=gnu99'])
    check('host gcc: shipped build = sq() inlined (no symbol), -fno-inline build = sq has its own bytes; .su frames parsed',
          'sq' not in sh['text'] and ni['text'].get('sq', 0) > 0 and 'add' in sh['text'] and 'main' in sh['stack'], (sorted(sh['text']), sorted(ni['text'])))
    check('GCC clone suffixes fold into the function: f.constprop.0 / f.isra.0 / f.part.0 → f',
          M.base_symbol('apply_command.constprop.0') == 'apply_command' and M.base_symbol('x.isra') == 'x' and M.base_symbol('y.part.1') == 'y')
    shutil.rmtree(d, ignore_errors=True)


def page():
    """demo1: every table on /display/c-atoms carries a non-empty description. demo-4: /display/c-atoms stays
    configured-only (class-rows-table + the api-structured-panel 'used by' reverse link — never raw JSON), and
    /display/c-canvas opens with the canvas panel, no raw JSON on the tables below it."""
    from cmod.cmod_page import SEED_CMOD_PAGE_DISPLAYS as P
    rows = json.loads(P[0]['definition'])['rows']
    items = [it for row in rows for it in row['items']]
    check('/display/c-atoms is configured surfaces only (class-rows-table + api-structured-panel, no JSON panel, no new component)',
          items and all(it['componentProps']['componentName'] in ('class-rows-table', 'api-structured-panel') for it in items))
    check('/display/c-atoms: every table carries a non-empty description',
          all(it.get('description') for it in items), str([it['id'] for it in items if not it.get('description')]))
    crows = json.loads(P[1]['definition'])['rows']
    citems = [it for row in crows for it in row['items']]
    check('/display/c-canvas: every item (the canvas + the described tables) carries a non-empty description',
          citems and all(it.get('description') for it in citems), str([it['id'] for it in citems if not it.get('description')]))
    check('/display/c-canvas opens the canvas FIRST (demo-1\'s rule: the demonstrable before the tables)',
          citems[0]['componentProps']['componentName'] == 'c-graph-canvas-panel')

    # D-ucd-12 (his ruling): the person-facing word is Purpose, not Capability — the CapabilityDefinition-titled
    # tables on c-canvas/firmware/firmware-solutions say "Purpose" and never "Capabilit" in title or description.
    by_id = {it['id']: it for it in citems}
    cap_item = by_id.get('c-canvas-capabilities')
    check('/display/c-canvas\'s CapabilityDefinition table titles itself Purpose, not Capabilit',
          cap_item is not None and 'Purpose' in cap_item['title'] and 'Capabilit' not in cap_item['title']
          and 'Capabilit' not in cap_item.get('description', ''), cap_item and cap_item['title'])
    frows = json.loads(P[2]['definition'])['rows']
    fitems = [it for row in frows for it in row['items']]
    panel_lean = next((it for it in fitems if it['id'] == 'firmware-panel-lean'), None)
    check('/display/firmware\'s panel description reads "grouped by capability" nowhere (D-ucd-12)',
          panel_lean is not None and 'capability' not in panel_lean.get('description', '').lower(),
          panel_lean and panel_lean.get('description'))
    srows = json.loads(P[3]['definition'])['rows']
    sitems = [it for row in srows for it in row['items']]
    by_sid = {it['id']: it for it in sitems}
    fw_cap_item = by_sid.get('firmware-capabilities')
    check('/display/firmware-solutions\' CapabilityDefinition table titles itself Purpose, not Capabilit',
          fw_cap_item is not None and 'Purpose' in fw_cap_item['title'] and 'Capabilit' not in fw_cap_item['title'],
          fw_cap_item and fw_cap_item['title'])
    panel_item = next((it for it in sitems if it['id'] == 'firmware-solution-panel'), None)
    check('…and the firmware-solution-panel description says "GROUPED by Purpose", not "by Capability"',
          panel_item is not None and 'GROUPED by Purpose' in panel_item.get('description', '')
          and 'by Capability' not in panel_item.get('description', ''), panel_item and panel_item.get('description'))


def demo4_targets():
    """demo-4 (DEMONSTRABLES_PLAN.md §3): targets derived for uno-sim-rig, the seeded capability + its two instances,
    the forward/reverse links, and the new API doors (render/build/prove buttons + targets/capabilities)."""
    from cmod.custom import targets as T
    rows = T.derive('uno-sim-rig-graph')
    by_ref = {r['port_ref']: r for r in rows}
    adc = by_ref.get('adc.channel')
    check('the ADC pin target is derived for uno-sim-rig (hal_adc_read channel -> A0, kind register, bound to a BoardPin)',
          adc is not None and adc['kind'] == 'register' and adc['lives_on'] == 'arduino-uno-r3:A0' and adc['provenance'] == 'annotation', adc)
    temp = by_ref.get('temp.return')
    check('the temp_c memory-field target is derived (sensor_value.return written into SimRigState.temp_c, unbound — a struct field, not a register)',
          temp is not None and temp['kind'] == 'memory-field' and temp['lives_on'] == 'unbound' and 'temp_c' in temp['controls']
          and temp['provenance'] == 'derived', temp)
    check('unbound targets are produced and visibly marked (not silently dropped) — at least one register touch with no board pin match',
          any(r['lives_on'] == 'unbound' for r in rows), [r['port_ref'] for r in rows if r['lives_on'] == 'unbound'])

    cap = T.temperature_sensor_capability()
    check('the "temperature sensor solution" capability requires exactly the ADC pin + temp_c memory-field targets',
          set(x.strip() for x in cap['required_targets'].split(',')) == {'adc.channel', 'temp.return'} and cap['exposes_fields'] == 'temp_c', cap)
    insts = T.temperature_sensor_instances()
    check('two CapabilityInstance rows exist (his worked example: "be able to define multiple temperature sensors")',
          len(insts) == 2 and {i['index'] for i in insts} == {1, 2} and all(i['capability'] == cap['name'] for i in insts), insts)


    # hw priorities P1 (AI-Notes/plans/HARDWARE_DEV_PRIORITIES.md §1/§4): the widened CapabilityDefinition
    # fields, the validator (refuses naming the first missing task/target), status derivation off the latest
    # ScenarioRun, the two seeds, and the firmware solution payload's new `capabilities` grouping.
    import json as _json
    from cmod.custom import capabilities as CAP
    from cmod.objects.cmod.CapabilityDefinition import CapabilityDefinition as CD
    check('CapabilityDefinition carries the widened fields with additive defaults (goal, tasks_by_runtime_json, '
          'acceptance_scenario, status, last_proof)',
          hasattr(CD(), 'goal') and CD().tasks_by_runtime_json == '{}' and CD().status == 'planned' and CD().last_proof == '')

    temp = CAP.find('temp-sensor-to-os')
    blink = CAP.find('blink-on-command')
    check('temp-sensor-to-os: his exact worked goal, a task per runtime (no typescript-browser), acceptance_scenario set',
          temp['goal'] == 'data is retrieved from a temp sensor and gets sent back over USB to the OS'
          and temp['acceptance_scenario'] == 'temp-sensor-to-os-acceptance'
          and _json.loads(temp['tasks_by_runtime_json'])['typescript-browser'] == [], temp)
    check('blink-on-command: his exact worked goal #2, D13 (led.on) the only required target',
          blink['goal'] == "the OS turns the board's LED on and off on command" and blink['required_targets'] == 'led.on', blink)

    ok, why = CAP.validate(temp)
    check('validate(temp-sensor-to-os) passes: every task resolves (c-device nodes, uno-temp-split/temp-analysis states) '
          'and every required target is registered', ok, why)
    ok, why = CAP.validate(blink)
    check('validate(blink-on-command) passes too (D13/led.on is already bound by uno-sim-rig\'s own register map)', ok, why)

    bad_target = dict(temp, required_targets=temp['required_targets'] + ', not.a.real.target')
    ok, why = CAP.validate(bad_target)
    check('the validator REFUSES an unregistered target, NAMING it (never a silent pass)',
          not ok and 'not.a.real.target' in why, why)
    bad_task = dict(blink)
    t = _json.loads(bad_task['tasks_by_runtime_json'])
    t['c-device'] = t['c-device'] + ['uno-sim-rig-graph:not_a_real_node']
    bad_task['tasks_by_runtime_json'] = _json.dumps(t)
    ok, why = CAP.validate(bad_task)
    check('the validator REFUSES a task that does not exist, NAMING it',
          not ok and 'not_a_real_node' in why, why)

    status, proof, swhy = CAP.derive_status(temp)
    check('derive_status with no live manager reads the row back unchanged (status is DERIVED from a live ScenarioRun, never guessed offline)',
          status == 'planned' and proof == '', (status, proof, swhy))

    from firmwarefaults.custom import acceptance as ACC
    sc = ACC.find('temp-sensor-to-os-acceptance')
    check('the acceptance Scenario is kind=acceptance, names its capability, and drives the twin\'s own ADC ramp stimulus',
          sc is not None and sc['kind'] == 'acceptance' and sc['capability'] == 'temp-sensor-to-os'
          and any(s['kind'] == 'drive-adc-ramp' for s in ACC.steps_of('temp-sensor-to-os-acceptance')), sc)

    # the live API: a manager seeded exactly like the server boots it (same lightweight pattern as
    # selftest_firmwaresol.firmware_parts — no full server boot)
    from types import SimpleNamespace
    from falcon import testing
    import falcon
    from cmod.cmod_seed import CMOD_SEED_PAIRS
    from cmod.cmod_firmware_api import FirmwareAPI
    from cmod.cmod_capability_api import CapabilityAPI
    tables = {}
    mgr = SimpleNamespace(objectTables=tables, idList=[], db=None)
    for name, cls, seed_rows in CMOD_SEED_PAIRS:
        for row in seed_rows:
            o = cls(manager=mgr, **{k: v for k, v in row.items() if k != '_converge'})
            tables.setdefault(name, {})[o.id] = o
    app = falcon.App()
    polServer = SimpleNamespace(falconServer=app, manager=mgr, idList=[])
    FirmwareAPI(polServer=polServer, manager=mgr)
    CapabilityAPI(polServer=polServer, manager=mgr)
    c = testing.TestClient(app)
    r = c.simulate_get('/api/capabilities')
    names = sorted(x['name'] for x in (r.json.get('capabilities') or []))
    check('GET /api/capabilities lists the 4 CapabilityDefinition rows (goal, status, last_proof per row) — ucd-0e2: + button-clock-to-os',
          r.status_code == 200 and names == sorted(['uno-sim-rig-graph:temperature-sensor-solution', 'temp-sensor-to-os', 'blink-on-command',
                                                     'button-clock-to-os']),
          names)
    r = c.simulate_get('/api/capabilities/temp-sensor-to-os')
    check('GET /api/capabilities/{name} carries tasks grouped by runtime + targets with their registration state',
          r.status_code == 200 and r.json['tasks_by_runtime']['python-backend'] == ['temp-analysis:on-temp']
          and any(t['port_ref'] == 'adc.channel' and t['registered'] for t in r.json['targets']), r.text[:300])
    r = c.simulate_get('/api/firmware/solutions/uno-sim-rig')
    cap_names = sorted(c_['name'] for c_ in (r.json.get('capabilities') or []))
    check('the firmware solution payload gains capabilities: [{name, goal, status, task_names}] for the UI to group Tasks by',
          r.status_code == 200 and cap_names == sorted(['uno-sim-rig-graph:temperature-sensor-solution', 'temp-sensor-to-os', 'blink-on-command'])
          and 'led' in next(c_ for c_ in r.json['capabilities'] if c_['name'] == 'blink-on-command')['task_names'], cap_names)
    # D-ucd-12 (his ruling): person-facing word is Purpose — `purposes` carries the SAME rows as the deprecated
    # `capabilities` key, for the Tasks section to group by without saying "capability" anywhere a person reads.
    purpose_names = sorted(p['name'] for p in (r.json.get('purposes') or []))
    check('…and the SAME payload also carries purposes: [{name, goal, status, task_names}], byte-identical to '
          'capabilities (D-ucd-12 — capabilities stays one release, deprecated)',
          purpose_names == cap_names and r.json.get('purposes') == r.json.get('capabilities'),
          (purpose_names, r.json.get('purposes'), r.json.get('capabilities')))

    # D-ucd-12: a task may be named by SEVERAL Purposes (never one exclusive bucket) — temp-sensor-to-os and
    # blink-on-command share no task today, so seed a THIRD, synthetic CapabilityDefinition over the same graph
    # that also names 'send' (already temp-sensor-to-os's) to prove 'send' lands in BOTH rows' task_names; removed
    # from the table immediately after so it leaves no trace on the real seed.
    from cmod.cmod_basis import CapabilityDefinition as _CapDef
    synth = _CapDef(manager=mgr, name='uplink-shared-test-only', graph='uno-sim-rig-graph', title='Test-only shared uplink',
                    goal='TEST ONLY: shares the send task with temp-sensor-to-os to prove multi-Purpose membership',
                    tasks_by_runtime_json=_json.dumps({'c-device': ['uno-sim-rig-graph:send'], 'java-bridge': [],
                                                       'python-backend': [], 'typescript-browser': []}))
    tables.setdefault('CapabilityDefinition', {})[synth.id] = synth
    try:
        r = c.simulate_get('/api/firmware/solutions/uno-sim-rig')
        by_name = {p['name']: p for p in r.json['purposes']}
        check('…and a task named by TWO Purposes (send: temp-sensor-to-os + the synthetic uplink-shared-test-only) '
              'appears in BOTH rows\' task_names — never exclusively one',
              'send' in by_name.get('temp-sensor-to-os', {}).get('task_names', [])
              and 'send' in by_name.get('uplink-shared-test-only', {}).get('task_names', []),
              {k: v.get('task_names') for k, v in by_name.items()})
        composed = next((row for row in r.json['schedule'] if row['task'] == 'send'), None)
        check('…and the reverse link (composed_by.purposes, D-ucd-12) names BOTH Purposes for that one task',
              composed is not None and {'temp-sensor-to-os', 'uplink-shared-test-only'} <= set(composed['composed_by'].get('purposes', [])),
              composed and composed.get('composed_by'))
    finally:
        del tables['CapabilityDefinition'][synth.id]

    # proof-push rule (a proof counts only when its run row exists on the server the pages read): the honest /prove
    # door refuses 409 (writing NO ScenarioRun) when its own engines rung cannot run a twin build, and the new
    # /runs door lets a run proved ELSEWHERE be stored + re-derived.
    from cmod.custom import cmod_engines as CE
    _orig_resolve = CE.resolve

    def _fake_remote_resolve(engine, *a, **kw):
        if engine == 'make':
            return {'how': 'refused', 'where': 'http://192.168.0.210:9830',
                    'why': "avr-gcc resolves to remote (http://192.168.0.210:9830); the board worker runs single "
                           "engines, not make"}
        return _orig_resolve(engine, *a, **kw)
    CE.resolve = _fake_remote_resolve
    try:
        before = len(tables.get('ScenarioRun', {}))
        r = c.simulate_post('/api/capabilities/temp-sensor-to-os/prove', body=_json.dumps({'mode': 'digital-twin'}))
        after = len(tables.get('ScenarioRun', {}))
        check('POST .../prove REFUSES 409 (naming the refusal + a retry command) when its engines rung resolves to '
              'a remote single-engine worker (faked here) and writes NO ScenarioRun',
              r.status_code == 409 and 'single engines, not make' in r.json.get('error', '')
              and 'pol capability prove' in r.json.get('retry', '') and after == before,
              (r.status_code, r.json, before, after))
    finally:
        CE.resolve = _orig_resolve

    run_body = {'name': 'blink-on-command-acceptance@digital-twin@pushed-test-1', 'scenario': 'blink-on-command-acceptance',
                'side': 'acceptance', 'outcome': 'passed', 'verdict_words': 'ok: glue_build.prove (simavr twin)',
                'frames_seen': 3, 'simulator_version': 'avr-twin',
                'repro_json': _json.dumps({'mode': 'digital-twin', 'scenario': 'blink-on-command-acceptance', 'capability': 'blink-on-command'}),
                'ran_at': '2026-10-07T00:00:00', 'notes': 'proved on a host whose rung could build the twin; pushed here (proof-push rule)'}
    r = c.simulate_post('/api/capabilities/blink-on-command/runs', body=_json.dumps(run_body))
    check('POST /api/capabilities/{name}/runs stores the pushed ScenarioRun and re-derives the capability\'s status',
          r.status_code == 200 and r.json.get('ok') and r.json.get('status') == 'proven-on-twin'
          and any(getattr(x, 'name', '') == run_body['name'] for x in tables.get('ScenarioRun', {}).values()), r.text[:300])
    r2 = c.simulate_get('/api/capabilities/blink-on-command')
    check('…and GET /api/capabilities/{name} reads it straight back (status persisted onto the row, not just the response)',
          r2.json['capability']['status'] == 'proven-on-twin', r2.json['capability'].get('status'))
    r3 = c.simulate_post('/api/capabilities/blink-on-command/runs',
                         body=_json.dumps(dict(run_body, name='mismatch-1', scenario='temp-sensor-to-os-acceptance')))
    check('POST .../runs REFUSES 422 when the run names a different scenario than the capability\'s own acceptance_scenario',
          r3.status_code == 422, r3.json)

    # derivation ignores engine-refusal ('undetermined') runs entirely — reuse `mgr` (already seeded with the real
    # RegisterAssignment rows validate() needs); only ScenarioRun rows for temp-sensor-to-os-acceptance are new.
    from firmwarefaults.firmwarefaults_basis import ScenarioRun as _SR
    u1 = _SR(manager=mgr, name='temp-sensor-to-os-acceptance@digital-twin@u1', scenario='temp-sensor-to-os-acceptance',
             side='acceptance', outcome='undetermined', verdict_words='engine refusal', ran_at='2026-10-07T00:00:00')
    tables.setdefault('ScenarioRun', {})[u1.id] = u1
    status, proof, why = CAP.derive_status(temp, manager=mgr)
    check('derive_status treats a lone undetermined (engine-refusal) run as NOT evidence — stays planned, naming the count',
          status == 'planned' and 'undetermined' in why and '1 ScenarioRun' in why, (status, why))
    p1 = _SR(manager=mgr, name='temp-sensor-to-os-acceptance@digital-twin@p1', scenario='temp-sensor-to-os-acceptance',
             side='acceptance', outcome='passed', verdict_words='ok', ran_at='2026-10-07T00:00:01',
             repro_json=_json.dumps({'mode': 'digital-twin'}))
    tables.setdefault('ScenarioRun', {})[p1.id] = p1
    status, proof, why = CAP.derive_status(temp, manager=mgr)
    check('…a later PASSED run is the latest EVIDENTIAL one (the undetermined run is skipped, not just outranked) → proven-on-twin',
          status == 'proven-on-twin', (status, why))
    u2 = _SR(manager=mgr, name='temp-sensor-to-os-acceptance@digital-twin@u2', scenario='temp-sensor-to-os-acceptance',
             side='acceptance', outcome='undetermined', verdict_words='engine refusal again', ran_at='2026-10-07T00:00:02')
    tables.setdefault('ScenarioRun', {})[u2.id] = u2
    status, proof, why = CAP.derive_status(temp, manager=mgr)
    check('…and a NEWER undetermined run never overwrites a prior pass (still not evidence either way) — stays proven-on-twin',
          status == 'proven-on-twin', (status, why))

    # ucd-0e2: button-clock-to-os — NO FirmwareSolution/CGraph exists for it (0e2b's job), so its c-device tasks are
    # 'project:atom' refs (validated against the atoms cmod's annotation parser finds in the app's own source) and its
    # acceptance Scenario runs through a DEDICATED runner (board.custom.button_clock_acceptance), never FW.run().
    bc = CAP.find('button-clock-to-os')
    ok, why = CAP.validate(bc)
    check('validate(button-clock-to-os) passes: the six c-device tasks all resolve against apps/button_clock.c + hal.c '
          '(no graph needed); empty java-bridge/python-backend/typescript-browser lists validate trivially (planned, named honestly)',
          ok, why)
    t_bc = _json.loads(bc['tasks_by_runtime_json'])
    t_bc['c-device'] = t_bc['c-device'] + ['uno-button-clock:not_a_real_atom']
    bad_atom = dict(bc, tasks_by_runtime_json=_json.dumps(t_bc))
    ok, why = CAP.validate(bad_atom)
    check('…and REFUSES a c-device atom that is not in apps/button_clock.c or hal.c, naming it',
          not ok and 'not_a_real_atom' in why, why)
    sc_bc = ACC.find('button-clock-to-os-acceptance')
    check('button-clock-to-os-acceptance is kind=acceptance, names its capability, and its steps are the probe\'s (a)+(f) '
          'case (a pin-at press + the wired/unwired field-arrival assertions)',
          sc_bc is not None and sc_bc['kind'] == 'acceptance' and sc_bc['capability'] == 'button-clock-to-os'
          and any(s['kind'] == 'pin-at' for s in ACC.steps_of('button-clock-to-os-acceptance')), sc_bc)
    r = c.simulate_post('/api/capabilities/button-clock-to-os/prove', body=_json.dumps({'mode': 'digital-twin'}))
    check('POST /api/capabilities/button-clock-to-os/prove --twin runs the dedicated runner on the REAL simavr twin '
          '(gen/build/harness, --pin-at + --wire, the Python wire reference codec) and passes',
          r.status_code == 200 and r.json.get('ok') and r.json['run']['outcome'] == 'passed', r.text[:300])
    r2 = c.simulate_get('/api/capabilities/button-clock-to-os')
    check('…the derived status is proven-on-twin, persisted onto the row',
          r2.json['capability'].get('status') == 'proven-on-twin', r2.json['capability'].get('status'))

    # the API: both link directions + the new doors, over a manager seeded exactly like the server boots it
    from types import SimpleNamespace
    from falcon import testing
    import falcon
    from cmod.cmod_seed import CMOD_SEED_PAIRS
    from cmod.cmod_api import CModAPI
    from hwnocode.hwnocode_seed import HWNOCODE_SEED_PAIRS
    tables = {}
    mgr = SimpleNamespace(objectTables=tables, idList=[], db=None)
    for _mid, pairs in (('cmod', CMOD_SEED_PAIRS), ('hwnocode', HWNOCODE_SEED_PAIRS)):
        for name, cls, seed_rows in pairs:
            for r in seed_rows:
                o = cls(manager=mgr, **{k: v for k, v in r.items() if k != '_converge'})
                tables.setdefault(name, {})[o.id] = o
    app = falcon.App()
    CModAPI(polServer=SimpleNamespace(falconServer=app, manager=mgr, idList=[]), manager=mgr)
    c = testing.TestClient(app)

    r = c.simulate_get('/api/cmod/graphs/uno-sim-rig-graph/targets')
    check('GET /api/cmod/graphs/{g}/targets → the derived rows (seeded, same as cmod.custom.targets.derive)',
          r.status_code == 200 and r.json['ok'] and len(r.json['targets']) == 16, r.text[:200])

    r = c.simulate_get('/api/cmod/graphs/uno-sim-rig-graph')
    used_by = r.json.get('used_by') or []
    check('the FORWARD link: HardwareSolution.cgraph names this graph (uno-temp-split)',
          any(getattr(h, 'cgraph', '') == 'uno-sim-rig-graph' for h in tables.get('HardwareSolution', {}).values()))
    check('the REVERSE link resolves on GET /api/cmod/graphs/{g}: used_by lists uno-temp-split',
          any(h['name'] == 'uno-temp-split' for h in used_by), used_by)
    check('GET /api/cmod/graphs/{g} also carries the targets inline (badges on the canvas read this)',
          len(r.json.get('targets') or []) == 16)

    r = c.simulate_get('/api/cmod/capabilities')
    caps = r.json.get('capabilities') or []
    this_cap = next((x for x in caps if x['name'] == cap['name']), None)
    # hw priorities P1: two MORE CapabilityDefinition rows now exist over the same graph (temp-sensor-to-os,
    # blink-on-command, cmod.custom.capabilities.SEED_CAPABILITIES) — this demo-4 row and its 2 instances still
    # resolve exactly as before, it is just no longer the ONLY capability.
    check('GET /api/cmod/capabilities → the seeded capability with its 2 instances inline (4 capabilities total: '
          'demo-4\'s + hw priorities P1\'s temp-sensor-to-os/blink-on-command + ucd-0e2\'s button-clock-to-os)',
          len(caps) == 4 and this_cap is not None and len(this_cap['instances']) == 2, caps)
    r = c.simulate_get('/api/cmod/capabilities/%s' % cap['name'])
    check('GET /api/cmod/capabilities/{cap} → one capability + its instances',
          r.status_code == 200 and len(r.json['instances']) == 2, r.text[:200])
    r = c.simulate_get('/api/cmod/capabilities/no-such-capability')
    check('an unknown capability is refused by name, 404', r.status_code == 404)

    # render/build/prove buttons: route to the right verbs. build/prove call glue_build (engines) — mocked here so the
    # selftest stays fast/deterministic (the real engines are exercised by the committed record itself and by
    # `pol cmod build|prove`, same as every other cmod-1 proof in this file).
    import cmod.custom.glue_build as GB
    orig_build, orig_prove = GB.build, GB.prove
    GB.build = lambda name, manager=None, conform=True: {'build': {'ok': True, 'built_by': 'FAKE (selftest)', 'hex_sha256': 'ab' * 32,
                                                                   'size_text': 1, 'size_data': 2, 'size_bss': 3, 'cost_why': 'fake'}}
    GB.prove = lambda name, manager=None, write=True: {'equivalent': True, 'frames_compared': 40, 'hex_identical': True, 'n_differences': 0,
                                                       'differences': []}
    try:
        r = c.simulate_post('/api/cmod/graphs/uno-sim-rig-graph/build')
        check('POST /api/cmod/graphs/{g}/build → the build verdict as fields, not raw JSON passthrough',
              r.status_code == 200 and r.json['ok'] and r.json['hex_sha256'] == 'ab' * 32, r.text[:200])
        r = c.simulate_post('/api/cmod/graphs/uno-sim-rig-graph/prove')
        check('POST /api/cmod/graphs/{g}/prove → the twin-equivalence verdict',
              r.status_code == 200 and r.json['ok'] and r.json['equivalent'] is True and r.json['frames_compared'] == 40, r.text[:200])
    finally:
        GB.build, GB.prove = orig_build, orig_prove
    r = c.simulate_post('/api/cmod/graphs/no-such-graph/build')
    check('build/prove on an unknown graph is refused by name, 404', r.status_code == 404)


def main():
    print('cmod selftest (cmod-0 + cmod-1)')
    from cmod.custom.selftest_uno import uno_parts
    from cmod.custom.selftest_glue import graph_parts
    from cmod.custom.selftest_firmwaresol import firmware_parts
    from cmod.custom.selftest_export import export_parts   # ucd-0f: the CMake export
    from cmod.custom.selftest_claims import claims_parts    # ucd-0b: pin/peripheral claims + generated register config
    from cmod.custom.selftest_pin_config import pin_config_parts   # ucd-0b: the GENERATED pin_config.h/.c
    from cmod.custom.selftest_requirements import requirements_parts   # ucd-0b2a: widened TargetDefinition/RegisterAssignment + TWI/SPI fixtures
    from cmod.custom.selftest_binding import binding_parts, _proof_parts   # ucd-0b2b: the HardwareBinding
    for part in ((parser_on_fixtures, refusals, types_and_preprocess, manifest_idempotence, host_measure, page, demo4_targets)
                 + uno_parts(check) + graph_parts(check) + firmware_parts(check) + export_parts(check) + claims_parts(check)
                 + pin_config_parts(check) + requirements_parts(check) + binding_parts(check) + _proof_parts(check)):
        print('-- %s' % part.__name__)
        part()
    print('\n%d/%d checks passed' % (passed, total))
    return 0 if passed == total else 1


if __name__ == '__main__':
    sys.exit(main())
