"""
@module biomining.objects.biomining.BioextractionAgent

Row class BioextractionAgent of the biomining module — one class per file (design §7), split
from biomining_basis.py (sap-2c). The class docstring below is the explanation.
"""
from objectTreeDecorators import treeObject, treeObjectInit

class BioextractionAgent(treeObject):
    """One organism that pulls a target element from the water."""

    @treeObjectInit
    def __init__(
        self,
        # kebab-case unique key ('magnetotactic-bacteria').
        name: str = '',
        display_name: str = '',
        # AGENT_TYPES entry.
        agent_type: str = 'bacteria',
        # MECHANISMS entry.
        mechanism: str = 'biomineralization',
        # The element it targets ('Fe', 'Mn', 'C', 'P', 'Ni', ...).
        target_element: str = 'Fe',
        # 0-1 — how specifically it takes the target vs everything else.
        selectivity: float = 0.8,
        # mg target element per g of agent biomass per day.
        uptake_rate_mg_per_g_per_day: float = 30.0,
        # 'fresh' | 'salt' | 'both'.
        water_type: str = 'both',
        optimal_ph: float = 7.0,
        # What it leaves behind (informational).
        byproduct: str = '',
        is_prior: bool = True,
        provenance_id: str = '',
        notes: str = '',
        manager=None,
    ):
        self.name = name
        self.display_name = display_name
        self.agent_type = agent_type
        self.mechanism = mechanism
        self.target_element = target_element
        self.selectivity = selectivity
        self.uptake_rate_mg_per_g_per_day = uptake_rate_mg_per_g_per_day
        self.water_type = water_type
        self.optimal_ph = optimal_ph
        self.byproduct = byproduct
        self.is_prior = is_prior
        self.provenance_id = provenance_id
        self.notes = notes
