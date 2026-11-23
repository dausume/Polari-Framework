"""
@module board.custom.light_c3_run

smp S5, the C3 TWIN RUNNER: build the esp32c3-light config through the shipped pipeline (gen_c3 + build_c3 on the esp engines image) and run the merged flash image in
Espressif's QEMU (`-machine esp32c3`) through the engine `c3-run` (prf-esp-engines/polari_c3_run.py). What this twin IS and IS NOT:

  IS    the real ESP-IDF v5.5.5 + FreeRTOS build for the ESP32-C3 core (RV32IMC), booted by the real ROM/bootloader image in QEMU: the FreeRTOS scheduler and its five tasks, the UART0
        driver (frames out, commands in), the flash (NVS boot counter kept across power cycles), esp_timer.
  IS NOT a pin model. QEMU's esp32c3 GPIO block is a register stub (measured 2026-10-19: gpio_set_level leaves GPIO_OUT at 0, GPIO_IN never moves, no pin lines exist on the machine),
        so a button cannot be pressed or an LED level read from outside. The build under test therefore replaces exactly the pin HAL (light_hal.h, PIN_SHIM=1): the LED level and the
        sense read live in RAM, the button follows a scripted falling-edge source from the flash params. The tasks, the struct and the frames are the same code as the chip HAL build.
  NO C3 BOARD is on the bench: nothing here is a chip result.

pt-4 (PIN_TWIN_PLAN.md), THE PIN MODEL: an esp engines image that holds the `polari-block` QEMU build (c3-run `--pins`) gives the machine real pads - the GPIO + IO_MUX registers
of Polari's own chip rows (board.custom.sim_layout), a level per pad, the GPIO interrupt. On it the build under test is the CHIP HAL (PIN_SHIM 0), the image a chip is flashed
with: a press is a stamped level on the button pad, the LED is its pad's level on the pin channel, the LED-to-sense jumper is a board wire. `pin_model()` says whether the engine
here has it; a run of a PIN_SHIM 0 build uses it, a run of a PIN_SHIM 1 build never does. Still not a chip: the pads are a model (no voltages, no timing of the pad drivers).

Stimuli: the button script is in the flash params (a[0..5], see light_hal.h); commands go in over UART0 RX paced by the firmware's own `@TEL n` trace lines (virtual time; see the
engine). Reads: the UART0 frames (decoded by the independent Python reference codec, as the UNO twin runs do) and the trace (`@LED <ms> <level>` = a write of the LED pin);
on the pin model the pin channel (`@<virtual ns> <pad> 0|1|z`, one line per pad level change).
"""
import json
import re
import struct

VARIANT = 'esp32c3-light'
SIM_CHIP = 'esp32c3-qemu'         # board.custom.sim_layout's name for the chip rows the pin model is exported from
PARAMS_OFFSET = 0x110000          # partitions.csv `polari` data partition
PARAMS_MAGIC = 0x33435350         # polari_c3.h
ICOUNT_SHIFT = 3                  # Espressif's documented value (125 M instructions per virtual second); the same as the sc-3 runs
N_PRESSES = 3
FIRST_MS, GAP_MS, HOLD_MS = 300, 150, 80      # 150 ms apart = 5 x the 30 ms lockout; 80 ms held
WINDOW_MS = FIRST_MS + N_PRESSES * GAP_MS + 400
BUTTON_GPIO, WRONG_GPIO = 3, 7                # the press goes to GPIO7 (a JTAG pad, not wired to the button) in the wrong-pin control
BOUND_MS = 100                                # the initialization Purpose's bound: one 10 Hz report period


def params(window_ms=0, presses=0, press_gpio=BUTTON_GPIO, jumper=1):
    """polari_c3.h polari_params_t: magic, version, seed, window_ms, rounds, a[8] (light_hal.h)."""
    a = [FIRST_MS, GAP_MS, HOLD_MS, presses, press_gpio, jumper, 0, 0]
    return struct.pack('<IIIII8i', PARAMS_MAGIC, 1, 0, window_ms, 0, *a)


def engine_ready():
    """(ready, why). c3-run is a batch engine - files in, files out, nothing attached - so a worker reached over the ladder (the ESP_ENGINES_URL knob, or the isle's
    `esp` binding) proves the light as well as a local one does. (The UNO's light twin is different: its bridge attaches to a process on this device, so it stays local.)
    Until release 93 this said no to a remote worker, and on the isle - where the engines are a store app on another device - the C3 light could not be proven at all."""
    from board.custom import board_engines as be
    where = be.resolve('c3-run')
    return where['how'] in ('local-binary', be.LOCAL_IMAGE, be.REMOTE), where['why']


_FEATURES = {}
REBUILD = 'docker compose -p esp-engines -f docker-compose.esp-engines.yml build   (from polari-rf-node/; prf-esp-engines/README.md)'


def engine_stale():
    """'' when the c3-run engine has the options the host-driven runs need (smp S5: --rx-plan, --boots), else why - an image built before smp S5 refuses them as
    `unknown option`, and every command / reboot run would come back with 0 frames (seen 2026-10-29: a 3-week-old prf-esp-engines:noble). Asked once per process:
    run with no arguments, the engine prints its usage text."""
    if 'why' not in _FEATURES:
        from board.custom import engine_run
        r = engine_run.run('c3-run', [], {}, timeout=60)
        usage = (r.get('stdout') or '') + (r.get('stderr') or '')
        missing = [o for o in ('--rx-plan', '--boots') if o not in usage]
        _FEATURES['why'] = ('the c3-run engine (%s) does not offer %s: its image predates smp S5 - rebuild it: %s' % (r.get('how', '?'), ', '.join(missing), REBUILD)
                            if missing and usage else '')
        _FEATURES['pins'] = ('' if '--pins' in usage and '--wires' in usage else
                             'the c3-run engine (%s) has no pin model (no --pins / --wires): its image predates pt-4 - rebuild it: %s' % (r.get('how', '?'), REBUILD))
    return _FEATURES['why']


def pin_model():
    """'' when the c3-run engine here runs the pin model (pt-4: the polari-block QEMU, `--pins` + `--wires`), else why not. Asked with engine_stale(), once per process."""
    engine_stale()
    return _FEATURES['pins']


def knobs_of(row):
    """The light knobs a built row was generated with (its repro record): the three pads and pin_shim."""
    from board.custom import variants_c3 as V3
    k = (json.loads(row.get('repro_json') or '{}').get('knobs') or {})
    return {n: k.get(n, V3.LIGHT_KNOBS[n]) for n in ('led_pin', 'sense_pin', 'button_pin', 'pin_shim')}


def on_pads(row):
    """True when `row` is the chip-HAL build (PIN_SHIM 0), whose runs go to the pin model."""
    return knobs_of(row)['pin_shim'] == 0


def stimulus(presses):
    """The pin channel's input file for [(pad, at_ms, hold_ms)]: the pad pulled low at `at`, released (z: the firmware's pull-up takes it back) after `hold`."""
    lines = []
    for pad, at, hold in presses:
        lines += ['@%d %d 0' % (at * 1000000, pad), '@%d %d z' % ((at + hold) * 1000000, pad)]
    return '\n'.join(lines) + '\n' if lines else ''


def pads_for(row, press_gpio=None, n=0, jumper=1):
    """The `pads` argument of run() for a chip-HAL row (None for a shim row): the LED-to-sense jumper as a board wire, `n` presses on `press_gpio`."""
    if not on_pads(row):
        return None
    k = knobs_of(row)
    return {'led': k['led_pin'], 'wires': '%d-%d' % (k['led_pin'], k['sense_pin']) if jumper else '',
            'stimulus': stimulus([(press_gpio, FIRST_MS + i * GAP_MS, HOLD_MS) for i in range(n)]) if press_gpio is not None else ''}


def build(work, variant=VARIANT, **knobs):
    from board.custom import build_c3, gen_c3
    gen_c3.gen_c3(variant, work, **knobs)
    return build_c3.build('c3', work)


def run(row, par, plan=None, files=None, boots=1, until='@END', max_wall=120, pads=None):
    """-> {'ok', 'states', 'events', 'bad_crc', 'trace', 'run', 'pin' (the LED pin's changes [(ms, level)]), 'how'} - one engine run of the built image.
    `pads` (pads_for(row)) puts the run on the pin model: {'led', 'wires', 'stimulus'}; the result then also carries 'pad_lines' (the pin channel) and 'pin_dump'."""
    from board.custom import engine_run
    sent = {'flash_image.bin': open(row['image_path'], 'rb').read()}
    args = ['flash_image.bin', '--params', par.hex(), '--params-offset', '0x%x' % PARAMS_OFFSET, '--icount', str(ICOUNT_SHIFT), '--max-wall', str(max_wall), '--until', until]
    if pads is not None:
        from board.custom import sim_layout as SL
        sent['layout.json'] = SL.text(SL.layout(SIM_CHIP)).encode()
        args += ['--pins', 'layout.json']
        if pads.get('stimulus'):
            sent['pins-in.txt'] = pads['stimulus'].encode()
            args += ['--pins-in', 'pins-in.txt']
        if pads.get('wires'):
            args += ['--wires', pads['wires']]
    if plan:
        sent['rx_plan.json'] = json.dumps(plan).encode()
        for k, v in (files or {}).items():
            sent[k] = v
        args += ['--rx-plan', 'rx_plan.json']
    if boots > 1:
        args += ['--boots', str(boots)]
    r = engine_run.run('c3-run', args, sent, timeout=max_wall * boots + 60)
    f = r.get('files') or {}
    trace = (f.get('trace.log') or b'').decode('utf-8', 'replace')
    states, events, bad = decode(f.get('uart0.bin') or b'')
    said = (r.get('stdout') or '') + (r.get('stderr') or '')
    unknown = 'unknown option' in said or (pads is not None and 'pins.log' not in f)       # a pin run with no pin channel never passes as a stub run
    pad_lines = (f.get('pins.log') or b'').decode('utf-8', 'replace')
    return {'ok': (bool(r.get('ok')) or '@END' in trace or bool(plan)) and not unknown, 'states': states, 'events': events, 'bad_crc': bad, 'trace': trace,
            'run': json.loads(f.get('run.json', b'{}') or b'{}'), 'pin': pin_writes(trace) if pads is None else pad_changes(pad_lines, pads['led']), 'how': r['how'],
            'stderr': (r.get('stderr') or r.get('stdout') or '')[-400:], 'stale_image': unknown, 'pad_lines': pad_lines,
            'pin_dump': (f.get('pb-dump.txt') or b'').decode('utf-8', 'replace'), 'on_pads': pads is not None}


def decode(uart0):
    from board.custom import light_variant_twin as LVT
    return LVT.decode(uart0)


def pin_writes(trace):
    return [(int(m.group(1)), int(m.group(2))) for m in re.finditer(r'^@LED (\d+) (\d)$', trace, re.M)]


def pad_levels(pad_lines, pad):
    """Per boot, the levels one pad took on the pin channel: [[(ns, '0'|'1'|'z'), ...], ...] (a `@POWER-CYCLE` line starts the next boot)."""
    boots = [[]]
    for line in pad_lines.splitlines():
        if line.startswith('@POWER-CYCLE'):
            boots.append([])
            continue
        m = re.fullmatch(r'@(\d+) (\d+) ([01z])', line.strip())
        if m and int(m.group(2)) == pad:
            boots[-1].append((int(m.group(1)), m.group(3)))
    return boots


def pad_changes(pad_lines, pad):
    """[(ms, level)] - what the LED pad did AFTER the firmware first drove it (hal_pins_init makes it an output, low): the same list the shim's `@LED` lines give,
    read off the pad instead of the firmware's own word. A pad that goes back to undriven (z) is kept as -1 so no judge can read it as a level."""
    out = []
    for boot in pad_levels(pad_lines, pad):
        driven = [i for i, (_ns, lv) in enumerate(boot) if lv != 'z']
        for ns, lv in (boot[driven[0] + 1:] if driven else []):
            out.append((ns // 1000000, -1 if lv == 'z' else int(lv)))
    return out


def led_pin_high(res):
    """The LED pin as last written (it starts low): the shim's last `@LED` line, or on the pin model the LED pad's last level."""
    return bool(res['pin'][-1][1] == 1) if res['pin'] else False


def press_run(row, n=N_PRESSES, press_gpio=BUTTON_GPIO, jumper=1):
    """`n` presses: the shim build follows its script from the params; the chip-HAL build gets them as stamped levels on the pad (its params script stays off)."""
    if on_pads(row):
        return run(row, params(WINDOW_MS, 0, press_gpio, jumper), pads=pads_for(row, press_gpio, n, jumper))
    return run(row, params(WINDOW_MS, n, press_gpio, jumper))


def command_run(row, frames, jumper=1):
    """Send each frame in turn, `@TEL` lines apart (5 before the first, 6 between), then 5 more reports; the pacing is the firmware's own virtual time."""
    files = {'cmd%d.bin' % i: fr for i, fr in enumerate(frames)}
    plan = [{'file': 'cmd%d.bin' % i, 'after': '@TEL', 'count': 5 if i == 0 else 6} for i in range(len(frames))]
    plan.append({'file': '', 'after': '@TEL', 'count': 5, 'end': True})
    return run(row, params(0, 0, BUTTON_GPIO, jumper), plan, files, until='NONE', pads=pads_for(row, jumper=jumper))


def reboot_run(row):
    """Two power cycles on the same flash (the NVS boot counter is kept): -> the runs' frames, each boot's first 100 ms of app time."""
    plan = [{'file': '', 'after': '@TEL', 'count': 3, 'end': True}]
    return run(row, params(0, 0), plan, boots=2, until='NONE', pads=pads_for(row))


def first_reports(states, bound=BOUND_MS):
    """Per boot (the `seq` restarts at 0), the frames the app sent within `bound` ms of its own start (esp_timer 0; the ROM and 2nd-stage bootloader time before it is NOT counted)."""
    boots, cur, prev = [], [], -1
    for f in states:
        s = int(f.get('seq') or 0)
        if s <= prev and cur:
            boots.append(cur)
            cur = []
        cur.append(f)
        prev = s
    if cur:
        boots.append(cur)
    return [[f for f in b if int(f.get('uptime_ms') or 0) <= bound] for b in boots]
