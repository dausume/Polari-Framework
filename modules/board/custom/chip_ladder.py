"""
@module board.custom.chip_ladder

chp-0: the chips-and-levels doors' bodies (MISSION_GENERIC_PLAN.md section 13.1). Pure functions over the ChipLadderEntry rows (live when a
manager holds them, else the seed) that FLATTEN one entry into one table row, and DERIVE what Polari already holds for the chip (SoC rows,
pin functions, registers, board rows) - never stored. The two sections never mix: a row is in `riscv` or in `convenience`, and the doors
take `?section=` so each tab reads only its own.

    GET /api/board/chip-ladder?section=riscv|convenience   {ok, section, rows}   one row per chip, the four levels as words + their basis
    GET /api/board/chip-ladder/levels                       {ok, rows}            the four levels: what each means, the open core picked for it
    GET /api/board/chip-ladder/emulators                    {ok, rows}            one row per emulator: kind, licence, chips it covers, pins, what is missing
"""
import json

from board.custom import chip_ladder_seed as SEED

LEVELS = (
    ('bare_c', 'Bare C', 'No operating system: one loop, interrupts, the chip HAL in plain C. Every Task is scheduled by the generated main loop.',
     'PicoRV32 (ISC, Verilog)', 'MISSION_GENERIC_PLAN.md section 13.1; riscv-cores-reference'),
    ('freertos', 'FreeRTOS', 'A small RTOS: one FreeRTOS task per Polari Task, queues between them, the same C atoms inside.',
     'CV32E40P (Solderpad, SystemVerilog)', 'MISSION_GENERIC_PLAN.md section 13.1; riscv-cores-reference'),
    ('zephyr', 'Zephyr', 'A full RTOS with a device tree and upstream board files: the board is described, not hand-wired.',
     'Hazard3 (Apache-2.0, Verilog; ships in the RP2350)', 'MISSION_GENERIC_PLAN.md section 13.1; riscv-cores-reference'),
    ('ubuntu', 'Ubuntu', 'A full Linux distribution with an MMU: the host or HMI tier; Polari itself can run here.',
     'CVA6 (Solderpad, SystemVerilog; FPGA only - no retail board, no Debian/Ubuntu proof)', 'MISSION_GENERIC_PLAN.md section 13.1; riscv-cores-reference'),
)

#: the emulators the ladder names, in the order the page lists them
EMULATORS = (
    ('simavr', 'simavr', 'GPL-3.0', 'real', 'exists', 'nothing - the UNO twin runs today (board.custom.light_twin)'),
    ('esp-emulator', 'esp-emulator (Espressif, Rust, Beta)', 'Apache-2.0', 'stub', 'exists (pins stub)',
     'a host-driven pin door (its feature request #5: output-change events out, input edges in) - the c3twin contribution'),
    ('qemu-espressif-fork', 'Espressif QEMU fork (esp32, esp32c3, esp32c6 machines)', 'GPL-2.0', 'stub', 'exists (pins stub)',
     'a GPIO + IO MUX model: hw/gpio/esp32_gpio.c reads only GPIO_STRAP, its write handler is empty, no pin lines - plan section 11.4'),
    ('qemu-upstream', 'QEMU upstream (microchip-icicle-kit, k230, milkv-duo, virt)', 'GPL-2.0', 'unverified', 'exists',
     'per machine: k230 has no SD controllers yet; milkv-duo lists no GPIO device; virt is generic'),
    ('renode', 'Renode (kendryte_k210, polarfire-soc, litex_*, ice40up5k-mdp-evn)', 'MIT', 'unverified', 'exists',
     'pin-line fidelity per platform unverified; no SAMD21, no RP2350, no ESP32 platform upstream'),
    ('rtl-simulation', 'Verilator / Icarus (the soft core\'s own RTL)', 'LGPL-3.0 / GPL-2.0', 'real', 'exists', 'nothing for the core; the peripherals around it are ours to write'),
    ('none', 'none known', '', 'none', 'none', 'SAMD21 (Arduino Zero, Feather M0 Express), RP2350, CH32V003: hardware-proven through the bench gate until a platform exists'),
)

#: how each emulator kind simulates, and what drives its inputs (his rule: hardware-only is said loudly, never left blank)
METHOD = {'simavr': 'instruction-level emulation of the real flashed image (AVR core + peripherals)',
          'esp-emulator': 'instruction-level emulation of the real flashed image (Espressif\'s Rust emulator)',
          'qemu-espressif-fork': 'QEMU machine running the real merged flash image (Espressif fork)',
          'qemu-upstream': 'QEMU board machine running the real image (upstream QEMU)',
          'renode': 'Renode platform (.repl) running the real ELF',
          'rtl-simulation': 'cycle-exact RTL simulation of the soft core (Verilator / Icarus)',
          'none': 'none'}
INPUTS = {'simavr': 'the twin worker\'s pin callbacks (board.custom.twin_sessions): presses, levels, analog ramps',
          'esp-emulator': 'none yet: UART injection only - a GPIO bridge is its open feature request #5 (the c3twin contribution)',
          'qemu-espressif-fork': 'none: the GPIO block is a stub, so the PIN_SHIM build scripts its presses in RAM',
          'qemu-upstream': 'per machine, unverified (QMP where the machine wires pin lines)',
          'renode': 'Renode GPIO connectors per platform (unverified for these platforms)',
          'rtl-simulation': 'the testbench\'s signals',
          'none': 'a person at the bench'}


def testing_of(em):
    """{group, word, software, how, inputs_driven_by} from one emulator entry. group: simulated | simulated-stub | planned | hardware-only.
    The word is what a person reads: HARDWARE ONLY in capitals when no emulator exists; STUB / UNVERIFIED / NO pins in capitals when the
    firmware runs but the pins cannot carry a proof."""
    em = em or {}
    kind, status, pins, name = em.get('kind', 'none'), em.get('status', 'none'), em.get('pins', 'none'), em.get('name', '') or 'none'
    base = {'software': name if kind != 'none' else 'none', 'how': METHOD.get(kind, 'unverified'), 'inputs_driven_by': INPUTS.get(kind, 'unverified')}
    if kind == 'none' or status == 'none':
        return dict(base, group='hardware-only', word='HARDWARE ONLY - no emulator known: every proof is on the real board')
    if status == 'planned':
        return dict(base, group='planned', word='HARDWARE ONLY until %s lands (planned twin)' % (em.get('module') or 'its twin module'))
    if pins == 'real':
        return dict(base, group='simulated', word='simulated: pins real (%s)' % name)
    if pins == 'stub':
        return dict(base, group='simulated-stub', word='simulated: pins STUB (%s) - the firmware runs, pin-level claims need the real board' % name)
    if pins == 'none':
        return dict(base, group='simulated-stub', word='simulated: NO pins modelled (%s) - the firmware runs, every pin claim is hardware-tested' % name)
    return dict(base, group='simulated-stub', word='simulated: pins UNVERIFIED (%s) - until checked, treat pin-level claims as hardware-tested' % name)


def _j(text, default):
    try:
        v = json.loads(text) if isinstance(text, str) and text else default
    except Exception:  # noqa: BLE001
        return default
    return v if isinstance(v, type(default)) else default


def entries(manager=None):
    """The ChipLadderEntry rows as dicts: the live rows when the manager holds any, else the seed."""
    rows = ((getattr(manager, 'objectTables', None) or {}).get('ChipLadderEntry', {}) or {}).values() if manager is not None else []
    live = []
    for r in rows:
        live.append({k: getattr(r, k, '') for k in ('name', 'section', 'slot', 'title', 'chip', 'vendor', 'family', 'core', 'soc_key',
                                                       'boards_json', 'levels_json', 'emulator_json', 'notes', 'source')})
    return live or [dict(e) for e in SEED.SEED_CHIP_LADDER]


def _tables(manager):
    """The board object's tables for the derived column; the pure seed tables when no manager (selftests)."""
    try:
        from board.custom import board_object as BO
        return BO.seed_tables()
    except Exception:  # noqa: BLE001 - the derived column says undetermined rather than failing the page
        return {}


def holdings(entry, tables):
    """What Polari already holds for the chip - DERIVED: SoC rows, pin functions (stored + derived), registers, board rows."""
    soc = entry.get('soc_key') or ''
    if not tables:
        return 'undetermined (the board tables did not load)'
    boards = {b.get('name') for b in tables.get('BoardDefinition', [])}
    mine = [b['board'] for b in _j(entry.get('boards_json'), []) if b.get('board') in boards]
    if not soc:
        return 'no SoC rows yet' + ('; board rows: %s' % ', '.join(mine) if mine else '; no board rows')
    socs = {s.get('name') for s in tables.get('SocDefinition', [])}
    if soc not in socs:
        return 'no SoC row named %s' % soc
    try:
        from board.custom import soc_functions as SF
        n_pf = len(SF.pin_functions(tables, soc))
    except Exception:  # noqa: BLE001
        n_pf = len([f for f in tables.get('PinFunction', []) if f.get('soc') == soc])
    n_reg = len([r for r in tables.get('Register', []) if r.get('soc') == soc])
    n_mem = len([r for r in tables.get('MemoryRegion', []) if r.get('soc') == soc])
    return 'SoC row yes; pin functions %d; registers %d; memory regions %d; board rows: %s' % (n_pf, n_reg, n_mem, ', '.join(mine) or 'none')


def flatten(entry, tables):
    """One table row per entry: the levels as status words with their basis beside them, the emulator in three columns, holdings derived."""
    lv = _j(entry.get('levels_json'), {})
    em = _j(entry.get('emulator_json'), {})
    boards = _j(entry.get('boards_json'), [])
    row = {'name': entry['name'], 'section': entry['section'], 'slot': entry.get('slot', ''), 'title': entry.get('title', ''),
           'chip': entry.get('chip', ''), 'vendor': entry.get('vendor', ''), 'family': entry.get('family', ''), 'core': entry.get('core', ''),
           'boards': ', '.join(b.get('title') or b.get('board', '') for b in boards),
           'on_hand': ', '.join(b.get('title') or b.get('board', '') for b in boards if b.get('on_hand')) or 'no',
           'emulator': em.get('name', ''), 'emulator_kind': em.get('kind', ''), 'emulator_pins': em.get('pins', ''),
           'emulator_status': em.get('status', ''), 'emulator_licence': em.get('licence', ''), 'emulator_basis': em.get('basis', ''),
           'in_polari': holdings(entry, tables), 'notes': entry.get('notes', ''), 'source': entry.get('source', '')}
    t = testing_of(em)
    row.update(testing_group=t['group'], testing=t['word'], software=t['software'], how=t['how'], inputs_driven_by=t['inputs_driven_by'])
    for key in ('bare_c', 'freertos', 'zephyr', 'ubuntu'):
        v = lv.get(key) or {}
        row[key] = v.get('status', 'unverified')
        row[key + '_basis'] = v.get('basis', '')
    return row


def rows(manager=None, section=''):
    ents = entries(manager)
    if section:
        ents = [e for e in ents if e.get('section') == section]
    tables = _tables(manager)
    return [flatten(e, tables) for e in ents]


def level_rows():
    return [{'level': k, 'title': t, 'what_it_means': w, 'open_core_pick': c, 'source': s} for k, t, w, c, s in LEVELS]


def emulator_rows(manager=None):
    ents = entries(manager)
    out = []
    for kind, name, licence, pins, status, missing in EMULATORS:
        covered = [e['name'] for e in ents if (_j(e.get('emulator_json'), {}).get('kind') == kind)]
        out.append({'kind': kind, 'emulator': name, 'licence': licence, 'pins': pins, 'status': status, 'chips_covered': ', '.join(covered) or '-',
                    'method': METHOD.get(kind, 'unverified'), 'inputs_driven_by': INPUTS.get(kind, 'unverified'), 'what_is_missing': missing})
    return out


def door(manager, params, which):
    """(status, payload) for the three doors."""
    if which == 'levels':
        return 200, {'ok': True, 'rows': level_rows()}
    if which == 'emulators':
        return 200, {'ok': True, 'rows': emulator_rows(manager)}
    section = (params.get('section') or '').strip()
    if section == 'all':
        section = ''
    if section and section not in ('riscv', 'convenience'):
        return 400, {'ok': False, 'error': 'section must be riscv or convenience (got %r)' % section}
    return 200, {'ok': True, 'section': section or 'all', 'rows': rows(manager, section)}
