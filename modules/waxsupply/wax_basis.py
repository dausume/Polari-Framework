"""
@cross-cutting
@module waxsupply.wax_basis
@tags @xc:bindings

Bio wax SOURCES for hydroponic + food-forest systems (wax-1). Wax is a
cornerstone of the manufacturing pipeline — lost-wax molds + electronic
masking for device fabrication — so we need wax that grows in the same
systems. This models the biological sources (plants, crop byproducts,
insects, macroalgae) with their wax properties, hydroponic feasibility,
and manufacturing use, each linked to a real materialsScience wax
material. Own module + own data (framework-core only).

  WaxSourceDefinition — one source: what organism/byproduct yields the
                        wax, its melt point + hardness, how feasibly it
                        grows hydroponically, its per-plant/feedstock
                        yield, its primary manufacturing use, and the
                        MaterialsScienceMaterial it refines to.

@consumers
  - polariServer.defClassList (auto-CRUDE + persistence)
  - waxsupply.custom.wax_analysis; supplychain (wax as a material output)
@see materialsScience/ wax materials (beeswax, carnauba-wax, ...)
"""

from objectTreeDecorators import treeObject, treeObjectInit

#: Where the wax comes from.
WAX_SOURCE_TYPES = ('plant-leaf', 'plant-seed', 'plant-berry',
                    'crop-byproduct', 'insect', 'macroalgae')

#: How feasibly the source grows in a hydroponic/food-forest system.
HYDROPONIC_FEASIBILITY = ('easy', 'moderate', 'hard', 'not-hydroponic')

#: Primary manufacturing use (molds + masks are the cornerstone).
WAX_USES = ('mold', 'electronic-mask', 'coating', 'candle',
            'wax-additive', 'lubricant')


class WaxSourceDefinition(treeObject):
    """One biological wax source + its properties + hydroponic fit."""

    @treeObjectInit
    def __init__(
        self,
        # kebab-case unique key ('carnauba').
        name: str = '',
        display_name: str = '',
        # WAX_SOURCE_TYPES entry.
        source_type: str = 'plant-leaf',
        # The organism / byproduct ('Copernicia palm leaves').
        organism: str = '',
        # The MaterialsScienceMaterial this wax IS ('carnauba-wax').
        wax_material_ref: str = '',
        # Melt point (C) + relative hardness (0-1) — set mold/mask fit.
        melt_point_c: float = 60.0,
        hardness: float = 0.5,
        # HYDROPONIC_FEASIBILITY entry.
        hydroponic_feasibility: str = 'moderate',
        # Realized yield: grams of wax per plant per year (plants) or
        # per kg of feedstock (byproducts) — unit named in yield_basis.
        yield_g_per_year: float = 0.0,
        yield_basis: str = 'per-plant-per-year',
        # WAX_USES entry — the primary manufacturing use.
        primary_use: str = 'mold',
        # Other WAX_USES it also serves (JSON list).
        secondary_uses_json: str = '[]',
        is_prior: bool = True,
        provenance_id: str = '',
        notes: str = '',
        manager=None,
    ):
        self.name = name
        self.display_name = display_name
        self.source_type = source_type
        self.organism = organism
        self.wax_material_ref = wax_material_ref
        self.melt_point_c = melt_point_c
        self.hardness = hardness
        self.hydroponic_feasibility = hydroponic_feasibility
        self.yield_g_per_year = yield_g_per_year
        self.yield_basis = yield_basis
        self.primary_use = primary_use
        self.secondary_uses_json = secondary_uses_json
        self.is_prior = is_prior
        self.provenance_id = provenance_id
        self.notes = notes
