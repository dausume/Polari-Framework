"""
@module board.custom.register_map

The register snapshot (custom/register_rows.json) → BoardDefinition / AdapterDefinition / Road rows. Register cells
are copied verbatim; the only judgements made here are written down as tables below, each with its reason:
  * PROGRAMMER — which ProgrammerKind reads the register's "USB programming" cell (nothing guessed: a cell whose method
    is unverified gets none, and its usb_rule stays `undetermined`)
  * ADAPTER aliases — register spellings that name a §1a row under another id
  * ADAPTER_USB_IDS — VID:PIDs for the generic-chip adapter rows, each with its source (the register has none)
A register `?` cell becomes '' and the row's notes say which columns were unknown (plan §8a; derive-or-cite).
"""
import json
import re

from board.custom.register_import import load as load_snapshot
from board.custom.programmers import SEED_PROGRAMMER_KINDS
from board.custom.uno_facts import BOARD as UNO, UNO_USB_IDS

#: register "USB programming" cell → ProgrammerKind (absent = the adapter's engine drives it, or undetermined)
PROGRAMMER = {
    'arduino-uno-r3': 'avrdude-optiboot', 'longan-nano-gd32vf103': 'dfu', 'ch32v203': 'wch-isp',
    'esp32-c3': 'esptool', 'esp32-c6': 'esptool', 'esp32-p4': 'esptool', 'lilygo-tbeam-tdeck': 'esptool',
    'heltec-lora32-v3': 'esptool', 'slimevr-trackers': 'esptool',
    'samd21-boards': 'uf2', 'samd51-boards': 'uf2', 'pico2-rp2350': 'uf2', 'rp2040': 'uf2', 'nrf52840-uf2-boards': 'uf2',
    'rak-wisblock-nrf52840-sx1262': 'uf2',
    'stm32f4-discovery': 'dfu', 'stm32g4-libresolar': 'dfu',
    'hifive1-revb': 'swd-probe',            # through its onboard USB-to-serial/JTAG debugger
    'icebreaker-ice40-up5k': 'fpga-usb-jtag', 'ulx3s-orangecrab-ecp5': 'fpga-usb-jtag',
    'beaglev-fire': 'hss-usbdmsc',          # D-brd-6: inside the refined rule via a USB-UART on the debug header
}
#: rows whose route is NOT established — the reason is the citation (never admitted until a road step settles it)
UNDETERMINED_WHY = {
    'k210-maixbit': 'register: flashing tool chain unverified; adapter cell "?"',
    'mobilinkd-tnc4': 'register: native USB, but DFU vs serial+bootloader unverified',
    'tr-usdx': 'register: onboard USB-serial bridge per community build, unverified',
    'newracom-nrc7292-boards': 'register: SPI-native chip; the USB bridge on HAT/dongle boards unverified',
    'morse-micro-mm6108-dongles': 'register: USB dongle, but its firmware is closed — no flash route of ours',
    'precursor': 'register: native USB via the vendor usb_update.py — not a ProgrammerKind yet (its road)',
}
NOT_A_TARGET = {'digirig': 'register: not itself programmable (a USB sound-card/PTT interface); see adapter digirig-mobile'}
ADAPTER_ALIASES = {'cp2102-usb-uart-friend': ['cp2102-usb-uart-modules'],
                   '`usb-uart`': ['cp2102-usb-uart-modules', 'wch-ch340-ch343-modules', 'ftdi-ft232h-ft2232h-boards']}
#: VID:PIDs for the generic-chip adapters (the register lists none), with the source of each
ADAPTER_USB_IDS = {
    'cp2102-usb-uart-modules': (['10c4:ea60'], ['Silicon_Labs_CP210', 'CP2102'],
                                'observed on pol-core 2026-10-01 (lsusb "Silicon Labs CP210x UART Bridge"); the Linux cp210x driver default id'),
    'wch-ch340-ch343-modules': (['1a86:7523'], ['1a86_USB_Serial', 'CH340'],
                                'the Linux ch341 driver id for the CH340; the CH343 id is not recorded yet (capture on first plug)'),
    'ftdi-ft232h-ft2232h-boards': (['0403:6014', '0403:6010'], ['FTDI'],
                                   'Linux ftdi_sio_ids.h: FTDI_232H_PID 0x6014, FTDI_8U2232C_PID 0x6010 (FT2232H)'),
}
SHARED_CHIP = {'tigard': 'ftdi-ft232h-ft2232h-boards', 'digirig-mobile': 'cp2102-usb-uart-modules'}
#: engines an adapter row brings into a board's toolchain
ADAPTER_ENGINE = {'wch-linke': 'wlink', 'usb-sd-card-reader': 'dd'}
C3 = 'esp32-c3'
EXPLICIT_TOOLCHAIN = {UNO: ['avr-gcc', 'avr-objcopy', 'avr-size', 'avrdude'],
                      'beaglev-fire': ['riscv-gcc', 'libero', 'dd', 'change-gateware'],
                      C3: ['idf-build', 'esptool', 'c3-run']}   # sc-3: ESP-IDF v5.5.5 + esptool + the QEMU fork (prf-esp-engines)
TRANSPORT = {UNO: 'usb-cdc-serial', 'beaglev-fire': 'usb-network+ssh', 'milk-v-duo': 'usb-network+ssh',
             C3: 'usb-cdc-serial'}   # sc-3: the frames on UART0 (a dev board's USB-UART; the twin's pty)
#: plan §8a: simulate FEW — the UNO first; sc-3 (D-sc-4 RULED 2026-10-02): the ESP32-C3, the RTOS board, in Espressif's QEMU
#: fork (FIRMWARE_SCENARIO_PLAN.md §9 sc-3 — the twin decision and its evidence); every other twin is a road step
PICKED = {UNO: 'simavr:atmega328p', C3: 'qemu:esp32c3'}
BY_ID_HINTS = {UNO: ['Arduino']}         # plan §3: by-id `usb-Arduino…_0043_<serial>-if00` is typical (unverified on his unit)
ROAD_STEPS = ['datasheet-facts', 'definition-complete', 'twin', 'firmware-template', 'flashed-on-hardware', 'measured']
ROAD_TREE = 'board-roads'

_DEV_COLS = {'class': 'device_class', 'status': 'register_status', 'chip': 'soc', 'ISA/arch': 'isa', 'MMU': 'mmu',
             'flash/SRAM': 'flash_sram', 'USB programming': 'usb_route', 'core RTL open': 'core_rtl_open',
             'board design open': 'board_design_open', 'silicon origin': 'silicon_origin', 'board origin': 'board_origin',
             'tiers proven': 'tiers_proven', 'radios': 'radios', 'power/BMS': 'power_bms', 'Polari role': 'polari_role',
             'relied-on resources': 'relied_on', 'cost measured': 'cost_measured', 'adapter needed': 'adapter_needed',
             'notes/unverified': 'notes'}
_ADA_COLS = {'kind': 'kind', 'chip': 'chip', 'USB connector': 'usb_connector', 'targets it programs': 'targets',
             'engine that drives it': 'engine', 'hardware open?': 'hardware_open', 'firmware open?': 'firmware_open',
             'origin (company, country)': 'origin', 'price class': 'price_class', 'notes/unverified': 'notes'}


def row_name(register_id):
    return register_id.split(' (')[0].strip()


def _copy(raw, cols):
    out, unknown = {}, []
    for col, field in cols.items():
        v = raw.get(col, '')
        if v == '?':
            unknown.append(col)
            v = ''
        out[field] = v
    if unknown:
        out['notes'] = (out.get('notes', '') + ' [unknown in the register: %s]' % ', '.join(unknown)).strip()
    return out


def _kind(name, device_class):
    c = device_class.lower()
    if name == 'beaglev-fire':
        return 'linux-soc-fpga'
    for key, kind in (('mcu', 'mcu'), ('soc-linux', 'soc-linux'), ('fpga', 'fpga'), ('radio-module', 'radio-module'), ('peripheral', 'peripheral')):
        if c.startswith(key):
            return kind
    return ''


def _adapter_ids(text, known):
    ids = [a for a in known if a in text]
    for alias, targets in ADAPTER_ALIASES.items():
        if alias in text:
            ids += [t for t in targets if t not in ids]
    return ids


def _twin(cell):
    m = re.match(r'`?((?:renode|simavr|qemu):[\w.-]+|verilator)', cell)
    return m.group(1) if m else ''


def board_rows(snapshot=None):
    snap = snapshot or load_snapshot()
    known = [row_name(a['id']) for a in snap['adapters']]
    engine_of = {p['name']: p['engine'] for p in SEED_PROGRAMMER_KINDS}
    rows = []
    for raw in snap['devices']:
        name = row_name(raw['id'])
        r = _copy(raw, _DEV_COLS)
        prog = PROGRAMMER.get(name, '')
        adapters = [] if name in NOT_A_TARGET else _adapter_ids(r['adapter_needed'], known)
        if name in NOT_A_TARGET:
            rule, why = 'not-a-target', NOT_A_TARGET[name]
        elif prog or adapters:
            rule = 'ok'
            why = ('programmer %s (host side USB)' % prog if prog else '') + ('; ' if prog and adapters else '') + \
                  ('adapter %s (host side USB)' % ' or '.join(adapters) if adapters else '')
        else:
            rule, why = 'undetermined', UNDETERMINED_WHY.get(name, 'no USB route established in the register')
        tools = EXPLICIT_TOOLCHAIN.get(name) or ([engine_of[prog]] if prog else []) + [ADAPTER_ENGINE[a] for a in adapters if a in ADAPTER_ENGINE]
        r.update({'name': name, 'title': name, 'register_id': raw['id'], 'kind': _kind(name, r['device_class']),
                  'usb_ids_json': json.dumps(UNO_USB_IDS if name == UNO else []),
                  'by_id_hints_json': json.dumps(BY_ID_HINTS.get(name, [])),
                  'programmer': prog, 'adapter_ids_json': json.dumps(adapters), 'usb_rule': rule, 'usb_rule_citation': why,
                  'toolchain_engines_json': json.dumps(tools), 'transport': TRANSPORT.get(name, ''),
                  'twin': PICKED.get(name) or _twin(raw.get('twin', '')), 'simulated': name in PICKED,
                  'flash_kb': 32 if name == UNO else 0, 'ram_kb': 2 if name == UNO else 0,
                  'licence_notes': '', 'designer': 'others', 'road': 'road-' + name,
                  'road_status': 'in-progress' if name in WALKED else 'todo'})
        rows.append(r)
    return rows


def adapter_rows(snapshot=None):
    snap = snapshot or load_snapshot()
    rows = []
    for raw in snap['adapters']:
        name = row_name(raw['id'])
        r = _copy(raw, _ADA_COLS)
        ids, hints, src = ADAPTER_USB_IDS.get(name, ([], [], ''))
        if name in SHARED_CHIP:
            src = 'presents the generic %s VID:PID — detect reports that chip row; a person names the product (brd-fi)' % SHARED_CHIP[name]
        elif not src:
            src = 'not in the register — captured on first plug (detect lists it unadmitted) or read from its cited firmware source'
        r.update({'name': name, 'register_id': raw['id'], 'usb_ids_json': json.dumps(ids), 'by_id_hints_json': json.dumps(hints),
                  'usb_ids_source': src})
        rows.append(r)
    return rows


#: where the UNO's road stands (brd-1, 2026-10-01) — the one road walked; every other road is all todo
UNO_STEPS = {
    'datasheet-facts': ('in-progress', 'boards.txt + product page + the ATmega328P datasheet (USART baud table, ADC formula) + TMP36 as 24 DatasheetFact rows; the pin map / full register facts are still to capture'),
    'definition-complete': ('done', 'BoardDefinition: usb ids, programmer avrdude-optiboot, toolchain, transport, limits, twin simavr:atmega328p'),
    'twin': ('done', 'brd-1: polari-avr-twin (simavr) runs the SAME .hex; UART at a pty; the Java bridge attached; BoardSimCost measured'),
    'firmware-template': ('done', 'brd-1: custom/firmware/uno — plain C on avr-libc around the AVR header; 4442 B flash / 763 B RAM'),
    'flashed-on-hardware': ('todo', 'OWED: no UNO attached — pol board detect → pol board flash uno --yes → the TMP36 reading tracks a finger'),
    'measured': ('in-progress', 'firmware sizes + the twin\'s cost measured; the real board\'s timing/USB reset not yet'),
}


#: sc-3: the ESP32-C3's road (2026-10-02, twin-first: no C3 on hand)
C3_STEPS = {
    'datasheet-facts': ('todo', 'no DatasheetFact rows yet: flash/SRAM in the register are nominal (unverified); the app partition and DRAM '
                                'totals come from the template\'s partitions.csv and idf.py size'),
    'definition-complete': ('in-progress', 'programmer esptool, toolchain idf-build/esptool/c3-run, transport, twin qemu:esp32c3; the USB VID:PID '
                                           'is not in the register (captured on first plug)'),
    'twin': ('done', 'sc-3: Espressif QEMU fork esp_develop_9.2.2_20260417 (-machine esp32c3) boots the SAME merged image; UART0 at a pty; '
                     'BoardSimCost measured'),
    'firmware-template': ('done', 'sc-3: custom/firmware/esp32c3 — ESP-IDF v5.5.5 C project, FreeRTOS tasks, the SAME SimRigState frames '
                                  '(c_twin target=host) on UART0, the trace hooks on UART1'),
    'flashed-on-hardware': ('todo', 'OWED: no C3 on hand — pol board flash c3 renders the esptool argv (DRY-RUN)'),
    'measured': ('in-progress', 'image sizes, build cost and the twin\'s cost measured; silicon timing not yet'),
}
WALKED = {UNO: UNO_STEPS, C3: C3_STEPS}


def road_rows(boards):
    out = []
    for b in boards:
        walked = WALKED.get(b['name'])
        steps = [{'step': s, 'status': walked[s][0] if walked else 'todo', 'note': walked[s][1] if walked else ''}
                 for s in ROAD_STEPS]
        out.append({'name': b['road'], 'board': b['name'], 'status': b['road_status'], 'steps_json': json.dumps(steps),
                    'concept_node': '%s/%s' % (ROAD_TREE, b['name']), 'notes': ''})
    return out


def tech_tree_rows(boards):
    tree = [{'name': ROAD_TREE, 'title': 'Board roads — every tracked device, what is done and what is to do', 'owner': 'polari',
             'description': 'One concept node per register device (plan §8a: track all, simulate few). The status of each road '
                            'lives on its Road row; the UNO is the first road walked.',
             'is_active': False, 'is_baseline': False, 'notes': 'plan BOARD_PROGRAMMING_PLAN.md §8a'}]
    nodes = [{'name': '%s/%s' % (ROAD_TREE, b['name']), 'tree_name': ROAD_TREE, 'title': b['name'],
              'description': '%s — %s' % (b['soc'], b['polari_role']), 'depends_on_json': '[]',
              'layout_hints_json': json.dumps({'column': b['kind'] or 'other'}),
              'cross_refs_json': json.dumps([{'module': 'board', 'class': 'Road', 'name': b['road'], 'relation': 'road-of'},
                                             {'module': 'board', 'class': 'BoardDefinition', 'name': b['name'], 'relation': 'device'}]),
              'data_dependencies_json': '[]', 'notes': ''} for b in boards]
    return tree, nodes
