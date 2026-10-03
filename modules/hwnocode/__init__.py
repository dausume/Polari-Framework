"""
@module hwnocode

HARDWARE AS NO-CODE (hn arc, AI-Notes/plans/HARDWARE_NOCODE_PLAN.md; his rulings D-hn-1..6, 2026-10-03): ONE no-code model across
frontend, backend and hardware. A `HardwareSolution` ties a backend SolutionDefinition to a cmod `CGraph` (the hardware SUBGRAPH,
D-hn-1), the board/twin it targets, the hw-interface (a grpcbridge HardwareInterfaceBinding — the device⇄backend split point) and
the configured displays. The placement rule (plan §2b) assigns every node to board | twin | bridge | backend | browser and REFUSES
a Python node on the device side (RULE 2). hn-0: the module, the node kinds on the ONE canvas (D-hn-2), the split-app graph
(variant h) over the existing peripheral (variant b), the `hn-split` compiler row, the runtime suggestion (SUGGEST ONLY, D-hn-3).
"""
