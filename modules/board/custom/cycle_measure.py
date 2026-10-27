"""
@module board.custom.cycle_measure

cyc-0 (MISSION_PROFILE_SOLVER_PLAN.md section 16): MEASURED CYCLE COUNTS of the UNO firmware's atoms, interrupts and main loop, on the simavr twin.

HOW A CYCLE IS SAMPLED. polari-avr-twin (board engines image, through the engines seam - never a hand-rolled docker run) already steps simavr one
instruction at a time when a scenario flag is given and reads the core's own cycle counter (avr->cycle). Three of its flags are the sampling points:
  --fn-cycles 0xENTRY:ret   cycles from the first instruction of a function to the `ret` that takes it back to its caller (SP rises above its value at
                            entry; the ret's own cycles included; the caller's CALL/RCALL is not): n calls, min, max. Calls made from inside an interrupt
                            handler are not counted; an interrupt that lands INSIDE the call is - so max is "this call, with whatever interrupted it".
  --isr-latency             per vector: n, min, max, mean of the ISR length (RUNNING raised -> lowered at reti) and of the latency (flag raised -> taken)
  --fn-cycles 0xA:0xB       cycles from the LAST visit of address A to address B (A re-arms on every visit): used for the main loop (below)
We chose these over a gdb stub or a VCD trace because they are the twin's own counters, exact to the cycle, need no second tool in the image
(there is no avr-gdb), and cost +25% wall (firmwarefaults/COST.md). The twin offers ONE --fn-cycles per run, so each function is its own run of the
SAME hex with the SAME stimulus: simavr is deterministic, so the runs see the same history (the selftest proves two runs give identical counts).
The twin gives n / min / max for a function (no sum), so a function's MEAN is not available; an ISR's mean is.

TWO BUILDS, SAID. A static function GCC inlined into its caller has no symbol and no entry address in the shipped hex. So atoms are measured in the
-fno-inline build (the same flags as the Makefile + -fno-inline, --no-gc-sections - exactly the manifest's `noinline` mode, whose sizes are
text_bytes_noinline): "what the atom costs as a separate node". The interrupt handlers and the main loop are measured in the SHIPPED hex (the one
`pol board build` flashes). The record keeps both hexes' sha256.

THE MAIN LOOP. A `for (;;)` pass has no function to measure. The loop's poll point (the top of the drain `while (hal_rx_pop(&b))`, found in the shipped
disassembly) is visited once per pass and once more per received byte; every route back to it is an unconditional jump. For each such jump we measure
poll point -> that jump (+ the jump's own cycles): the gap between two visits of the poll point, by which way the loop came back. The longest gap of
any kind is the longest the loop went without polling (the worst pass the stimulus produced); a received frame of L bytes takes L byte-gaps plus the
pass that follows.

Nothing here is a guess: a number is a recorded twin run with its hex sha256, the stimulus, the tool versions, and the record's own sha256.

    python3 -m board.custom.cycle_measure measure <variant> [--json] [--save]     # build, measure, print (and write the committed record)
    python3 -m board.custom.cycle_measure show <variant> [--json]                 # the committed record
    python3 -m board.custom.cycle_measure verify <variant>                        # re-measure and compare with the record
`pol board cycles <variant>` is the CLI case line for this.
"""
import hashlib
import json
import os
import re
import shutil
import sys
import tempfile
import datetime

from board.custom import board_engines as be, cycle_stimuli as ST, engine_run, gen
from board.custom import build as B

SCHEMA = 'cycle-measurement/1'
MCU = 'atmega328p'
CLOCK_HZ = 16000000
#: variants the shipped records cover (the four of the plan + the v2 light + the sim rig: its ADC read and PWM apply)
VARIANTS = ('uno-light-unsensed', 'uno-button-clock', 'uno-light-pcint', 'uno-light-analog', 'uno-light-v2', 'uno-sim-rig')
JUMP_CYCLES = {'rjmp': 2, 'jmp': 3}
_TARGET = re.compile(r'0x([0-9a-f]+)')
_BASE = re.compile(r'(\.(constprop|isra|part|cold|lto_priv)(\.\d+)?)+$')
_NOT_FN = re.compile(r'^__(stack|heap|data|bss|eeprom|text|trampolines|ctors|dtors|DATA|TEXT|RAM|FLASH|EEPROM)')


class CycleRefused(RuntimeError):
    pass


def sha(b):
    return hashlib.sha256(b).hexdigest()


# ------------------------------------------------------------------ the two builds
def build_pair(variant, work):
    """-> {'shipped': {hex, elf, row}, 'noinline': {hex, elf}, 'files': {name: bytes} (the sources), 'project': dir}. Refuses when a build fails."""
    from firmwarefaults.custom import fault_engines as fe
    gen.gen('uno', None, work, variant=variant)
    row = B.build('uno', work)
    if row.get('state') != 'built':
        raise CycleRefused('%s did not build: %s' % (variant, row.get('notes')))
    project = row['project_dir']
    files = {fn: open(os.path.join(project, fn), 'rb').read() for fn in sorted(os.listdir(project)) if fn.endswith(('.c', '.h'))}
    sources = sorted(fn for fn in files if fn.endswith('.c'))
    r = engine_run.run('avr-gcc', B.CFLAGS + ['-fno-inline', '-Wno-error'] + B.LDFLAGS + ['-Wl,--no-gc-sections', '-o', 'firmware.elf'] + sources, files)
    if not r['ok'] or 'firmware.elf' not in r['files']:
        raise CycleRefused('the -fno-inline build of %s failed: %s' % (variant, (r.get('stderr') or '')[-400:]))
    elf_n = r['files']['firmware.elf']
    r2 = engine_run.run('avr-objcopy', ['-O', 'ihex', '-R', '.eeprom', 'firmware.elf', 'firmware.hex'], {'firmware.elf': elf_n})
    if not r2['ok']:
        raise CycleRefused('objcopy failed: %s' % (r2.get('stderr') or '')[-300:])
    return {'shipped': {'hex': open(row['hex_path'], 'rb').read(), 'elf': open(os.path.join(work, 'out', 'firmware.elf'), 'rb').read(), 'row': row},
            'noinline': {'hex': r2['files']['firmware.hex'], 'elf': elf_n}, 'files': files, 'project': project, 'fe': fe}


# ------------------------------------------------------------------ symbols and the disassembly
def _fe(engine, args, elf):
    from firmwarefaults.custom import fault_engines as fe
    r = fe.run(engine, args, {'firmware.elf': elf})
    if not r.get('ok'):
        raise CycleRefused('%s failed: %s' % (engine, (r.get('stderr') or '')[-300:]))
    return r['stdout']


def symbols(elf):
    """{symbol: [byte address, ...]} for the text symbols of an ELF (clones of one function - f.constprop.0 - are listed under f)."""
    from firmwarefaults.custom import disasm
    out = {}
    for name, d in disasm.parse_nm(_fe('avr-nm', ['-n', 'firmware.elf'], elf)).items():
        if d['space'] == 'text' and d['type'] in 'TtWw' and not name.startswith('.'):
            out.setdefault(_BASE.sub('', name), []).append((d['addr'], name))
    return out


def main_listing(elf):
    """The instructions of main() in the shipped ELF: [{pc, op, args, comment}] in address order + {label address, ...} - from avr-objdump."""
    text = _fe('avr-objdump', ['-d', '--no-show-raw-insn', 'firmware.elf'], elf)
    ins, in_main, labels = [], False, {}
    ins_re = re.compile(r'^\s+([0-9a-f]+):\s+(\S+)\s*([^;]*?)\s*(?:;\s*(.*))?$')
    for line in text.splitlines():
        m = re.match(r'^([0-9a-f]+) <([^>]+)>:$', line.strip())
        if m:
            name = m.group(2)
            if not name.startswith('.') and '^' not in name:
                in_main = name == 'main'
            if in_main:
                labels[int(m.group(1), 16)] = name
            continue
        if in_main:
            m = ins_re.match(line)
            if m:
                ins.append({'pc': int(m.group(1), 16), 'op': m.group(2), 'args': m.group(3).strip(), 'comment': (m.group(4) or '').strip()})
    return ins, labels


def _target(i):
    m = _TARGET.search(i['comment']) or _TARGET.search(i['args'])
    return int(m.group(1), 16) if m else None


def loop_sites(elf):
    """-> {'head': pc, 'sites': [{pc, op, cycles}], 'conditional': [pc...]}: the loop's poll point and every unconditional jump back to it, or raises."""
    ins, _labels = main_listing(elf)
    if not ins:
        raise CycleRefused('no main() in the shipped ELF')
    pop = next((i for i in ins if i['op'] == 'call' and 'hal_rx_pop' in i['comment']), None)
    if pop is None:
        raise CycleRefused('main() never calls hal_rx_pop: no poll point to measure the loop by')
    back = {_target(i) for i in ins if (i['op'] in JUMP_CYCLES or i['op'].startswith('br')) and _target(i) is not None and _target(i) < i['pc']}
    cands = [t for t in back if t <= pop['pc']]
    if not cands:
        raise CycleRefused('no backward jump lands before the hal_rx_pop call in main(): not a polling loop this harness understands')
    head = max(cands)
    sites = [{'pc': i['pc'], 'op': i['op'], 'cycles': JUMP_CYCLES[i['op']]} for i in ins if i['op'] in JUMP_CYCLES and _target(i) == head]
    cond = [i['pc'] for i in ins if i['op'].startswith('br') and _target(i) == head]
    return {'head': head, 'sites': sites, 'conditional': cond}


# ------------------------------------------------------------------ one twin run
def twin(hex_bytes, stim, extra):
    from firmwarefaults.custom import harness
    r = harness.run_files(stim['argv'] + list(extra), hex_bytes, stim['files'], timeout=300)
    if not r['ok'] or not r['final']:
        raise CycleRefused('the twin run failed: %s' % ((r.get('stderr') or r.get('stdout') or '')[-400:]))
    return r


def fn_run(hex_bytes, stim, start, end):
    """One --fn-cycles run -> {n, min, max} (n 0 = the stimulus never reached it). end = 'ret' or an address."""
    spec = '0x%x:ret' % start if end == 'ret' else '0x%x:0x%x' % (start, end)
    r = twin(hex_bytes, stim, ['--fn-cycles', spec])
    f = r['final'].get('fn_cycles') or {}
    return {'n': int(f.get('n', 0)), 'min': int(f.get('min', 0)), 'max': int(f.get('max', 0))}, r


def frames_of(uart):
    """[total bytes of each frame the board sent] - class-agnostic (the stream parser only needs the header)."""
    from board.custom import packet_ref
    p = packet_ref.StreamParser()
    return [len(packet_ref.frame(mt, dev, seq, payload, version=ver)) for mt, dev, seq, payload, ver in p.feed(bytes(uart))]


# ------------------------------------------------------------------ the twin's UART is not the chip's
def uart_model(txlog, files):
    """The byte time of the TWIN's USART0 (the smallest spacing between consecutive transmitted bytes in the twin's own tx log) against the CHIP's from the
    firmware's own divisor (UBRR0_VALUE in hal.c, USART_U2X in board_config.h): 10 bit times x 8 (U2X) or 16 x (UBRR+1) cycles. simavr times a byte as if
    U2X were off (the firmware writes UBRR before U2X and simavr does not re-derive the baud), so a measured send wait is longer than the chip's."""
    import struct
    cy = [struct.unpack_from('<Q', txlog, i * 9)[0] for i in range(len(txlog) // 9)]
    gaps = [b - a for a, b in zip(cy, cy[1:])]
    twin = min(gaps) if gaps else None
    hal = files.get('hal.c', b'').decode(errors='replace')
    cfg = files.get('board_config.h', b'').decode(errors='replace')
    mu = re.search(r'#define\s+USART_U2X\s+(\d)', cfg)
    m_on = re.search(r'#if\s+USART_U2X\s*\n\s*#define\s+UBRR0_VALUE\s+(\d+)', hal)
    m_off = re.search(r'#else\s*\n\s*#define\s+UBRR0_VALUE\s+(\d+)', hal)
    chip, ubrr, u2x = None, None, None
    if mu and m_on and m_off:
        u2x = int(mu.group(1))
        ubrr = int(m_on.group(1) if u2x else m_off.group(1))
        chip = 10 * (8 if u2x else 16) * (ubrr + 1)
    return {'twin_cycles_per_byte_min': twin, 'bytes_logged': len(cy), 'chip_cycles_per_byte': chip, 'ubrr': ubrr, 'u2x': u2x,
            'chip_formula': '10 bit times x (8 if U2X else 16) x (UBRR+1) cycles (ATmega328P USART baud equations; the divisor is read from the build\'s own hal.c / board_config.h)',
            'note': ('the twin spaces bytes %s cycles apart, the chip %s: the twin\'s send wait is %.2fx the chip\'s' % (twin, chip, twin / float(chip))) if twin and chip else ''}


def _source_calls(files):
    """{function: {names it calls}} read from the C text itself (a function body runs from its definition line to the next `}` at column 0) - for a variant the
    committed manifest does not list."""
    out = {}
    for fn in ('main.c', 'hal.c'):
        text = files.get(fn, b'').decode(errors='replace')
        for m in re.finditer(r'^[A-Za-z_][^\n;{}]*?\b(\w+)\s*\([^\n;]*\)\s*\n?\{(.*?)^\}', text, re.M | re.S):
            out.setdefault(m.group(1), set()).update(re.findall(r'\b(\w+)\s*\(', m.group(2)))
    return out


def _calls_send(function, files=None):
    """True when `function` is hal_usart_send or reaches it through the committed manifest's call lists (or, for a variant the manifest lacks, the source text)."""
    from cmod.custom import code_interface as CI
    calls = _source_calls(files) if files else {}
    for proj, _m, a in CI._manifest_candidates():
        if proj == 'uno':
            calls.setdefault(a['function'], set()).update(a['calls'])
    seen, todo = set(), [function]
    while todo:
        f = todo.pop()
        if f == 'hal_usart_send':
            return True
        if f not in seen:
            seen.add(f)
            todo += list(calls.get(f, ()))
    return False


def split_uart(fns, uart, frames, n_frames, files=None):
    """For a function that reaches hal_usart_send and was called exactly once per frame the board sent (measured: n == frames sent), take the twin's UART wait
    out: cpu_cycles_max = max - (frame - 1) x the twin's byte spacing (a LOWER bound on the wait of that call, so the CPU part is not understated). Only when every
    frame is the same length: with frames of several lengths a call's wait cannot be paired with its count, so the measured count stays whole (with the twin's wait in it).
    The wait itself stays a separate, physical thing (rt-0 derives it from the baud); only the CPU work of the call is what 'cpu_cycles' means."""
    if not uart.get('twin_cycles_per_byte_min') or not frames:
        return
    wait_min = (min(frames) - 1) * uart['twin_cycles_per_byte_min']
    for f in fns.values():
        if f.get('n') and _calls_send(f['function'], files):
            f['blocks_on_uart'] = True
            if f['n'] == n_frames and min(frames) == max(frames):
                f['cpu_cycles_max'] = max(0, f['max'] - wait_min)
                f['cpu_cycles_min'] = max(0, f['min'] - wait_min)
                f['uart_wait_removed_cycles'] = wait_min
                f['cpu_basis'] = ('called once per frame sent (%d calls, %d frames), so each call waited at least (%d B - 1) x %s cycles on the twin\'s UART; that wait is taken out' % (
                    f['n'], n_frames, min(frames), uart['twin_cycles_per_byte_min']))


def chip_time_loop(loop, uart, frames):
    """A loop gap that happens exactly once per frame sent is the pass that sends the report: its twin-measured length includes the twin's slow UART. At the chip's
    byte time it is shorter by (smallest frame - 1) x (twin - chip cycles per byte) - DERIVED, said so; every other gap is unchanged."""
    tw, chip = uart.get('twin_cycles_per_byte_min'), uart.get('chip_cycles_per_byte')
    for g in loop['gaps']:
        if frames and g['n'] == len(frames) and tw and chip and tw > chip:
            cut = (min(frames) - 1) * (tw - chip)
            g['sends_report'] = True
            g['chip_timed_max_cycles'] = g['max_cycles'] - cut
            g['chip_timed_basis'] = 'once per frame sent (%d of %d); minus (%d B - 1) x (%d twin - %d chip cycles per byte) = %d' % (g['n'], len(frames), min(frames), tw, chip, cut)
    if loop['gaps']:
        loop['worst_gap_chip_timed_cycles'] = max(g.get('chip_timed_max_cycles', g['max_cycles']) for g in loop['gaps'])


TWIN_CAVEATS = {'boot_session_mint': 'EEPROM writes complete at once in simavr; the chip waits per byte for EEPE (init only, not in the loop) - not applied here',
                'eeprom': 'EEPROM writes complete at once in simavr; the chip waits per byte for EEPE - not applied here'}


def caveat(function, f):
    for k, v in TWIN_CAVEATS.items():
        if k in function:
            return v
    if f.get('blocks_on_uart'):
        return 'includes the twin\'s USART wait (its byte time is longer than the chip\'s, see the record\'s uart block); cpu_cycles_* is the call without that wait' if 'cpu_cycles_max' in f \
            else 'includes the twin\'s USART wait (its byte time is longer than the chip\'s); the wait could not be separated (calls != frames sent, or the frames differ in length)'
    return ''


# ------------------------------------------------------------------ the measurement
#: a variant the committed manifest does not list yet (its atoms are not parsed): its app, so the POLARI_NODE functions of its main.c and hal.c are measured by name
APP_OF = {'uno-light-v2': 'light_v2'}


def atoms_of(variant, files=None):
    """[(atom name, function)] for every non-ISR, non-main atom of this variant in the committed uno manifest; a variant the manifest does not list yet falls back to
    the POLARI_NODE(...) functions (and, in main.c, the static functions) of its own sources (named 'apps/<app>.<fn>' / 'hal.<fn>', the manifest's own naming), so they are measured but no cost basis reads them."""
    from cmod.custom import code_interface as CI
    out = []
    for proj, _m, a in CI._manifest_candidates():
        if proj == 'uno' and variant in a.get('configs', ()) and a['kind'] != 'isr' and a['function'] != 'main':
            out.append((a['name'], a['function']))
    if not out and files and variant in APP_OF:
        for fn, mod in (('main.c', 'apps/' + APP_OF[variant]), ('hal.c', 'hal')):
            text = files.get(fn, b'').decode(errors='replace')
            names = re.findall(r'POLARI_NODE\(\s*(\w+)', text) + (re.findall(r'^static\s+[^\n(;]*?\b(\w+)\s*\([^\n;]*\)\s*$', text, re.M) if fn == 'main.c' else [])
            for name in names:
                if name != 'main' and not name.endswith('_vect'):
                    out.append(('%s.%s' % (mod, name), name))
    return sorted(set(out))


def vectors():
    from cmod.custom import registers as R
    return {n: v for n, v in R.load(MCU)['vectors'].items()}


def _tool_versions(image_id):
    tools = {'image': {'name': be.image_name(), 'id': image_id},
             'simavr': 'libsimavr2 / simavr 1.6+dfsg-3 (Debian trixie), via polari-avr-twin in the image above (prf-board-engines/Dockerfile)',
             'avr-gcc': engine_run.version('avr-gcc'), 'binutils': 'avr-nm / avr-objdump 2.43 (binutils-avr, same image)'}
    return tools


def measure(variant, work=None, only=None, progress=None):
    """Build both hexes of `variant`, drive them with its stimulus, and return the CycleMeasurement record (a dict, record_sha256 set).
    only: restrict the per-function runs to these functions (the selftest)."""
    ready, why = be.resolve('avr-twin')['how'] in ('local-binary', be.LOCAL_IMAGE), be.resolve('avr-twin')['why']
    if not ready:
        raise CycleRefused('no simavr twin here: %s' % why)
    own = work is None
    work = work or tempfile.mkdtemp(prefix='cyc0-')
    try:
        return _measure(variant, work, only, progress)
    finally:
        if own:
            shutil.rmtree(work, ignore_errors=True)


def _measure(variant, work, only, progress):
    pr = build_pair(variant, work)
    stim = ST.stimulus(variant)
    sh, ni = pr['shipped'], pr['noinline']
    sym_ni, sym_sh = symbols(ni['elf']), symbols(sh['elf'])
    say = progress or (lambda s: None)
    # -- the functions (atoms as nodes, -fno-inline build)
    fns, runs = {}, 0
    for atom, fn in atoms_of(variant, pr['files']):
        if only and fn not in only:
            continue
        clones = sym_ni.get(fn)
        if not clones:
            fns[atom] = {'function': fn, 'n': 0, 'note': 'no symbol in the -fno-inline build'}
            continue
        best = None
        for addr, name in sorted(clones):
            m, _r = fn_run(ni['hex'], stim, addr, 'ret')
            runs += 1
            m.update(symbol=name, entry='0x%x' % addr)
            if best is None or m['max'] > best['max'] or (m['n'] and not best['n']):
                best = m
        best['function'] = fn
        if best['n'] == 0:
            best['note'] = 'the stimulus never called it (or only from inside an interrupt)'
        fns[atom] = best
        say('%s: n=%d min=%d max=%d' % (atom, best['n'], best['min'], best['max']))
    # -- the interrupts (shipped hex, one run) + ipb-7 the masked windows on the same run (an older twin image without the flag: one run without it, said)
    try:
        r = twin(sh['hex'], stim, ['--isr-latency', '--uart-tx-log', 'tx.bin', '--masked-windows'])
        masked_note = ''
    except CycleRefused as e:
        r = twin(sh['hex'], stim, ['--isr-latency', '--uart-tx-log', 'tx.bin'])
        masked_note = 'this twin image has no --masked-windows (rebuild prf-board-engines): %s' % str(e)[-160:]
        runs += 1
    runs += 1
    fin = r['final']
    masked = _masked(fin.get('masked_windows') or {}, sym_sh, masked_note)
    vec_names = {int(n): name for name, n in vectors().items() if n is not None}
    isrs = {}
    for v, d in (fin.get('isr_cycles') or {}).items():
        name = vec_names.get(int(v), 'vector %s' % v)
        lat = (fin.get('isr_latency') or {}).get(v) or {}
        isrs[name] = {'vector': int(v), 'n': d['n'], 'min': d['min'], 'max': d['max'], 'mean': d['mean'],
                      'latency_max': lat.get('max'), 'basis': 'shipped hex, RUNNING raised -> lowered at reti'}
    frames = frames_of(r['uart'])
    uart = uart_model(r['files'].get('tx.bin', b''), pr['files'])
    split_uart(fns, uart, frames, len(frames), pr['files'])
    for name, f in fns.items():
        cav = caveat(f['function'], f)
        if cav:
            f['twin_caveat'] = cav
    # -- the loop (shipped hex)
    loop = {'poll_point': None, 'gaps': [], 'worst_gap_cycles': None}
    if not only or 'loop' in only:
        ls = loop_sites(sh['elf'])
        loop['poll_point'] = '0x%x' % ls['head']
        loop['conditional_back_jumps_not_separable'] = ['0x%x' % p for p in ls['conditional']]
        for s in ls['sites']:
            m, _r = fn_run(sh['hex'], stim, ls['head'], s['pc'])
            runs += 1
            if m['n']:
                loop['gaps'].append({'back_jump': '0x%x' % s['pc'], 'op': s['op'], 'n': m['n'], 'min_cycles': m['min'] + s['cycles'], 'max_cycles': m['max'] + s['cycles'],
                                     'measure': 'poll point -> %s at 0x%x, + the jump\'s own %d cycles' % (s['op'], s['pc'], s['cycles'])})
        if loop['gaps']:
            loop['worst_gap_cycles'] = max(g['max_cycles'] for g in loop['gaps'])
    chip_time_loop(loop, uart, frames)
    inputs = {'shipped_hex_sha256': sha(sh['hex']), 'shipped_elf_sha256': sha(sh['elf']), 'noinline_hex_sha256': sha(ni['hex']), 'noinline_elf_sha256': sha(ni['elf']),
              'sources': [{'path': fn, 'sha256': sha(d)} for fn, d in sorted(pr['files'].items())],
              'cflags': B.CFLAGS, 'ldflags': B.LDFLAGS, 'noinline_extra': ['-fno-inline', '-Wno-error', '-Wl,--no-gc-sections'],
              'flash_bytes': sh['row'].get('flash_bytes'), 'ram_bytes': sh['row'].get('ram_bytes')}
    stimulus = {'name': stim['name'], 'argv': stim['argv'], 'files_sha256': {k: sha(v) for k, v in sorted(stim['files'].items())}, 'seconds': stim['seconds'],
                'seed': 1, 'describe': stim['describe'], 'drives': stim['drives'], 'sim_cycles': fin.get('cycles'),
                'uart_tx_bytes': len(r['uart']), 'frames_sent': len(frames), 'frame_bytes_max': max(frames) if frames else None, 'frame_bytes_min': min(frames) if frames else None}
    rec = {'schema': SCHEMA, 'variant': variant, 'mcu': MCU, 'clock_hz': CLOCK_HZ, 'inputs': inputs, 'stimulus': stimulus,
           'tools': _tool_versions(be.local_image()), 'functions': fns, 'isrs': isrs, 'loop': loop, 'uart': uart, 'masked': masked, 'twin_runs': runs,
           'what': {'functions': 'cycles per call, entry -> ret, in the -fno-inline build (atom as a node; includes everything it calls and any interrupt that landed inside); the caller\'s CALL (4 cycles) is not counted',
                    'isrs': 'cycles per interrupt, vector taken -> reti, in the shipped hex',
                    'loop': 'cycles between two visits of the loop\'s poll point, by the way the loop came back, in the shipped hex',
                    'masked': 'ipb-7: cycles with SREG.I cleared in main-line code outside ISRs (cli -> the instruction that set I again), per opening pc with its enclosing function, in the shipped hex',
                    'mean': 'a function\'s mean is not offered by the twin (n / min / max only); an interrupt\'s is'},
           'rule': 'measured = a recorded twin run with its inputs by sha256, the stimulus and the tool versions (reproducible-initial-conditions, 2026-09-26)'}
    return seal(rec)


def _masked(mw, sym, note=''):
    """ipb-7: the twin's masked windows -> {n, min, max, mean, max_pc, max_function, sites[{pc, function, n, min, max}], basis}; each opening pc (the cli's byte
    address) is given its ENCLOSING function = the largest text symbol at or below it. No data (an old image) -> n -1 and the note says so."""
    # linker-script symbols sit in the text listing without being functions (__stack = RAMEND 0x8ff, weak): never an enclosing function
    flat = sorted((addr, name) for clones in sym.values() for addr, name in clones if not _NOT_FN.match(name))

    def fn_of(pc):
        hit = ''
        for addr, name in flat:
            if addr <= pc:
                hit = name
            else:
                break
        return _BASE.sub('', hit)

    if not mw:
        return {'n': -1, 'min': -1, 'max': -1, 'mean': -1, 'max_pc': '', 'max_function': '', 'sites': [], 'armed': 0, 'open_at_exit': 0,
                'basis': note or 'the twin answered no masked_windows block'}
    n = int(mw.get('n', 0))
    sites = sorted(({'pc': '0x%x' % int(s['pc']), 'function': fn_of(int(s['pc'])), 'n': int(s['n']), 'min': int(s['min']), 'max': int(s['max'])} for s in mw.get('sites', [])),
                   key=lambda s: (-s['max'], s['pc']))
    return {'n': n, 'min': int(mw.get('min', 0)) if n else -1, 'max': int(mw.get('max', 0)) if n else 0, 'mean': float(mw.get('mean', 0)) if n else -1,
            'max_pc': ('0x%x' % int(mw.get('max_pc', 0))) if n else '', 'max_function': fn_of(int(mw.get('max_pc', 0))) if n else '',
            'armed': int(mw.get('armed', 0)), 'open_at_exit': int(mw.get('open_at_exit', 0)), 'sites_overflow': int(mw.get('sites_overflow', 0)), 'sites': sites,
            'basis': 'shipped hex, --masked-windows: cycles with SREG.I cleared in main-line code outside ISRs, from the cli (pc = its byte address) to the instruction that set I '
                     'again (an ATOMIC_BLOCK\'s SREG restore counts); armed by the first sei (the reset -> sei stretch is initialisation, not a critical section); '
                     + ('%d windows measured, the longest named' % n if n else 'max 0 = measured, none seen (the stimulus ran no critical section)')}


def seal(rec):
    """record_sha256 = sha256 of the record's canonical JSON without recorded_at and the sha itself (so a re-measure of the same inputs seals identically)."""
    body = {k: v for k, v in rec.items() if k not in ('record_sha256', 'recorded_at')}
    rec['record_sha256'] = sha(json.dumps(body, sort_keys=True, separators=(',', ':')).encode())
    rec.setdefault('recorded_at', datetime.datetime.now().isoformat(timespec='seconds'))
    return rec


def counts(rec):
    """{what: (n, min, max)} - the comparable core of a record (the selftest's determinism check)."""
    out = {}
    for k, f in rec['functions'].items():
        out['fn ' + k] = (f.get('n'), f.get('min'), f.get('max'))
    for k, f in rec['isrs'].items():
        out['isr ' + k] = (f['n'], f['min'], f['max'])
    for g in rec['loop']['gaps']:
        out['loop ' + g['back_jump']] = (g['n'], g['min_cycles'], g['max_cycles'])
    for s in (rec.get('masked') or {}).get('sites', []):      # ipb-7: the masked windows are deterministic too
        out['masked ' + s['pc']] = (s['n'], s['min'], s['max'])
    return out


# ------------------------------------------------------------------ plain words
def us(cycles):
    return cycles / float(CLOCK_HZ) * 1e6


def table(rec):
    lines = ['%s - %s' % (rec['variant'], rec['stimulus']['describe']),
             'hex %s (shipped), %s (-fno-inline); image %s; record %s' % (rec['inputs']['shipped_hex_sha256'][:12], rec['inputs']['noinline_hex_sha256'][:12],
                                                                          (rec['tools']['image']['id'] or '')[7:19], rec['record_sha256'][:12]),
             '', '%-44s %6s %9s %9s %10s %12s' % ('atom (-fno-inline, per call)', 'n', 'min', 'max', 'max us', 'cpu max')]
    for k, f in sorted(rec['functions'].items()):
        lines.append('%-44s %6s %9s %9s %10s %12s%s' % (k, f.get('n'), f.get('min', '-') if f.get('n') else '-', f.get('max', '-') if f.get('n') else '-',
                                                       '%.1f' % us(f['max']) if f.get('n') else '-', f.get('cpu_cycles_max', ''), '  ' + f['note'] if f.get('note') else ''))
    if rec.get('uart', {}).get('note'):
        lines.append('USART: ' + rec['uart']['note'] + ' (cpu max = the call without the twin\'s send wait)')
    lines += ['', '%-44s %6s %9s %9s %10s %9s' % ('interrupt (shipped, per event)', 'n', 'min', 'max', 'max us', 'mean')]
    for k, f in sorted(rec['isrs'].items()):
        lines.append('%-44s %6d %9d %9d %10.1f %9.1f' % (k, f['n'], f['min'], f['max'], us(f['max']), f['mean']))
    lp = rec['loop']
    lines += ['', 'main loop (shipped), poll point %s - gap between two visits, by the way back:' % lp['poll_point']]
    for g in lp['gaps']:
        lines.append('  via %s %-6s n=%-5d min %7d  max %7d cycles = %.1f us' % (g['back_jump'], g['op'], g['n'], g['min_cycles'], g['max_cycles'], us(g['max_cycles'])))
    for g in lp['gaps']:
        if g.get('sends_report'):
            lines.append('  the gap via %s sends the report once per frame; at the chip\'s byte time it is %d cycles = %.2f ms (derived)' % (g['back_jump'], g['chip_timed_max_cycles'], us(g['chip_timed_max_cycles']) / 1000.0))
    if lp['worst_gap_cycles']:
        lines.append('  longest gap on the twin %d cycles = %.2f ms; at the chip\'s byte time %.2f ms' % (lp['worst_gap_cycles'], us(lp['worst_gap_cycles']) / 1000.0,
                                                                                             us(lp.get('worst_gap_chip_timed_cycles') or lp['worst_gap_cycles']) / 1000.0))
    mk = rec.get('masked') or {}
    if mk.get('n', -1) >= 0:
        lines += ['', 'masked windows (shipped; SREG.I cleared in main-line code, outside ISRs): n=%d, longest %d cycles = %.2f us at %s in %s' % (
            mk['n'], mk['max'], us(mk['max']), mk.get('max_pc') or '-', mk.get('max_function') or '-')]
        for s in mk.get('sites', [])[:12]:
            lines.append('  cli at %s in %-28s n=%-5d min %5d  max %5d cycles' % (s['pc'], s['function'], s['n'], s['min'], s['max']))
    elif mk:
        lines += ['', 'masked windows: not measured - ' + mk.get('basis', '')]
    s = rec['stimulus']
    lines.append('frames sent: %s, largest %s B, smallest %s B' % (s['frames_sent'], s['frame_bytes_max'], s['frame_bytes_min']))
    return '\n'.join(lines)


def main(argv):
    import argparse
    from board.custom import cycle_records as CR
    ap = argparse.ArgumentParser(prog='pol board cycles')
    ap.add_argument('verb', choices=('measure', 'show', 'verify'))
    ap.add_argument('variant')
    ap.add_argument('--json', action='store_true')
    ap.add_argument('--save', action='store_true', help='write the committed record (board/custom/cycle_records/<variant>.json)')
    a = ap.parse_args(argv)
    try:
        if a.verb == 'show':
            rec = CR.load(a.variant)
            if rec is None:
                print('[REFUSED] no committed cycle record for %s (python3 -m board.custom.cycle_measure measure %s --save)' % (a.variant, a.variant))
                return 3
        else:
            rec = measure(a.variant, progress=None if a.json else (lambda s: print('  ' + s)))
        if a.verb == 'verify':
            old = CR.load(a.variant)
            same = old is not None and counts(old) == counts(rec) and old['inputs']['shipped_hex_sha256'] == rec['inputs']['shipped_hex_sha256']
            print('[ %s ] re-measured %s: %d numbers %s the committed record' % ('OK' if same else 'DIFFERS', a.variant, len(counts(rec)), 'match' if same else 'differ from'))
            return 0 if same else 1
        if a.verb == 'measure' and a.save:
            print('[ OK ] wrote %s' % CR.save(rec))
        print(json.dumps(rec, indent=1) if a.json else table(rec))
    except (CycleRefused, gen.GenRefused, engine_run.EngineRefused) as e:
        print('[REFUSED] %s' % e)
        return 3
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
