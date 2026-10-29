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

Stimuli: the button script is in the flash params (a[0..5], see light_hal.h); commands go in over UART0 RX paced by the firmware's own `@TEL n` trace lines (virtual time; see the
engine). Reads: the UART0 frames (decoded by the independent Python reference codec, as the UNO twin runs do) and the trace (`@LED <ms> <level>` = a write of the LED pin).
"""
import json
import re
import struct

VARIANT = 'esp32c3-light'
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
    from board.custom import board_engines as be
    where = be.resolve('c3-run')
    return where['how'] in ('local-binary', be.LOCAL_IMAGE), where['why']


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
    return _FEATURES['why']


def build(work, variant=VARIANT, **knobs):
    from board.custom import build_c3, gen_c3
    gen_c3.gen_c3(variant, work, **knobs)
    return build_c3.build('c3', work)


def run(row, par, plan=None, files=None, boots=1, until='@END', max_wall=120):
    """-> {'ok', 'states', 'events', 'bad_crc', 'trace', 'run', 'pin' (the LED pin writes [(ms, level)]), 'how'} - one engine run of the built image."""
    from board.custom import engine_run
    sent = {'flash_image.bin': open(row['image_path'], 'rb').read()}
    args = ['flash_image.bin', '--params', par.hex(), '--params-offset', '0x%x' % PARAMS_OFFSET, '--icount', str(ICOUNT_SHIFT), '--max-wall', str(max_wall), '--until', until]
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
    unknown = 'unknown option' in (r.get('stdout') or '') + (r.get('stderr') or '')
    return {'ok': (bool(r.get('ok')) or '@END' in trace or bool(plan)) and not unknown, 'states': states, 'events': events, 'bad_crc': bad, 'trace': trace,
            'run': json.loads(f.get('run.json', b'{}') or b'{}'), 'pin': pin_writes(trace), 'how': r['how'], 'stderr': (r.get('stderr') or r.get('stdout') or '')[-400:],
            'stale_image': unknown}


def decode(uart0):
    from board.custom import light_variant_twin as LVT
    return LVT.decode(uart0)


def pin_writes(trace):
    return [(int(m.group(1)), int(m.group(2))) for m in re.finditer(r'^@LED (\d+) (\d)$', trace, re.M)]


def led_pin_high(res):
    """The LED pin as the shim last wrote it (it starts low); None for a run of the chip HAL, which logs no pin write."""
    return bool(res['pin'][-1][1]) if res['pin'] else False


def press_run(row, n=N_PRESSES, press_gpio=BUTTON_GPIO, jumper=1):
    return run(row, params(WINDOW_MS, n, press_gpio, jumper))


def command_run(row, frames, jumper=1):
    """Send each frame in turn, `@TEL` lines apart (5 before the first, 6 between), then 5 more reports; the pacing is the firmware's own virtual time."""
    files = {'cmd%d.bin' % i: fr for i, fr in enumerate(frames)}
    plan = [{'file': 'cmd%d.bin' % i, 'after': '@TEL', 'count': 5 if i == 0 else 6} for i in range(len(frames))]
    plan.append({'file': '', 'after': '@TEL', 'count': 5, 'end': True})
    return run(row, params(0, 0, BUTTON_GPIO, jumper), plan, files, until='NONE')


def reboot_run(row):
    """Two power cycles on the same flash (the NVS boot counter is kept): -> the runs' frames, each boot's first 100 ms of app time."""
    plan = [{'file': '', 'after': '@TEL', 'count': 3, 'end': True}]
    return run(row, params(0, 0), plan, boots=2, until='NONE')


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
