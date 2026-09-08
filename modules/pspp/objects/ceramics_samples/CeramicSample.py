"""
@module pspp.objects.ceramics_samples.CeramicSample

Row class CeramicSample of the pspp module — one class per file (design §7), split
from ceramics_samples_basis.py (sap-2c). The class docstring below is the explanation.
"""
from objectTreeDecorators import treeObject, treeObjectInit
from pspp.objects.ceramics_samples._shared import TEMP_CLAIM

class CeramicSample(treeObject):
    """One usable ceramic body + its temperature/sourcing/carbon
    profile. A row is a SAMPLE a maker can target, not a measured
    datasheet — temp_claim_status says how firm each number is."""

    @treeObjectInit
    def __init__(
        self,
        name: str = '',
        display_name: str = '',
        # earthenware | stoneware | fireclay | cordierite | mullite |
        # alumina | silicon-carbide | dolomitic-basic | forsterite |
        # zirconia (free string — extensible).
        family: str = '',
        # JSON list of {material, tier, note} — the feedstocks.
        feedstocks_json: str = '[]',
        # Rollup accessibility (worst feedstock tier) — one of
        # ACCESSIBILITY_TIERS.
        accessibility_tier: str = 'common-industrial',
        # Peak temperature to MAKE it (fire/sinter), Celsius.
        peak_firing_temp_c: float = 0.0,
        # Max continuous SERVICE temperature, Celsius (approximate).
        max_service_temp_c: float = 0.0,
        # Softening/melting onset, Celsius (approximate; 0 = unknown).
        softening_temp_c: float = 0.0,
        temp_claim_status: str = TEMP_CLAIM,
        # THERMAL_SHOCK entry.
        thermal_shock: str = 'moderate',
        # REFRACTORY_CLASSES entry.
        refractory_class: str = 'not-refractory',
        # CARBON_PROFILES entry.
        carbon_profile: str = 'neutral',
        # JSON list of use-case strings.
        use_cases_json: str = '[]',
        # 'vessel' | 'kiln-furniture' | 'refractory-brick' |
        # 'furnace-lining' | 'crucible' | 'heating-element' — its role
        # in the escalation ladder ('' = end product only).
        ladder_role: str = '',
        # 'local' | 'non-local' — which track it belongs to.
        track: str = 'local',
        source_reference: str = '',
        provenance_id: str = '',
        notes: str = '',
        manager=None,
    ):
        self.name = name
        self.display_name = display_name
        self.family = family
        self.feedstocks_json = feedstocks_json
        self.accessibility_tier = accessibility_tier
        self.peak_firing_temp_c = peak_firing_temp_c
        self.max_service_temp_c = max_service_temp_c
        self.softening_temp_c = softening_temp_c
        self.temp_claim_status = temp_claim_status
        self.thermal_shock = thermal_shock
        self.refractory_class = refractory_class
        self.carbon_profile = carbon_profile
        self.use_cases_json = use_cases_json
        self.ladder_role = ladder_role
        self.track = track
        self.source_reference = source_reference
        self.provenance_id = provenance_id
        self.notes = notes
