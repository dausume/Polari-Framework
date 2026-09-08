"""
@module electrodevice.device_basis

The multiscale electronics ladder's first rung
(HARDWARE_SIMULATION_PLAN.md section 4): a SIMPLE electronic device
whose electrical parameters DERIVE from previously-simulated material
data, abstracted into a SPICE card, tested in a circuit driven by the
FPGA's pins.

First device: the **CNT-doped sol-gel composite resistor** — the
current-limiting resistor for the 4x4 LED grid the FPGA already
drives. Its conductivity comes from EXECUTING the existing msci
percolation model (cnt-solgel-percolation: CNT axial sigma in a
xerogel matrix), never from a hand-typed constant; provenance rides
on the row. Object coherence: the device, its SPICE card, and every
circuit run are rows in the tree, configurable AT the row.

@consumers
  - electrodevice.custom.device_derive (derivation + card rendering)
  - electrodevice.custom.spice_run (ngspice circuit tests)
  - electrodevice.device_api (the knob surface)
  - polariServer (registration + seed)
"""
# sap-2c INDEX (design §7): the classes live one-per-file under objects/device/;
# this file re-exports them (imports keep working) and holds what they share.
# The original imports stay: names this file imported were re-exported implicitly.

from objectTreeDecorators import treeObject, treeObjectInit

from electrodevice.objects.device._shared import SEED_DEVICES  # noqa: F401
from electrodevice.objects.device.ElectronicDeviceDefinition import ElectronicDeviceDefinition  # noqa: F401
from electrodevice.objects.device.SpiceModelCard import SpiceModelCard  # noqa: F401
from electrodevice.objects.device.CircuitRunResult import CircuitRunResult  # noqa: F401
