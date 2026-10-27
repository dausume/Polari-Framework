"""cmod_budget_selftest — ipb-0..3 (INTERRUPT_POLL_BUDGET_PLAN.md §4, §4b): the fact rows are cited or -1 and RISC-V-named; the uno-light plan's budget
has TWO columns on ONE hart whose rows are the plan's lanes with the cycle record's numbers; the derived block is numbers with their basis; the 2x check
names the polled sense; TC-A2 (RP2350, two Hazard3 harts, facts-only) and TC-A1 (QEMU virt, 2 harts by knob) give FOUR columns; TC-B2 (UNO + C3 on
one plan) gives four columns and a link row per command path; a forced tiny scan deadline produces the headroom blocker naming its rows; the bench
budget serves the real home-bench (the UNO from its Mission, the others facts-only, the S3 as two harts); the page uses only configured tables over
registered routes; the manifests conform.

    PYTHONPATH=.:modules python3 -m cmod.cmod_budget_selftest      # from polari-framework/ (the first plan derivation is sol-0's cold run: ~15 s)
"""
import json
import re
import sys

passed = total = 0


def check(label, cond, extra=''):
    global passed, total
    total += 1
    passed += bool(cond)
    print('  [%s] %s %s' % ('\033[0;32mPASS\033[0m' if cond else '\033[0;31mFAIL\033[0m', label, extra if not cond else ''))


def _walk(node, out):
    if isinstance(node, dict):
        for k, v in node.items():
            if k in ('dataPath', 'data_path', 'path') and isinstance(v, str) and v.startswith('/api/'):
                out.append(v)
            _walk(v, out)
    elif isinstance(node, list):
        for v in node:
            _walk(v, out)


_CACHE = {}


def light_plan():
    if 'plan' not in _CACHE:
        from cmod.custom import solve_doors as SD
        from cmod.custom import task_plan as TP
        res = SD.compute('uno-light-mission', None, None, None, {}, None)
        _CACHE['plan'] = TP.derive_task_plan('uno-light-mission', 'uno-light-system', solve_run=res)
    return _CACHE['plan']


def facts():
    from board.custom import interrupt_controllers as IC
    names = [r['name'] for r in IC.CONTROLLERS]
    check('ipb-0 FACTS: every numeric fact is cited or -1 (uncited list empty)', IC.uncited_numbers() == [], IC.uncited_numbers())
    check('ipb-0 FACTS: RISC-V rows first and canonical (clint-plic, clic, hazard3, esp32c3), then the adaptation rows (avr, nvic, xtensa)',
          names[:4] == ['riscv-clint-plic', 'riscv-clic', 'riscv-hazard3', 'riscv-esp32c3-matrix'] and {'avr-vectors', 'arm-nvic', 'xtensa-matrix'} <= set(names), names)
    plic = IC.controller('riscv-clint-plic')
    check('ipb-0 FACTS: the PLIC row carries what was READ (ratified spec: priority 0 = never, no nesting, 1023 sources) with its citation',
          plic['nesting'] == 'none' and plic['max_sources'] == 1023 and 'never interrupt' in plic['priority_0_meaning'] and 'riscv-plic-spec' in plic['citation'])
    avr = IC.controller('avr-vectors')
    check('ipb-0 FACTS: the AVR adaptation row answers the RISC-V questions in its own names (SREG I = MIE, reti, sleep); entry latency 4 cycles CITED to the AVR core '
          'section read (the PB datasheet; the 328P page named in to_read); Hazard3 16 priority levels cited to the Pico SDK',
          'mstatus.MIE' in avr['global_enable'] and avr['exit_instruction'].startswith('reti') and avr['entry_latency_cycles'] == 4 and 'four clock cycles minimum' in avr['citation']
          and 'DS40002061B' in avr['to_read'] and IC.controller('riscv-hazard3')['priority_levels'] == 16 and 'top 4 bits' in IC.controller('riscv-hazard3')['citation'])
    uno, s3, pico, qemu = IC.facts_for_board('arduino-uno-r3'), IC.facts_for_board('elecrow-esp32-eval'), IC.hart_facts('rp2350'), IC.hart_facts('qemu-virt-rv32')
    check('ipb-0 FACTS: harts per processor - UNO 1 (16 MHz cited to the cycle record), S3 2, RP2350 2 Hazard3, QEMU virt configurable (-1) and fully open',
          uno['harts'] == 1 and uno['clock_hz'] == 16000000 and 'cycle record' in uno['clock_citation'] and s3['harts'] == 2 and pico['harts'] == 2
          and pico['controller'] == 'riscv-hazard3' and qemu['harts'] == -1 and IC.openness_words(qemu) == 'ISA open / core RTL open / silicon open / tooling open')
    rows = IC.hart_rows()
    check('ipb-0 FACTS: hart rows are plain strings for the table (harts_text, clock_text, openness) and every ladder board on the home bench resolves',
          all(isinstance(r['harts_text'], str) and isinstance(r['clock_text'], str) for r in rows)
          and all(IC.facts_for_board(b) for b in ('arduino-uno-r3', 'arduino-zero', 'adafruit-feather-m0-express', 'elecrow-esp32-eval', 'esp32-c3-devkitm-1', 'rpi-pico2')))


def plan_budget():
    from cmod.custom import budget as BG
    from cmod.custom import budget_suggest as SG
    plan = light_plan()
    sb = BG.system_budget(plan, 'uno-light')
    _CACHE['sb'] = sb
    hb = sb['harts'][0]
    check('ipb-1 PLAN: the uno-light plan budgets ONE hart (the UNO\'s U1) with TWO columns, superloop (bare C), tier bare-c',
          len(sb['harts']) == 1 and sb['columns'] == 2 and hb['hart'] == 'arduino-uno-r3:U1#0' and hb['schedule_model'] == 'superloop' and sb['tier'] == 'bare-c')
    polls = {p['atom_short'] for p in hb['polls']}
    ints = {i['vector'] for i in hb['interrupts']}
    loop_atoms = {s['atom'].split(':', 1)[1] for t in plan['tasks'] for s in t['steps'] if s['lane'] == 'loop'}
    isr_atoms = {s['atom'].rsplit('.', 1)[-1] for t in plan['tasks'] for s in t['steps'] if s['lane'] == 'isr'}
    check('ipb-1 PLAN: the POLL column = the plan\'s loop-lane atoms (once each) and the INTERRUPT column = its isr-lane vectors (INT0, USART_RX, TIMER2_COMPA)',
          polls == loop_atoms and ints == isr_atoms == {'INT0_vect', 'USART_RX_vect', 'TIMER2_COMPA_vect'} and len(hb['polls']) == len(polls), (polls ^ loop_atoms, ints))
    sense = next(p for p in hb['polls'] if p['atom_short'] == 'apps/light.sense_poll')
    usart = next(i for i in hb['interrupts'] if i['vector'] == 'USART_RX_vect')
    timer = next(i for i in hb['interrupts'] if i['vector'] == 'TIMER2_COMPA_vect')
    check('ipb-1 PLAN: numbers come from the cycle record - sense_poll cycles 130..250 measured; USART_RX length mean 48 / latency 5 with a twin-seen rate; TIMER2 rate = 1000 / 100 ms period',
          sense['cycles_min'] == 130 and sense['cycles_max'] == 250 and usart['length_mean'] == 48.0 and usart['latency_max'] == 5 and usart['expected_rate_hz'] > 0
          and 'twin' in usart['rate_basis'] and timer['expected_rate_hz'] == 10.0 and 'period' in timer['rate_basis'])
    d = hb['derived']
    check('ipb-1 PLAN: derived - polls_per_scan = the poll count (dividers 1), scan_cycles a bound beside the twin\'s measured worst gap, scan_ms at 16 MHz, deadline defaulted '
          'to the shortest wanted / 2 (50 ms) and SAID, headroom in (0, 1), worst latency -1 with its basis',
          d['polls_per_scan'] == len(hb['polls']) and d['scan_cycles'] > 0 and d['measured_worst_gap_cycles'] == 175647 and abs(d['scan_ms'] - d['scan_cycles'] / 16000.0) < 1e-9
          and d['scan_deadline_ms'] == 50.0 and 'shortest wanted' in d['scan_deadline_basis'] and 0 < d['headroom'] < 1 and d['worst_latency_cycles'] == -1 and 'masked window' in d['worst_latency_basis'], d)
    checks = {c['atom']: c['verdict'] for c in hb['checks']}
    check('ipb-1 PLAN: the 2x check runs per poll and names the polled sense (ok at 50 ms)', checks.get('apps/light.sense_poll') == 'ok' and len(hb['checks']) == len(hb['polls']), checks)
    check('ipb-1 PLAN: the command path is a LINK row - host -> uart -> USART_RX_vect -> receive-command (baud / frame / transit -1, said)',
          len(sb['links']) == 1 and sb['links'][0]['transport'] == 'uart' and sb['links'][0]['receiving_interrupt'] == 'USART_RX_vect' and sb['links'][0]['baud'] == -1, sb['links'])
    kinds = [s['kind'] for s in SG.suggestions(sb)]
    check('ipb-3 SUGGEST: a healthy UNO budget gets only masked-window (advice: measure the masked window; the AVR entry latency is already cited), naming its evidence',
          kinds == ['masked-window'] and all(s['evidence'] for s in SG.suggestions(sb)) and 'cite' not in SG.suggestions(sb)[0]['suggestion'], kinds)
    forced = BG.system_budget(plan, 'uno-light', {'scan_deadline_ms': 0.001})
    fs = SG.suggestions(forced)
    costliest = max(forced['harts'][0]['polls'], key=lambda p: p['cost_per_scan_cycles'])['atom_short']
    check('ipb-3 SUGGEST: a forced 1 us scan deadline -> headroom < 0 -> the headroom BLOCKER names the costliest poll (%s) and the derived numbers' % costliest,
          forced['harts'][0]['derived']['headroom'] < 0 and fs[0]['kind'] == 'headroom' and fs[0]['severity'] == 'blocker' and 'derived.headroom' in fs[0]['evidence'] and costliest in fs[0]['suggestion'], fs[:1])
    noisy = BG.system_budget(plan, 'uno-light', {'poll_divider': {'uno:apps/light.sense_poll': 4}, 'expected_rate_hz': {'USART_RX_vect': 2000}})
    hb2 = noisy['harts'][0]
    s2 = next(p for p in hb2['polls'] if p['atom_short'] == 'apps/light.sense_poll')
    u2 = next(i for i in hb2['interrupts'] if i['vector'] == 'USART_RX_vect')
    check('ipb-1 KNOBS: poll_divider 4 quarters the sense cost per scan; expected_rate_hz 2000 on USART_RX sets its utilisation = 48 x 2000 / 16e6',
          s2['cost_per_scan_cycles'] == 250 / 4 and u2['rate_basis'] == 'rate: knob' and abs(u2['utilisation'] - 48.0 * 2000 / 16e6) < 1e-12)
    none = BG.system_budget(plan, '')
    check('ipb-1 HONEST: with no cycle record every measured number is -1 and the scan is unknown (checks say unknown, costs named as unknown)',
          all(p['cycles_max'] == -1 for p in none['harts'][0]['polls']) and none['harts'][0]['derived']['scan_ms'] == -1
          and all(c['verdict'] == 'unknown' for c in none['harts'][0]['checks']) and none['harts'][0]['derived']['unknown_poll_costs'])


def _two_chip_plan():
    """TC-B2: the uno-light plan plus a C3 processor carrying a FreeRTOS-shaped relay task that receives the UNO's frames (a message trigger)."""
    plan = json.loads(json.dumps(light_plan()))
    plan['processors'].append({'name': 'esp32-c3-devkitm-1:U1', 'board': 'esp32-c3-devkitm-1', 'role': 'chip U1 (mcu)', 'soc': 'esp32c3'})
    plan['tasks'].append({'task': 'relay-frame', 'title': 'relay the UNO frame', 'processor': 'esp32-c3-devkitm-1:U1', 'context': 'task', 'priority': 1, 'deadline_ms': 50.0,
                          'period_ms': -1.0, 'trigger': {'kind': 'message', 'what': 'a frame from the UNO', 'how': 'interrupt', 'route': 'uart-rx-interrupt'},
                          'steps': [{'n': 1, 'lane': 'isr', 'atom': 'c3:hal.UART0_IRQ', 'instance': 'uart0', 'role': 'notices'},
                                    {'n': 2, 'lane': 'loop', 'atom': 'c3:apps/relay.frame_to_gpio', 'instance': 'relay', 'role': 'acts'}], 'routes': [], 'purposes': []})
    return plan


def test_cases():
    from cmod.custom import budget as BG
    plan = light_plan()
    # TC-A2: the RISC-V-first multi-hart case, facts-only
    pico = json.loads(json.dumps(plan))
    pico['processors'] = [{'name': 'rpi-pico2:U1', 'board': 'rpi-pico2', 'role': 'chip U1 (mcu)', 'soc': 'rp2350'}]
    for t in pico['tasks']:
        t['processor'] = 'rpi-pico2:U1'
    sb = BG.system_budget(pico, '', {'hart_of': {'relay-state': 1, 'sense': 1}})
    h0, h1 = sb['harts']
    check('TC-A2 RP2350: two Hazard3 harts -> FOUR columns; tasks placed by hart_of (relay-state + sense on hart 1); every number -1 (facts only, no record), RISC-V controller row',
          sb['columns'] == 4 and h0['hart'].endswith('#0') and h1['hart'].endswith('#1') and h0['controller'] == 'riscv-hazard3' and h0['clock_hz'] == 150000000
          and {i['vector'] for i in h1['interrupts']} == {'TIMER2_COMPA_vect'} and 'apps/light.sense_poll' in {p['atom_short'] for p in h1['polls']}
          and all(p['cycles_max'] == -1 for h in sb['harts'] for p in h['polls']) and h0['derived']['scan_ms'] == -1, ([i['vector'] for i in h1['interrupts']], h0['controller']))
    # TC-A1: the fully open virtual machine, hart count by knob
    virt = json.loads(json.dumps(pico))
    virt['processors'] = [{'name': 'qemu-virt-rv32:hart', 'board': 'qemu-virt-rv32', 'role': 'chip (mcu)', 'soc': 'qemu-virt-rv32'}]
    for t in virt['tasks']:
        t['processor'] = 'qemu-virt-rv32:hart'
    v2 = BG.system_budget(virt, '', {'harts': 2})
    v3 = BG.system_budget(virt, '', {'harts': 3})
    check('TC-A1 QEMU virt: harts is a KNOB on the configurable machine - 2 -> four columns, 3 -> six; CLINT + PLIC row; the note says the count is a knob',
          v2['columns'] == 4 and v3['columns'] == 6 and v2['harts'][0]['controller'] == 'riscv-clint-plic' and any('knob' in n for n in v2['harts'][0]['notes']))
    # TC-B2: two chips, mixed bare C + RTOS-shaped task, a link between them
    tb = BG.system_budget(_two_chip_plan(), 'uno-light')
    uno = next(h for h in tb['harts'] if h['soc'] == 'atmega328p')
    c3 = next(h for h in tb['harts'] if h['soc'] == 'esp32c3')
    link = next((l for l in tb['links'] if l['to_hart'] == c3['hart']), None)
    check('TC-B2 UNO + C3: FOUR columns on two chips; the C3 hart holds the relay task as a THREAD sub-row, its UART interrupt in its column (numbers -1: no C3 record yet); '
          'the message path is a link row from another hart with the chain named',
          tb['columns'] == 4 and len(c3['threads']) == 1 and c3['threads'][0]['task'] == 'relay-frame' and [i['vector'] for i in c3['interrupts']] == ['UART0_IRQ']
          and c3['interrupts'][0]['length_mean'] == -1 and uno['interrupts'] and link is not None and link['from'] == 'another hart' and 'UART0_IRQ' in link['chain'], (len(tb['harts']), tb['links']))


def bench():
    from cmod.custom import budget as BG
    bb = BG.bench_budget('home-bench', None, None, plan_for=lambda m, s: light_plan())
    by = {e['board']: e for e in bb['boards']}
    harts = {h['hart']: h for h in bb['harts']}
    check('ipb-1 BENCH: the real home-bench - UNO from its Mission (2 columns with rows), Zero + Feather facts-only (1 hart each, empty columns), the S3 as TWO harts -> 10 columns',
          bb['columns'] == 10 and 'uno-light-mission' in by['arduino-uno-r3']['state'] and by['arduino-uno-r3']['mission'] == 'uno-light-mission'
          and by['elecrow-esp32-eval']['harts'] == 2 and 'facts only' in by['arduino-zero']['state'] and len(harts['arduino-uno-r3:U1#0']['polls']) > 0
          and harts['elecrow-esp32-eval:esp32-xtensa#1']['polls'] == [] and harts['elecrow-esp32-eval:esp32-xtensa#1']['interrupts'] == [], (bb['columns'], [e['state'][:40] for e in bb['boards']]))
    check('ipb-1 BENCH: every view yields plain rows (no nested dicts / lists) with the hart named, and an unknown bench is None',
          all(all(not isinstance(v, (dict, list)) for v in r.values()) for k, f in BG.VIEWS.items() for r in f(bb)) and all('hart' in r for r in BG.poll_rows(bb))
          and BG.bench_budget('no-such-bench') is None)


def page_and_manifest():
    from cmod.cmod_budget_page import BUDGET_PAGES as P
    d = json.loads(P[0]['definition'])
    items = [it for t in d['tabs'] for r in t['rows'] for it in r['items']]
    kinds = {it.get('componentProps', {}).get('componentName') for it in items}
    check('ipb-2 PAGE: /display/budget = three tabs (bench, plan, facts), every panel a configured table (class-rows-table), no api-json-panel',
          P[0]['pageRoute'] == 'budget' and [t['key'] for t in d['tabs']] == ['bench', 'plan', 'facts'] and 'api-json-panel' not in P[0]['definition']
          and all('columns' in (it.get('componentProps') or it) or it.get('type') == 'table' or 'class-rows-table' in json.dumps(it) for it in items), kinds)
    paths = []
    _walk(d, paths)
    api = open(__file__.replace('cmod_budget_selftest.py', 'cmod_budget_api.py')).read()
    routes = re.findall(r"add\('([^']+)'", api)
    bad = [p for p in paths if not any(re.fullmatch(re.sub(r'\{[^}]+\}', '[^/]+', r), p.split('?')[0]) for r in routes)]
    check('ipb-2 PATHS: every path the page uses (%d) is a route in cmod_budget_api.py' % len(paths), paths and not bad, bad)
    views = {p.split('view=')[1] for p in paths if 'view=' in p and 'hart-facts' not in p}
    from cmod.custom import budget as BG
    check('ipb-2 VIEWS: every budget view the page asks for exists', views <= set(BG.VIEWS) | {'suggestions'}, views - set(BG.VIEWS) - {'suggestions'})
    from moduleService.manifests import conform
    for m in ('cmod', 'board'):
        r = conform(m)
        check('ipb MANIFEST: pol modules conform %s is clean with the new files listed' % m, r['ok'], r.get('findings'))


def main():
    facts()
    plan_budget()
    test_cases()
    bench()
    page_and_manifest()
    print('\n%d/%d passed' % (passed, total))
    return 0 if passed == total else 1


if __name__ == '__main__':
    sys.exit(main())
