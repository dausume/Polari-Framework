"""
@module firmwarefaults.custom.wdt_order

hal-3b step 1 (econ's review, 2026-11-13): the watchdog's ORDER RULE shown on the twin, not argued. DS40002061B §11.9.2 p.64:
"WDE is overridden by WDRF in MCUSR ... To clear WDE, WDRF must be cleared first." One tiny program in two arms, built from
the GENERATED HAL units (hal.custom.generate, peripheral WDT) - nothing hand-written about the registers:

  power-on      WDRF 0  -> HAL_WDT_ENABLE(0) (WDTO_15MS) and hang, never kicked -> ONE deliberate watchdog reset
  after it      WDRF 1  -> .init3 disables, main hangs, never kicked:
     arm A (the HAL's order)   HAL_WDT_DISABLE: MCUSR = 0x07 (WDRF 0, the other w0c flags written 1 = kept), then wdt_disable()
                               -> stays off: exactly 1 reset in a run longer than the longest time-out (WDTO_8S)
     arm B (the order broken)  wdt_disable() alone, WDRF still 1 -> WDE stays on -> a reset every time-out (a reset loop)

The twin's own reset log is the evidence (its `resets` list holds at most 32 entries, so arm B reads ">= 32", said so).
OWED (econ, 2026-11-13; both are polari-avr-twin engine changes, i.e. an image rebuild): (1) a full `resets_total` counter beside the
32-entry log, so arm B asserts its exact count (~560 in 9 s at the 16 ms period) instead of a lower bound; (2) a plain `--report-resets`
flag (or the reset log always printed), so this probe no longer needs the never-firing --jump-at that turns the scenario report on.
  run(seconds)  -> {'A': {...}, 'B': {...}, 'seconds', 'cite'}
"""
import json

CITE = 'DS40002061B §11.9.2 WDTCSR p.64 (WDRF overrides WDE); §11.8 p.61 (clear WDRF and WDE in the initialization routine)'
ARMS = {'A': 'HAL_WDT_DISABLE_WDT();', 'B': 'wdt_disable();'}
SRC = r'''
#include "probe_hal.h"
uint8_t boot_flags __attribute__((section(".noinit")));
void early(void) __attribute__((naked, used, section(".init3")));
void early(void) { boot_flags = MCUSR; %s }
int main(void) {
    if (!(boot_flags & _BV(WDRF))) { HAL_WDT_ENABLE_WDT(0); }   /* power-on: the shortest time-out, never kicked */
    for (;;) { }                                               /* after the watchdog reset: disabled at .init3, never kicked */
}
'''


def header():
    from hal.custom import generate as G
    units = [G.unit('atmega328p', op, 'WDT')['unit'] for op in ('wdt.enable', 'wdt.disable')]
    bad = [u['key'] for u in units if u['status'] != 'resolved']
    if bad:
        raise RuntimeError('the HAL does not resolve %s' % ', '.join(bad))
    return '#include <avr/io.h>\n#include <avr/wdt.h>\n#include <stdint.h>\n' + '\n'.join(u['c_text'] for u in units) + '\n'


def run(seconds=9.0):
    from board.custom import build as B, engine_run
    from firmwarefaults.custom import harness
    hdr = header()
    out = {'seconds': seconds, 'cite': CITE}
    for arm, dis in ARMS.items():
        files = {'probe_hal.h': hdr.encode(), 'main.c': (SRC % dis).encode()}
        r = engine_run.run('avr-gcc', B.CFLAGS + B.LDFLAGS + ['-o', 'firmware.elf', 'main.c'], files)
        if not r.get('ok') or 'firmware.elf' not in (r.get('files') or {}):
            out[arm] = {'ok': False, 'why': 'build failed: %s' % (r.get('stderr') or '')[-300:]}
            continue
        h = engine_run.run('avr-objcopy', ['-O', 'ihex', '-R', '.eeprom', 'firmware.elf', 'firmware.hex'], {'firmware.elf': r['files']['firmware.elf']})
        # --jump-at beyond the end never fires; it turns the twin's scenario report (and so its reset log) on
        t = harness.run(['--hex', 'firmware.hex', '--mcu', 'atmega328p', '--freq', '16000000', '--free', '--seconds', '%g' % seconds,
                         '--status-ms', '0', '--uart-out', harness.UART, '--seed', '0', '--jump-at', 'cycle=%d,pc=0x0' % int((seconds + 1) * 16e6)],
                        h['files']['firmware.hex'], timeout=1200)
        rs = (t.get('final') or {}).get('resets') or {}
        lst = rs.get('list') or []
        out[arm] = {'ok': bool(t.get('ok')), 'resets': rs.get('n'), 'wdrf_all': all(x.get('wdrf') for x in lst),
                    'cycles': [x['cycle'] for x in lst], 'capped': len(lst) >= 32}
    return out


if __name__ == '__main__':
    print(json.dumps(run(), indent=1))
