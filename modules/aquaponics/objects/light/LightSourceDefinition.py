"""
@module aquaponics.objects.light.LightSourceDefinition

Row class LightSourceDefinition of the aquaponics module — one class per file (design §7), split
from light_basis.py (sap-2c). The class docstring below is the explanation.
"""
from objectTreeDecorators import treeObject, treeObjectInit

class LightSourceDefinition(treeObject):
    """One light source — directional (sun-like) or point (a grow
    light). Position/direction are in the SAME pot-local (cm*10=mm,
    z-vertical-through-the-pot's-own-center) frame plant_skeleton.py
    already uses, so a source drops into the existing pot/plant scene
    with no extra transform."""

    @treeObjectInit
    def __init__(
        self,
        # unique key ('overhead-sun', 'south-window-led').
        name: str = '',
        display_name: str = '',
        description: str = '',
        # LIGHT_SOURCE_KINDS entry.
        source_kind: str = 'directional',
        # 'directional' — compass azimuth (0=north, 90=east, clockwise)
        # the light travels FROM, and elevation above the horizon
        # (90=straight overhead, 0=grazing the horizon).
        azimuth_deg: float = 180.0,
        elevation_deg: float = 60.0,
        # 'point' — JSON [x,y,z] mm, pot-local frame (e.g. a grow
        # light fixture mounted above the pot).
        position_mm_json: str = '[0.0, 0.0, 400.0]',
        # Broadband irradiance AT THE PLANT (W/m^2) — v1 does not
        # model inverse-square falloff from a point source's own
        # distance; this is the value already-arrived-at-the-canopy
        # magnitude, an honest simplification stated here rather than
        # a silently-wrong distance model.
        intensity_w_m2: float = 1000.0,
        spectrum_name: str = '',
        provenance_id: str = '',
        notes: str = '',
        manager=None,
    ):
        self.name = name
        self.display_name = display_name
        self.description = description
        self.source_kind = source_kind
        self.azimuth_deg = azimuth_deg
        self.elevation_deg = elevation_deg
        self.position_mm_json = position_mm_json
        self.intensity_w_m2 = intensity_w_m2
        self.spectrum_name = spectrum_name
        self.provenance_id = provenance_id
        self.notes = notes
