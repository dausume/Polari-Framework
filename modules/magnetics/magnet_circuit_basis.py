"""
@module magnetics.magnet_circuit_basis

mag-3: MAGNETIC CIRCUITS PROMOTED TO DATA — the electrodevice
circuit_basis mirrored 1:1 through the classical Hopkinson analogy
(MMF ~ voltage, flux ~ current, reluctance R = l/(mu*A) ~ resistance).
A MagneticCircuitDefinition owns MagneticElementDefinition rows
(elements, terminals wired by FLUX-NODE NAME) and FluxNodeDefinition
rows (declared nodes = documentation + drift visibility). The
reluctance network GENERATES from the rows (magnetic_netlist),
through the same GraphCompilerDefinition seam.

Element materials REFERENCE the Section-A catalog
(MagneticMaterialOption.name) — mu/B_sat/H_c come from those rows,
never copied numbers; a missing row refuses by name.

@consumers
  - magnetics.magnetic_netlist_seed (the generator/solver)
  - magnetics.magnet_api (the knob surface)
  - polariServer (registration + seed)
"""
# sap-2c INDEX (design §7): the classes live one-per-file under objects/magnet_circuit/;
# this file re-exports them (imports keep working) and holds what they share.
# The original imports stay: names this file imported were re-exported implicitly.

from objectTreeDecorators import treeObject, treeObjectInit

from magnetics.objects.magnet_circuit._shared import ELEMENT_KINDS, SEED_FLUX_NODES, SEED_MAGNETIC_CIRCUITS, SEED_MAGNETIC_ELEMENTS  # noqa: F401
from magnetics.objects.magnet_circuit.MagneticCircuitDefinition import MagneticCircuitDefinition  # noqa: F401
from magnetics.objects.magnet_circuit.FluxNodeDefinition import FluxNodeDefinition  # noqa: F401
from magnetics.objects.magnet_circuit.MagneticElementDefinition import MagneticElementDefinition  # noqa: F401
