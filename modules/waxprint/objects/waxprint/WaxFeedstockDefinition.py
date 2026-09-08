"""
@module waxprint.objects.waxprint.WaxFeedstockDefinition

Row class WaxFeedstockDefinition of the waxprint module — one class per file (design §7), split
from waxprint_basis.py (sap-2c). The class docstring below is the explanation.
"""
from objectTreeDecorators import treeObject, treeObjectInit

class WaxFeedstockDefinition(treeObject):
    """An all-natural engineered wax fed as pellets, with its computed
    material properties and thermal-safety window."""

    @treeObjectInit
    def __init__(
        self,
        name: str = '',
        display_name: str = '',
        description: str = '',

        # Links (object coherence).
        wax_material_ref: str = '',      # materialsScience material
        wax_source_ref: str = '',        # waxsupply WaxSourceDefinition

        # Pellet + thermophysical properties (SI-ish, mm for the pellet).
        pellet_diameter_mm: float = 3.0,
        density_kg_m3: float = 950.0,
        specific_heat_j_kgk: float = 2100.0,
        latent_heat_fusion_j_kg: float = 180000.0,
        thermal_conductivity_w_mk: float = 0.25,

        # Phase + SAFETY window (Celsius).
        melt_point_c: float = 82.0,
        # Below this the melt is too stiff to flow (informational).
        safe_melt_min_c: float = 85.0,
        # Thermal-degradation / volatilization ceiling — the HARD safety
        # limit the melt gate refuses to cross.
        safe_melt_max_c: float = 150.0,

        # Arrhenius melt viscosity eta(T)=eta_ref*exp(B(1/T-1/T_ref)).
        viscosity_ref_pa_s: float = 5.0,
        viscosity_ref_temp_c: float = 100.0,
        viscosity_activation_k: float = 6000.0,

        notes: str = '',
        provenance_id: str = '',
        manager=None,
    ):
        self.name = name
        self.display_name = display_name
        self.description = description
        self.wax_material_ref = wax_material_ref
        self.wax_source_ref = wax_source_ref
        self.pellet_diameter_mm = pellet_diameter_mm
        self.density_kg_m3 = density_kg_m3
        self.specific_heat_j_kgk = specific_heat_j_kgk
        self.latent_heat_fusion_j_kg = latent_heat_fusion_j_kg
        self.thermal_conductivity_w_mk = thermal_conductivity_w_mk
        self.melt_point_c = melt_point_c
        self.safe_melt_min_c = safe_melt_min_c
        self.safe_melt_max_c = safe_melt_max_c
        self.viscosity_ref_pa_s = viscosity_ref_pa_s
        self.viscosity_ref_temp_c = viscosity_ref_temp_c
        self.viscosity_activation_k = viscosity_activation_k
        self.notes = notes
        self.provenance_id = provenance_id
