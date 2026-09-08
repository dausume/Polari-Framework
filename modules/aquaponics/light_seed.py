"""
@cross-cutting
@module aquaponics.light_seed
@tags @xc:bindings

Demo light spectrum + source rows (plant-growth-sim phase 8,
2026-07-15) — one 'blackbody' spectrum at the sun's 5778K photosphere
temperature (the standard "sunlight at Earth's surface" reference,
matching electrodevice/custom/photo_derive.py's own choice of the same
constant), bound as a 'point' grow-light source overhead demo-herb-pot
(these are indoor tent/chamber systems — aquaponics.atmosphere_seed's
'ventilated-grow-tent'/'sealed-chamber' — so a grow light is the
physically appropriate source, not direct outdoor sun).
intensity_w_m2 is not a round guess: 207.71 W/m^2 was solved from the
REAL aquaponics.custom.light_field.spectrum_ppfd() computation to land at
~350 PPFD — matching the healthy system's existing static
AtmosphereDefinition.light_ppfd_umol_m2_s (aqp-5's own
'ventilated-grow-tent' row) so the two independent light-modeling
paths (static field vs computed light-field) tell a plausible,
consistent story for the demo, even though they're genuinely separate
computations.

@consumers
  - polariServer seed_pairs
@see /AQUAPONICS_POT_SHAPE_PLAN.md phase 8
"""

SEED_LIGHT_SPECTRA = [
    {
        'name': 'sunlight-5778k',
        'display_name': 'Sunlight (5778K blackbody)',
        'description': "The standard reference model for sunlight at "
                       "Earth's surface — a 5778K blackbody spectrum "
                       '(the sun\'s photosphere temperature), same '
                       'constant electrodevice/custom/photo_derive.py uses '
                       'for its own solar-cell calculations.',
        'kind': 'blackbody',
        'wavelength_nm': 550.0,
        'bandwidth_nm': 10.0,
        'temperature_k': 5778.0,
        'provenance_id': 'plant-growth-sim phase 8',
        'notes': 'PAR energy fraction ~36.75% of total blackbody '
                 'emission (computed, not a literature citation).',
    },
    {
        'name': 'red-led-660nm',
        'display_name': 'Red LED grow light (660nm)',
        'description': 'A narrow-band red LED — the "particular '
                       'wavelength" case, distinct from the broadband '
                       'blackbody spectrum above.',
        'kind': 'monochromatic',
        'wavelength_nm': 660.0,
        'bandwidth_nm': 20.0,
        'temperature_k': 5778.0,
        'provenance_id': 'plant-growth-sim phase 8',
        'notes': '660nm sits inside the PAR band (400-700nm) — full '
                 'PAR overlap for this narrow band.',
    },
]

SEED_LIGHT_SOURCES = [
    {
        'name': 'demo-herb-pot-grow-light',
        'display_name': 'Demo herb pot overhead grow light',
        'description': 'A point source directly above demo-herb-pot, '
                       'bound to the healthy ventilated-tent system.',
        'source_kind': 'point',
        'azimuth_deg': 180.0,
        'elevation_deg': 60.0,
        # 40cm (400mm) above the pot's core origin — a plausible
        # fixture height for a small grow tent.
        'position_mm_json': '[0.0, 0.0, 400.0]',
        # Solved from the real spectrum_ppfd() computation to land at
        # ~350 PPFD at the canopy — see module docstring.
        'intensity_w_m2': 207.71,
        'spectrum_name': 'sunlight-5778k',
        'provenance_id': 'plant-growth-sim phase 8',
        'notes': 'bound via PotSystemDefinition.light_source_name on '
                 "'basil-aquaponic-tent'.",
    },
]
