"""
@module pspp.characterization

mtt-2 characterization: HOW a maker actually SEES what a material is —
XRD and FTIR as first-class methods, each explained in plain language
so a non-specialist can follow what a measurement means and why.

Why FTIR matters here (Dustin): our headline materials — geopolymers,
sol-gels, silica gels — are AMORPHOUS. XRD needs long-range crystalline
order, so on a gel it shows only a broad "halo" (little information).
FTIR reads molecular BONDS (Si-O-Si, Si-O-Al, O-H, carbonate), which
are present whether or not the material is crystalline — so it suits
exactly the statistical/amorphous materials this module is built for.
FTIR also DETECTS CARBONATION (a ~1400-1450 cm-1 carbonate band), so it
is the honest way to VERIFY the olivine carbon-negative pathway.

- CHARACTERIZATION_METHODS: XRD + FTIR as data — what each measures,
  how it works (plain), its diagnostic signals + what they mean, and
  whether it is locally + safely buildable (an XRD source is a real
  radiation hazard; FTIR is non-ionizing and safe, though ambitious).
- simulated_ftir(): the diagnostic FTIR bands a given aluminosilicate
  would show — the main Si-O-T stretch (position shifts LOWER with more
  Al / less polymerization, APPROXIMATE + cited), plus water and
  carbonate bands when present, each with a plain-language reading.
  Peak intensities and exact positions refuse (they need the real
  instrument's calibration).

@consumers
  - pspp.pspp_api (/api/pspp/characterization/*)
  - pspp.selftest_characterization
"""

#: Main aluminosilicate Si-O-T asymmetric-stretch band vs Si:Al ratio
#: (cm-1, APPROXIMATE — geopolymer/zeolite FTIR literature): the band
#: moves to LOWER wavenumber as Al substitutes for Si (heavier, weaker
#: bond) and as the network is less polymerized. Anchors only; between
#: values interpolate, outside they clamp with an honest note.
_SIOT_ANCHORS = [
    (1.0, 985.0),   # Si:Al = 1 (nepheline/kalsilite-like)
    (2.0, 1010.0),  # Si:Al = 2 (ideal Na-PSS geopolymer)
    (3.0, 1035.0),  # Si:Al = 3 (albite-like)
    (6.0, 1065.0),  # silica-rich
]
_PURE_SILICA_CM = 1080.0  # no Al at all

_CARBONATE_NOTE = (
    'a band here means CARBONATE has formed — CO2 reacted into the '
    'material. Wanted for the olivine carbon-negative pathway '
    '(verifies sequestration); unwanted as efflorescence on a cured '
    'geopolymer.')


CHARACTERIZATION_METHODS = [
    {
        'name': 'xrd',
        'display_name': 'X-ray diffraction (XRD)',
        'measures': 'long-range CRYSTALLINE order — which crystal '
                    'phases are present, and their atomic spacings',
        'how_plain': 'A crystal is atoms stacked in a regular, '
                     'repeating grid. Shine X-rays on it and they '
                     'bounce off those regular planes only at special '
                     'angles — the pattern of angles is a fingerprint '
                     'that names the crystal. An amorphous (glassy) '
                     'material has no regular grid, so it gives just a '
                     'broad blurry "halo", not sharp lines.',
        'key_signals': [
            {'signal': 'sharp peaks at set angles',
             'means': 'a crystalline phase — each set of peaks names '
                      'one mineral (e.g. leucite, kalsilite, quartz)'},
            {'signal': 'broad halo ~27-30 deg 2-theta',
             'means': 'an AMORPHOUS gel (geopolymer / silica) — no '
                      'long-range order, so XRD can say little more'},
            {'signal': 'peaks sharpening / appearing on heating',
             'means': 'crystallization — the gel is turning into a '
                      'ceramic (this is the geopolymer->ceramic path)'},
        ],
        'suits': 'crystalline ceramics; watching crystallization '
                 'onset when a geopolymer is fired',
        'weak_on': 'amorphous gels + glasses (only a halo)',
        'local_buildable': 'hard',
        'safety': 'an X-ray source is a REAL radiation hazard — this '
                  'is NOT a safe DIY build; use a lab or a paid '
                  'service scan',
        'source_reference': 'Standard materials characterization '
                            '(Cullity, Elements of X-ray Diffraction).',
    },
    {
        'name': 'ftir',
        'display_name': 'Fourier-transform infrared (FTIR)',
        'measures': 'molecular BONDS — which chemical linkages are '
                    'present (Si-O-Si, Si-O-Al, O-H water, carbonate)',
        'how_plain': 'Every chemical bond is like a tiny spring that '
                     'vibrates at its own pitch. Infrared light is a '
                     'range of "pitches"; a bond absorbs the one that '
                     'matches its vibration. So the pattern of which '
                     'infrared colors get absorbed tells you which '
                     'bonds are in the material. Crucially this works '
                     'on GLASSY/amorphous materials too — which is why '
                     'it suits geopolymers and gels where XRD is '
                     'nearly blind.',
        'key_signals': [
            {'signal': 'main band 950-1100 cm-1 (Si-O-T stretch)',
             'means': 'the backbone aluminosilicate bond. Its position '
                      'moves LOWER with more aluminium and a less '
                      'connected network, so it TRACKS geopolymer- '
                      'ization — a lower number = more Al / less '
                      'polymerized'},
            {'signal': 'band ~1400-1450 cm-1 (carbonate)',
             'means': _CARBONATE_NOTE},
            {'signal': 'bands ~1640 + ~3400 cm-1 (water / O-H)',
             'means': 'free + bound water and hydroxyl — dries down as '
                      'the material cures or is heated'},
            {'signal': 'band ~450 cm-1 (Si-O-Si bending)',
             'means': 'the network connectivity / bending mode'},
            {'signal': 'band ~560 cm-1 (secondary building units)',
             'means': 'ring/zeolite-like ordering starting to form'},
        ],
        'suits': 'AMORPHOUS geopolymers, sol-gels, glasses; detecting '
                 'CARBONATION (carbon-negative verification); tracking '
                 'curing (water leaving) + polymerization',
        'weak_on': 'naming a specific crystal phase (XRD is better '
                   'for that) + absolute quantification without '
                   'calibration',
        'local_buildable': 'ambitious',
        'safety': 'SAFE — infrared is non-ionizing (it is just heat/ '
                  'light). The build is the hard part, not the hazard.',
        'source_reference': 'Geopolymer/zeolite FTIR literature '
                            '(Davidovits; Mozgawa et al. on Si-O-T '
                            'band shifts). Positions are approximate '
                            'and material-specific.',
        'build_note': 'A true FTIR needs a broadband IR source, an '
                      'interferometer (or monochromator) and an IR '
                      'detector — the hardest of the common tools. The '
                      'VISIBLE-light spectrometer (a DVD grating + a '
                      'webcam) is the accessible cousin that already '
                      'powers most colorimetric assays; build that '
                      'first, treat FTIR as the reach goal.',
    },
]


import json as _json

#: The FTIR main-band calibration as a provisional, REFUSING dataset:
#: the code model uses cited literature ANCHORS, but a real band-vs-
#: composition calibration (from measured spectra) refuses until
#: digitized — the honest data ask behind the approximate position.
SEED_CHARACTERIZATION_DATASETS = [
    {
        'name': 'ftir-siot-band-vs-si-al',
        'source_reference': 'Geopolymer/zeolite FTIR literature '
                            '(Mozgawa et al.; Davidovits) — a specific '
                            'measured band-position vs Si:Al table is '
                            'PENDING digitization',
        'status': 'provisional-low-confidence',
        'independent_variables_json': '["si_al_ratio"]',
        'dependent_variables_json': '["siot_band_cm"]',
        'units_json': _json.dumps({
            'si_al_ratio': 'mol Si / mol Al',
            'siot_band_cm': 'cm-1'}),
        'source_conditions_json': _json.dumps({
            'system': 'alkali-activated aluminosilicate (geopolymer)',
            'note': 'the main Si-O-T asymmetric-stretch position; '
                    'material- and instrument-specific, so a real '
                    'calibration replaces the code anchors'}),
        'interpolation_policy': 'linear',
        'extrapolation_policy': 'UNSUPPORTED',
        'validity_domain_json': '{}',
        'digitization_method': 'NOT digitized — code uses literature '
                               'anchors; a measured table refines it',
        'points_json': '[]',
        'qualitative_shape':
            'The main Si-O-T band moves to LOWER wavenumber as Al '
            'substitutes for Si (heavier, weaker bond) and as the '
            'network is less polymerized: ~985 cm-1 near Si:Al=1 up '
            'toward ~1080 cm-1 for pure silica.',
        'notes': 'DATA ASK: digitize a measured FTIR band-position vs '
                 'Si:Al table (or run your own spectrometer standards) '
                 'to replace the code anchors with a calibrated curve. '
                 'The SHIFT DIRECTION is reliable now; the exact number '
                 'is approximate.',
        'provenance_id': 'mtt-2 characterization FTIR seed 2026-07-27',
    },
]


def _method(name):
    for m in CHARACTERIZATION_METHODS:
        if m['name'] == name:
            return m
    return None


def characterization_methods():
    """The method catalog — plain-language what/how + diagnostic
    signals + local-buildability + safety, for a non-specialist."""
    return {'ok': True, 'methods': CHARACTERIZATION_METHODS}


def _siot_band(si_al_ratio):
    """Approximate main Si-O-T band position (cm-1) for a Si:Al ratio,
    interpolated across the cited anchors. Returns (position, note)."""
    if si_al_ratio is None:
        return None, ('no Si:Al ratio given — the main-band POSITION '
                      'needs a composition; the band ASSIGNMENT still '
                      'holds')
    try:
        r = float(si_al_ratio)
    except (TypeError, ValueError):
        return None, f'Si:Al ratio {si_al_ratio!r} is not a number'
    if r <= 0:
        return None, f'Si:Al ratio {r} must be positive'
    anchors = _SIOT_ANCHORS
    if r <= anchors[0][0]:
        return anchors[0][1], ('at/below Si:Al=1 — clamped to the '
                               'lowest anchor (approximate)')
    if r >= anchors[-1][0]:
        # trend on toward pure silica, gently.
        hi_r, hi_cm = anchors[-1]
        frac = min(1.0, (r - hi_r) / (20.0 - hi_r))
        return (hi_cm + (_PURE_SILICA_CM - hi_cm) * frac,
                'silica-rich — extrapolated toward the pure-silica '
                'band (approximate)')
    for (r0, c0), (r1, c1) in zip(anchors, anchors[1:]):
        if r0 <= r <= r1:
            pos = c0 + (c1 - c0) * (r - r0) / (r1 - r0)
            return pos, 'interpolated across the cited anchors'
    return None, 'position unresolved'


def simulated_ftir(si_al_ratio=None, has_water=True,
                   has_carbonate=False):
    """The diagnostic FTIR bands an aluminosilicate would show, each
    with a plain-language reading. The main Si-O-T band POSITION is
    approximate (cited anchors); intensities + exact positions REFUSE
    (they need the real instrument's calibration). Always returns the
    band assignments (those are structural, not numeric)."""
    ftir = _method('ftir')
    pos, note = _siot_band(si_al_ratio)
    bands = [{
        'assignment': 'Si-O-T asymmetric stretch (main aluminosilicate '
                      'band)',
        'approxPositionCm': (round(pos, 0) if pos is not None else None),
        'region_cm': '950-1100',
        'reading': ('the backbone bond; lower wavenumber = more Al / '
                    'less polymerized. ' + note),
        'confidence': 'approximate-position' if pos is not None
        else 'assignment-only',
    }]
    if has_water:
        bands.append({
            'assignment': 'O-H stretch + H-O-H bend (water/hydroxyl)',
            'region_cm': '~3400 and ~1640',
            'reading': 'water + OH present; shrinks as the material '
                       'cures or is fired',
            'confidence': 'assignment-only'})
    if has_carbonate:
        bands.append({
            'assignment': 'carbonate (CO3) stretch',
            'region_cm': '~1400-1450',
            'reading': _CARBONATE_NOTE,
            'confidence': 'assignment-only'})
    bands.append({
        'assignment': 'Si-O-Si bending',
        'region_cm': '~450',
        'reading': 'network connectivity (bending mode)',
        'confidence': 'assignment-only'})
    return {
        'ok': True,
        'method': 'ftir',
        'siAlRatio': si_al_ratio,
        'bands': bands,
        'interpretation': (
            'FTIR reads the BONDS, so it works on this amorphous '
            'material where XRD would show only a halo. Track the main '
            '950-1100 band to follow polymerization, the ~3400/1640 '
            'bands to follow drying, and watch ~1400-1450 for '
            'carbonate (CO2 uptake).'),
        'refusals': [
            'peak INTENSITIES are not predicted — they need your '
            'measured spectrum (baseline + calibration)',
            'the exact main-band position is instrument- and '
            'composition-specific; the value here is a literature '
            'approximation, and the DIRECTION of its shift is the '
            'reliable part',
        ],
        'howPlain': ftir['how_plain'],
    }
