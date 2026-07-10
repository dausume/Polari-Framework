"""
Selftest for hwfpga (hwsim-3).

Run from polari-framework/:
  python3 -m hwfpga.selftest_fpga

Stdlib + fake manager for generation checks; when `verilator` is on
PATH (oss-cad-suite) the generated core is ACTUALLY SIMULATED: the
self-checking bench (also generated from the same rows) proves the
constants, rw readback, heartbeat liveness, and the mode-MUX select
in real verilated logic. Honest skip otherwise.
"""

import os
import shutil
import subprocess
import sys
import tempfile
import types

from hwfpga import fpga_verilog as fv
from hwfpga.fpga_basis import SEED_REGISTER_MAPS, SEED_REGISTERS

_results = []


def check(label, cond, extra=''):
    _results.append((label, bool(cond)))
    print(f'{"PASS" if cond else "FAIL"}: {label}'
          + (f' — {extra}' if extra and not cond else ''))


def _mgr():
    mgr = types.SimpleNamespace(objectTables={
        'RegisterMapDefinition': {}, 'RegisterDefinition': {}})
    for seed in SEED_REGISTER_MAPS:
        row = types.SimpleNamespace(**seed)
        mgr.objectTables['RegisterMapDefinition'][row.name] = row
    for seed in SEED_REGISTERS:
        row = types.SimpleNamespace(**seed)
        mgr.objectTables['RegisterDefinition'][row.name] = row
    return mgr


def main():
    mgr = _mgr()
    map_row = fv.get_map(mgr, 'hardware-runtime')
    registers = fv.map_registers(mgr, 'hardware-runtime')
    check('seed map + registers present',
          map_row is not None and len(registers) == 8)

    core = fv.render_core(map_row, registers)
    check('core: const DEVICE_ID hardwired from the row',
          "rdata <= 32'h504C0001;" in core)
    check('core: rw registers get write cases + resets',
          "r_commands <= wdata;" in core
          and "r_config <= 32'h00000000;" in core)
    check('core: the MUX select is the MODE_MUX knob bit',
          'r_mode_mux[0] ? hw_pin_in : sim_counter' in core)
    check('core: pins_out row emits a wired output port (4x4 LED)',
          'output wire [15:0] led_matrix_pins' in core
          and 'assign led_matrix_pins = r_led_matrix[15:0];' in core)

    defines = fv.render_c_defines(map_row, registers)
    check('c-defines: base + offsets + const values from rows',
          '#define FPGA_BASE 0x70000000u' in defines
          and '#define FPGA_STATUS_OFFSET 0x0008u' in defines
          and '#define FPGA_DEVICE_ID_VALUE 0x504C0001u' in defines)

    sim_top = fv.render_sim_top(registers)
    check('sim wrapper: 64-bit channels (IntegrationLibrary binds '
          'uint64_t)',
          '[63:0] awaddr' in sim_top and '[63:0] rdata' in sim_top)

    # --- real verilated logic (honest skip without verilator) --------
    verilator = shutil.which('verilator')
    if verilator is None:
        print('SKIP: verilator not on PATH — the behavioral bench '
              'needs it (oss-cad-suite). Honest skip, not a pass.')
    else:
        tb = fv.render_testbench(registers)
        with tempfile.TemporaryDirectory() as td:
            with open(os.path.join(td, 'polari_regblock.v'),
                      'w') as f:
                f.write(core)
            with open(os.path.join(td, 'tb.sv'), 'w') as f:
                f.write(tb)
            build = subprocess.run(
                [verilator, '--binary', '--timing', '-Wno-fatal',
                 '--top-module', 'tb', 'tb.sv',
                 'polari_regblock.v'],
                cwd=td, capture_output=True, text=True)
            check('verilator builds the generated core + bench',
                  build.returncode == 0, build.stderr[-400:])
            if build.returncode == 0:
                run = subprocess.run(
                    [os.path.join(td, 'obj_dir', 'Vtb')],
                    cwd=td, capture_output=True, text=True,
                    timeout=120)
                check('verilated logic: consts + rw readback + '
                      'heartbeat + mode MUX all pass in simulation',
                      'TB PASS' in run.stdout,
                      (run.stdout + run.stderr)[-400:])

    passed = sum(1 for _, ok in _results if ok)
    print(f'\n{passed}/{len(_results)} checks passed')
    return 0 if passed == len(_results) else 1


if __name__ == '__main__':
    sys.exit(main())
