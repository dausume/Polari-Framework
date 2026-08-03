"""
@module climate.co2_scenarios

THREE ERAS, ONE TABLE: what CO2 people breathed, breathe, and are
projected to breathe — outdoor and indoor, urban and not, against
the same threshold ladder.

Dustin: the page should "talk to different scenarios for the
historical, modern, and future contexts in terms of CO2
thresholds".

The point of putting them in ONE table with ONE threshold ladder
is that it makes the comparison structural. A reader can see that
a modern closed bedroom is above a line a pre-industrial field
never approached, and that a future urban room crosses lines the
present one does not - without the page having to assert any of
it in prose.

⚠ THE THREE ERAS DO NOT HAVE EQUAL EVIDENCE, and the table says
so per row rather than in a footnote:
  HISTORICAL  outdoor is MEASURED (ice cores). Indoor is
              MODELLED from combustion tracers, because nobody
              measured CO2 in a hearth-heated dwelling.
  MODERN      outdoor is MEASURED. Indoor is MODELLED but has
              published measurements to be checked against, and
              two of the three rooms come back "pessimistic".
  FUTURE      everything is PROJECTED from a fit. A crossing year
              is a consequence of a quadratic, not a forecast of
              the world, and the fit's own acceleration term is
              not a constant of nature.

So confidence DECREASES left to right across the table, which is
the opposite of how such tables usually read - the future column
is normally the most confident-looking and is always the weakest.

@consumers climate.climate_views, climate.climate_api,
climate.selftest_climate
"""

PROV = 'co2-SC'

#: Which era each scenario belongs to, and how much its numbers
#: can be trusted. `evidence` is the honest label; `provenance`
#: maps onto climate_claims' four classes.
ERAS = ('historical', 'modern', 'future')


def _scenario(name, era, label, outdoor_ppm, indoor_ppm,
              provenance, evidence, note, setting='',
              space='', year=None):
    return {
        'name': name, 'era': era, 'label': label,
        'year': year, 'setting': setting, 'space': space,
        'outdoorPpm': outdoor_ppm, 'indoorPpm': indoor_ppm,
        'provenance': provenance, 'evidence': evidence,
        'note': note,
    }


def build_scenarios(manager, background_ppm,
                    future_years=(2050.0, 2100.0)):
    """The three-era table, built from the engines rather than
    restated - so it cannot drift from what they say."""
    from climate.co2_settings import (
        all_space_levels, local_outdoor_ppm,
    )
    rows_out = []

    # ---- HISTORICAL -----------------------------------------
    from climate.co2_combustion import hearth_dwelling_estimate
    hearth = hearth_dwelling_estimate()
    rows_out.append(_scenario(
        'historical-outdoor-preindustrial', 'historical',
        'Pre-industrial outdoor, anywhere', 280.0, None,
        'measured',
        'MEASURED - Antarctic ice cores, ingested here',
        'The whole 800,000 years before the last millennium cap '
        'below 300 ppm. This is the air every human ancestor '
        'breathed and no living person has.',
        year=1750.0))
    if hearth.get('ok'):
        rows_out.append(_scenario(
            'historical-indoor-hearth', 'historical',
            'Pre-industrial dwelling with a hearth fire', 280.0,
            (hearth['dwellingLowPpm'] + hearth['dwellingHighPpm'])
            / 2.0,
            'modelled',
            'MODELLED from combustion tracers - nobody measured '
            'CO2 in such a dwelling',
            f'A wood fire makes about 31x an adult\'s CO2, so the '
            f'source was large; the measured PM2.5 and CO in '
            f'surviving analogues bound how much reached the room '
            f'at {hearth["dwellingLowPpm"]:.0f}-'
            f'{hearth["dwellingHighPpm"]:.0f} ppm daily average. '
            f'Cooking peaks ran higher and are the exposure that '
            f'mattered.',
            space='hearth-dwelling', year=1750.0))

    # ---- MODERN ---------------------------------------------
    rows_out.append(_scenario(
        'modern-outdoor-background', 'modern',
        'Outdoor, global background', background_ppm, None,
        'measured', 'MEASURED - NOAA Mauna Loa, ingested here',
        'The number every headline quotes, and a deliberately '
        'clean-air baseline almost nobody actually breathes.'))
    urban = local_outdoor_ppm(manager, background_ppm,
                              'outdoor-urban-core')
    if urban.get('ok'):
        rows_out.append(_scenario(
            'modern-outdoor-urban', 'modern',
            'Outdoor, city centre', urban['localOutdoorPpm'], None,
            'cited',
            'CITED - surface urban-dome measurements (Phoenix, '
            'Baltimore, Tokyo)',
            'Already past the lowest threshold on the ladder '
            'before anyone steps indoors.',
            setting='outdoor-urban-core'))
    levels = all_space_levels(manager, background_ppm)
    for want, label in (('bedroom-overnight-closed',
                         'Modern bedroom, closed, overnight'),
                        ('classroom-occupied',
                         'Modern classroom, occupied'),
                        ('bedroom-window-ajar',
                         'The same bedroom, window ajar')):
        found = next((s for s in (levels.get('spaces') or [])
                      if s.get('space') == want), None)
        if not found:
            continue
        check = (found.get('observedCheck') or {}).get('verdict', '')
        rows_out.append(_scenario(
            f'modern-{want}', 'modern', label,
            found['localOutdoorPpm'], found['indoorPpm'],
            'modelled',
            'MODELLED - and checkable: published measurements of '
            'rooms like this exist',
            (check or 'no published counterpart to check against')
            + ('  The window-ajar row is the same room with the '
               'ventilation knob turned - it is the cheapest '
               'intervention on this whole page.'
               if want == 'bedroom-window-ajar' else ''),
            space=want))

    # ---- FUTURE ---------------------------------------------
    from climate.co2_crossing import build_fits
    from climate.co2_trend import project
    from climate.series_ingest import series_points
    points = series_points(manager, 'co2-mauna-loa-annual')
    fits, refusal = build_fits(points) if points else ({}, 'x')
    if fits and fits.get('quadratic', {}).get('ok'):
        quad = fits['quadratic']
        lin = fits.get('linear', {})
        for year in future_years:
            proj = project(quad, year)
            lin_proj = project(lin, year) if lin.get('ok') else None
            if not proj.get('ok'):
                continue
            out_ppm = proj['value']
            band = ''
            if lin_proj and lin_proj.get('ok'):
                lo = min(out_ppm, lin_proj['value'])
                hi = max(out_ppm, lin_proj['value'])
                band = (f' The linear fit gives {lin_proj["value"]:.0f} '
                        f'and the quadratic {out_ppm:.0f}, so treat '
                        f'{lo:.0f}-{hi:.0f} as the band.')
            rows_out.append(_scenario(
                f'future-outdoor-{year:.0f}', 'future',
                f'Outdoor background, {year:.0f}', out_ppm, None,
                'modelled',
                'PROJECTED from a quadratic fit - not a forecast',
                ('a crossing year is a consequence of a fit, not a '
                 'prediction of the world. Emissions policy, the '
                 'sinks and the acceleration term itself can all '
                 'move it.' + band),
                year=year))
            city = local_outdoor_ppm(manager, out_ppm,
                                     'outdoor-urban-core')
            bedroom = next(
                (s for s in (levels.get('spaces') or [])
                 if s.get('space') == 'bedroom-overnight-closed'),
                None)
            if city.get('ok') and bedroom:
                offset = bedroom.get('ventilationOffsetPpm') or 0.0
                rows_out.append(_scenario(
                    f'future-bedroom-{year:.0f}', 'future',
                    f'City bedroom, closed, {year:.0f}',
                    city['localOutdoorPpm'],
                    city['localOutdoorPpm'] + offset,
                    'modelled',
                    'PROJECTED outdoor PLUS a modelled room - two '
                    'models stacked, so the weakest row here',
                    'the room does not change; the floor it sits '
                    'on does. That is the whole argument for why '
                    'a rising background is an indoor problem.',
                    space='bedroom-overnight-closed', year=year))

    return {'ok': True, 'scenarios': rows_out,
            'count': len(rows_out), 'eras': list(ERAS),
            'note': ('CONFIDENCE DECREASES from historical to '
                     'future, which is the opposite of how such '
                     'tables usually read. Historical outdoor is '
                     'measured; future indoor is two models '
                     'stacked on each other.')}


def scenario_thresholds(manager, background_ppm,
                        future_years=(2050.0, 2100.0)):
    """Every scenario against every ABSOLUTE threshold: which
    lines each era's air is above."""
    from climate.co2_thresholds import absolute_ppm
    from composition.data_refs import rows
    built = build_scenarios(manager, background_ppm, future_years)
    if not built.get('ok'):
        return built
    thresholds = sorted(
        rows(manager, 'CO2HealthThreshold'),
        key=lambda t: getattr(t, 'ppm', 0.0))
    out = []
    for scen in built['scenarios']:
        level = scen['indoorPpm'] or scen['outdoorPpm']
        if level is None:
            continue
        crossed = []
        for row in thresholds:
            target = absolute_ppm(row, scen['outdoorPpm'] or 0.0)
            if level >= target:
                crossed.append({
                    'threshold': getattr(row, 'name', ''),
                    'displayName': getattr(row, 'display_name', ''),
                    'absolutePpm': round(target, 1),
                    'evidenceGrade': getattr(row, 'evidence_grade',
                                             ''),
                    'isDifferential': bool(
                        getattr(row, 'is_differential', False)),
                })
        out.append({**scen, 'levelPpm': round(level, 1),
                    'thresholdsCrossed': crossed,
                    'crossedCount': len(crossed)})
    return {'ok': True, 'rows': out, 'count': len(out),
            'note': ('a threshold is counted as crossed when the '
                     'air is at or above its ABSOLUTE level - '
                     'differential thresholds are converted '
                     'against that scenario\'s own outdoor first, '
                     'which is the only way the two kinds belong '
                     'on one axis'),
            'caveat': ('crossing a line is not the same as '
                       'suffering its effect. Most of these lines '
                       'are contested, several are indicators '
                       'rather than harms, and the strongest '
                       'evidence on this page concerns acute '
                       'exposures far above any of these rooms.')}
