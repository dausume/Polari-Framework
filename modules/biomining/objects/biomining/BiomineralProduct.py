"""
@module biomining.objects.biomining.BiomineralProduct

Row class BiomineralProduct of the biomining module — one class per file (design §7), split
from biomining_basis.py (sap-2c). The class docstring below is the explanation.
"""
from objectTreeDecorators import treeObject, treeObjectInit

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
