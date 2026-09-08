"""
@module casting.objects.casting.MasterFeedstockDefinition

Row class MasterFeedstockDefinition of the casting module — one class per file (design §7), split
from casting_basis.py (sap-2c). The class docstring below is the explanation.
"""
from objectTreeDecorators import treeObject, treeObjectInit
from casting.objects.casting._shared import FEEDSTOCK_PRIORITIES, MASTER_MATERIAL_KINDS, REMOVAL_ROUTES

class MasterFeedstockDefinition(treeObject):
    """A material the sacrificial master can be made from, with its
    make route(s), mechanical/thermal data (claim status attached),
    and how it leaves the mold. Natural wax rows link back to their
    waxsupply source; commercial rows carry their own numbers."""

    @treeObjectInit
    def __init__(
        self,
        name: str = '',
        display_name: str = '',
        # MASTER_MATERIAL_KINDS entry.
        material_kind: str = 'natural-wax',
        # FEEDSTOCK_PRIORITIES entry — 'core' is the local focus.
        priority: str = 'supported',
        # solgel_sourcing ACCESSIBILITY_TIERS vocabulary.
        accessibility_tier: str = 'common-industrial',
        renewable: bool = False,
        # natural waxes: the waxsupply WaxSourceDefinition this rides.
        wax_source_ref: str = '',
        # JSON list of MAKE_ROUTES entries this feedstock supports.
        make_routes_json: str = '[]',
        # --- mechanical/thermal (claim status travels with them) ---
        density_kg_m3: float = 0.0,
        compressive_strength_mpa: float = 0.0,
        # loses structural credibility here (wax: near melt; PLA: Tg).
        soften_temp_c: float = 0.0,
        melt_temp_c: float = 0.0,
        claim_status: str = 'literature-approximate',
        # --- print params for the FDM/auger routes ---
        print_temp_c: float = 0.0,
        nozzle_diameter_mm: float = 0.4,
        layer_height_mm: float = 0.2,
        print_speed_mm_s: float = 30.0,
        # --- the sacrificial exit ---
        removal_route: str = 'melt-out',
        removal_temp_c: float = 0.0,
        removal_notes: str = '',
        is_prior: bool = True,
        notes: str = '',
        provenance_id: str = '',
        manager=None,
    ):
        self.name = name
        self.display_name = display_name
        self.material_kind = (material_kind
                              if material_kind in MASTER_MATERIAL_KINDS
                              else 'natural-wax')
        self.priority = (priority if priority in FEEDSTOCK_PRIORITIES
                         else 'supported')
        self.accessibility_tier = accessibility_tier
        self.renewable = renewable
        self.wax_source_ref = wax_source_ref
        self.make_routes_json = make_routes_json
        self.density_kg_m3 = density_kg_m3
        self.compressive_strength_mpa = compressive_strength_mpa
        self.soften_temp_c = soften_temp_c
        self.melt_temp_c = melt_temp_c
        self.claim_status = claim_status
        self.print_temp_c = print_temp_c
        self.nozzle_diameter_mm = nozzle_diameter_mm
        self.layer_height_mm = layer_height_mm
        self.print_speed_mm_s = print_speed_mm_s
        self.removal_route = (removal_route
                              if removal_route in REMOVAL_ROUTES
                              else 'melt-out')
        self.removal_temp_c = removal_temp_c
        self.removal_notes = removal_notes
        self.is_prior = is_prior
        self.notes = notes
        self.provenance_id = provenance_id
