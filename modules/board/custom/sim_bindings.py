"""
@module board.custom.sim_bindings

pt-1a (AI-Notes/plans/PIN_TWIN_PLAN.md §2a, the user 2026-11-13: "build our own clean data structure for later on when we are building out our own
custom risc-v chips which we will need to plug into simulations. We can layer and make an overlay/interface for going between them so they act like
one device"): the behaviour and simulation-binding rows (layers 2 and 3). Layer 1, what the chip IS, stays the existing rows (SocDefinition,
Peripheral, Register, RegisterField, RegisterAccessKind); nothing here re-types a register fact.

  BLOCK_BEHAVIOURS   -> BlockBehaviour rows: `pinbank` (the roles it needs, the pin-level rule in words)
  SIMULATED_CHIPS    -> SimulatedChip rows: the C3 in Espressif's QEMU fork
  SIM_OVERLAYS       -> SimOverlay rows: per address span, who models it (vendor / overlay / native) and why
  chip(name) / overlays(chip) / behaviour(name)

The role names are hal.custom.soc_rules RULES[soc]['roles'] keys: the firmware generator and the simulator read ONE binding per chip.
"""
import json

from board.custom import registers_esp32c3 as R3

_FORK = 'Espressif QEMU fork esp-develop-9.2.2-20260417 (commit 40edccac), hw/riscv/esp32c3.c read 2026-11-13'

#: the pin-level rule (PIN_TWIN_PLAN.md §2), the rule the polari-block device runs for a `pinbank`
PINBANK_RULE = ('A pad DRIVES when its pad function is one of THAT PAD\'s GPIO functions (pad_function: on the C3 function 1 on every pad, and '
                'function 0 too on GPIO0-3, 8-11, 18, 19 - TRM Table 5.12-1 p.174, econ 2026-11-13; MCU_SEL resets to 0, so firmware that never '
                'writes it still drives GPIO8), its output route is the plain GPIO output (output_route = gpio_out) and its output is enabled. With '
                'output_route = gpio_out the enable is the pad\'s GPIO_ENABLE bit WHATEVER output_enable_source says (an inference from ESP-IDF\'s '
                'working path - gpio_ll_matrix_out_default writes OUT_SEL_CFG = 128, so OEN_SEL = 0, and the LED drives on silicon; TRM §5.5.3 p.165 '
                'names only OUT_SEL = 128 + GPIO_OUT - not the TRM\'s own words); for a peripheral route, output_enable_source picks GPIO_ENABLE '
                'or the peripheral. A driving pad drives the output bit; with output_driver = open_drain it drives only a 0 and a 1 releases the '
                'pad. A pad that does not drive takes the level driven from outside, else its pull (pull_up / pull_down), else it floats (z). The '
                'input register reads level AND pad_input_enable. An edge of the kind edge_sense names sets the pad\'s status bit (edge_flag clears '
                'it); the CPU\'s interrupt status reads status AND edge_mask (C3: GPIO_PCPU_INT = STATUS AND INT_ENA bit 0, the register ESP-IDF\'s '
                'ISR reads), and the interrupt line to interrupt_source is the OR of that CPU status, not of the raw status bits. A value the '
                'behaviour does not model (C3: INT_TYPE 4 / 5 level triggers, OUT_INV_SEL / OEN_INV_SEL = 1) is logged by the device as an '
                'unmodelled value, never silently read as 0.')

BLOCK_BEHAVIOURS = [
    {'name': 'pinbank', 'title': 'a bank of pads: output, enable, input, pulls, pad function, output route, open drain, pin interrupts',
     'roles_json': json.dumps({'modelled': ['output', 'direction', 'input', 'pull_up', 'pull_down', 'pad_input_enable', 'pad_function',
                                            'output_route', 'output_enable_source', 'output_driver', 'edge_sense', 'edge_mask', 'edge_flag'],
                               'values': ['interrupt_source']}),
     'rules': PINBANK_RULE,
     'basis': 'PIN_TWIN_PLAN.md §2 (pol, 2026-11-13); roles bound per chip in hal.custom.soc_rules RULES (C3: econ, hal-3b step 2)'},
]

SIMULATED_CHIPS = [
    {'name': 'esp32c3-qemu', 'soc': R3.SOC, 'simulator': 'qemu:esp32c3', 'machine': 'esp32c3', 'engine': 'c3-run',
     'notes': 'the C3 twin (board.custom.twin_c3): the real flash image on Espressif\'s CPU, UART, timers and flash, with Polari\'s pads on top',
     'basis': _FORK},
]


def _span(block, size=0x1000):
    return '0x%08X' % R3.BASES[block], '0x%X' % size


def _ov(block, mode, why, evidence, behaviour='', device='', params=None):
    base, size = _span(block)
    return {'name': 'esp32c3-qemu:%s' % block, 'chip': 'esp32c3-qemu', 'peripheral': '%s:%s' % (R3.SOC, R3.PERIPHERAL_OF[block]), 'mode': mode,
            'behaviour': behaviour, 'device': device, 'base': base, 'size': size, 'params_json': json.dumps(params or {}, sort_keys=True),
            'why': why, 'evidence': evidence}


_SPAN_CITE = 'ESP32-C3 TRM v1.4 %s (4 KB per module)' % R3.BASE_CITE
_PINS = {'pins': len(R3.PADS)}

SIM_OVERLAYS = [
    _ov('GPIO', 'overlay',
        'the fork\'s esp32.gpio is a stub: its read answers only GPIO_STRAP (0x38) and its write is empty, so no pad ever moves; ours models the '
        'pad registers, and the strap stays Espressif\'s (unmapped offsets fall through to it)',
        '%s: esp32_gpio_read / esp32_gpio_write (hw/gpio/esp32_gpio.c), mapped at DR_REG_GPIO_BASE, 0x1000, priority 0; %s' % (_FORK, _SPAN_CITE),
        behaviour='pinbank', device='pins', params=dict(_PINS, leave_to_vendor=['GPIO_STRAP_REG'])),
    _ov('IO_MUX', 'overlay',
        'the fork has no IO_MUX device: its offsets fall to the machine\'s catch-all esp32c3.iomem, so the pad function, input enable and pulls '
        'are never stored; ours models them as part of the same pinbank as the GPIO span',
        '%s: no IO_MUX region; esp32c3.iomem (0xd1000 at ESP32C3_IO_START_ADDR) answers; %s' % (_FORK, _SPAN_CITE),
        behaviour='pinbank', device='pins', params=_PINS),
] + [_ov(block, 'vendor', why, '%s: %s; %s' % (_FORK, ev, _SPAN_CITE)) for block, why, ev in (
    ('UART0', 'the fork models UART0: the C3 light\'s UART0 is byte-identical between the prebuilt and the from-source binary (pt-0)',
     'DR_REG_UART_BASE mapped (esp32c3.c:480-483)'),
    ('SYSTIMER', 'the fork models the system timer: the ESP-IDF tick runs and the light\'s LED times match (pt-0: 300 / 450 / 600 ms)',
     'DR_REG_SYSTIMER_BASE mapped (esp32c3.c:563)'),
    ('INTMTX', 'the fork models the interrupt matrix; the pinbank\'s interrupt line enters it at interrupt_source (pt-3)',
     'DR_REG_INTERRUPT_BASE mapped (esp32c3.c:437)'),
    ('SYSTEM', 'the fork models the clock / reset registers', 'DR_REG_SYSTEM_BASE mapped (esp32c3.c:522)'),
    ('RTC_CNTL', 'the fork models the RTC control block (the reset cause)', 'DR_REG_RTCCNTL_BASE mapped (esp32c3.c:462)'),
    ('LEDC', 'NOT modelled by the fork: the catch-all esp32c3.iomem answers (said, not hidden: a pwm firmware sees no output here yet)',
     'no LEDC region in esp32c3.c'),
    ('APB_SARADC', 'NOT modelled by the fork: the catch-all esp32c3.iomem answers (an adc firmware reads no sample here yet)',
     'no APB_SARADC region in esp32c3.c'),
)]


def chip(name):
    return next((c for c in SIMULATED_CHIPS if c['name'] == name), None)


def overlays(chip_name):
    return [o for o in SIM_OVERLAYS if o['chip'] == chip_name]


def behaviour(name):
    return next((b for b in BLOCK_BEHAVIOURS if b['name'] == name), None)
