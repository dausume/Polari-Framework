"""
@cross-cutting
@module biomining.biomining_basis
@tags @xc:bindings

Biomining / bioextraction as specialized aquaponic variants (biomine-1).
Own module + own data (framework-core only; a lazy tanks read resolves a
coupled system's surplus for the nutrient-recovery variant). Organisms
(bacteria / algae / biofilm) pull target elements out of the water, and
a refinement pathway carries the raw element to a useful product —
iron → ferrite for magnets, mixed metals → steel feedstock, concentrated
carbon → carbon-nanotube feedstock, or excess nutrients recovered to
SUPPLEMENT a system that lacks them. Each variant is a distinct
"specialized hydroponic" configuration.

Three treeObjects (auto-CRUDE + persisted — object-coherence):

  BioextractionAgent      one organism: what element it targets, by what
                          mechanism, how selectively + how fast.
  BiomineralProduct       the refined output + its pathway (element →
                          refined form → a real MaterialsScienceMaterial
                          where one exists, e.g. 'ferrite',
                          'carbon-nanotube').
  BiomineSystemDefinition a specialized aquaponic VARIANT binding
                          agents + a product + a source stream, with the
                          extraction cap that keeps it from stripping
                          the parent (the biochar/regulation idiom).

@consumers
  - polariServer.defClassList (auto-CRUDE + persistence)
  - biomining.biomining_analysis
@see materialsScience/ (ferrite + CNT targets), tanks/, microalgae/
"""

from objectTreeDecorators import treeObject, treeObjectInit

AGENT_TYPES = ('bacteria', 'algae', 'fungi', 'biofilm', 'plant')
#: Bio-extraction mechanisms. 'biosynthesis' = fermentation-produced
#: organic ligands (tartrate, glycine) rather than element capture.
MECHANISMS = ('bioaccumulation', 'biosorption', 'bioleaching',
              'biomineralization', 'bioprecipitation', 'biosynthesis')
#: The specialized-aquaponic variants (Dustin's biomining kinds).
#: 'optical-dielectric' = fully-bio-derivable dielectric crystals/glass
#: for precision laser control (KDP/Rochelle/silica/ZnO...).
BIOMINE_VARIANTS = ('iron-ferrite', 'steel-feedstock',
                    'carbon-nanotube', 'nutrient-recovery',
                    'trace-metal', 'optical-dielectric')
#: Where the target element comes from.
SOURCE_KINDS = ('tank', 'reactor', 'aquaponics', 'feedstock')
PRODUCT_KINDS = ('ferrite-magnet', 'steel-feedstock',
                 'carbon-nanotube-feedstock', 'recovered-nutrient',
                 'metal-powder', 'electro-optic-crystal',
                 'optical-glass', 'coating-dielectric',
                 'birefringent-crystal', 'ir-window',
                 'nickel-metal', 'coated-steel')


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


class BiomineralProduct(treeObject):
    """A refined biomining product + its element→product pathway."""

    @treeObjectInit
    def __init__(
        self,
        # kebab-case unique key ('ferrite-magnet-feedstock').
        name: str = '',
        display_name: str = '',
        # PRODUCT_KINDS entry.
        product_kind: str = 'ferrite-magnet',
        # The element the agents recover ('Fe', 'C', 'P', ...).
        source_element: str = 'Fe',
        # The refined chemical form ('magnetite Fe3O4 → sintered
        # ferrite').
        refined_form: str = '',
        # Optional MaterialsScienceMaterial name the pathway ends at
        # ('ferrite', 'carbon-nanotube'); '' = no material row yet.
        material_ref: str = '',
        # Ordered refinement steps (JSON list of strings).
        refinement_pathway_json: str = '[]',
        # mg refined product per mg of recovered element (stoichiometry
        # + purification loss). e.g. Fe→Fe3O4 ≈ 1.38; C→purified ≈ 0.8.
        element_to_product_yield: float = 1.0,
        # Target purity (0-1) of the refined product.
        purity_target: float = 0.9,
        is_prior: bool = True,
        provenance_id: str = '',
        notes: str = '',
        manager=None,
    ):
        self.name = name
        self.display_name = display_name
        self.product_kind = product_kind
        self.source_element = source_element
        self.refined_form = refined_form
        self.material_ref = material_ref
        self.refinement_pathway_json = refinement_pathway_json
        self.element_to_product_yield = element_to_product_yield
        self.purity_target = purity_target
        self.is_prior = is_prior
        self.provenance_id = provenance_id
        self.notes = notes


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
