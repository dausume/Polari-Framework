"""
@module electrodevice.circuit_basis

ncg-4: CIRCUITS PROMOTED TO DATA. spice_run.py's hand-coded netlist
renderers become rows: a CircuitDefinition owns CircuitComponentDefinition
rows (components, pins wired by NET NAME) and CircuitNetDefinition
rows (the declared nets — documentation + drift visibility). The
netlist GENERATES from the rows (circuit_netlist), through the same
GraphCompilerDefinition seam as judicial forks and logic designs.

Standard promotion protocol per component kind (hwsim-5): parameters
come from an msci-derived device row (kind 'device' → the derived
subckt card, provenance attached) or an explicit value with the row
as its honest record. Net '0' is SPICE ground by convention.

@consumers
  - electrodevice.circuit_netlist_seed (the generator/runner)
  - electrodevice.circuit_api (the knob surface)
  - polariServer (registration + seed)
"""
# sap-2c INDEX (design §7): the classes live one-per-file under objects/circuit/;
# this file re-exports them (imports keep working) and holds what they share.
# The original imports stay: names this file imported were re-exported implicitly.

from objectTreeDecorators import treeObject, treeObjectInit

from electrodevice.objects.circuit._shared import COMPONENT_KINDS, SEED_CIRCUITS, SEED_CIRCUIT_COMPONENTS, SEED_CIRCUIT_NETS  # noqa: F401
from electrodevice.objects.circuit.CircuitDefinition import CircuitDefinition  # noqa: F401
from electrodevice.objects.circuit.CircuitNetDefinition import CircuitNetDefinition  # noqa: F401
from electrodevice.objects.circuit.CircuitComponentDefinition import CircuitComponentDefinition  # noqa: F401
