"""
@module pspp.material_structure_basis

The STRUCTURE layer (plan pspp-3) — what processing writes and what
property-prediction engines read. Structure attaches to a
MaterialState (not to the bare material: a slurry and its cured solid
have different structures), per scale level, with L2 allowed MULTIPLE
domain rows (gel domains, capillary pores, reaction rims, fiber
interphases, microcrack networks — ChatGPT convergence: sub-domains
inside L2, never new top-level scales).

Mandatory core is exactly FIVE descriptors (bulk_density,
phase_fractions, total_porosity, moisture_state, reaction_extent —
reaction_extent continuous in [0,1], the Ch.5-8 aging/pot-life
insight). Everything else is optional and honestly absent; ENGINES
declare what they need via require_descriptors and get an
evidence-bearing refusal pointing at the exact missing knob.

Q-species (Figs 5.5/5.6, pp.84-85) are structural MOTIFS, not
complete structures — a qDistribution descriptor summarizes them;
the underlying network graph (when an L3 representation exists) is
never replaced by the summary.

@consumers
  - polariServer.defClassList (auto-CRUDE + persistence)
  - pspp.custom.state_resolution (structure rows key by state)
"""
# sap-2c INDEX (design §7): the classes live one-per-file under objects/material_structure/;
# this file re-exports them (imports keep working) and holds what they share.
# The original imports stay: names this file imported were re-exported implicitly.

import json
from objectTreeDecorators import treeObject, treeObjectInit

from pspp.objects.material_structure._shared import L2_DOMAIN_TYPES, MANDATORY_DESCRIPTORS, _rows, descriptors_for_state, require_descriptors, structure_profile, structure_rows_for_state  # noqa: F401
from pspp.objects.material_structure.ScaleStructureDefinition import ScaleStructureDefinition  # noqa: F401
