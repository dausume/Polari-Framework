"""
@cross-cutting
@module aquaponics.light_basis
@tags @xc:bindings

Plant-growth-sim phase 8 (2026-07-15) — Dustin: "we should define the
direction of sunlight or a growth light in general and be able to
convert its incidence on a plant into a value it absorbs and applies
to growth equation. We should have an independent capability to
simulate light vector fields of both particular wavelengths, and
defined spectrum equations of light (like the standard light from the
sun on the surface of the earth for example)." Confirmed scope
(same session): direct/collimated light first (this phase); diffuse
scattered light via the existing FEM diffusion engine, and per-part-
SHAPE-specific incidence (flat leaf blades vs cylindrical stems/
roots) are both explicitly deferred to a later phase.

Two classes:

  LightSpectrumDefinition — HOW a source's energy distributes across
    wavelength. Two kinds, both Tier-A/always-available (no equation
    authoring required — a custom equation-driven spectrum is future
    work, deliberately not built this pass to keep v1 fast + simple,
    per Dustin's own "much simpler for now"):
      'monochromatic' — a single wavelength ± bandwidth (a specific-
        color grow light, e.g. a red/blue LED panel).
      'blackbody'     — a Planck's-law thermal spectrum at
        temperature_k — THE standard model for "the standard light
        from the sun on the surface of the earth" (5778K, the sun's
        photospheric temperature, is the default).

  LightSourceDefinition — the source itself: 'directional' (sun-like
    — parallel rays from a fixed azimuth/elevation, no position) or
    'point' (a grow light — a fixed position, rays radiate outward),
    a broadband intensity magnitude, and a spectrum reference.

The actual field/incidence MATH (aquaponics/light_field.py) reuses
electrodevice/photo_derive.py's proven numeric blackbody-photon-
integration TECHNIQUE (E^2/(exp(E/kT)-1)-style quadrature), adapted
from eV/bandgap-threshold framing to nm/PAR-band framing — real
photon counting, not an approximate W/m^2->umol/J fudge constant.

@consumers
  - aquaponics.light_field (the field/incidence engine)
  - aquaponics.plant_stress (the 'light' stress type's optional
    computed-value override, when a PotSystemDefinition.
    light_source_name is bound)
  - polariServer.defClassList (auto-CRUDE + persistence)
@see /AQUAPONICS_POT_SHAPE_PLAN.md phase 8
"""

from objectTreeDecorators import treeObject, treeObjectInit

LIGHT_SPECTRUM_KINDS = ('monochromatic', 'blackbody')
LIGHT_SOURCE_KINDS = ('directional', 'point')


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
