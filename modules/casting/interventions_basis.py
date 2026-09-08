"""
@cross-cutting
@module casting.interventions_basis
@tags @xc:bindings

cast-6 (Dustin's original ask): ALTER the fill when it needs help —
positive or negative pressure through a sprue, heat or cold — with
every intervention GATED so it damages neither the mold nor the
cast material, and NOTHING auto-applied (knobs-and-suggestions:
the report says what the knob would do and what the gates say;
turning it is the human's move).

  pressure-positive  compresses trapped air (Boyle, ideal-gas,
                     named) and helps thin channels — gated by the
                     pour-loading wall-bending model at the raised
                     pressure, plus the clamping force it demands.
  pressure-vacuum    pre-fill evacuation eliminates TOPOLOGICAL
                     pockets (unfed chambers stay unfed — vacuum
                     moves air, not slurry) — gated by the same
                     plate model (atmosphere now pushes INWARD) and
                     slurry outgassing (a named absence).
  heat-soak          for geopolymer this is COUNTERPRODUCTIVE and
                     the measured data says so: pot life falls
                     210→45 min from cure 40→85°C — reported as a
                     refutation with the evidence, not a silent
                     apply. Mold softening margin re-gated at the
                     raised temperature.
  chill              extends the geopolymer pot life toward the
                     measured 210 min ceiling; below the 40°C
                     validity floor it refuses to extrapolate.
                     Ceramic molds re-gate on thermal_shock.

FillInterventionDefinition rows seed the four knobs so the
capability is discoverable as data (object-coherence).

@see /WAX_MOLD_NESTING_PLAN.md (PHASE cast-6)
"""
# sap-2c INDEX (design §7): the classes live one-per-file under objects/interventions/;
# this file re-exports them (imports keep working) and holds what they share.
# The original imports stay: names this file imported were re-exported implicitly.

from casting.fill_sim_basis import simulate_fill
from casting.custom.pour_loading import (
    EXOTHERM_MEASURED, cure_duration_min, pour_loading_report,
)
from objectTreeDecorators import treeObject, treeObjectInit

from casting.objects.interventions._shared import INTERVENTION_KINDS, SEED_FILL_INTERVENTIONS, _ATM_KPA, evaluate_intervention  # noqa: F401
from casting.objects.interventions.FillInterventionDefinition import FillInterventionDefinition  # noqa: F401
