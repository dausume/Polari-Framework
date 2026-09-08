"""
@module pspp.objects.solgel_sourcing.PrecursorSource

Row class PrecursorSource of the pspp module — one class per file (design §7), split
from solgel_sourcing_basis.py (sap-2c). The class docstring below is the explanation.
"""
from objectTreeDecorators import treeObject, treeObjectInit

class PrecursorSource(treeObject):
    """One sourcing option for a species: how accessible it is and
    what common materials it can be made from."""

    @treeObjectInit
    def __init__(
        self,
        # Unique kebab-case key ('water-glass-from-sand-alkali').
        name: str = '',
        display_name: str = '',
        # The ChemicalSpecies.name this sources.
        species_ref: str = '',
        # One of ACCESSIBILITY_TIERS.
        accessibility_tier: str = 'lab-reagent',
        # JSON list of common inputs this is derivable from (each a
        # {material, tier, note}) — empty = obtained directly.
        common_inputs_json: str = '[]',
        # Prose: how the derivation is done (community-scale).
        derivation: str = '',
        # JSON list of species/reagent names this can SUBSTITUTE FOR
        # (e.g. citric-acid substitutes-for a mineral-acid catalyst) —
        # the substitution map.
        substitutes_for_json: str = '[]',
        # 'community-proven' | 'literature' | 'proposed' — the standing
        # of the accessibility CLAIM (never the numeric performance).
        claim_status: str = 'literature',
        source_reference: str = '',
        provenance_id: str = '',
        notes: str = '',
        manager=None,
    ):
        self.name = name
        self.display_name = display_name
        self.species_ref = species_ref
        self.accessibility_tier = accessibility_tier
        self.common_inputs_json = common_inputs_json
        self.derivation = derivation
        self.substitutes_for_json = substitutes_for_json
        self.claim_status = claim_status
        self.source_reference = source_reference
        self.provenance_id = provenance_id
        self.notes = notes
