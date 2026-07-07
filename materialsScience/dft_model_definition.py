"""
@module materialsScience.dft_model_definition

DFTModelDefinition — the DFT-SPECIFIC simulation interface: one
configured electronic-structure calculation, sectioned the way DFT
tools structure their inputs (Quantum ESPRESSO namelists &CONTROL/
&SYSTEM/&ELECTRONS + ATOMIC_SPECIES/K_POINTS cards, ASE calculators,
pymatgen input sets):

    Structure (molecule | bulk) -> Method (basis, XC functional,
    charge/spin, pseudopotentials) -> Accuracy (cutoffs, k-points)
    -> Calculation type -> Outputs

Values inside the section JSON may be literals or BINDINGS (see
fem_model_definition / component_binding — the same three kinds).

`calculation_ref` names the EngineModelTemplate (dft-* catalog row):
    dft-molecular-energy  (pyscf SCF, local -> msci-engines worker)
    dft-bulk-structure    (ASE structure build — cheap, structural facts)
    dft-total-energy      (QE pw.x SCF — refuses honestly without the
                           execution layer / WITH_QE worker build)

Honesty notes baked into validation: pseudopotentials are only
meaningful to the QE execution layer (declaring them elsewhere earns a
note, not silent acceptance); accuracy.kpts/ecutwfc are consumed by
total-energy and noted-as-ignored by molecular calculations.

The last execution's result persists ON the row (object coherence).

@consumers
  - polariServer.defClassList (auto-CRUDE + persistence)
  - materialsScience.component_binding / model_execution
  - materialsScience.engine_model_seed ('paraffin-quantum-energy')
  - the msim engineModel stage (msci-16) + the DFT config UI (msci-17)
"""

from objectTreeDecorators import treeObject, treeObjectInit


class DFTModelDefinition(treeObject):
    """One configured DFT calculation (see module docstring).
    Identified by `name`."""

    @treeObjectInit
    def __init__(
        self,
        name: str = '',
        display_name: str = '',
        description: str = '',
        # The EngineModelTemplate this calculation instantiates (dft-*).
        calculation_ref: str = '',
        # {"kind": "molecule", "atoms": <binding|string>}      (pyscf
        #   geometry string, e.g. "C 0 0 0; H ...")
        # {"kind": "bulk", "symbol": "Al", "crystal": "fcc",
        #  "latticeA": 4.05}
        structure_json: str = '{}',
        # {"basis": "6-31g", "xc": "b3lyp", "charge": 0, "spin": 0,
        #  "pseudopotentials": null}   (pseudos: QE execution layer only)
        method_json: str = '{}',
        # {"ecutwfc": 30.0, "kpts": [3, 3, 3]} — consumed by
        # total-energy; noted-as-ignored by molecular calculations.
        accuracy_json: str = '{}',
        last_result_json: str = '{}',
        last_executed_at: str = '',
        notes: str = '',
        enabled: bool = True,
        manager=None,
    ):
        self.name = name
        self.display_name = display_name
        self.description = description
        self.calculation_ref = calculation_ref
        self.structure_json = structure_json
        self.method_json = method_json
        self.accuracy_json = accuracy_json
        self.last_result_json = last_result_json
        self.last_executed_at = last_executed_at
        self.notes = notes
        self.enabled = enabled
