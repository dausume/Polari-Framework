"""
@module foodstate.custom.food_chemistry

fsp-3 (first slice) — the chemistry-domain engines, cited-constants
only (MEAL_PLANNING_APP_PLAN follow-on; FOOD_STATE_PSPP_PLAN §4
fsp-3):

  speciation      Henderson–Hasselbalch ionization fractions for an
                  organic acid at a given pH — CALCULATED, but only
                  for acids whose pKa set is CITED in CITED_PKA;
                  anything else REFUSES by name (I5: no invented
                  constants).
  titratable_acidity   TA from per-species acid amounts — exact
                  stoichiometric bookkeeping (all carboxyl protons,
                  the pH-8.1 endpoint convention), reported as
                  meq/100g and as-citric g/100g.
  buffer_capacity REFUSES — the cited buffer model (acid speciation
                  + phosphate/protein buffering) is registered but
                  NOT implemented; loading a cited calibration is
                  the only way it appears.

pKa provenance (verified this session, 2026-09-01):
  citric 3.128/4.761/6.396 — Goldberg, Kishore & Lennen 2002
  (J Phys Chem Ref Data; zero ionic strength, 25 °C; via the
  citric-acid article's cited infobox/text).
  malic 3.40/5.20 — Dawson et al., Data for Biochemical Research
  3rd ed. 1986 (via the malic-acid article's cited infobox).
  acetic/lactic carry TRANSCRIBED values, labeled — verify before
  publication-grade use.

@consumers
  - foodstate.food_api (chemistry routes)
  - foodstate.food_chemistry_selftest
"""

_VERIFIED = 'verified 2026-09-01 against the cited source'
_TRANSCRIBED = ('TRANSCRIBED without same-session verification — '
                'verify against the cited source before '
                'publication-grade use')

#: acid → {pkas, molar_mass_g_mol, protons, citation, status}
CITED_PKA = {
    'citric': {
        'pkas': [3.128, 4.761, 6.396],
        'molar_mass_g_mol': 192.12,
        'protons': 3,
        'citation': 'Goldberg, Kishore & Lennen 2002, Thermodynamic '
                    'Quantities for the Ionization Reactions of '
                    'Buffers (zero ionic strength, 25 °C)',
        'status': _VERIFIED,
    },
    'malic': {
        'pkas': [3.40, 5.20],
        'molar_mass_g_mol': 134.09,
        'protons': 2,
        'citation': 'Dawson et al., Data for Biochemical Research '
                    '3rd ed., Clarendon Press 1986',
        'status': _VERIFIED,
    },
    'acetic': {
        'pkas': [4.756],
        'molar_mass_g_mol': 60.05,
        'protons': 1,
        'citation': 'Goldberg, Kishore & Lennen 2002 (standard '
                    'value)',
        'status': _TRANSCRIBED,
    },
    'lactic': {
        'pkas': [3.86],
        'molar_mass_g_mol': 90.08,
        'protons': 1,
        'citation': 'CRC Handbook convention value',
        'status': _TRANSCRIBED,
    },
}


def speciation(acid, ph):
    """Ionization fractions of one acid at one pH — exact
    Henderson–Hasselbalch algebra over the CITED pKa set."""
    entry = CITED_PKA.get(acid)
    if entry is None:
        return {'ok': False,
                'refusal': f'no CITED pKa set for "{acid}" — the '
                           f'engine computes only over cited '
                           f'constants (I5); known: '
                           f'{sorted(CITED_PKA)}'}
    try:
        ph = float(ph)
    except (TypeError, ValueError):
        return {'ok': False, 'refusal': 'pH must be a number'}
    if not 0.0 <= ph <= 14.0:
        return {'ok': False,
                'refusal': f'pH {ph:g} outside 0–14'}
    pkas = entry['pkas']
    # cumulative products: term_i = 10^(sum_{j<=i}(pH - pKa_j))
    terms = [1.0]
    exponent = 0.0
    for pka in pkas:
        exponent += ph - pka
        terms.append(10.0 ** exponent)
    total = sum(terms)
    fractions = [t / total for t in terms]
    charge = -sum(i * f for i, f in enumerate(fractions))
    species = []
    for i, fraction in enumerate(fractions):
        species.append({
            'deprotonated': i,
            'label': (f'H{entry["protons"] - i}A' if i
                      < entry['protons'] else 'A'
                      ) + (f'{-i}' if i else ''),
            'fraction': round(fraction, 6),
        })
    return {'ok': True, 'schema': 'acid-speciation/1',
            'acid': acid, 'pH': ph,
            'pkas': pkas,
            'species': species,
            'fractionFullyProtonated': round(fractions[0], 6),
            'meanCharge': round(charge, 4),
            'citation': entry['citation'],
            'citationStatus': entry['status'],
            'honesty': 'exact algebra over cited constants; ionic-'
                       'strength and temperature corrections are '
                       'NOT applied (assumption named)'}


def titratable_acidity(acid_amounts_g_per_100g):
    """TA from per-species amounts (g/100g): meq/100g + as-citric.

    Convention: titration to the phenolphthalein endpoint counts
    ALL carboxyl protons (the standard food-TA method); acids
    without cited molar-mass rows refuse by name."""
    if not acid_amounts_g_per_100g:
        return {'ok': False, 'refusal': 'no acid amounts given'}
    meq = 0.0
    parts, unknown = [], []
    for acid, grams in sorted(acid_amounts_g_per_100g.items()):
        entry = CITED_PKA.get(acid)
        if entry is None:
            unknown.append(acid)
            continue
        grams = float(grams or 0.0)
        acid_meq = (grams / entry['molar_mass_g_mol']
                    * entry['protons'] * 1000.0)
        meq += acid_meq
        parts.append({'acid': acid, 'gramsPer100g': grams,
                      'meqPer100g': round(acid_meq, 3),
                      'citationStatus': entry['status']})
    if not parts:
        return {'ok': False,
                'refusal': f'no cited acids among {unknown} — '
                           f'known: {sorted(CITED_PKA)}'}
    citric = CITED_PKA['citric']
    as_citric = meq / 1000.0 / citric['protons'] \
        * citric['molar_mass_g_mol']
    return {'ok': True, 'schema': 'titratable-acidity/1',
            'meqPer100g': round(meq, 3),
            'asCitricGPer100g': round(as_citric, 4),
            'contributions': parts,
            'unknownAcids': unknown,
            'honesty': 'stoichiometric bookkeeping (all carboxyl '
                       'protons, phenolphthalein-endpoint '
                       'convention); a measured TA row always beats '
                       'this calculation'}


def buffer_capacity(*_args, **_kwargs):
    """Registered-unimplemented (I5)."""
    return {'ok': False,
            'refusal': 'buffer-capacity model registered but NOT '
                       'implemented — real food buffering includes '
                       'phosphates/proteins beyond the organic '
                       'acids, and no cited calibration is loaded; '
                       'a measured buffer-capacity claim is the '
                       'honest path today (fsp-3 remainder)'}


def ingredient_acidity(manager, slug):
    """One ingredient's chemistry-domain report: organic-acid
    claims + pH claim + calculated TA + speciation at the claimed
    pH — refusing per missing piece, never inventing."""
    tables = getattr(manager, 'objectTables', None) or {}
    subject = f'{slug}#as-defined'
    acids, ph_claim = {}, None
    for row in (tables.get('PropertyClaim') or {}).values():
        if getattr(row, 'subject_state_key', '') != subject:
            continue
        quantity = getattr(row, 'property_meaning_name', '')
        if quantity.startswith('organic-acid-'):
            acids[quantity.replace('organic-acid-', '')] = {
                'gramsPer100g': float(getattr(row, 'value', 0.0)),
                'provenance': getattr(row, 'provenance_id', ''),
            }
        elif quantity == 'pH':
            ph_claim = {'ph': float(getattr(row, 'value', 0.0)),
                        'provenance': getattr(row, 'provenance_id',
                                              '')}
    report = {'ok': True, 'schema': 'ingredient-acidity/1',
              'ingredient': slug, 'subject': subject,
              'organicAcids': acids, 'phClaim': ph_claim}
    if acids:
        report['titratableAcidity'] = titratable_acidity(
            {a: v['gramsPer100g'] for a, v in acids.items()})
    else:
        report['titratableAcidity'] = {
            'ok': False,
            'refusal': f'no organic-acid claims on {subject} — the '
                       f'D4 gap; vendoring a cited measurement is '
                       f'the only way this appears'}
    if ph_claim and acids:
        report['speciationAtClaimedPh'] = {
            acid: speciation(acid, ph_claim['ph'])
            for acid in acids}
    report['bufferCapacity'] = buffer_capacity()
    return report
