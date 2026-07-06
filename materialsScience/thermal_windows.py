"""
@cross-cutting
@module materialsScience.thermal_windows
@tags @xc:bindings

THERMAL PROCESSING WINDOWS — Dustin's no-volatiles rule as a gate.

From his notebook (Open-Source-Economy-Notes/01-Wax-Materials-And-
Properties, 'Base Wax Properties' pages IMG_2823/2824): every base wax
has a melt range AND a Smoking Point Temperature (where volatiles
emit). A formulation is processable at temperature T only when EVERY
component has melted (T ≥ max melt-high) and NO component smokes
(T ≤ min smoke-low − safety margin):

    window = [ max(melt_high_i),  min(smoke_low_i) − margin ]

Empty window ⇒ the formulation cannot be melt-processed without some
component emitting volatiles — refused with the offending components
named. Printable/machinable verdicts layer process-specific knobs on
top (window width for extrusion control; solid-at-shop-temp for CNC).

ThermalProcessingProfile rows carry the data (object coherence: one
row per material, provenance = the notebook page). Missing profiles
are HONEST gaps — never assumed safe.
"""

from objectTreeDecorators import treeObject, treeObjectInit


class ThermalProcessingProfile(treeObject):
    """One material's melt range + volatile-emission (smoking) range."""

    @treeObjectInit
    def __init__(
        self,
        # MaterialsScienceMaterial.name this profile belongs to.
        name: str = '',
        melt_low_c: float = 0.0,
        melt_high_c: float = 0.0,
        # Volatile-emission onset (Smoking Point Temperature row of the
        # notes). smoke_high_c = 0 means only the onset is known.
        smoke_low_c: float = 0.0,
        smoke_high_c: float = 0.0,
        # Melt-flow estimate (prose — ranges + at-temperature, verbatim
        # from the notes; parsed later if the search needs it).
        mfi_note: str = '',
        # False for particulate fillers (grog, clays, graphite…): they
        # DISPERSE in the melt and never themselves melt, so they don't
        # raise the melt-through temperature — but their volatile limit
        # (if any) still caps the window.
        melts: bool = True,
        provenance_note: str = '',
        manager=None,
    ):
        self.name = name
        self.melt_low_c = melt_low_c
        self.melt_high_c = melt_high_c
        self.smoke_low_c = smoke_low_c
        self.smoke_high_c = smoke_high_c
        self.mfi_note = mfi_note
        self.melts = melts
        self.provenance_note = provenance_note


_NOTES = ("Dustin's notebook, 'Base Wax Properties' "
          "(Open-Source-Economy-Notes/01-Wax-Materials-And-Properties/"
          "IMG_2823.jpg + IMG_2824.jpg, read 2026-07-06)")

SEED_THERMAL_PROFILES = [
    {'name': 'beeswax', 'melt_low_c': 62.0, 'melt_high_c': 64.0,
     'smoke_low_c': 204.0, 'smoke_high_c': 204.0,
     'mfi_note': 'Est 50-200 g/10min at ~60-70C',
     'provenance_note': _NOTES},
    {'name': 'candelilla-wax', 'melt_low_c': 68.8, 'melt_high_c': 72.5,
     'smoke_low_c': 240.0, 'smoke_high_c': 240.0,
     'mfi_note': 'Est 20-100 g/10min at ~70-90C; >240C noted as known '
                 'boiling point',
     'provenance_note': _NOTES},
    {'name': 'carnauba-wax', 'melt_low_c': 82.0, 'melt_high_c': 86.0,
     'smoke_low_c': 200.0, 'smoke_high_c': 220.0,
     'mfi_note': 'Est 10-50 g/10min at ~80-100C',
     'provenance_note': _NOTES},
    {'name': 'coconut-wax', 'melt_low_c': 35.0, 'melt_high_c': 38.0,
     'smoke_low_c': 200.0, 'smoke_high_c': 200.0,
     'mfi_note': 'Est 200-400 g/10min at ~40-60C',
     'provenance_note': _NOTES},
]

_LIT = ('LITERATURE-TYPICAL value entered by Claude 2026-07-06 — NOT '
        'from Dustin\'s notebook; verify/replace (veto anytime).')
_INERT = ('Particulate filler: thermally inert far above wax-processing '
          'temperatures; melts=False (disperses, never melts). ' + _LIT)

#: Fillers + organics Dustin's notes don't cover. Minerals are inert
#: (smoke set at 400C — far above any wax window, so they never govern);
#: organics carry real literature onsets, lecithin's LOW one included.
SEED_THERMAL_PROFILES += [
    {'name': name, 'melt_low_c': 0.0, 'melt_high_c': 0.0,
     'smoke_low_c': 400.0, 'smoke_high_c': 400.0,
     'melts': False, 'provenance_note': _INERT}
    for name in ('grog-(1-um)', 'grog-(3-um)', 'grog-(6-um)',
                 'kaolinite-clay', 'calcium-bentonite-clay',
                 'graphite-powder', 'diatomaceous-earth',
                 'attapulgite-clay', 'illite-clay', 'silica-flour',
                 'chalk-(calcium-carbonate)')
] + [
    {'name': 'pine-rosin', 'melt_low_c': 100.0, 'melt_high_c': 150.0,
     'smoke_low_c': 215.0, 'smoke_high_c': 215.0,
     'provenance_note': 'Dustin, dictated 2026-07-06: smoking point '
                        '215C, melting between 100C and 150C. The '
                        'amorphous crystal disruptor from his morphology '
                        'notes — governs melt-through in any wax blend '
                        '(window [150, 215-margin]).'},
    {'name': 'soy-wax', 'melt_low_c': 45.0, 'melt_high_c': 55.0,
     'smoke_low_c': 230.0, 'smoke_high_c': 230.0,
     'provenance_note': _LIT},
    {'name': 'stearin', 'melt_low_c': 55.0, 'melt_high_c': 70.0,
     'smoke_low_c': 230.0, 'smoke_high_c': 230.0,
     'provenance_note': _LIT},
    {'name': 'soy-lecithin', 'melt_low_c': 40.0, 'melt_high_c': 60.0,
     'smoke_low_c': 120.0, 'smoke_high_c': 160.0,
     'provenance_note': 'Degrades EARLY — the low onset genuinely closes '
                        'windows above ~100C. ' + _LIT},
    {'name': 'ethylene-vinyl-acetate-(eva)', 'melt_low_c': 75.0,
     'melt_high_c': 95.0, 'smoke_low_c': 210.0, 'smoke_high_c': 230.0,
     'provenance_note': 'EVA deacetylation (acetic-acid volatiles) '
                        'onsets ~210-230C — a real window cap. ' + _LIT},
    {'name': 'polyethylene-wax-(low-mw)', 'melt_low_c': 85.0,
     'melt_high_c': 110.0, 'smoke_low_c': 250.0, 'smoke_high_c': 250.0,
     'provenance_note': _LIT},
    {'name': 'microcrystalline-wax-(heavy)', 'melt_low_c': 60.0,
     'melt_high_c': 90.0, 'smoke_low_c': 250.0, 'smoke_high_c': 260.0,
     'provenance_note': _LIT},
    {'name': 'cork-flour', 'melt_low_c': 0.0, 'melt_high_c': 0.0,
     'smoke_low_c': 200.0, 'smoke_high_c': 250.0, 'melts': False,
     'provenance_note': 'Organic particulate (disperses, never melts); '
                        'thermal degradation onset ~200C. ' + _LIT},
]


def profiles_from_rows(rows):
    """{material name: profile dict} from seed dicts or tree rows."""
    profiles = {}
    for row in rows:
        get = row.get if isinstance(row, dict) else \
            lambda k, default=None, r=row: getattr(r, k, default)
        profiles[get('name')] = {
            'meltLowC': float(get('melt_low_c', 0.0)),
            'meltHighC': float(get('melt_high_c', 0.0)),
            'smokeLowC': float(get('smoke_low_c', 0.0)),
            'smokeHighC': float(get('smoke_high_c', 0.0)),
            'melts': bool(get('melts', True)
                          if get('melts', True) is not None else True),
        }
    return profiles


def processing_window(componentNames, profiles, marginC=20.0):
    """The no-volatiles melt-processing window for a set of components.

    Returns {'ok', 'meltThroughC', 'volatileLimitC', 'windowC':
    [lo, hi]|None, 'widthC', 'limitedBy', 'meltGovernedBy',
    'missingProfiles'} — ok is False when the window is empty OR any
    component lacks a profile (honest gap, not assumed safe).
    """
    missing = [n for n in componentNames if n not in profiles]
    known = [n for n in componentNames if n in profiles]
    if not known:
        return {'ok': False, 'missingProfiles': missing,
                'error': 'no thermal profiles for any component'}
    # Only components that MELT govern the melt-through temperature —
    # particulate fillers disperse in the carrier melt. Every component
    # still contributes its volatile limit.
    melting = [n for n in known if profiles[n].get('melts', True)]
    if not melting:
        return {'ok': False, 'missingProfiles': missing,
                'error': 'no meltable component — nothing to carry the '
                         'fillers (add a wax/resin base)'}
    meltGov = max(melting, key=lambda n: profiles[n]['meltHighC'])
    limGov = min(known, key=lambda n: profiles[n]['smokeLowC'])
    meltThrough = profiles[meltGov]['meltHighC']
    volatileLimit = profiles[limGov]['smokeLowC'] - float(marginC)
    window = [meltThrough, volatileLimit] \
        if volatileLimit > meltThrough else None
    return {
        'ok': window is not None and not missing,
        'meltThroughC': meltThrough,
        'volatileLimitC': volatileLimit,
        'windowC': window,
        'widthC': (volatileLimit - meltThrough) if window else 0.0,
        'meltGovernedBy': meltGov,
        'limitedBy': limGov,
        'marginC': float(marginC),
        'missingProfiles': missing,
    }


def printable_verdict(componentNames, profiles, marginC=20.0,
                      minWindowWidthC=20.0):
    """3D-printability (melt extrusion): a real window with enough
    width for extruder temperature control (knob)."""
    window = processing_window(componentNames, profiles, marginC)
    verdict = dict(window)
    verdict['process'] = '3d-print'
    verdict['minWindowWidthC'] = float(minWindowWidthC)
    if window['ok'] and window['widthC'] < minWindowWidthC:
        verdict['ok'] = False
        verdict['refusal'] = (
            f"processing window {window['windowC']} is only "
            f"{window['widthC']:.1f}C wide (< {minWindowWidthC}C knob) — "
            f"too tight for extruder control")
    elif not window['ok'] and window.get('windowC') is None \
            and not window.get('missingProfiles'):
        verdict['refusal'] = (
            f"no volatile-safe window: '{window['limitedBy']}' smokes at "
            f"{profiles[window['limitedBy']]['smokeLowC']}C (−{marginC}C "
            f"margin) before '{window['meltGovernedBy']}' melts through "
            f"at {window['meltThroughC']}C")
    return verdict


def machinable_verdict(componentNames, profiles, shopTempC=25.0,
                       frictionMarginC=15.0):
    """CNC machinability: every component solid at shop temperature
    plus a cutting-friction margin (the blend must not smear)."""
    missing = [n for n in componentNames if n not in profiles]
    known = [n for n in componentNames if n in profiles]
    # Fillers (melts=False) are rigid particulates — only meltable
    # components can soften and smear.
    meltable = [n for n in known if profiles[n].get('melts', True)]
    softest = min(meltable, key=lambda n: profiles[n]['meltLowC']) \
        if meltable else None
    required = float(shopTempC) + float(frictionMarginC)
    ok = softest is not None and not missing \
        and profiles[softest]['meltLowC'] >= required
    verdict = {
        'ok': ok, 'process': 'cnc-machine',
        'requiredSolidUpToC': required,
        'softestComponent': softest,
        'softestMeltLowC': profiles[softest]['meltLowC'] if softest else None,
        'missingProfiles': missing,
    }
    if softest is None and known:
        verdict['refusal'] = ('no meltable binder among the components — '
                              'loose filler is not a machinable stock')
    if softest and not ok and not missing:
        verdict['refusal'] = (
            f"'{softest}' starts melting at "
            f"{profiles[softest]['meltLowC']}C < shop {shopTempC}C + "
            f"friction margin {frictionMarginC}C — would smear under "
            f"the cutter")
    return verdict
