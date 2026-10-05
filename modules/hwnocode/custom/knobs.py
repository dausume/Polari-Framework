"""
@module hwnocode.custom.knobs

THE `firmware_runtime` KNOB (HARDWARE_NOCODE_PLAN.md §2c, §3; D-hn-3 ruled "suggest only"): the person picks bare-c | freertos |
esp-idf | zephyr; Polari never pre-selects and never picks silently (`pol hwnocode suggest` shows its suggestion with evidence,
nothing more). hn-0 renders ONE target — bare C, cmod-glue's main loop + ISRs — and refuses every other value with the reason:

  auto       refused — D-hn-3: there is no automatic pick; the suggestion is shown, the person chooses
  an RTOS    on an S-class board (UNO: 2 KB RAM) refused for the RAM (plan §3 rule 1: a kernel + per-task stacks do not fit);
             elsewhere refused as not-yet-a-graph-target (the task/queue/mutex glue target is hn-5; Zephyr on the C3, D-hn-5;
             ESP-IDF runs today only as sc-3's hand-written template, not from a graph)

THE `HARDWARE_MODE` KNOB (his 2026-10-05 message: "a configuration based conditional... digital twin route when the
configuration is in one mode, and [hardware] route in the other case"): same idiom as every other env-var knob in this
forest (board.custom.installer.TWIN_LINK/TWIN_TCP, board.custom.twin_pty.DEFAULT_LINK) — an environment variable, read
once at import, with a sane default; never silently coerced to something outside its two values.
"""
import os

RUNTIMES = ('bare-c', 'freertos', 'esp-idf', 'zephyr')
SUPPORTED = ('bare-c',)

HARDWARE_MODES = ('digital-twin', 'hardware')


def hardware_mode():
    """'digital-twin' (default) | 'hardware' — HWNOCODE_HARDWARE_MODE env var. An unrecognized value is treated as the
    default and never raises (a knob refuses loud only where it picks something consequential; this one just routes)."""
    v = str(os.environ.get('HWNOCODE_HARDWARE_MODE', 'digital-twin')).strip() or 'digital-twin'
    return v if v in HARDWARE_MODES else 'digital-twin'


def memory_class(board_row):
    """'S' | 'M' | 'L' | '' from the register's device class (MCU-S …) else ram_kb (S ≤ 32 KB, M ≤ 512 KB) — the register's
    own classes (AI-Notes/designs/HARDWARE_CAPABILITY_REGISTER.md)."""
    dc = str((board_row or {}).get('device_class', '') or '')
    if dc.upper().endswith('-S'):
        return 'S'
    if dc.upper().endswith('-M'):
        return 'M'
    if dc.upper().endswith('-L'):
        return 'L'
    ram = int((board_row or {}).get('ram_kb') or 0)
    if not ram:
        return ''
    return 'S' if ram <= 32 else 'M' if ram <= 512 else 'L'


def check_runtime(runtime, board_row=None):
    """(ok, reason) for the knob's value on this board."""
    r = str(runtime or 'bare-c').strip()
    board = (board_row or {}).get('name', 'the board')
    if r == 'bare-c':
        return True, 'bare C: cmod-glue\'s target (one main loop + ISRs, no kernel) — what hn-0 renders'
    if r == 'auto':
        return False, ('auto is refused: D-hn-3 ruled SUGGEST ONLY — Polari never picks the runtime; choose bare-c | freertos | '
                       'esp-idf | zephyr (`pol hwnocode suggest <solution>` shows the suggestion and its evidence)')
    if r not in RUNTIMES:
        return False, 'firmware_runtime %r is not one of %s' % (r, ' | '.join(RUNTIMES))
    if memory_class(board_row) == 'S':
        return False, ('%s on %s is refused: an S-class board (%s RAM) — a kernel plus per-task stacks do not fit (plan §3 rule 1); '
                       'bare-c is the only runtime for it' % (r, board, (board_row or {}).get('flash_sram') or '%s KB' % (board_row or {}).get('ram_kb')))
    why = {'freertos': 'the RTOS glue target (task / queue / mutex nodes) is not built — hn-5',
           'esp-idf': 'ESP-IDF runs today as sc-3\'s hand-written C3 template only; a graph does not render to it yet (hn-5)',
           'zephyr': 'the Zephyr glue target is hn-5 (D-hn-5: on the ESP32-C3 first)'}[r]
    return False, '%s is refused in hn-0: %s — hn-0 renders bare-c only' % (r, why)
