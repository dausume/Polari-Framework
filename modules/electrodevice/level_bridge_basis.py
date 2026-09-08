"""
@module electrodevice.level_bridge_basis

ncg-6: the CROSS-LEVEL COUPLING — "the FPGA design you drew drives
the circuit you plugged in." A PinBindingDefinition row declares
that one bit of a LogicBlockDesign output node drives one voltage
source (a breadboard placement or a circuit component): logic 1 =
vdd on that source, logic 0 = 0 V. Driving a circuit = evaluate the
design (hwdigital.custom.logic_sim, the same reference the verilated bench
answers to), set the bound sources, run the netlist, and judge LED
currents against the honest window — the verdict rides back as an
EVIDENCE-BEARING SUGGESTION on the result, never an auto-applied
change ([[knobs-and-suggestions]]).

This generalizes hwsim-led's `<register>_pins` trick from one
hand-wired register to ANY design output × ANY circuit source.

@consumers
  - electrodevice.circuit_api (the drive act)
  - polariNoCode.nocode_tests (circuit test subjects, ncg-6)
  - polariServer (registration + seed)
"""
# sap-2c INDEX (design §7): the classes live one-per-file under objects/level_bridge/;
# this file re-exports them (imports keep working) and holds what they share.
# The original imports stay: names this file imported were re-exported implicitly.

import json
from objectTreeDecorators import treeObject, treeObjectInit
from electrodevice.custom.spice_run import LED_MAX_A, LED_MIN_A

from electrodevice.objects.level_bridge._shared import MAX_DRIVE_STEPS, SEED_PIN_BINDINGS, _TARGET_TABLE, _apply_binding, _led_verdict, _rows, bindings_for, drive_boards_from_design  # noqa: F401
from electrodevice.objects.level_bridge.PinBindingDefinition import PinBindingDefinition  # noqa: F401
