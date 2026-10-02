"""
@module firmwarefaults.custom.scenarios

THE SCENARIOS AS ROWS (FIRMWARE_SCENARIO_PLAN.md §3): scenario 1 (the torn millis read — the ring buffer cannot tear,
the four-load g_ms read does) and 1b (RX_RING > 256 — now a refused build), their ordered steps, the step-kind
catalogue (which kinds the harness can force today, and why the rest cannot yet), and the two SCENARIO VARIANTS of the
UNO template they build (FirmwareVariant rows, board's class; seeded here because they exist only for scenarios):

  uno-sim-rig-torn     the whole rig with HAL_MILLIS_ATOMIC 0 — the BEFORE build of scenario 1 (D-sc-7: a variant knob,
                       never a patched binary; it is a real FirmwareBuild with its own sha)
  uno-sim-rig-ring512  the whole rig with RX_RING 512 — refused by hal.c's _Static_assert (scenario 1b's static guard)

A step names its PC as a SYMBOL plus a disassembly pattern (`lds-sequence` of a variable, between load i and i+1), so
every build re-resolves the address from its own ELF (custom/disasm.py) — never a hard-coded address.
"""
import json

J = json.dumps

#: kind → (forcible on the avr-twin today, the harness flag or the reason it cannot yet)
STEP_KINDS = {
    'irq-at-pc': (True, '--irq-at pc=0x…,vec=N[,when=…] (twin_forcing.c: raise + service at the instruction boundary)'),
    'irq-at-cycle': (True, '--irq-at cycle=N,vec=N (raised at the first boundary >= N; the core services it)'),
    'corrupt-word': (True, '--poke 0xADDR/W=0xVAL@CYCLE (avr_core_watch_write per byte)'),
    'drop-nth-frame': (False, 'needs --drop-frame on the TX/RX path and a request/ack variant to drop from (sc-1)'),
    'flip-bit-at-cycle': (False, '--poke writes a value; an XOR of one bit at a cycle is sc-1'),
    'uart-ber': (False, 'needs --uart-ber p with seeded draws on the RX feed (sc-1, scenario 4)'),
    'hold-lock-order': (False, 'the UNO has no RTOS and no locks; needs the ESP32-C3 FreeRTOS twin (sc-3, D-sc-4)'),
    'clock-skew': (False, 'one simavr process runs one clock; skew needs two clocked parties (Renode, sc-3)'),
}
FORCIBLE_KINDS = tuple(k for k, (ok, _) in STEP_KINDS.items() if ok)

TIMER2_COMPA = 7   # verified: avr-gcc names the tick ISR __vector_7 (plan §2a); the runner re-checks the ELF has it
USART_RX = 18      # ATmega328P USART_RX_vect = __vector_18 (the runner re-checks the ELF has it; plan §2a marked it unverified)


def _s(name, title, description, before, after, fault_class, fault, breaks, technique, expected, kind, seconds, notes='', status='runnable'):
    return {'name': name, 'title': title, 'description': description, 'target_board': 'arduino-uno-r3', 'before_variant': before,
            'after_variant': after, 'fault_class': fault_class, 'fault': fault, 'breaks': breaks, 'technique': technique,
            'expected_observable': expected, 'observable_kind': kind, 'window_cycles': int(seconds * 16000000), 'run_seconds': seconds,
            'seed_policy': 'fixed', 'seed': 0, 'simulator': 'avr-twin', 'status': status,
            'provenance': 'sc-0 seed (FIRMWARE_SCENARIO_PLAN.md §3)', 'notes': notes}


SEED_SCENARIOS = [
    _s('torn-millis-read', 'Scenario 1 — the torn tick read on the UNO',
       'Force the 1 ms tick ISR (TIMER2_COMPA, vector 7) between the FIRST and SECOND `lds` of g_ms in hal_millis, at the moment '
       'g_ms\'s low byte is 0xFF: the bare read (uno-sim-rig-torn) combines byte 0 = 0xFF with bytes 1..3 of 0x00000100 → 511 '
       'instead of 255/256. The shipped build (ATOMIC_BLOCK) keeps the forced interrupt pending through `cli` and takes it after '
       '`out SREG`.', 'uno-sim-rig-torn', 'uno-sim-rig', 'TornReadFault', 'torn-read-g-ms', 'g-ms-read-atomic', 'atomic-block',
       'BEFORE: uptime_ms goes backwards in the decoded frames (… 200, 511, 400 …) while every CRC passes → refuted. AFTER: monotone → '
       'witnessed.', 'uptime-monotone', 0.6,
       notes='The plan\'s optional first step (corrupt-word g_ms = 0xFE at 20 ms) is NOT used: g_ms reaches 0xFF by itself at 255 ms '
             '(4.08 M cycles, ~0.1 s of simulation), and the poke would put its own time jump into the frames. The forced interrupt adds '
             'ONE extra tick (+1 ms), recorded on the run; align-at-pc (no extra tick) is sc-1.'),
    _s('rx-ring-over-256', 'Scenario 1b — an RX ring past 256 slots',
       'A variant with RX_RING 512 would need 16-bit ring indices — then `rx_tail == rx_head` in hal_rx_pop is two loads and DOES tear. '
       'With hal.c\'s uint8_t indices it would silently use 256 of its 512 slots. Since sc-0 hal.c refuses the build '
       '(_Static_assert: the Technique static-guard), so the vulnerable firmware cannot exist.', 'uno-sim-rig-ring512', '',
       'BufferOverrunFault', 'rx-ring-over-256', 'rx-index-single-load', 'static-guard',
       'the build is REFUSED with the static assertion\'s message → inapplicable (no such firmware); a build that went through would be '
       'undetermined until sc-1 forces the head read', 'build-refused', 0.0,
       notes='the run is a build attempt, not a twin run; the claim is inapplicable — not refuted, not witnessed'),
]


def _step(scenario, order, kind, args, condition=None, notes=''):
    ok, why = STEP_KINDS[kind]
    return {'name': '%s#%d' % (scenario, order), 'scenario': scenario, 'order': order, 'kind': kind, 'args_json': J(args),
            'condition_json': J(condition or {}), 'forcible': ok, 'not_forcible_reason': '' if ok else why, 'notes': notes}


SEED_STEPS = [
    _step('torn-millis-read', 1, 'irq-at-pc',
          {'symbol': 'hal_millis', 'pattern': 'lds-sequence', 'of': 'g_ms', 'before_load': 2, 'vec': TIMER2_COMPA,
           'vector_name': 'TIMER2_COMPA', 'shots': 1},
          {'symbol': 'g_ms', 'width': 4, 'mask': 255, 'value': 255},
          notes='the ISR runs with the 2nd lds as its return address: byte 0 was read as 0xFF, the ISR carries into byte 1'),
    _step('rx-ring-over-256', 1, 'irq-at-pc',
          {'symbol': 'hal_rx_pop', 'pattern': 'lds-sequence', 'of': 'rx_head', 'before_load': 2, 'vec': USART_RX,
           'vector_name': 'USART_RX', 'shots': 1}, {},
          notes='would split the 16-bit head read; with the static guard there is no build to force it in'),
]


def _variant(name, title, purpose, flags, watch, notes):
    from board.custom.variants import SEED_FIRMWARE_VARIANTS
    base = next(v for v in SEED_FIRMWARE_VARIANTS if v['name'] == 'uno-sim-rig')
    return dict(base, name=name, title=title, purpose=purpose, build_flags_json=J(flags), what_to_watch=watch, origin='seeded', notes=notes)


def scenario_variants():
    """The two scenario variants (FirmwareVariant rows) — built lazily so importing this file never needs board."""
    return [
        _variant('uno-sim-rig-torn', 'SCENARIO ONLY — the whole rig with the bare (torn) millis read',
                 'sc-0 scenario torn-millis-read, the BEFORE build: HAL_MILLIS_ATOMIC 0 reads the 4-byte tick g_ms without masking '
                 'interrupts, so a tick between the loads tears it. It exists to show the fault on the twin — never install it on a '
                 'board you rely on.', ['HAL_MILLIS_ATOMIC=0'],
                 'uptime_ms jumps 256 ms ahead and falls back (…200, 511, 400…) when the tick lands inside hal_millis — rarely by itself, '
                 'every time when `pol faults run torn-millis-read --before` forces it.',
                 'firmwarefaults (sc-0): a scenario variant — the knob is HAL_MILLIS_ATOMIC (hal.c), default 1'),
        _variant('uno-sim-rig-ring512', 'SCENARIO ONLY — RX_RING 512 (refused by the static guard)',
                 'sc-0 scenario rx-ring-over-256: a 512-slot RX ring cannot be indexed by hal.c\'s uint8_t indices; hal.c\'s '
                 '_Static_assert refuses the build, which is the point.', ['RX_RING=512'],
                 '`pol board build` refuses it with the static assertion\'s message.',
                 'firmwarefaults (sc-0): expected to be refused at compile time'),
    ]


def steps_of(scenario, steps=None):
    return sorted([s for s in (steps or SEED_STEPS) if s['scenario'] == scenario], key=lambda s: s['order'])


def runnable(scenario, steps=None):
    """A scenario is runnable only when EVERY step's kind is forcible today (the selftest pins it)."""
    st = steps_of(scenario['name'] if isinstance(scenario, dict) else scenario, steps)
    return all(s['kind'] in FORCIBLE_KINDS for s in st)


def find(name, rows=None):
    for s in (rows or SEED_SCENARIOS):
        d = s if isinstance(s, dict) else {k: getattr(s, k, '') for k in SEED_SCENARIOS[0]}
        if d.get('name') == name:
            return dict(d)
    return None
