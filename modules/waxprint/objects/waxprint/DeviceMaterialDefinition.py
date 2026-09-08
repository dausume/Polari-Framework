"""
@module waxprint.objects.waxprint.DeviceMaterialDefinition

Row class DeviceMaterialDefinition of the waxprint module — one class per file (design §7), split
from waxprint_basis.py (sap-2c). The class docstring below is the explanation.
"""
from objectTreeDecorators import treeObject, treeObjectInit

class DeviceMaterialDefinition(treeObject):
    """A material a printer part is made of — nozzle / auger / chamber /
    bed. Lightweight and waxprint-local (a soft peer of a full
    materialsScience row, linked by material_ref): it carries just the
    handful of properties the print sim actually consumes — thermal
    conductivity (wall temperature uniformity), max service temperature
    (a SECOND safety axis: the part must tolerate its zone temperature),
    thermal mass (bed cooling, wp-2) and a bed adhesion factor (wp-3)."""

    @treeObjectInit
    def __init__(
        self,
        name: str = '',
        display_name: str = '',
        description: str = '',
        role: str = 'multi',
        # Optional link to the full materialsScience material.
        material_ref: str = '',
        thermal_conductivity_w_mk: float = 15.0,
        density_kg_m3: float = 7800.0,
        specific_heat_j_kgk: float = 500.0,
        # The part's own thermal limit (e.g. a PTFE-lined hotend ~260C).
        max_service_temp_c: float = 400.0,
        # For beds: 0..1 first-layer adhesion quality (wp-3).
        bed_adhesion_factor: float = 0.5,
        surface_note: str = '',
        notes: str = '',
        provenance_id: str = '',
        manager=None,
    ):
        self.name = name
        self.display_name = display_name
        self.description = description
        self.role = role
        self.material_ref = material_ref
        self.thermal_conductivity_w_mk = thermal_conductivity_w_mk
        self.density_kg_m3 = density_kg_m3
        self.specific_heat_j_kgk = specific_heat_j_kgk
        self.max_service_temp_c = max_service_temp_c
        self.bed_adhesion_factor = bed_adhesion_factor
        self.surface_note = surface_note
        self.notes = notes
        self.provenance_id = provenance_id
