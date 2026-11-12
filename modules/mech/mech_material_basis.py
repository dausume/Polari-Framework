"""
@module mech.mech_material_basis

mxc-1 (MECH_FREECAD_INTERCHANGE_PLAN section 3.3, 9.1, D-mxc-9): MATERIALS
AS REGISTRY ROWS. The Polari critical-materials registry (econ-core,
2026-11-03: 51 materials with IARC-classed feedstocks, a status
polari_preferred | polari_acceptable | legacy_harmful, and replaced_by;
35 part categories with default / alternative / legacy choices) lands
as two row classes:

- `MechMaterialOption` — NOT a fourth material identity. It mirrors
  `magnetics.MagneticMaterialOption`'s shape (msci_material_ref,
  item_ref, properties_json {prop: {value, unit, provenance}},
  realization fields) and is registered in
  `composition.custom.data_refs.MATERIAL_PROPERTY_CLASSES`, so
  `material_prop` / `role_viability` read it with no new code. Density,
  E, nu, yield, tensile, hardness (scale named), the headline
  `friction_coefficient` and the per-counter `friction_json` live on
  it as textbook PRIORS (-1 where no number is held) until measured.
- `MechMaterialPreference` — the plan's `MaterialRole`, renamed: one
  row per part category → default_ids / alternative_ids / legacy_ids +
  `role_refs_json` naming the COMPOSITION roles the part plays. It is
  checked by composition's `role_viability()`
  (`mech.custom.material_registry.preference_check`), never by
  predicates of its own.

Honesty pinned here: the IARC rows are from knowledge, not yet checked
against the monographs (every row carries `confidence`; AEM's methyl
acrylate and the two wood rows say 'check'); property values are
textbook priors with their provenance tag; a missing property is
UNASSESSED in every role check, never a pass. A `legacy_harmful`
material may be named on a part instance only with a `legacy_reason`
(plan 3.3).

@consumers mech.custom.material_registry, mech.mech_material_seed,
mech.mech_material_selftest, composition.custom.data_refs (by name),
polariServer
"""
# design §7 INDEX: the classes live one-per-file under objects/material/;
# this file re-exports them and holds what they share.
from mech.objects.material._shared import (  # noqa: F401
    CLASS_ALIASES, CONFIDENCES, IARC_GROUPS, MATERIAL_CLASSES,
    REALIZATION_LEVELS, STATUSES, worst_iarc,
)
from mech.objects.material.MechMaterialOption import MechMaterialOption  # noqa: F401
from mech.objects.material.MechMaterialPreference import MechMaterialPreference  # noqa: F401
