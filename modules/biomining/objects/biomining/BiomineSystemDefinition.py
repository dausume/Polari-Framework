"""
@module biomining.objects.biomining.BiomineSystemDefinition

Row class BiomineSystemDefinition of the biomining module — one class per file (design §7), split
from biomining_basis.py (sap-2c). The class docstring below is the explanation.
"""
from objectTreeDecorators import treeObject, treeObjectInit

class BiomineSystemDefinition(treeObject):
    """A specialized aquaponic variant for one biomining purpose."""

    @treeObjectInit
    def __init__(
        self,
        # kebab-case unique key ('iron-ferrite-biomine').
        name: str = '',
        display_name: str = '',
        description: str = '',
        # BIOMINE_VARIANTS entry.
        variant: str = 'iron-ferrite',
        water_type: str = 'fresh',
        # {agent_name: biomass_g} — the working culture.
        agent_stock_json: str = '{}',
        # The BiomineralProduct this system yields.
        product_name: str = '',
        # The stream the element comes from + its kind.
        source_system_name: str = '',
        source_kind: str = 'feedstock',
        # Available target element in the source (mg/day) — the feedstock
        # rate; for nutrient-recovery on a tank it's resolved live.
        source_element_supply_mg_per_day: float = 0.0,
        # REGULATION KNOB: max element pulled per day (mg). 0 = uncapped
        # (flagged when it would strip the source).
        extraction_cap_mg_per_day: float = 0.0,
        # nutrient-recovery only: the lacking system the recovered
        # nutrient is transferred to supplement.
        supplement_target_system: str = '',
        # Persisted yield snapshot (JSON).
        biomine_result_json: str = '',
        provenance_id: str = '',
        notes: str = '',
        manager=None,
    ):
        self.name = name
        self.display_name = display_name
        self.description = description
        self.variant = variant
        self.water_type = water_type
        self.agent_stock_json = agent_stock_json
        self.product_name = product_name
        self.source_system_name = source_system_name
        self.source_kind = source_kind
        self.source_element_supply_mg_per_day = \
            source_element_supply_mg_per_day
        self.extraction_cap_mg_per_day = extraction_cap_mg_per_day
        self.supplement_target_system = supplement_target_system
        self.biomine_result_json = biomine_result_json
        self.provenance_id = provenance_id
        self.notes = notes
