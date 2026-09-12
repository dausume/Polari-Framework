"""
@module climate.co2_symptoms_seed

THE SYMPTOM LADDER, CITED — from a headache nobody notices to the
concentrations that kill.

Dustin: "what about cited symptoms on the ladder and the much
higher levels that result in death".

Two things this file is careful about.

⚠ 1. THE LITERATURE ITSELF DISAGREES, AND OSHA SAYS SO. From the
OSHA ID-172 method document, verbatim: "Literature citations
reveal a wide variation in physiological response to exposures at
certain CO2 concentrations." So `SymptomOnsetClaim` holds a BAND
per source rather than a point, and two sources that disagree
about where a symptom starts both get a row. A single authoritative
number here would be a fabrication of consensus.

⚠ 2. THE LETHAL END IS NOT AN EXTRAPOLATION OF THE INDOOR END.
Everything below about 5000 ppm is a question about chronic
exposure and subtle effects, argued over in the literature.
Everything above about 40000 ppm is acute asphyxiant toxicology
and is not controversial at all. They are different questions with
different evidence, and drawing one smooth curve from "measurable
circulatory change" to "death" would imply a continuum the
evidence does not support. The ladder is ordered; it is not
interpolated.

🔑 AND THE REVERSIBILITY IS PART OF THE CLAIM. OSHA states that
low-level CO2 intoxication is "sudden and reversible" and that
after exposure ends "signs and symptoms usually dissipate within a
few minutes". A ladder that puts headache next to convulsions
without saying which undo themselves is frightening rather than
informative.

@consumers climate.climate_views_seed, climate.climate_api,
climate.climate_selftest, polariServer
"""

from moduleService.seed_upsert import upsert_seed_pairs

PROV = 'co2-S'

#: The OSHA method document is the backbone of the high end. It is
#: a federal analytical method, not a health guideline, and its
#: health section is a literature summary - which is exactly why
#: it is honest about the spread.
_OSHA = 'osha'
_OSHA_CITE = ('OSHA. Carbon Dioxide in Workplace Atmospheres, '
              'Method ID-172. US Department of Labor, '
              'Occupational Safety and Health Administration.')


def _symptom(name, display, system, rank, reversible, description,
             notes=''):
    return {'name': name, 'display_name': display,
            'body_system': system, 'severity_rank': rank,
            'is_reversible': reversible, 'description': description,
            'is_prior': True, 'provenance_id': PROV, 'notes': notes}


SEED_HEALTH_SYMPTOMS = [
    _symptom('sym-circulatory-change',
             'Measurable circulatory change', 'cardiovascular', 1,
             True,
             'Raised heart rate, blood pressure and peripheral '
             'circulation - detected by instrument, not felt.',
             notes='Rank 1 on purpose: an instrument reading is '
                   'not a symptom a person has.'),
    _symptom('sym-headache', 'Headache', 'cardiovascular', 2, True,
             'Head pain, attributed to cerebral vasodilation.',
             notes='OSHA names headache and sweating as "usually '
                   'the first symptoms observed", and says they '
                   'are prevalent in LOW concentration exposures.'),
    _symptom('sym-sweating', 'Sweating', 'cardiovascular', 2, True,
             'Perspiration from peripheral vasodilation.'),
    _symptom('sym-irritation',
             'Eye, nose and throat irritation', 'sensory', 2, True,
             'Mucous-membrane irritation, part of the '
             'building-related symptom cluster.',
             notes='In the indoor literature this travels with '
                   'poor ventilation generally, not with CO2 '
                   'specifically - which is the whole indicator-'
                   'versus-pollutant question.'),
    _symptom('sym-fatigue', 'Fatigue and lassitude',
             'central-nervous', 2, True,
             'Tiredness, sleepiness, reduced alertness.'),
    _symptom('sym-cognitive-decrement',
             'Reduced decision-making performance',
             'central-nervous', 3, True,
             'Measured decrements on decision-making batteries.',
             notes='The most contested symptom on this ladder; see '
                   'the Satish/Rodeheffer/Scully/Du rows.'),
    _symptom('sym-dizziness', 'Dizziness', 'central-nervous', 3,
             True, 'Light-headedness, unsteadiness.'),
    _symptom('sym-dyspnoea', 'Shortness of breath (dyspnoea)',
             'respiratory', 4, True,
             'Air hunger and laboured breathing; respiratory rate '
             'and depth rise as blood CO2 rises.'),
    _symptom('sym-respiratory-acidosis', 'Respiratory acidosis',
             'metabolic', 4, True,
             'Blood pH falls as CO2 accumulates faster than it is '
             'eliminated.'),
    _symptom('sym-confusion', 'Confusion and impaired judgement',
             'central-nervous', 4, True,
             'Disorientation; the point at which a person may no '
             'longer recognise that they should leave.',
             notes='THE DANGEROUS ONE in an asphyxiant: the '
                   'symptom that removes the judgement needed to '
                   'escape arrives BEFORE incapacitation.'),
    _symptom('sym-narcosis', 'Narcosis', 'central-nervous', 5,
             True,
             'CO2-induced depression of the central nervous '
             'system, progressing toward stupor.'),
    _symptom('sym-convulsions', 'Convulsions', 'central-nervous',
             5, True,
             'Seizure activity at high concentrations.'),
    _symptom('sym-unconsciousness', 'Loss of consciousness',
             'central-nervous', 5, True,
             'The person can no longer remove themselves from the '
             'exposure.',
             notes='Reversible IF the person is removed. Left '
                   'in place it is the step before death, which '
                   'is why is_reversible alone never tells the '
                   'whole story.'),
    _symptom('sym-death', 'Death', 'general', 6, False,
             'Asphyxiation.',
             notes='The only irreversible row on this ladder.'),
]


def _claim(name, symptom, ppm_from, ppm_to, source, grade,
           exposure, description, quote='', lethal=False,
           population='general', notes=''):
    return {'name': name, 'symptom_ref': symptom,
            'ppm_from': ppm_from, 'ppm_to': ppm_to,
            'source_ref': source, 'evidence_grade': grade,
            'exposure': exposure, 'onset_note': description,
            'population': population, 'quote': quote,
            'is_lethal': lethal, 'is_prior': True,
            'provenance_id': PROV, 'notes': notes}


#: ppm_to = 0.0 means "and above".
SEED_SYMPTOM_CLAIMS = [
    # ---- the contested indoor end ---------------------------
    _claim('claim-circulatory-500', 'sym-circulatory-change',
           500.0, 5000.0, 'azuma-2018-low-level-co2-review',
           'observational', 'hours',
           'A review reports linear physiological changes in '
           'circulatory, cardiovascular and autonomic measures '
           'across this whole band.',
           notes='Outdoor air is already inside this band. That is '
                 'a statement about detectability, not about harm.'),
    _claim('claim-building-symptoms-700', 'sym-irritation', 700.0,
           0.0, 'azuma-2018-low-level-co2-review', 'observational',
           'chronic',
           'Epidemiological association between indoor CO2 from '
           'about 700 ppm and building-related symptoms.',
           notes='CONFOUNDED BY CONSTRUCTION: CO2 rises when '
                 'ventilation falls, and so does everything else '
                 'people emit. Lowther 2021 is the paper that '
                 'asks whether CO2 is the cause or the marker.'),
    _claim('claim-fatigue-700', 'sym-fatigue', 700.0, 0.0,
           'azuma-2018-low-level-co2-review', 'observational',
           'chronic',
           'Tiredness within the same building-related symptom '
           'cluster.'),
    _claim('claim-headache-700', 'sym-headache', 700.0, 0.0,
           'azuma-2018-low-level-co2-review', 'observational',
           'chronic',
           'Headache within the building-related symptom cluster.',
           notes='The same symptom appears again at 40000 ppm from '
                 'occupational medicine. Two rows, two grades, two '
                 'severities - which is why symptoms are objects '
                 'and not strings on a threshold.'),
    _claim('claim-cognitive-1000', 'sym-cognitive-decrement',
           1000.0, 0.0, 'satish-2012-co2-decision-making',
           'contested-controlled-study', 'hours',
           'Six of nine decision-making scales fell 11-23 percent '
           'against a 600 ppm baseline.',
           notes='FAILED TO REPLICATE in Rodeheffer 2018 and '
                 'Scully 2019; Du 2020 found rigorous studies show '
                 'no or marginal effects. The authors themselves '
                 'asked for replication.'),
    _claim('claim-cognitive-2500', 'sym-cognitive-decrement',
           2500.0, 0.0, 'satish-2012-co2-decision-making',
           'contested-controlled-study', 'hours',
           'Seven scales fell 44-94 percent; five reached levels '
           'the authors call marginal or dysfunctional.',
           quote='effects at 2500 ppm "almost defy credibility"',
           notes='The quote is the AUTHORS\' own assessment of '
                 'their result, not a critic\'s.'),
    # ---- the acute end: OSHA's own symptom list --------------
    _claim('claim-osha-symptom-cluster', 'sym-dyspnoea', 30000.0,
           0.0, _OSHA, 'occupational-limit', 'acute',
           'OSHA lists increased respiratory rate, lassitude, '
           'sleepiness, headache, convulsions, dyspnoea, sweating, '
           'dizziness and narcosis as the signs and symptoms of '
           'larger gas-phase CO2 concentrations.',
           quote='Larger gas-phase concentrations of CO2 may '
                 'produce signs and symptoms of increased '
                 'respiratory rate, lassitude, sleepiness, '
                 'headache, convulsions, dyspnea, sweating, '
                 'dizziness, or narcosis.',
           notes='OSHA gives this as ONE list for "larger '
                 'concentrations" without assigning each symptom '
                 'its own threshold, and immediately adds that '
                 'the literature varies widely. Splitting the list '
                 'into precise per-symptom onsets would invent '
                 'precision the source refuses to claim.'),
    _claim('claim-headache-sweating-first', 'sym-sweating', 5000.0,
           0.0, _OSHA, 'occupational-limit', 'acute',
           'Sweating and headache, from peripheral and cerebral '
           'vasodilation, are usually the FIRST symptoms observed.',
           quote='Peripheral and cerebral vasodilation, as '
                 'demonstrated by signs of sweating and headaches, '
                 'are usually the first symptoms observed and are '
                 'prevalent in low concentration exposures.'),
    _claim('claim-dizziness-50000', 'sym-dizziness', 50000.0, 0.0,
           'airgradient-2025-hidden-health-risks',
           'secondary-reporting', 'acute',
           'Dizziness, headache, confusion and shortness of breath '
           'reported for this band.',
           notes='Graded secondary-reporting because the article '
                 'gives no primary attribution for this rung. The '
                 'band is not controversial in occupational '
                 'medicine - the SOURCING here is what is weak, '
                 'not the physiology.'),
    _claim('claim-confusion-50000', 'sym-confusion', 50000.0, 0.0,
           'airgradient-2025-hidden-health-risks',
           'secondary-reporting', 'acute',
           'Confusion in the same band.',
           notes='This is the rung that matters operationally: '
                 'confusion arrives BEFORE collapse, so a person '
                 'may lose the judgement to leave while still '
                 'physically able to.'),
    # ---- lethal ---------------------------------------------
    _claim('claim-immediate-threat-100000', 'sym-unconsciousness',
           100000.0, 0.0, _OSHA, 'occupational-limit', 'acute',
           'OSHA states that concentrations above 10 percent '
           '(100000 ppm) are generally agreed to pose an immediate '
           'physiologic threat.',
           quote='Exposure to CO2 concentrations above 10% are '
                 'generally agreed upon as posing an immediate '
                 'physiologic threat.',
           lethal=True,
           notes='THE MOST AUTHORITATIVE STATEMENT ON THIS PAGE '
                 'about the lethal end, and note what it does NOT '
                 'say: it gives no time-to-death and no LC50. '
                 'Neither does this row.'),
    _claim('claim-idlh-40000', 'sym-unconsciousness', 40000.0,
           0.0, 'niosh', 'occupational-limit', 'acute',
           'Immediately Dangerous to Life or Health: the level '
           'from which an unprotected person could not escape '
           'within 30 minutes without irreversible harm.',
           lethal=True,
           notes='IDLH is an ESCAPE criterion, not a death '
                 'threshold - a distinction that matters, because '
                 'it is defined by the 30 minutes you have, not '
                 'by a dose that kills.'),
    _claim('claim-death-100000', 'sym-death', 100000.0, 0.0,
           'airgradient-2025-hidden-health-risks',
           'secondary-reporting', 'acute',
           'Dimmed vision, sweating, tremor, unconsciousness and '
           'possible death are reported at and above roughly '
           '80000-100000 ppm.',
           lethal=True,
           notes='The lethal rung is carried at the OSHA 10 '
                 'percent figure rather than the article\'s 8 '
                 'percent, because OSHA is the stronger source '
                 'and its number is the more conservative claim. '
                 'CO2 kills as an ASPHYXIANT and by acidosis, and '
                 'in a real confined space oxygen displacement '
                 'usually arrives with it - which is why '
                 'single-gas ladders understate confined-space '
                 'risk.'),
]


def seed_co2_symptoms(manager):
    from climate.climate_basis import (
        HealthSymptomDefinition, SymptomOnsetClaim,
    )
    return upsert_seed_pairs(manager, [
        ('HealthSymptomDefinition', HealthSymptomDefinition,
         SEED_HEALTH_SYMPTOMS),
        ('SymptomOnsetClaim', SymptomOnsetClaim,
         SEED_SYMPTOM_CLAIMS),
    ], tag='ClimateSymptomSeed')


def symptom_ladder(manager, max_ppm=0.0):
    """THE LADDER: every cited symptom claim, ordered by the level
    it is claimed at, with its source resolved and its severity.

    `max_ppm` clips the ladder - a page about indoor air does not
    need the asphyxiation rungs, and a confined-space page does.
    """
    from climate.climate_citations_seed import resolve_citation
    from composition.custom.data_refs import rows
    symptoms = {getattr(r, 'name', ''): r
                for r in rows(manager, 'HealthSymptomDefinition')}
    if not symptoms:
        return {'ok': False,
                'refusal': ('no HealthSymptomDefinition rows - '
                            'seed_co2_symptoms delivers them')}
    out = []
    for claim in rows(manager, 'SymptomOnsetClaim'):
        ppm_from = float(getattr(claim, 'ppm_from', 0.0))
        if max_ppm and ppm_from > max_ppm:
            continue
        sym = symptoms.get(getattr(claim, 'symptom_ref', ''))
        cite = resolve_citation(manager,
                                getattr(claim, 'source_ref', ''))
        out.append({
            'claim': getattr(claim, 'name', ''),
            'symptom': getattr(claim, 'symptom_ref', ''),
            'symptomDisplay': getattr(sym, 'display_name', '')
            if sym is not None else '(unknown symptom)',
            'bodySystem': getattr(sym, 'body_system', '')
            if sym is not None else '',
            'severityRank': int(getattr(sym, 'severity_rank', 0))
            if sym is not None else 0,
            'reversible': bool(getattr(sym, 'is_reversible', True))
            if sym is not None else None,
            'ppmFrom': ppm_from,
            'ppmTo': float(getattr(claim, 'ppm_to', 0.0)),
            'exposure': getattr(claim, 'exposure', ''),
            'evidenceGrade': getattr(claim, 'evidence_grade', ''),
            'isLethal': bool(getattr(claim, 'is_lethal', False)),
            'onsetNote': getattr(claim, 'onset_note', ''),
            'quote': getattr(claim, 'quote', ''),
            'sourceRef': getattr(claim, 'source_ref', ''),
            'sourceKind': cite.get('kind', ''),
            'citationLine': cite.get('citationLine', ''),
            'sourceResolved': cite.get('ok', False),
            'notes': getattr(claim, 'notes', ''),
        })
    out.sort(key=lambda c: (c['ppmFrom'], -c['severityRank']))
    unresolved = [c['claim'] for c in out
                  if not c['sourceResolved']]
    return {
        'ok': True, 'ladder': out, 'count': len(out),
        'unresolvedSources': unresolved,
        'lethalFrom': min([c['ppmFrom'] for c in out
                           if c['isLethal']] or [0.0]) or None,
        'note': ('the ladder is ORDERED, not interpolated. Below '
                 'about 5000 ppm these are contested claims about '
                 'chronic exposure; above about 40000 ppm they are '
                 'uncontroversial acute asphyxiant toxicology. '
                 'Drawing one smooth curve between them would '
                 'imply a continuum the evidence does not '
                 'support.'),
        'reversibilityNote': (
            'OSHA states that low-level CO2 intoxication is '
            '"sudden and reversible" and that symptoms usually '
            'dissipate within a few minutes of leaving the '
            'exposure. Only death is marked irreversible here; '
            'unconsciousness is reversible IF the person is '
            'removed, which is exactly why confusion - the '
            'symptom that removes the judgement to leave - is the '
            'operationally dangerous rung.'),
        'disagreementNote': (
            'OSHA itself records that "literature citations reveal '
            'a wide variation in physiological response to '
            'exposures at certain CO2 concentrations", which is '
            'why each claim carries a BAND and a source rather '
            'than the page asserting one onset per symptom.'),
    }


def ladder_for_space(manager, indoor_ppm):
    """Which cited symptoms have been claimed at or below the
    level a given room actually sits at."""
    full = symptom_ladder(manager)
    if not full.get('ok'):
        return full
    reached = [c for c in full['ladder']
               if c['ppmFrom'] <= indoor_ppm]
    worst = max([c['severityRank'] for c in reached] or [0])
    return {'ok': True, 'indoorPpm': indoor_ppm,
            'reached': reached, 'count': len(reached),
            'worstSeverityRank': worst,
            'anyLethalReached': any(c['isLethal'] for c in reached),
            'note': ('"reached" means a source has claimed this '
                     'symptom at or below this level - NOT that '
                     'anyone in this room has it. Most of these '
                     'claims are contested and the strongest are '
                     'about acute exposures far above any room '
                     'here.')}
