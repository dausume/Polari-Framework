"""
@module aquaponics.objects.light.LightSpectrumDefinition

Row class LightSpectrumDefinition of the aquaponics module — one class per file (design §7), split
from light_basis.py (sap-2c). The class docstring below is the explanation.
"""
from objectTreeDecorators import treeObject, treeObjectInit

class LightSpectrumDefinition(treeObject):
    """One light spectrum — monochromatic or a blackbody thermal
    curve. See module docstring for the two-kind design."""

    @treeObjectInit
    def __init__(
        self,
        # unique key ('sunlight-5778k', 'red-led-660nm').
        name: str = '',
        display_name: str = '',
        description: str = '',
        # LIGHT_SPECTRUM_KINDS entry.
        kind: str = 'blackbody',
        # 'monochromatic' fields.
        wavelength_nm: float = 550.0,
        bandwidth_nm: float = 10.0,
        # 'blackbody' field — 5778 K is the sun's photosphere, the
        # standard reference temperature for "sunlight at Earth's
        # surface" (the exact same constant electrodevice/
        # photo_derive.py's own solar-cell calculations use).
        temperature_k: float = 5778.0,
        provenance_id: str = '',
        notes: str = '',
        manager=None,
    ):
        self.name = name
        self.display_name = display_name
        self.description = description
        self.kind = kind
        self.wavelength_nm = wavelength_nm
        self.bandwidth_nm = bandwidth_nm
        self.temperature_k = temperature_k
        self.provenance_id = provenance_id
        self.notes = notes
