"""
@module climate.climate_claims

EVERY NUMBER THE PAGE SHOWS, CLASSIFIED BY WHERE IT CAME FROM.

Dustin: "a combination of citations and differs between those
cited and the custom simulations we ran (which should be stated
as speculation / not peer reviewed specifically)".

This module exists so that distinction is STRUCTURAL rather than
a styling choice. A renderer cannot forget to mark a modelled
number as speculative if the payload will not hand it over
without the mark.

FOUR CLASSES, and the boundary that matters most is between the
first two and the last one:

  measured  — somebody else's instrument, ingested here. NOAA's
              Mauna Loa record, the ice cores, NHANES lab values.
              We did not produce the number; we fetched it.

  cited     — stated by a named peer-reviewed study or a
              standards body. Satish 2012's decrements, ASHRAE's
              ventilation criterion, NIOSH's limits.

  derived   — OUR ARITHMETIC ON MEASURED DATA. A least-squares
              slope, the 800 kyr maximum, a unit conversion.
              Reproducible by anyone with the same rows, and
              claiming no new science. Still ours, so still
              labelled.

  modelled  — OUR SIMULATION OUTPUT. Indoor steady states,
              crossing years, the hearth-dwelling estimate.
              NOT PEER REVIEWED. NOT PUBLISHED. Speculative in
              the strict sense: a computation whose inputs are
              named priors, whose method nobody outside this
              repository has checked, and which no journal has
              seen. It may still be the most useful number on
              the page - but it is not evidence, and the page
              must never let it read like one.

⚠ THE FAILURE MODE THIS PREVENTS is subtle and common: a page
puts a measured 427.35 ppm next to a modelled crossing year of
2049 in the same typeface, and a reader takes both as findings.
One is a measurement. The other is what a quadratic fit says if
its assumptions hold. Same page, same table, utterly different
epistemic status.

@consumers climate.climate_api, climate.climate_views,
angular co2-health.component
"""

PROVENANCE_CLASSES = ('measured', 'cited', 'derived', 'modelled')

#: Everything a reader needs in order to weigh a number, keyed by
#: its class. The renderer shows these verbatim; it does not
#: invent its own wording.
CLASS_META = {
    'measured': {
        'label': 'Measured',
        'shortLabel': 'MEASURED',
        'peerReviewed': None,
        'tone': 'ok',
        'meaning': ('an instrument reading published by an '
                    'official source and ingested here. We did '
                    'not produce this number, we fetched it.'),
    },
    'cited': {
        'label': 'Cited',
        'shortLabel': 'CITED',
        'peerReviewed': True,
        'tone': 'ok',
        'meaning': ('stated by a named peer-reviewed study or '
                    'standards body. Follow the citation and '
                    'judge the source yourself.'),
    },
    'derived': {
        'label': 'Derived here',
        'shortLabel': 'DERIVED',
        'peerReviewed': False,
        'tone': 'warn',
        'meaning': ('our arithmetic on measured data - a fit, a '
                    'maximum, a unit conversion. Reproducible '
                    'from the same rows and claiming no new '
                    'science, but computed by this project and '
                    'not reviewed by anyone else.'),
    },
    'modelled': {
        'label': 'Our model - speculative, NOT peer reviewed',
        'shortLabel': 'OUR MODEL',
        'peerReviewed': False,
        'tone': 'bad',
        'meaning': ('OUTPUT OF A SIMULATION WE WROTE. Its inputs '
                    'are named priors, its method has not been '
                    'reviewed outside this repository, and no '
                    'journal has seen it. Treat it as a '
                    'structured argument, not as evidence.'),
    },
}


def claim(label, value, provenance, unit='', source_ref='',
          method='', caveat='', section='', detail=''):
    """One number, with the reason you may or may not believe it.

    `provenance` outside the four known classes falls back to
    'modelled' rather than to something reassuring: an
    unclassifiable number is the LEAST trustworthy kind, not the
    most.
    """
    kind = provenance if provenance in PROVENANCE_CLASSES \
        else 'modelled'
    meta = CLASS_META[kind]
    out = {
        'label': label, 'value': value, 'unit': unit,
        'provenance': kind,
        'provenanceLabel': meta['label'],
        'provenanceShort': meta['shortLabel'],
        'provenanceMeaning': meta['meaning'],
        'peerReviewed': meta['peerReviewed'],
        'tone': meta['tone'],
        'sourceRef': source_ref, 'method': method,
        'caveat': caveat, 'section': section, 'detail': detail,
    }
    if kind == 'modelled' and not method:
        out['method'] = ('a computation in this repository; see '
                         'the module that produced it')
    return out


def page_claims(manager, background_ppm=None):
    """EVERY headline number on the CO2/health page, classified.

    Built by asking the engines, so the page cannot drift from
    what the engines actually say - and refusals travel as
    refusals rather than being dropped.
    """
    from climate.series_ingest import series_points
    out = []

    points = series_points(manager, 'co2-mauna-loa-annual')
    if background_ppm is None:
        background_ppm = points[-1]['value'] if points else None

    # ---- what is measured -----------------------------------
    if points:
        latest = points[-1]
        out.append(claim(
            'Outdoor CO2, global background',
            round(latest['value'], 2), 'measured', unit='ppm',
            source_ref='noaa-gml', section='outdoor-record',
            detail=f'annual mean for {latest["year"]:.0f}',
            caveat=('Mauna Loa is a deliberately clean-air '
                    'baseline. Almost nobody breathes it - see '
                    'the urban rows.')))

    ice = series_points(manager, 'co2-ice-core-composite')
    if ice:
        older = [p['value'] for p in ice if p['year'] < 1000.0]
        if older:
            out.append(claim(
                '800,000-year maximum, before the last millennium',
                round(max(older), 1), 'derived', unit='ppm',
                source_ref='bereiter-2015-co2-composite',
                method='maximum over ingested ice-core rows with '
                       'year < 1000 CE',
                section='human-history',
                caveat=('the underlying points are measured; '
                        'taking their maximum is our arithmetic')))

    # ---- what the fits say ----------------------------------
    if points:
        from climate.co2_crossing import build_fits
        fits, refusal = build_fits(points)
        quad = fits.get('quadratic') if fits else None
        if quad and quad.get('ok'):
            out.append(claim(
                'CO2 acceleration', round(quad['acceleration'], 5),
                'derived', unit='ppm/yr2',
                method=(f'least-squares quadratic over '
                        f'{quad["nPoints"]} annual means, '
                        f'{quad["windowFromYear"]:.0f}-'
                        f'{quad["windowToYear"]:.0f}'),
                section='trend-fits',
                caveat=('a fit is a summary of the past, not a '
                        'law. NOAA publishes its own growth rate '
                        'and the two agree to 0.4 percent.')))

    # ---- cited thresholds -----------------------------------
    from composition.data_refs import rows
    for row in rows(manager, 'CO2HealthThreshold'):
        grade = getattr(row, 'evidence_grade', '')
        if grade in ('contested-controlled-study',
                     'standard-or-guideline', 'occupational-limit',
                     'observational'):
            out.append(claim(
                getattr(row, 'display_name', ''),
                getattr(row, 'ppm', 0.0), 'cited', unit='ppm',
                source_ref=getattr(row, 'source_ref', ''),
                section='thresholds',
                detail=f'evidence grade: {grade}',
                caveat=(getattr(row, 'contested_by', '')
                        or getattr(row, 'notes', ''))[:400]))
        elif grade == 'secondary-reporting':
            out.append(claim(
                getattr(row, 'display_name', ''),
                getattr(row, 'ppm', 0.0), 'cited', unit='ppm',
                source_ref=getattr(row, 'source_ref', ''),
                section='thresholds',
                detail='reported by a credentialed author outside '
                       'peer review',
                caveat=('secondary reporting: the author has '
                        'relevant credentials AND the piece was '
                        'not peer reviewed, and the publisher '
                        'sells CO2 monitors.')))

    # ---- OUR MODEL ------------------------------------------
    if background_ppm is not None:
        from climate.co2_settings import all_space_levels
        levels = all_space_levels(manager, background_ppm)
        for space in (levels.get('spaces') or []):
            if space.get('refused'):
                continue
            check = space.get('observedCheck') or {}
            out.append(claim(
                space.get('displayName', space.get('space', '')),
                round(space.get('indoorPpm') or 0.0, 0),
                'modelled', unit='ppm',
                method=('steady-state mass balance: local outdoor '
                        'plus occupant emission over ventilation. '
                        'Volume, occupancy, activity and air '
                        'changes are all NAMED PRIORS, not '
                        'measurements of any real room.'),
                section='indoor-coupling',
                caveat=(check.get('verdict')
                        or ('no published measurement of a room '
                            'like this to check against'))))

        from climate.co2_crossing import (
            coupled_crossings, outdoor_crossings,
        )
        thresholds = list(rows(manager, 'CO2HealthThreshold'))
        outdoor = outdoor_crossings(points, thresholds)
        for entry in (outdoor.get('crossings') or []):
            if entry.get('skipped') or entry.get('refused'):
                continue
            if entry.get('alreadyCrossed'):
                continue
            low, high = (entry.get('crossingYearLow'),
                         entry.get('crossingYearHigh'))
            if low is None:
                continue
            out.append(claim(
                f'Outdoor reaches {entry.get("targetPpm"):.0f} ppm',
                (f'{low:.0f}' if abs(high - low) < 1
                 else f'{low:.0f}-{high:.0f}'),
                'modelled', unit='year',
                method=('linear and quadratic fits projected '
                        'forward; the band is the two fits, not a '
                        'confidence interval'),
                section='crossings',
                caveat=('a crossing year is a consequence of a '
                        'fit, not a prediction of the world. '
                        'Emissions policy, sinks and the '
                        'acceleration term itself can all move '
                        'it.')))

    return {
        'ok': True, 'claims': out, 'count': len(out),
        'classes': CLASS_META,
        'byClass': _count_by_class(out),
        'note': ('every number on this page carries the reason '
                 'you may or may not believe it. The important '
                 'boundary is between the first three classes and '
                 'the last: measured, cited and derived numbers '
                 'all trace to something outside this repository. '
                 'A MODELLED number does not.'),
        'speculationNote': (
            'Numbers marked OUR MODEL are the output of '
            'simulations written for this project. They have not '
            'been peer reviewed, published, or checked by anyone '
            'outside this repository, and their inputs are named '
            'priors rather than measurements of any real room. '
            'They are shown because a structured argument beats '
            'no answer - not because they are evidence.'),
    }


def _count_by_class(claims):
    counts = {k: 0 for k in PROVENANCE_CLASSES}
    for entry in claims:
        counts[entry['provenance']] = counts.get(
            entry['provenance'], 0) + 1
    return counts
