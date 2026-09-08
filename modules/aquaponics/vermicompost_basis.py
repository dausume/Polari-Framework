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

from objectTreeDecorators import treeObject, treeObjectInit

#: Flow-coupling modes (Dustin 2026-07-09).
COMPOST_MODES = ('direct', 'periodic')

#: Feedstock kinds — set the abstract release priors' magnitude.
FEEDSTOCK_KINDS = ('food-scraps', 'manure', 'mixed')


class CompostBinDefinition(treeObject):
    """One worm-compost bin the aquaponic water is routed through."""

    @treeObjectInit
    def __init__(
        self,
        # kebab-case unique key ('kitchen-worm-bin').
        name: str = '',
        display_name: str = '',
        description: str = '',
        # Vessel + bed.
        volume_l: float = 40.0,
        bed_mass_kg: float = 12.0,
        # kg worms / kg bed (Eisenia fetida beds run ~0.05-0.15).
        worm_density: float = 0.1,
        # FEEDSTOCK_KINDS entry.
        feedstock_kind: str = 'mixed',
        c_to_n_ratio: float = 25.0,
        # 0-1 gravimetric moisture (worm beds want ~0.7-0.85).
        moisture_target: float = 0.8,
        temperature_c: float = 20.0,
        # How cured the castings are (days) — maturity gates release.
        maturity_days: float = 60.0,
        # The release profile this bed leaches (a VermicompostProfile).
        release_profile_name: str = '',
        # Flow-coupling mode + schedule (schedule used in periodic only).
        mode: str = 'direct',
        on_minutes: float = 20.0,
        cycle_hours: float = 6.0,
        provenance_id: str = '',
        notes: str = '',
        manager=None,
    ):
        self.name = name
        self.display_name = display_name
        self.description = description
        self.volume_l = volume_l
        self.bed_mass_kg = bed_mass_kg
        self.worm_density = worm_density
        self.feedstock_kind = feedstock_kind
        self.c_to_n_ratio = c_to_n_ratio
        self.moisture_target = moisture_target
        self.temperature_c = temperature_c
        self.maturity_days = maturity_days
        self.release_profile_name = release_profile_name
        self.mode = mode
        self.on_minutes = on_minutes
        self.cycle_hours = cycle_hours
        self.provenance_id = provenance_id
        self.notes = notes


class VermicompostProfile(treeObject):
    """The soluble-nutrient RELEASE profile of mature castings.

    concentrations_json: {species_name: mg per kg of bed available to
    leach} — the POOL the bed can transfer into passing water. Distinct
    from aqp-2's NutrientProfile (a water solution); this is the source
    reservoir. Values are ABSTRACT PRIORS (literature range) until a
    bed is measured — priors_flagged carries that admission."""

    @treeObjectInit
    def __init__(
        self,
        name: str = '',
        display_name: str = '',
        description: str = '',
        # {species_name: mg soluble / kg bed} (JSON).
        concentrations_json: str = '{}',
        # First-order mineralization rate at 20 C (per day) — how fast
        # the bound pool becomes soluble. Abstract prior.
        k_min_per_day_20c: float = 0.03,
        # Q10 for the temperature response of k_min.
        q10: float = 2.0,
        # Mass-transfer coefficient (per hour of contact) — leaching
        # efficiency of the concentration gradient. Abstract prior.
        transfer_coeff_per_hr: float = 0.15,
        priors_flagged: bool = True,
        source: str = '',
        provenance_id: str = '',
        notes: str = '',
        manager=None,
    ):
        self.name = name
        self.display_name = display_name
        self.description = description
        self.concentrations_json = concentrations_json
        self.k_min_per_day_20c = k_min_per_day_20c
        self.q10 = q10
        self.transfer_coeff_per_hr = transfer_coeff_per_hr
        self.priors_flagged = priors_flagged
        self.source = source
        self.provenance_id = provenance_id
        self.notes = notes


class CompostLoopDefinition(treeObject):
    """Binds a compost bin + a pot system + the mode into one runnable,
    rankable configuration (mirrors PotSystemDefinition)."""

    @treeObjectInit
    def __init__(
        self,
        name: str = '',
        display_name: str = '',
        description: str = '',
        bin_name: str = '',
        # The PotSystemDefinition whose water this bin enriches.
        pot_system_name: str = '',
        # Overrides the bin's mode when set (else the bin's mode).
        mode: str = '',
        # Assumed loop flow (L/hr) pending aqp-3; a knob so aqp-7 runs
        # independently. When the bound pot system's water carries
        # flow_rate_l_per_hr, the analysis prefers that.
        assumed_flow_l_per_hr: float = 1.5,
        # Persisted enrichment snapshot (JSON) — simulate writes it;
        # scoring binds to it. Empty until first computed.
        enrichment_result_json: str = '',
        provenance_id: str = '',
        notes: str = '',
        manager=None,
    ):
        self.name = name
        self.display_name = display_name
        self.description = description
        self.bin_name = bin_name
        self.pot_system_name = pot_system_name
        self.mode = mode
        self.assumed_flow_l_per_hr = assumed_flow_l_per_hr
        self.enrichment_result_json = enrichment_result_json
        self.provenance_id = provenance_id
        self.notes = notes
