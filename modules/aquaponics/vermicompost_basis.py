"""
@cross-cutting
@module aquaponics.vermicompost_basis
@tags @xc:bindings

aqp-7 — worm-compost (vermicompost) nutrient-enrichment loop objects.

A worm-bin the aquaponic water passes through to be ENRICHED (a
nutrient SOURCE). Two flow-coupling modes, both selectable:

  direct    the bin is inline; all circulating water flows through the
            vermicompost continuously (steady enrichment at loop flow).
  periodic  water is routed through the bin on_minutes each cycle_hours,
            otherwise bypasses it; the bed RECHARGES between windows so
            periodic delivers PULSES of higher enrichment.

Object model (all treeObjects, auto-CRUDE + persisted —
object-coherence):

  CompostBinDefinition   the vessel + worm bed + MODE + schedule knobs.
  VermicompostProfile    the RELEASE profile of mature castings: per
                         NutrientSpecies soluble concentration the bed
                         can leach into passing water. Reuses aqp-2's
                         NutrientSpecies vocabulary. ABSTRACT PRIORS
                         (literature-range) until measured — flagged.
  CompostLoopDefinition  binds a bin + a PotSystemDefinition + the mode
                         into ONE runnable, rankable object (mirrors
                         PotSystemDefinition); enrichment_result_json is
                         objectRef-scorable.

The kinetics (mineralization + leaching box-model) live in
vermicompost_analysis.py; CompostLoopState (the running pool) in the
same file's cells_json convention. Rate constants are ABSTRACT PRIORS
— every one carries its literature range in the analysis, no
pseudo-precision (honest-absence).

@consumers
  - polariServer.defClassList (auto-CRUDE + persistence)
  - aquaponics.custom.vermicompost_analysis / vermicompost_api / scoring
@see /AQUAPONICS_PHASE2_PLAN.md §aqp-7
"""
# sap-2c INDEX (design §7): the classes live one-per-file under objects/vermicompost/;
# this file re-exports them (imports keep working) and holds what they share.
# The original imports stay: names this file imported were re-exported implicitly.

from objectTreeDecorators import treeObject, treeObjectInit

from aquaponics.objects.vermicompost._shared import COMPOST_MODES, FEEDSTOCK_KINDS  # noqa: F401
from aquaponics.objects.vermicompost.CompostBinDefinition import CompostBinDefinition  # noqa: F401
from aquaponics.objects.vermicompost.VermicompostProfile import VermicompostProfile  # noqa: F401
from aquaponics.objects.vermicompost.CompostLoopDefinition import CompostLoopDefinition  # noqa: F401
