"""
@cross-cutting
@module simulations.simulation_coupling_definition
@tags @xc:bindings

SimulationCouplingDefinition — the first-class record of a CROSS-SPACE
coupling: "when simulation A steps class C, sample a field from
simulation B's run and inject the result into C's step context."

This is the composition primitive the multi-scale PoC exists to prove:
spaces stay independent SimulationDefinitions (own classes, own dt, own
solutions), and a coupling row declares the directed data flow between
them. The physics consuming the injected values stays no-code (e.g. the
pendulum bob's wind-drag Partial reads `wind_vx/vy/vz` exactly like any
other context key); this row plus the runner's coupling pre-pass is the
only plumbing.

Which SOURCE RUN feeds a given target run is deliberately NOT stored
here — a definition-level coupling declares the relationship between
SIMULATIONS; the run-level pairing lives on SimulationRun's
`coupled_run_refs_json` ({source_sim_name: source_run_name}), so the
same sim def can have coupled and uncoupled runs side by side (wind vs
vacuum) and the coupling degrades to its declared defaults when a run
names no source.

`config_json` schema:
  {
    "sampler": {
      "operands": {                      # symbol -> operand spec
        "<sym>": {"kind": "source_field_json", "field": "cells_json"},
        "<sym>": {"kind": "source_field",      "field": "<numeric field>"},
        "<sym>": {"kind": "target_fields",     "fields": ["px","py","pz"]},
        "<sym>": {"kind": "constant",          "value": 1.0}
      }
    },
    "inject": {                          # context key -> injection spec
      "<key>": {"kind": "sample_element", "index": 0},
      "<key>": {"kind": "sample"},
      "<key>": {"kind": "constant", "value": 1.0}
    },
    "defaults": {"<key>": 0.0, ...}      # injected when no source run /
  }                                      # sampling fails (soft-degrade)

The sampler math itself is a saved (no-code) MatrixEquationDefinition
named by `sampler_equation_ref` — e.g. `field-sample-nearest` picks the
grid cell nearest the bob. Swapping nearest for trilinear is authoring,
not plumbing.

@consumers
  - polariServer.defClassList (auto-CRUDE + persistence)
  - simulations.simulation_coupling (the runner-side pre-pass)
  - simulations.wind_field_seed (the wind→pendulum coupling row)
@see /OVERLAP_MAP.md
"""

from objectTreeDecorators import treeObject, treeObjectInit


class SimulationCouplingDefinition(treeObject):
    """One directed cross-simulation coupling (source field → target
    step context). Identified by `name`."""

    @treeObjectInit
    def __init__(
        self,
        name: str = '',
        description: str = '',
        # The simulation + class whose step context RECEIVES the sample.
        target_simulation_ref: str = '',
        target_class_name: str = '',
        # The simulation + class whose run PROVIDES the sampled row.
        source_simulation_ref: str = '',
        source_class_name: str = '',
        # Saved MatrixEquationDefinition that computes the sample from the
        # operands declared in config_json (no-code sampling math).
        sampler_equation_ref: str = '',
        # Operand map, injection map, and defaults — see module docstring.
        config_json: str = '{}',
        enabled: bool = True,
        manager=None,
    ):
        self.name = name
        self.description = description
        self.target_simulation_ref = target_simulation_ref
        self.target_class_name = target_class_name
        self.source_simulation_ref = source_simulation_ref
        self.source_class_name = source_class_name
        self.sampler_equation_ref = sampler_equation_ref
        self.config_json = config_json
        self.enabled = enabled
