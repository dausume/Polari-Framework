"""
@module pspp.custom.composition_math

Deterministic composition math (plan pspp-6 Tier 1, brought forward):
oxide mole/ratio derivation, waterglass MR/WR (never silently
interchanged — the book's explicit warning), and Baumé ↔ specific
gravity. Composition DESCRIPTORS ARE COMPUTED, never hand-stored
(Ch.8 convergence): store the composition, derive the ratios.

Book cross-checks (Davidovits, Geopolymer Chemistry and Applications):
p.84 states MR = 1.032·WR (Na) and MR = 1.568·WR (K) — our molar-mass
derivation must reproduce both (selftest-pinned). Table 5.1 (p.84)
gives the commercial-silicate MR presets. °Bé = 145(1 − 1/SG) is the
book's Baumé relation for liquids denser than water.
"""

OXIDE_MOLAR_MASSES = {
    # g/mol — standard atomic weights.
    'SiO2': 60.084, 'Al2O3': 101.961, 'Na2O': 61.979, 'K2O': 94.196,
    'CaO': 56.077, 'MgO': 40.304, 'Fe2O3': 159.688, 'H2O': 18.015,
}

#: Moles of the CATION per mole of oxide (Si per SiO2 = 1, Al per
#: Al2O3 = 2, Na per Na2O = 2…), for atomic ratios like Si:Al.
CATIONS_PER_OXIDE = {
    'SiO2': ('Si', 1), 'Al2O3': ('Al', 2), 'Na2O': ('Na', 2),
    'K2O': ('K', 2), 'CaO': ('Ca', 1), 'MgO': ('Mg', 1),
    'Fe2O3': ('Fe', 2), 'H2O': ('H', 2),
}

#: p.84: practical MR range for sodium silicates in praxis.
PRACTICAL_MR_RANGE_NA = (0.4, 4.0)

#: Table 5.1 (p.84): commercial silicate MR presets.
COMMERCIAL_SILICATE_MR = {
    'sodium-orthosilicate': {'formula': 'Na4SiO4', 'MR': 0.5},
    'sodium-metasilicate': {'formula': 'Na2SiO3', 'MR': 1.0},
    'sodium-disilicate': {'formula': 'Na2Si2O5', 'MR': 2.0},
    'sodium-polysilicate': {'formula': 'Na2O·3.3SiO2', 'MR': 3.30},
}


def oxide_moles(mass_composition):
    """{oxide: mass} (any consistent mass unit) → verdict with
    {oxide: moles}. Unknown oxides REFUSE (honest vocabulary gap),
    never get dropped silently."""
    unknown = sorted(k for k in mass_composition
                     if k not in OXIDE_MOLAR_MASSES)
    if unknown:
        return {
            'ok': False,
            'refusal': f'unknown oxides {unknown} — no molar mass on '
                       'record',
            'suggestion': 'add the oxide to '
                          'pspp.custom.composition_math.OXIDE_MOLAR_MASSES '
                          '(with its source) or correct the key; '
                          f'known: {sorted(OXIDE_MOLAR_MASSES)}',
        }
    return {'ok': True, 'moles': {
        oxide: mass / OXIDE_MOLAR_MASSES[oxide]
        for oxide, mass in mass_composition.items() if mass > 0}}


def oxide_ratios(mass_composition):
    """The derived composition descriptors (Ch.8 set) from a MASS
    composition — see ratios_from_moles for the shared ratio math."""
    verdict = oxide_moles(mass_composition)
    if not verdict['ok']:
        return verdict
    return ratios_from_moles(verdict['moles'])


def ratios_from_moles(mole_composition):
    """The derived composition descriptors (Ch.8 set): molar
    SiO2/Al2O3, M2O/SiO2, M2O/Al2O3, H2O/M2O (M2O = Na2O + K2O
    equivalents) and atomic Si/Al, Na/K. Ratios whose denominator is
    absent come back None with the reason — never a crash, never a
    silent zero. Accepts oxide-formula mole inputs directly (e.g. the
    book's 1.1Na2O:4SiO2:Al2O3:17H2O benchmark)."""
    unknown = sorted(k for k in mole_composition
                     if k not in OXIDE_MOLAR_MASSES)
    if unknown:
        return {'ok': False,
                'refusal': f'unknown oxides {unknown}',
                'suggestion': f'known: {sorted(OXIDE_MOLAR_MASSES)}'}
    moles = {k: v for k, v in mole_composition.items() if v > 0}
    m2o = moles.get('Na2O', 0.0) + moles.get('K2O', 0.0)
    atoms = {}
    for oxide, count in moles.items():
        symbol, per = CATIONS_PER_OXIDE[oxide]
        atoms[symbol] = atoms.get(symbol, 0.0) + per * count

    def ratio(num, den, label):
        if den <= 0:
            return None, f'{label}: denominator absent from composition'
        return num / den, None

    out, notes = {}, []
    for key, num, den in (
        ('SiO2/Al2O3', moles.get('SiO2', 0.0),
         moles.get('Al2O3', 0.0)),
        ('M2O/SiO2', m2o, moles.get('SiO2', 0.0)),
        ('M2O/Al2O3', m2o, moles.get('Al2O3', 0.0)),
        ('H2O/M2O', moles.get('H2O', 0.0), m2o),
        ('H2O/Al2O3', moles.get('H2O', 0.0),
         moles.get('Al2O3', 0.0)),
        ('Si/Al', atoms.get('Si', 0.0), atoms.get('Al', 0.0)),
        ('Na/K', atoms.get('Na', 0.0), atoms.get('K', 0.0)),
    ):
        value, note = ratio(num, den, key)
        out[key] = value
        if note:
            notes.append(note)
    return {'ok': True, 'ratios': out, 'molarBasis': moles,
            'atomicBasis': atoms, 'absentDenominators': notes}


def mr_wr_factor(cation='Na'):
    """MR = factor · WR for one alkali family — derived from molar
    masses; the book states 1.032 (Na) and 1.568 (K) on p.84."""
    oxide = {'Na': 'Na2O', 'K': 'K2O'}.get(cation)
    if oxide is None:
        return {'ok': False,
                'refusal': f'unknown cation family {cation!r}',
                'suggestion': "use 'Na' or 'K' (Li needs its molar "
                              'mass added first, with source)'}
    return {'ok': True, 'factor':
            OXIDE_MOLAR_MASSES[oxide] / OXIDE_MOLAR_MASSES['SiO2']}


def mr_from_wr(wr, cation='Na'):
    """Weight ratio → molar ratio. Kept as an EXPLICIT conversion —
    storing one as the other is the classic error the book warns
    about; Polari stores both, converts only through here."""
    factor = mr_wr_factor(cation)
    if not factor['ok']:
        return factor
    return {'ok': True, 'MR': wr * factor['factor'],
            'note': f"MR = {factor['factor']:.4f} x WR ({cation}); "
                    'book p.84 states '
                    f"{1.032 if cation == 'Na' else 1.568}"}


def wr_from_mr(mr, cation='Na'):
    factor = mr_wr_factor(cation)
    if not factor['ok']:
        return factor
    return {'ok': True, 'WR': mr / factor['factor']}


def mr_from_solution(mass_composition, cation='Na'):
    """MR straight from an actual solution composition (the 'never
    store waterglass grade 3.3 as sufficient chemistry' rule)."""
    verdict = oxide_moles(mass_composition)
    if not verdict['ok']:
        return verdict
    moles = verdict['moles']
    oxide = {'Na': 'Na2O', 'K': 'K2O'}.get(cation)
    if not oxide or moles.get(oxide, 0.0) <= 0:
        return {'ok': False,
                'refusal': f'no {oxide or cation} in the composition',
                'suggestion': 'MR needs the alkali oxide mass — enter '
                              'the full oxide+water composition'}
    if moles.get('SiO2', 0.0) <= 0:
        return {'ok': False, 'refusal': 'no SiO2 in the composition',
                'suggestion': 'enter the full oxide+water composition'}
    mr = moles['SiO2'] / moles[oxide]
    out = {'ok': True, 'MR': mr,
           'WR': (mass_composition.get('SiO2', 0.0)
                  / mass_composition.get(oxide, 1.0))}
    lo, hi = PRACTICAL_MR_RANGE_NA
    if cation == 'Na' and not (lo <= mr <= hi):
        out['caution'] = (f'MR {mr:.2f} is outside the practical '
                          f'range [{lo}, {hi}] for sodium silicates '
                          '(book p.84)')
    return out


def baume_from_sg(sg):
    """°Bé = 145(1 − 1/SG) — liquids denser than water; the book's
    stated temperature convention rides in dataset metadata."""
    if sg <= 0:
        return {'ok': False, 'refusal': 'SG must be positive',
                'suggestion': 'check the measurement'}
    return {'ok': True, 'baume': 145.0 * (1.0 - 1.0 / sg)}


def sg_from_baume(baume):
    """SG = 145 / (145 − °Bé)."""
    if baume >= 145:
        return {'ok': False,
                'refusal': f'Baume {baume} >= 145 is outside the '
                           'relation\'s domain',
                'suggestion': 'check the reading — the heavy-Baume '
                              'scale is asymptotic at 145'}
    return {'ok': True, 'sg': 145.0 / (145.0 - baume)}
