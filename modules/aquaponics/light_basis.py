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

The actual field/incidence MATH (aquaponics/custom/light_field.py) reuses
electrodevice/custom/photo_derive.py's proven numeric blackbody-photon-
integration TECHNIQUE (E^2/(exp(E/kT)-1)-style quadrature), adapted
from eV/bandgap-threshold framing to nm/PAR-band framing — real
photon counting, not an approximate W/m^2->umol/J fudge constant.

@consumers
  - aquaponics.custom.light_field (the field/incidence engine)
  - aquaponics.plant_stress_basis (the 'light' stress type's optional
    computed-value override, when a PotSystemDefinition.
    light_source_name is bound)
  - polariServer.defClassList (auto-CRUDE + persistence)
@see /AQUAPONICS_POT_SHAPE_PLAN.md phase 8
"""
# sap-2c INDEX (design §7): the classes live one-per-file under objects/light/;
# this file re-exports them (imports keep working) and holds what they share.
# The original imports stay: names this file imported were re-exported implicitly.

from objectTreeDecorators import treeObject, treeObjectInit

from aquaponics.objects.light._shared import LIGHT_SOURCE_KINDS, LIGHT_SPECTRUM_KINDS  # noqa: F401
from aquaponics.objects.light.LightSpectrumDefinition import LightSpectrumDefinition  # noqa: F401
from aquaponics.objects.light.LightSourceDefinition import LightSourceDefinition  # noqa: F401
