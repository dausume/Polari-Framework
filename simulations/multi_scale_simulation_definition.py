"""
@cross-cutting
@module simulations.multi_scale_simulation_definition
@tags @xc:bindings

MultiScaleSimulationDefinition — the object that ties a MULTI-SCALE
simulation together as pure configuration (roadmap Milestone C made
concrete): which spaces participate, which couplings bind them, which
run the user drives, and which configured interfaces (scenes, graphs,
initial-condition setters, displays) present it.

Everything it names is another definition object reachable by name/id —
composing a multi-scale simulation is linking, not coding. The frontend
Multi-Scale Simulation Page renders one of these; its Configure-mode
part rail edits the referenced objects through their own editors.

`panels_json` — ordered panel refs for the page's default layout; each
entry is `{kind, ...refs}` pointing at OTHER definition objects:
    {"kind": "scene",   "simSpaceRef": "<SimSpaceDefinition name>",
     "run": "primary" | "<run name>"}
    {"kind": "graph",   "graphRef": "<GraphDefinition name>",
     "sourceClass": "<*SimState>", "runs": ["primary", ...]}
    {"kind": "ic",      "icInterfaceRef":
     "<InitialConditionInterfaceDefinition name>"}
    {"kind": "display", "displayId": <Display id>}   # embed a Display grid

`stages_json` — the MULTI-SCALE PROGRESSION, itself no-code: an ordered
list of stages the run set advances through, each gated by a no-code
predicate over the previous stage's results. E.g. first RUN the material
simulation to completion (search temp/pressure for conditions where the
chosen substance condenses into a solid ball, analyze the resulting ball
size, PROVE a solid ball is possible) — and only when its gate passes
does the pendulum stage unlock, with the gate's derived values (mass,
radius) flowing into the next stage's initial conditions:
    [{"key": "material-precondition", "kind": "runToCompletion",
      "simulationRef": "<sim def name>",
      "gate": {"solutionRef": "<SolutionDefinition name>"},
      "derive": {"params": {"<sim>.<param>": "<gate output key>", ...}}},
     {"key": "pendulum-in-wind", "kind": "coStep",
      "primarySimulationRef": "<sim def name>",
      "couplingRefs": ["<SimulationCouplingDefinition name>", ...]}]
Gate solutions execute through the SAME SolutionExecutionEngine flow the
initial-conditions validator uses (flattened `<class>.<field>` results
context in, outcome/reason/derived values out) — authored in the
existing no-code editor, no new engine surface.

`compare_run_policy_json` — how comparison runs stay in tune:
    {"mode": "fanOutSteps", "runs": ["<run name>", ...]}
(coupled source runs need no policy — the runner's lazy pull already
synchronizes them to the primary run's time).

@consumers
  - polariServer.defClassList (auto-CRUDE + persistence)
  - simulations.multi_scale_seed (the "Pendulum in Wind" demo)
  - frontend /multi-scale-sims pages
@see /OVERLAP_MAP.md
"""

from objectTreeDecorators import treeObject, treeObjectInit


class MultiScaleSimulationDefinition(treeObject):
    """One configured multi-scale simulation (spaces + couplings + the
    interfaces that present it). Identified by `name`."""

    @treeObjectInit
    def __init__(
        self,
        name: str = '',
        description: str = '',
        # Participating spaces — SimulationDefinition names.
        member_simulation_refs_json: str = '[]',
        # The SimulationCouplingDefinitions binding those spaces.
        coupling_refs_json: str = '[]',
        # The space whose run the page's play/step controls drive;
        # coupled sources advance via the runner's lazy pull.
        primary_simulation_ref: str = '',
        # Ordered no-code progression stages + gates (see module
        # docstring). Empty = a single implicit coStep stage over
        # primary_simulation_ref with coupling_refs_json.
        stages_json: str = '[]',
        # Ordered panel refs for the default page layout (see module
        # docstring for the per-kind shapes).
        panels_json: str = '[]',
        # Optional: a Display (grid) id that REPLACES the default layout
        # entirely — full custom composition via the Display editor.
        display_ref: str = '',
        # How comparison (non-coupled) runs are kept in tune.
        compare_run_policy_json: str = '{}',
        enabled: bool = True,
        manager=None,
    ):
        self.name = name
        self.description = description
        self.member_simulation_refs_json = member_simulation_refs_json
        self.coupling_refs_json = coupling_refs_json
        self.primary_simulation_ref = primary_simulation_ref
        self.stages_json = stages_json
        self.panels_json = panels_json
        self.display_ref = display_ref
        self.compare_run_policy_json = compare_run_policy_json
        self.enabled = enabled
