"""
@module electrodevice.semiconductor

THE DEDICATED SEMICONDUCTOR DATA SECTION (Dustin 2026-07-10):
general semiconductor / band-structure character derived from
EXECUTED material sims — the DFT fragment models (pyscf B3LYP
frontier orbitals) — never hand-typed:

  gap_ev        = LUMO - HOMO of the material's fragment model
  carrier_type  = classified from the CHEMICAL-POTENTIAL (midgap)
                  shift vs the pristine reference: mu down = hole-
                  rich = 'p'; mu up = 'n'; |shift| < 0.3 eV =
                  'intrinsic'
  level_shift_ev= the signed mu shift vs reference

Every derived number carries provenance + the sims' own honesty
notes (Kohn-Sham orbitals approximate frontier levels; small
fragments overestimate bulk-tube gaps). The validator
(device_validator) is the judge of whether these results meet
semiconductor-device standards — derivation here never self-blesses.

@consumers
  - electrodevice.device_derive (transistor threshold heuristics)
  - electrodevice.device_validator (the standards judge)
  - electrodevice.device_api (/api/electrodevice/semiconductors)
"""

import json
from datetime import datetime, timezone

from objectTreeDecorators import treeObject, treeObjectInit


class SemiconductorProfile(treeObject):
    """One material variant's derived semiconductor character."""

    @treeObjectInit
    def __init__(
        self,
        name: str = '',
        material: str = '',
        # Claimed variant — the validator checks the DERIVED carrier
        # type against this claim.
        variant: str = 'intrinsic',
        # The executable msci DFT model + the pristine reference.
        sim_model: str = '',
        reference_model: str = '',
        # Derived (never hand-set):
        homo_ev: float = 0.0,
        lumo_ev: float = 0.0,
        gap_ev: float = 0.0,
        level_shift_ev: float = 0.0,
        carrier_type: str = '',
        derived_at: str = '',
        provenance_json: str = '{}',
        notes: str = '',
        manager=None,
    ):
        self.name = name
        self.material = material
        self.variant = variant
        self.sim_model = sim_model
        self.reference_model = reference_model
        self.homo_ev = homo_ev
        self.lumo_ev = lumo_ev
        self.gap_ev = gap_ev
        self.level_shift_ev = level_shift_ev
        self.carrier_type = carrier_type
        self.derived_at = derived_at
        self.provenance_json = provenance_json
        self.notes = notes


SEED_SEMICONDUCTOR_PROFILES = [
    {'name': 'cnt-intrinsic', 'material': 'carbon-nanotube',
     'variant': 'intrinsic', 'sim_model': 'cnt-fragment-energy',
     'reference_model': ''},
    {'name': 'cnt-n-doped', 'material': 'n-doped-carbon-nanotube',
     'variant': 'n', 'sim_model': 'doped-cnt-fragment-energy',
     'reference_model': 'cnt-fragment-energy'},
    {'name': 'cnt-p-doped', 'material': 'b-doped-carbon-nanotube',
     'variant': 'p', 'sim_model': 'p-doped-cnt-fragment-energy',
     'reference_model': 'cnt-fragment-energy'},
    # Community n-doping candidates (all CLAIM n — the validator
    # judges each against its executed sim):
    {'name': 'cnt-phosphorus-doped', 'material': 'carbon-nanotube',
     'variant': 'n', 'sim_model': 'phos-doped-cnt-fragment-energy',
     'reference_model': 'cnt-fragment-energy'},
    {'name': 'cnt-amine-doped', 'material': 'carbon-nanotube',
     'variant': 'n', 'sim_model': 'amine-doped-cnt-fragment-energy',
     'reference_model': 'cnt-fragment-energy'},
    {'name': 'cnt-potash-doped', 'material': 'carbon-nanotube',
     'variant': 'n', 'sim_model': 'potash-doped-cnt-fragment-energy',
     'reference_model': 'cnt-fragment-energy'},
    # The larger N-fragment: GRAPHITIC (interior) nitrogen vs the
    # same-size naphthalene reference.
    {'name': 'cnt-graphitic-n-doped',
     'material': 'n-doped-carbon-nanotube', 'variant': 'n',
     'sim_model': 'graphitic-n-cnt-fragment-energy',
     'reference_model': 'cnt-fragment-energy-l2'},
]


def get_profile(manager, name):
    tables = getattr(manager, 'objectTables', None) or {}
    for row in (tables.get('SemiconductorProfile') or {}).values():
        if getattr(row, 'name', '') == name:
            return row
    return None


def _frontier(report):
    result = report.get('result') or {}
    return (float(result.get('homoEv') or 0.0),
            float(result.get('lumoEv') or 0.0),
            float(result.get('gapEv') or 0.0),
            result.get('frontierNote', ''))


def classify_carrier(homo, lumo, ref_homo, ref_lumo,
                     threshold_ev=0.3):
    """Chemical-potential (midgap) shift vs the pristine reference:
    mu = (HOMO+LUMO)/2. mu moving TOWARD the valence side (down) =
    hole-rich = 'p'; toward the conduction side (up) = 'n'; within
    the threshold = 'intrinsic'. This is the defensible classifier at
    KS-fragment fidelity — a dopant whose fragment does NOT move mu
    the claimed way is a data verdict for the validator, not
    something to paper over."""
    mu = (homo + lumo) / 2.0
    ref_mu = (ref_homo + ref_lumo) / 2.0
    shift = mu - ref_mu
    if abs(shift) < threshold_ev:
        return 'intrinsic', shift
    return ('n', shift) if shift > 0 else ('p', shift)


def derive_semiconductor(manager, profile, executor=None):
    """Execute the fragment sim (+ reference), stamp the character."""
    if executor is None:
        from materialsScience.model_execution import execute_model
        executor = execute_model
    report = executor(manager, profile.sim_model)
    if not report.get('ok'):
        return {'ok': False,
                'error': f'fragment sim "{profile.sim_model}" '
                         'refused',
                'simReport': {k: v for k, v in report.items()
                              if k not in ('resolved',)}}
    homo, lumo, gap, note = _frontier(report)
    ref = None
    carrier, shift = 'intrinsic', 0.0
    if profile.reference_model:
        ref_report = executor(manager, profile.reference_model)
        if not ref_report.get('ok'):
            return {'ok': False,
                    'error': f'reference sim '
                             f'"{profile.reference_model}" refused'}
        ref = _frontier(ref_report)
        carrier, shift = classify_carrier(homo, lumo, ref[0], ref[1])
    provenance = {
        'simModel': profile.sim_model,
        'referenceModel': profile.reference_model,
        'engine': report.get('engine', ''),
        'homoEv': homo, 'lumoEv': lumo, 'gapEv': gap,
        'referenceHomoEv': ref[0] if ref else None,
        'referenceLumoEv': ref[1] if ref else None,
        'classifier': 'chemical-potential (midgap) shift vs the '
                      'pristine reference: down -> p, up -> n, '
                      '|shift| < 0.3 eV -> intrinsic',
        'honesty': note or 'Kohn-Sham orbital energies — approximate '
                           'frontier levels',
        'fragmentCaveat': 'small-fragment gaps overestimate bulk '
                          'tubes; treat as CHARACTER, not band '
                          'structure',
    }
    profile.homo_ev = homo
    profile.lumo_ev = lumo
    profile.gap_ev = gap
    profile.level_shift_ev = shift
    profile.carrier_type = carrier
    profile.derived_at = datetime.now(timezone.utc).isoformat()
    profile.provenance_json = json.dumps(provenance)
    try:
        db = getattr(manager, 'db', None)
        if db is not None:
            db.saveInstanceInDB(profile)
    except Exception:
        pass
    return {'ok': True, 'profile': profile.name,
            'gapEv': gap, 'carrierType': carrier,
            'levelShiftEv': shift, 'provenance': provenance}
