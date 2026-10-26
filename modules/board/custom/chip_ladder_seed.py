"""
@module board.custom.chip_ladder_seed

chp-0: THE CHIPS-AND-LEVELS SEED (MISSION_GENERIC_PLAN.md section 13.1, his rulings 2026-10-24). Two sections that never mix:

  riscv        the fixed RISC-V SAMPLE - two chips per software level (bare C, FreeRTOS, Zephyr, Ubuntu), each preferring a chip whose
               emulator ALREADY EXISTS, plus the named exceptions (kept beside the sample, not in it)
  convenience  the convenience and cross-reference boards - the AVR Arduinos (simavr twins), the SAMD21 boards, the Xtensa ESP32, the bare
               iCE40 FPGA - kept because "the arduinos are still very accessible and we want to keep using them"

Every level claim carries its basis: a document URL, a Polari row or module, or the word `unverified` (nobody has checked yet) - never a
guess. Every emulator entry says whether its pins are real, a stub, or unverified, and its licence. `on_hand` is what he showed on
2026-10-24 (the boxes and the order labels) - part names only, nothing personal.
"""
import json

_S = 'MISSION_GENERIC_PLAN.md section 13.1 (2026-10-24)'
ZEPHYR = 'https://docs.zephyrproject.org/latest/boards/'
_NA_MCU = {'status': 'n/a', 'basis': 'a microcontroller without an MMU: no full Linux distribution'}
_ESP_BARE = {'status': 'yes', 'basis': 'plain-C chip HAL; the ESP-IDF bootloader loads any ELF (board.custom.firmware/esp32c3 is the pattern)'}
_ESP_RTOS = {'status': 'yes', 'basis': 'ESP-IDF v5.5.5 is FreeRTOS; the C3 is built by `pol board build c3` (sc-3, board.custom.build_c3)'}
_ESP_EMU = ('esp-emulator (Espressif, Rust, Beta) + the Espressif QEMU fork', 'esp-emulator',
            'Apache-2.0 (esp-emulator) / GPL-2.0 (QEMU fork)',
            'esp-emulator models GPIO, LEDC, MCPWM, PCNT, timers and the interrupt controller but has NO host-driven pin door yet (its feature '
            'request #5); the QEMU fork\'s GPIO is a register stub (hw/gpio/esp32_gpio.c: only GPIO_STRAP readable) - plan section 11.4 / 12')


def _lv(bare_c, freertos, zephyr, ubuntu):
    return json.dumps({'bare_c': bare_c, 'freertos': freertos, 'zephyr': zephyr, 'ubuntu': ubuntu})


def _emu(name, kind, pins, licence, status, basis, module=''):
    return json.dumps({'name': name, 'kind': kind, 'pins': pins, 'licence': licence, 'status': status, 'module': module, 'basis': basis})


_UNV_FP = {'rows': -1, 'row_spacing_pitches': -1, 'pins_per_row': -1, 'pitch_in': 0.1, 'straddles': None,
           'basis': 'unverified: no vendor mechanical drawing read for this board'}
_UNV_RADIO = [{'kind': 'unverified', 'module': 'unverified', 'precertified': {'fcc_id': 'unverified', 'ic': 'unverified', 'ce': None},
               'basis': 'unverified: radio fit and module certification page not read for this board'}]


def _no_radio(why):
    return [{'kind': 'none', 'module': '', 'precertified': {'fcc_id': '', 'ic': '', 'ce': None}, 'basis': why}]


_NO_RADIO_CHIP = _no_radio('no radio on the chip (it has none); board assumed radio-less from the vendor product name - vendor page not read')
_SHIELD = {'rows': 2, 'row_spacing_pitches': -1, 'pins_per_row': -1, 'pitch_in': 0.1, 'straddles': False,
           'basis': 'shield headers - not breadboardable; sits beside the breadboard'}
_C3_RADIO = [{'kind': 'wifi', 'module': 'ESP32-C3-MINI-1 (per the wb plan; Espressif module page not read)',
              'precertified': {'fcc_id': 'unverified', 'ic': 'unverified', 'ce': None}, 'basis': 'unverified: certification IDs not read from Espressif'},
             {'kind': 'ble', 'module': 'ESP32-C3-MINI-1 (per the wb plan; Espressif module page not read)',
              'precertified': {'fcc_id': 'unverified', 'ic': 'unverified', 'ce': None}, 'basis': 'unverified: certification IDs not read from Espressif'}]
_S3_RADIO = [{'kind': k, 'module': 'unverified', 'precertified': {'fcc_id': 'unverified', 'ic': 'unverified', 'ce': None},
              'basis': 'chip features Wi-Fi + BT 5 (LE) read by esptool 2026-10-24; module brand under the case, unread'} for k in ('wifi', 'ble')]
_FACTS = {
    'arduino-uno-r3': (_SHIELD, _NO_RADIO_CHIP),
    'arduino-zero': (dict(_SHIELD, basis='same UNO form factor (repo note: Arduino Zero = UNO form factor); shield headers - not breadboardable; sits beside the breadboard'), _NO_RADIO_CHIP),
    'arduino-mega-2560': (None, _NO_RADIO_CHIP),
    'attiny85-dip': (None, _NO_RADIO_CHIP),
    'adafruit-feather-m0-express': (dict(_UNV_FP, rows=2, basis='unverified: Adafruit Feather mechanical drawing not read (Adafruit learn pages fetched 2026-10-25 do not state row spacing)'), _NO_RADIO_CHIP),
    'elecrow-esp32-eval': (None, _S3_RADIO),
    'esp32-c3-devkitm-1': (None, _C3_RADIO),
}


def _b(board, title, on_hand=False, note='', price_usd=None):
    d = {'board': board, 'title': title, 'on_hand': bool(on_hand), 'note': note}
    if price_usd is not None:
        d['price_usd'] = price_usd
    fp, rd = _FACTS.get(board, (None, None))
    d['footprint_json'] = dict(fp or _UNV_FP)
    d['radios_json'] = [dict(r) for r in (rd or _UNV_RADIO)]
    return d


RISCV = [
    {'name': 'esp32c3', 'section': 'riscv', 'slot': 'bare-c 1', 'title': 'ESP32-C3 (bare C sample)', 'chip': 'ESP32-C3', 'vendor': 'Espressif',
     'family': 'RISC-V', 'core': 'RV32IMC 160 MHz, single core', 'soc_key': 'esp32c3',
     'boards_json': json.dumps([_b('esp32-c3-devkitm-1', 'ESP32-C3-DevKitM-1', False, 'to buy (D-mis-20); offers on file USD 9-24')]),
     'levels_json': _lv(_ESP_BARE, _ESP_RTOS,
                        {'status': 'yes', 'basis': 'Zephyr upstream board esp32c3_devkitm - ' + ZEPHYR + 'espressif/esp32c3_devkitm/doc/index.html'}, _NA_MCU),
     'emulator_json': _emu(*_ESP_EMU[:2], 'stub', _ESP_EMU[2], 'exists (pins stub)', _ESP_EMU[3], module='c3twin (planned: the pin door)'),
     'notes': 'The first RISC-V board of the arc; its twin module (c3twin) adds the pin door.', 'source': _S},
    {'name': 'k210', 'section': 'riscv', 'slot': 'bare-c 2', 'title': 'Kendryte K210 (bare C sample)', 'chip': 'K210', 'vendor': 'Canaan',
     'family': 'RISC-V', 'core': 'RV64GC, dual core 400 MHz, 8 MB SRAM', 'soc_key': '',
     'boards_json': json.dumps([_b('sipeed-maix-bit', 'Sipeed Maix Bit', False, 'availability mixed 2026-10-24: DFRobot/Probots in stock, Seeed/DigiKey discontinued', 21)]),
     'levels_json': _lv({'status': 'yes', 'basis': 'Kendryte standalone SDK (bare metal) - https://github.com/kendryte/kendryte-standalone-sdk'},
                        {'status': 'unverified', 'basis': 'kendryte-freertos-sdk exists; whether it is maintained is unverified'},
                        {'status': 'no', 'basis': 'no upstream Zephyr board found 2026-10-24'},
                        {'status': 'no', 'basis': 'no MMU-class Linux distribution; 8 MB SRAM'}),
     'emulator_json': _emu('Renode kendryte_k210', 'renode', 'unverified', 'MIT', 'exists', 'renode/platforms/cpus/kendryte_k210.repl ships with Renode'),
     'notes': 'Fallback if Maix boards vanish: LiteX / PicoRV32 on the same ECP5 board (Renode litex_picorv32) - D-mis-26.', 'source': _S},
    {'name': 'esp32p4', 'section': 'riscv', 'slot': 'freertos 1', 'title': 'ESP32-P4 (FreeRTOS sample)', 'chip': 'ESP32-P4', 'vendor': 'Espressif',
     'family': 'RISC-V', 'core': 'dual RV32 400 MHz + LP core; MCPWM, Ethernet, USB HS; no radio', 'soc_key': '',
     'boards_json': json.dumps([_b('esp32-p4-function-ev-board', 'ESP32-P4-Function-EV-Board', False, 'not on hand')]),
     'levels_json': _lv(_ESP_BARE, _ESP_RTOS, {'status': 'unverified', 'basis': 'Zephyr ESP32-P4 board status unverified 2026-10-24'}, _NA_MCU),
     'emulator_json': _emu('esp-emulator (Espressif, Rust, Beta)', 'esp-emulator', 'stub', 'Apache-2.0', 'exists (pins stub)',
                           'esp-emulator lists the P4 (PTP, jumbo frames and the LP core not modelled); GPIO / LEDC / MCPWM modelled, no host pin door (feature request #5)'),
     'notes': 'The richer MCU controller for motor PWM and Ethernet; same emulator family as the C3.', 'source': _S},
    {'name': 'polarfire-soc-e51', 'section': 'riscv', 'slot': 'freertos 2', 'title': 'PolarFire SoC - the E51 monitor core (FreeRTOS sample)',
     'chip': 'MPFS025T (PolarFire SoC)', 'vendor': 'Microchip', 'family': 'RISC-V', 'core': 'E51 RV64IMAC monitor core (SiFive, closed) beside 4 x U54 + FPGA fabric',
     'soc_key': '',
     'boards_json': json.dumps([_b('beaglev-fire', 'BeagleV-Fire', False, 'not on hand')]),
     'levels_json': _lv({'status': 'yes', 'basis': 'Microchip bare-metal examples for PolarFire SoC - https://github.com/polarfire-soc'},
                        {'status': 'yes', 'basis': 'Microchip FreeRTOS examples for PolarFire SoC - https://github.com/polarfire-soc'},
                        {'status': 'yes', 'basis': 'Zephyr upstream board mpfs_icicle - ' + ZEPHYR + 'microchip/mpfs_icicle/doc/index.html'},
                        {'status': 'yes', 'basis': 'see the U54 entry (the same chip runs Ubuntu on its U54 cores)'}),
     'emulator_json': _emu('QEMU upstream microchip-icicle-kit + Renode polarfire-soc', 'qemu-upstream', 'unverified', 'GPL-2.0 / MIT', 'exists',
                           'https://www.qemu.org/docs/master/system/riscv/microchip-icicle-kit.html ; renode/platforms/cpus/polarfire-soc.repl'),
     'notes': 'ONE chip running an RTOS beside Linux - the heterogeneous case a machine controller needs.', 'source': _S},
    {'name': 'esp32c6', 'section': 'riscv', 'slot': 'zephyr 1', 'title': 'ESP32-C6 (Zephyr sample)', 'chip': 'ESP32-C6', 'vendor': 'Espressif',
     'family': 'RISC-V', 'core': 'RV32IMAC 160 MHz + LP core; Wi-Fi 6, 802.15.4', 'soc_key': '',
     'boards_json': json.dumps([_b('esp32-c6-devkitc-1', 'ESP32-C6-DevKitC-1', False, 'not on hand', 8)]),
     'levels_json': _lv(_ESP_BARE, _ESP_RTOS,
                        {'status': 'yes', 'basis': 'Zephyr upstream board esp32c6_devkitc - ' + ZEPHYR + 'espressif/esp32c6_devkitc/doc/index.html'}, _NA_MCU),
     'emulator_json': _emu(*_ESP_EMU[:2], 'stub', _ESP_EMU[2], 'exists (pins stub)', _ESP_EMU[3] + '; the QEMU fork has an esp32c6 machine too (hw/riscv/esp32c6.c)'),
     'notes': '', 'source': _S},
    {'name': 'litex-vexriscv', 'section': 'riscv', 'slot': 'zephyr 2', 'title': 'LiteX / VexRiscv soft SoC on an ECP5 (Zephyr sample)',
     'chip': 'VexRiscv (soft core) on Lattice ECP5', 'vendor': 'SpinalHDL / LiteX (open); Lattice (FPGA)', 'family': 'RISC-V',
     'core': 'VexRiscv RV32IM(AFDC) - OPEN core (MIT), generated Verilog', 'soc_key': '',
     'boards_json': json.dumps([_b('orangecrab', 'OrangeCrab (ECP5-25F, USB-C DFU)', False, 'not on hand', 35)]),
     'levels_json': _lv({'status': 'yes', 'basis': 'LiteX BIOS and bare-metal demos - https://github.com/enjoy-digital/litex'},
                        {'status': 'unverified', 'basis': 'FreeRTOS on VexRiscv: ports exist in the community; unverified'},
                        {'status': 'yes', 'basis': 'Zephyr upstream board litex_vexriscv - ' + ZEPHYR + 'enjoydigital/litex_vexriscv/doc/index.html'},
                        {'status': 'no', 'basis': 'Linux via Buildroot (litex_vexriscv_linux), not Ubuntu'}),
     'emulator_json': _emu('Renode litex_vexriscv_zephyr (+ Verilator for the RTL)', 'renode', 'unverified', 'MIT (Renode) / LGPL-3.0 (Verilator)', 'exists',
                           'renode/platforms/cpus/litex_vexriscv_zephyr.repl ships with Renode; the RTL itself simulates in Verilator'),
     'notes': 'The open-core slot: the soft SoC can be edited, not only used (language-layering rule: generated Verilog = a fixed artifact).', 'source': _S},
    {'name': 'polarfire-soc-u54', 'section': 'riscv', 'slot': 'ubuntu 1', 'title': 'PolarFire SoC - the four U54 cores (Ubuntu sample)',
     'chip': 'MPFS025T (PolarFire SoC)', 'vendor': 'Microchip', 'family': 'RISC-V', 'core': '4 x U54 RV64GC (SiFive, closed) + FPGA fabric',
     'soc_key': '',
     'boards_json': json.dumps([_b('beaglev-fire', 'BeagleV-Fire', False, 'not on hand')]),
     'levels_json': _lv({'status': 'yes', 'basis': 'see the E51 entry'}, {'status': 'yes', 'basis': 'see the E51 entry'},
                        {'status': 'yes', 'basis': 'Zephyr upstream board mpfs_icicle - ' + ZEPHYR + 'microchip/mpfs_icicle/doc/index.html'},
                        {'status': 'yes', 'basis': 'BeagleBoard Ubuntu 24.04 image for the BeagleV-Fire (dated 2025-07-21) and Debian 13 (2026-07-25) - https://www.beagleboard.org/distros'}),
     'emulator_json': _emu('QEMU upstream microchip-icicle-kit + Renode polarfire-soc', 'qemu-upstream', 'unverified', 'GPL-2.0 / MIT', 'exists',
                           'https://www.qemu.org/docs/master/system/riscv/microchip-icicle-kit.html ; renode/platforms/cpus/polarfire-soc.repl'),
     'notes': 'The FPGA fabric is where our motion logic or open soft cores can live.', 'source': _S},
    {'name': 'k230', 'section': 'riscv', 'slot': 'ubuntu 2', 'title': 'Kendryte K230 (Ubuntu sample)', 'chip': 'K230', 'vendor': 'Canaan',
     'family': 'RISC-V', 'core': 'C908 big + little cores, RV64GCV (vector 1.0), KPU', 'soc_key': '',
     'boards_json': json.dumps([_b('canmv-k230', 'CanMV-K230', False, 'not on hand', 50), _b('canmv-k230d-zero', 'Banana Pi CanMV-K230D-Zero', False, 'not on hand', 30)]),
     'levels_json': _lv({'status': 'unverified', 'basis': 'the K230 SDK runs RT-Smart on the little core; bare metal on it is unverified'},
                        {'status': 'no', 'basis': 'the SDK\'s RTOS is RT-Thread RT-Smart, not FreeRTOS'},
                        {'status': 'no', 'basis': 'no upstream Zephyr board found 2026-10-24'},
                        {'status': 'yes', 'basis': 'Canaan K230 SDK Debian and Ubuntu images (one review: Ubuntu\'s Ethernet flaky, Debian stable) - https://owhinata.github.io/canmv-k230/en/'}),
     'emulator_json': _emu('QEMU upstream k230', 'qemu-upstream', 'unverified', 'GPL-2.0', 'exists',
                           'https://www.qemu.org/docs/master/system/riscv/k230.html - one C908 core, five UARTs, two watchdogs; SD controllers not emulated yet'),
     'notes': '', 'source': _S},
    # ---- exceptions: beside the sample, not in it
    {'name': 'rp2350', 'section': 'riscv', 'slot': 'exception', 'title': 'RP2350 / Raspberry Pi Pico 2 (exception: no emulator, PIO)', 'chip': 'RP2350',
     'vendor': 'Raspberry Pi', 'family': 'RISC-V', 'core': 'dual Hazard3 RV32IMAC 150 MHz - OPEN core (Apache-2.0) - or dual Cortex-M33; 3 PIO blocks', 'soc_key': '',
     'boards_json': json.dumps([_b('rpi-pico2', 'Raspberry Pi Pico 2 (UF2 over USB)', False, 'not on hand', 5)]),
     'levels_json': _lv({'status': 'yes', 'basis': 'Pico SDK bare metal (RISC-V build) - https://github.com/raspberrypi/pico-sdk'},
                        {'status': 'yes', 'basis': 'FreeRTOS SMP port for the RP2350 in the FreeRTOS kernel (RP2350_RISC-V) - unverified detail'},
                        {'status': 'yes', 'basis': 'Zephyr upstream board rpi_pico2/rp2350a/hazard3_0 - ' + ZEPHYR + 'raspberrypi/rpi_pico2/doc/index.html'}, _NA_MCU),
     'emulator_json': _emu('none upstream', 'none', 'none', '', 'none',
                           'Renode RP2350 exists only as project-specific platforms (an ArduPilot PR); matgla/Renode_RP2040 is frozen - checked 2026-10-24'),
     'notes': 'The one retail open core with PIO step generation; taken when PIO is needed, hardware-proven - D-mis-25.', 'source': _S},
    {'name': 'milkv-duo', 'section': 'riscv', 'slot': 'exception', 'title': 'Milk-V Duo (exception: Linux, not Ubuntu)', 'chip': 'Sophgo CV1800B',
     'vendor': 'Milk-V / Sophgo', 'family': 'RISC-V', 'core': 'C906 1 GHz (Linux) + C906 700 MHz (RTOS core)', 'soc_key': '',
     'boards_json': json.dumps([_b('milkv-duo', 'Milk-V Duo', False, 'not on hand', 9), _b('milkv-duo-s', 'Milk-V Duo S (SG2000)', False, 'not on hand', 10)]),
     'levels_json': _lv({'status': 'unverified', 'basis': 'bare metal on the little core: unverified'},
                        {'status': 'unverified', 'basis': 'the Duo SDK runs FreeRTOS on the small core: unverified 2026-10-24'},
                        {'status': 'no', 'basis': 'no upstream Zephyr board found 2026-10-24'},
                        {'status': 'no', 'basis': 'Linux (Buildroot) from the Duo SDK, not Ubuntu'}),
     'emulator_json': _emu('QEMU upstream milkv-duo', 'qemu-upstream', 'none', 'GPL-2.0', 'exists (pins stub)',
                           'https://www.qemu.org/docs/master/system/riscv/milkv-duo.html - C906 cores, CLINT, PLIC, dw8250 UART, SDHCI; no GPIO device listed'),
     'notes': 'The cheapest Linux-plus-RTOS-core board; the Klipper-style host and MCU on one chip.', 'source': _S},
    {'name': 'ch32v003', 'section': 'riscv', 'slot': 'exception', 'title': 'CH32V003 (exception: the price floor, no emulator)', 'chip': 'CH32V003',
     'vendor': 'WCH', 'family': 'RISC-V', 'core': 'QingKe RV32EC 48 MHz, 2 KB SRAM, 16 KB flash', 'soc_key': '',
     'boards_json': json.dumps([_b('ch32v003-dev-board', 'CH32V003 dev boards (various; programmed through a WCH-LinkE USB dongle)', False, 'not on hand', 2)]),
     'levels_json': _lv({'status': 'yes', 'basis': 'ch32v003fun bare-metal SDK - https://github.com/cnlohr/ch32v003fun'},
                        {'status': 'no', 'basis': '2 KB SRAM'}, {'status': 'no', 'basis': 'no upstream Zephyr board found 2026-10-24'}, _NA_MCU),
     'emulator_json': _emu('none', 'none', 'none', '', 'none', 'no QEMU or Renode platform found 2026-10-24'),
     'notes': 'Kept as the price floor the competitive scoring needs; bends the USB-only rule (link dongle).', 'source': _S},
    {'name': 'spacemit-k1', 'section': 'riscv', 'slot': 'exception', 'title': 'SpacemiT K1 boards (exception: Ubuntu host, virt-only twin)', 'chip': 'SpacemiT K1 / M1',
     'vendor': 'SpacemiT', 'family': 'RISC-V', 'core': '8 x X60 RVA22 + vector 1.0, 2 GHz', 'soc_key': '',
     'boards_json': json.dumps([_b('bpi-f3', 'Banana Pi BPI-F3', False, 'not on hand', 61), _b('milkv-jupiter', 'Milk-V Jupiter', False, 'not on hand', 60)]),
     'levels_json': _lv({'status': 'n/a', 'basis': 'an application processor'}, {'status': 'n/a', 'basis': 'an application processor'},
                        {'status': 'no', 'basis': 'no upstream Zephyr board found 2026-10-24'},
                        {'status': 'yes', 'basis': 'Ubuntu 24.04 for the K1 (Canonical); the K3 targets RVA23 and Ubuntu 26.04 - https://www.heise.de/en/news/RISC-V-single-board-computer-with-RVA23-chip-for-new-Linux-distributions-11167158.html'}),
     'emulator_json': _emu('QEMU upstream virt (approximates, no board machine)', 'qemu-upstream', 'none', 'GPL-2.0', 'exists (pins stub)', 'generic virt platform only'),
     'notes': 'A host we may buy anyway; not a sample slot.', 'source': _S},
]

CONVENIENCE = [
    {'name': 'atmega328p', 'section': 'convenience', 'slot': 'AVR', 'title': 'ATmega328P - Arduino UNO R3 / Nano', 'chip': 'ATmega328P', 'vendor': 'Microchip (Atmel)',
     'family': 'AVR', 'core': 'AVR 8-bit, 16 MHz, 32 KB flash, 2 KB SRAM, 1 KB EEPROM', 'soc_key': 'atmega328p',
     'boards_json': json.dumps([_b('arduino-uno-r3', 'Arduino UNO R3 (from the Starter Kit)', True, 'on the bench 2026-10-24 (the kit\'s box: 20 digital, 6 PWM, 6 analog, 68.6 x 53.4 mm)'),
                                _b('arduino-nano', 'Arduino Nano (DIP-30 footprint, breadboard-friendly)', False, 'not on hand')]),
     'levels_json': _lv({'status': 'yes', 'basis': 'the core demo: board.custom.firmware/uno, avr-gcc, Optiboot over USB'},
                        {'status': 'unverified', 'basis': 'community FreeRTOS AVR ports exist (Arduino_FreeRTOS_Library); 2 KB SRAM - unverified for our tasks'},
                        {'status': 'no', 'basis': 'Zephyr has no AVR architecture'}, _NA_MCU),
     'emulator_json': _emu('simavr', 'simavr', 'real', 'GPL-3.0', 'exists', 'the UNO twin (board.custom.light_twin): pins real, cycle counts measured', module='board'),
     'notes': 'The non-RISC-V reference every other board is compared against.', 'source': _S},
    {'name': 'atmega2560', 'section': 'convenience', 'slot': 'AVR', 'title': 'ATmega2560 - Arduino Mega 2560 (the "more pins" answer)', 'chip': 'ATmega2560',
     'vendor': 'Microchip (Atmel)', 'family': 'AVR', 'core': 'AVR 8-bit, 16 MHz, 256 KB flash, 8 KB SRAM; 54 digital + 16 analog pins, 4 UARTs', 'soc_key': '',
     'boards_json': json.dumps([_b('arduino-mega-2560', 'Arduino Mega 2560 R3', False, 'not on hand', 48)]),
     'levels_json': _lv({'status': 'yes', 'basis': 'avr-gcc, the same toolchain as the UNO'},
                        {'status': 'unverified', 'basis': 'community FreeRTOS AVR ports; 8 KB SRAM - unverified for our tasks'},
                        {'status': 'no', 'basis': 'Zephyr has no AVR architecture'}, _NA_MCU),
     'emulator_json': _emu('simavr (atmega2560 core)', 'simavr', 'real', 'GPL-3.0', 'exists', 'simavr ships an atmega2560 core; untested in Polari', module='board'),
     'notes': 'Needs its datasheet transcription (legs, pin functions, lifecycle, registers) before the solver sees it; the 2560 follows the 328P\'s register pattern.', 'source': _S},
    {'name': 'attiny85', 'section': 'convenience', 'slot': 'AVR', 'title': 'ATtiny85 (the AVR price floor)', 'chip': 'ATtiny85', 'vendor': 'Microchip (Atmel)',
     'family': 'AVR', 'core': 'AVR 8-bit, 8 KB flash, 512 B SRAM, DIP-8', 'soc_key': '',
     'boards_json': json.dumps([_b('attiny85-dip', 'bare ATtiny85 DIP-8 on the breadboard (programmed through the UNO as ISP, or a Digispark\'s USB bootloader)', False, 'not on hand', 2)]),
     'levels_json': _lv({'status': 'yes', 'basis': 'avr-gcc'}, {'status': 'no', 'basis': '512 B SRAM'}, {'status': 'no', 'basis': 'Zephyr has no AVR architecture'}, _NA_MCU),
     'emulator_json': _emu('simavr (attiny85 core)', 'simavr', 'real', 'GPL-3.0', 'exists', 'simavr ships attiny cores; untested in Polari', module='board'),
     'notes': 'The smallest thing that can hold one Task.', 'source': _S},
    {'name': 'samd21g18a', 'section': 'convenience', 'slot': 'ARM Cortex-M0+', 'title': 'ATSAMD21G18A - Arduino Zero / Adafruit Feather M0 Express', 'chip': 'ATSAMD21G18A',
     'vendor': 'Microchip (Atmel)', 'family': 'ARM Cortex-M0+', 'core': 'Cortex-M0+ 48 MHz, 256 KB flash, 32 KB SRAM, 3.3 V', 'soc_key': '',
     'boards_json': json.dumps([_b('arduino-zero', 'Arduino Zero (UNO form factor: 22 digital, 12 PWM, 6/1 analog, 68.8 x 53.4 mm)', True, 'on the bench 2026-10-24 (box)'),
                                _b('adafruit-feather-m0-express', 'Adafruit Feather M0 Express (PID 3403) + short headers + two 3.7 V LiPo cells', True, 'on the bench 2026-10-24 (order)', 19.95)]),
     'levels_json': _lv({'status': 'yes', 'basis': 'Arduino SAMD core / Microchip START bare metal'},
                        {'status': 'unverified', 'basis': 'FreeRTOS Cortex-M0 port; Adafruit\'s FreeRTOS-SAMD21 library - unverified for our tasks'},
                        {'status': 'yes', 'basis': 'Zephyr upstream board arduino_zero/samd21g18a (Maintained) - ' + ZEPHYR + 'arduino/zero/doc/index.html ; the Feather M0 Express has no upstream board (only feather_m0_basic_proto / feather_m0_lora, same chip)'},
                        _NA_MCU),
     'emulator_json': _emu('none known', 'none', 'none', '', 'none',
                           'no QEMU machine; Renode ships sam4s_xplained (SAM4S), not a SAMD21 platform - checked 2026-10-24. Smallest path: a Renode SAMD21 platform (Renode has the Cortex-M0+ core)'),
     'notes': 'A third ISA family on the bench; hardware-proven until a platform exists.', 'source': _S},
    {'name': 'esp32-xtensa', 'section': 'convenience', 'slot': 'Xtensa LX7', 'title': 'ESP32-S3 (Xtensa LX7) - the Elecrow e-paper display board',
     'chip': 'ESP32-S3 (QFN56) revision v0.2 - READ 2026-10-24 over USB with esptool v5.6.0 `chip-id` / `flash-id` (CH340 bridge, ttyUSB0): features Wi-Fi, BT 5 (LE), dual core + LP core, 240 MHz, '
             'embedded PSRAM 8 MB (AP_3v3); crystal 40 MHz; flash manufacturer 0xc8 device 0x4017 = 8 MB, quad (4 data lines), 3.3 V by eFuse. 8 MB flash + 8 MB PSRAM is the WROOM-1 "N8R8" '
             'pairing by Espressif\'s module naming (N8 = 8 MB flash, R8 = 8 MB PSRAM) - the module brand itself is under the case, unread. First derived from the GPIO header silk '
             '(IO8 IO13 IO14 IO9 IO16 IO15 IO18 IO17 IO20 IO19 IO38 IO21 + 4x3V3/4xGND - only the S3 has both GPIO20 and GPIO38), then confirmed by the chip',
     'vendor': 'Espressif (chip) / Elecrow (board)', 'family': 'Xtensa LX7', 'core': 'dual Xtensa LX7 240 MHz, Wi-Fi + BLE - NOT RISC-V', 'soc_key': '',
     'boards_json': json.dumps([_b('elecrow-esp32-eval', 'Elecrow "EVAL BOARD FOR ESP32" DIE01237S001 (DigiKey 5131-DIE01237S001-ND) - in hand it is an enclosed e-paper HMI display (CrowPanel form: UART0, RESET/BOOT, 2x10 GPIO header, battery connector, MENU/EXIT/arrow keys)', True,
                                   'on the bench 2026-10-24 (order label; his photos of the case + header silk); chip + flash + PSRAM read by esptool over its CH340 USB-serial (so: no native USB on the connector - UART0 bridge); panel size unread')]),
     'levels_json': _lv({'status': 'yes', 'basis': 'ESP-IDF bootloader loads any ELF; plain-C HAL possible'}, {'status': 'yes', 'basis': 'ESP-IDF is FreeRTOS'},
                        {'status': 'unverified', 'basis': 'Zephyr upstream esp32s3_devkitc / esp32s3_devkitm if the module is a WROOM-1 - pending esptool'}, _NA_MCU),
     'emulator_json': _emu('Espressif QEMU fork esp32s3 machine; esp-emulator (S3)', 'qemu-espressif-fork', 'stub', 'GPL-2.0', 'exists (pins stub)',
                           'the fork\'s esp32s3 machine shares the hw/gpio stub family of the C3 (only GPIO_STRAP readable) - its S3 GPIO status unchecked; esp-emulator covers the S3 (plan section 11.4 / D-mis-21b), '
                           'so this board is NOW a candidate for the esp-emulator route - it was not while it was taken for an original ESP32'),
     'notes': 'A GPIO model in the QEMU fork\'s parent file would fix the ESP32, C3 and C6 machines at once - a point for the QEMU route of D-mis-21b.', 'source': _S},
    {'name': 'ice40up5k', 'section': 'convenience', 'slot': 'FPGA', 'title': 'Lattice iCE40UP5K (bare chip) - the open-FPGA soft-core tier', 'chip': 'iCE40UP5K-UWG30ITR1K',
     'vendor': 'Lattice', 'family': 'FPGA', 'core': '5 280 LUT iCE40 UltraPlus, 21 I/O in a 30-ball WLCSP; hosts PicoRV32 or SERV (open RISC-V soft cores)', 'soc_key': '',
     'boards_json': json.dumps([_b('ice40up5k-wlcsp30', 'bare iCE40UP5K-UWG30ITR1K (needs a PCB: WLCSP, 0.4 mm pitch - the pcb arc)', True, 'on the bench 2026-10-24 (order label), one piece')]),
     'levels_json': _lv({'status': 'yes', 'basis': 'PicoRV32 / SERV bare C on the UP5K (riscv-cores-reference: SERV 198 LUT, PicoRV32 761-2019 LUT)'},
                        {'status': 'no', 'basis': 'too small for an RTOS-class soft SoC'},
                        {'status': 'unverified', 'basis': 'LiteX on the UP5K is not an upstream Zephyr board'}, {'status': 'n/a', 'basis': 'an FPGA'}),
     'emulator_json': _emu('Verilator / Icarus for the RTL; Renode litex_picorv32 and ice40up5k-mdp-evn platforms', 'rtl-simulation', 'real', 'LGPL-3.0 / GPL-2.0 / MIT', 'exists',
                           'the soft core\'s own RTL simulates cycle-exactly; renode/platforms/cpus/litex_picorv32.repl and platforms/boards/ice40up5k-mdp-evn.repl ship with Renode'),
     'notes': 'The fully open flow: yosys + nextpnr + icestorm. A bare WLCSP chip is unusable until a board carries it.', 'source': _S},
]

SEED_CHIP_LADDER = RISCV + CONVENIENCE
