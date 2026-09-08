"""
@module waxsupply.objects.wax.WaxSourceDefinition

Row class WaxSourceDefinition of the waxsupply module — one class per file (design §7), split
from wax_basis.py (sap-2c). The class docstring below is the explanation.
"""
from objectTreeDecorators import treeObject, treeObjectInit

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
