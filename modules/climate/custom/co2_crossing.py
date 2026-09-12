"""
@module climate.custom.co2_crossing

THE COUPLED CROSSING PROJECTION (CO2_HEALTH_PLAN.md §7) — the
piece that makes this a study rather than a chart.

Indoor CO2 is not an independent series. A room sits at

    indoor_ppm = outdoor_ppm + emission / ventilation

so every absolute threshold indoors moves EARLIER on the calendar
as outdoor rises, one-for-one, on top of whatever the room's own
ventilation already contributes. The indoor offset is computed by
`co2_indoor.space_offset`, which is the aquaponics steady-state
solver with the source term's sign flipped - one equation, two
callers, guard-tested.

Two rules this module exists to enforce:

1. A DIFFERENTIAL threshold is not an absolute one. ASHRAE's
   criterion is "700 ppm above outdoor", so its absolute value
   RISES with the outdoor record. Comparing it to a fixed line
   without adding outdoor CO2 first is the single easiest way to
   get this whole subject wrong, and `co2_thresholds.absolute_ppm`
   is the only sanctioned way to put the two kinds on one axis.

2. Every answer is a BAND. The linear and quadratic fits bracket
   the crossing, and the gap between them IS the acceleration
   finding. A single year with no band is the documented failure
   mode.

Where a room is ALREADY past a line, the answer is
`already-crossed` with the outdoor level that put it there - never
a negative "years away". For several archetypes that is the
answer, and it is the finding.

@consumers climate.climate_api, climate.climate_views_seed,
climate.climate_selftest
"""

import datetime

from climate.co2_indoor_seed import space_offset, ventilation_knob
from climate.co2_thresholds_seed import absolute_ppm
from climate.custom.co2_trend import crossing_band, fit_trend

PROV = 'co2-5'

#: Windows the fits run over. The linear window is short (recent
#: behaviour); the quadratic needs enough years for the curvature
#: to be resolvable rather than fitted to noise.
LINEAR_WINDOW_YEARS = 30.0
QUADRATIC_WINDOW_YEARS = 45.0


def _now():
    return datetime.datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%SZ')


def build_fits(points, linear_window=LINEAR_WINDOW_YEARS,
               quadratic_window=QUADRATIC_WINDOW_YEARS):
    """The linear/quadratic pair the band is built from."""
    if not points:
        return {}, ('no observations - ingest the outdoor series '
                    'before projecting from it')
    last = max(p['year'] for p in points)
    fits = {
        'linear': fit_trend(points, method='linear',
                            window_from=last - linear_window),
        'quadratic': fit_trend(points, method='quadratic',
                               window_from=last - quadratic_window),
    }
    if not any(f.get('ok') for f in fits.values()):
        return {}, ('neither fit succeeded: '
                    + '; '.join(f.get('refusal', '')
                                for f in fits.values()))
    return fits, ''


def outdoor_crossings(points, thresholds, horizon_years=200):
    """When outdoor background reaches each ABSOLUTE threshold.

    Differential thresholds are skipped here by construction: "700
    ppm above outdoor" is not a level the outdoor record can ever
    reach, and reporting a year for it would be nonsense.
    """
    fits, refusal = build_fits(points)
    if refusal:
        return {'ok': False, 'refusal': refusal}
    present = fits.get('quadratic', {}).get('level') \
        or fits.get('linear', {}).get('level') or 0.0

    out = []
    for row in thresholds:
        name = getattr(row, 'name', '')
        if bool(getattr(row, 'is_differential', False)):
            out.append({
                'threshold': name, 'skipped': True,
                'reason': ('a differential threshold has no outdoor '
                           'crossing - it is defined relative to '
                           'outdoor CO2, so it moves with it'),
            })
            continue
        target = float(getattr(row, 'ppm', 0.0))
        band = crossing_band(fits, target,
                             horizon_years=horizon_years)
        out.append(_band_entry(name, row, target, band, present))
    return {'ok': True, 'presentPpm': round(present, 2),
            'crossings': out, 'fits': _fit_summary(fits),
            'note': ('bands come from the linear and quadratic '
                     'fits; the gap between them is the '
                     'acceleration, not an error bar')}


def _band_entry(name, row, target, band, present):
    entry = {
        'threshold': name,
        'displayName': getattr(row, 'display_name', name),
        'targetPpm': target,
        'evidenceGrade': getattr(row, 'evidence_grade', ''),
        'population': getattr(row, 'population', ''),
        'exposure': getattr(row, 'exposure', ''),
        'skipped': False,
    }
    if target <= present:
        entry.update(alreadyCrossed=True, crossingYearLow=None,
                     crossingYearHigh=None,
                     note=('already at or above this level'))
        return entry
    if not band.get('ok'):
        entry.update(alreadyCrossed=False, refused=True,
                     refusal=band.get('refusal', ''))
        return entry
    low, high = band.get('low'), band.get('high')
    if low is None or high is None:
        # Belt and braces with the fix in crossing_band: a band
        # whose bounds are missing must never reach a renderer as
        # an "ok" row, because a null formats as "None" in every
        # template language and reads as a value.
        entry.update(alreadyCrossed=False, refused=True,
                     refusal=(band.get('refusal')
                              or 'the band has no bounds'))
        return entry
    entry.update(alreadyCrossed=False, crossingYearLow=low,
                 crossingYearHigh=high,
                 oneSided=bool(band.get('oneSided')),
                 note=band.get('note', ''))
    return entry


def _fit_summary(fits):
    out = {}
    for key, fit in fits.items():
        if not fit.get('ok'):
            out[key] = {'ok': False,
                        'refusal': fit.get('refusal', '')}
            continue
        out[key] = {
            'ok': True, 'level': round(fit['level'], 3),
            'velocity': round(fit['velocity'], 5),
            'velocityStderr': round(fit['velocityStderr'], 5),
            'acceleration': round(fit['acceleration'], 6),
            'accelerationStderr': round(
                fit['accelerationStderr'], 6),
            'nPoints': fit['nPoints'],
            'windowFromYear': fit['windowFromYear'],
            'windowToYear': fit['windowToYear'],
            'residualRms': round(fit['residualRms'], 4),
        }
    return out


def coupled_crossings(points, thresholds, spaces,
                      horizon_years=200):
    """THE TABLE: threshold x space -> crossing year band.

    For each room the outdoor projection is shifted by that room's
    steady-state offset, so the question becomes "when does
    outdoor + offset reach the threshold" - which is the same
    projection solved against a LOWER outdoor target.
    """
    fits, refusal = build_fits(points)
    if refusal:
        return {'ok': False, 'refusal': refusal}
    present = fits.get('quadratic', {}).get('level') \
        or fits.get('linear', {}).get('level') or 0.0

    rows_out, offsets = [], {}
    for space in spaces:
        space_name = getattr(space, 'name', '')
        off = space_offset(space, present)
        if not off.get('ok'):
            rows_out.append({'space': space_name, 'refused': True,
                             'refusal': off.get('refusal', '')})
            continue
        offset_ppm = off.get('offsetPpm', 0.0)
        offsets[space_name] = offset_ppm
        knob = ventilation_knob(space, present, factor=2.0)

        for row in thresholds:
            t_name = getattr(row, 'name', '')
            # A differential threshold becomes absolute the moment
            # outdoor CO2 is known - and it keeps moving.
            target_abs = absolute_ppm(row, present)
            # Indoor reaches `target_abs` when outdoor reaches
            # target_abs - offset.
            outdoor_target = target_abs - offset_ppm
            entry = {
                'space': space_name,
                'spaceDisplay': getattr(space, 'display_name',
                                        space_name),
                'threshold': t_name,
                'thresholdDisplay': getattr(row, 'display_name',
                                            t_name),
                'thresholdPpm': float(getattr(row, 'ppm', 0.0)),
                'isDifferential': bool(
                    getattr(row, 'is_differential', False)),
                'absoluteTargetPpm': round(target_abs, 2),
                'indoorOffsetPpm': round(offset_ppm, 2),
                'indoorPpmToday': round(present + offset_ppm, 2),
                'evidenceGrade': getattr(row, 'evidence_grade', ''),
            }
            if outdoor_target <= present:
                entry.update(
                    alreadyCrossed=True, crossingYearLow=None,
                    crossingYearHigh=None,
                    note=('this room is ALREADY past this line at '
                          'today\'s outdoor level and its stated '
                          'ventilation'))
            else:
                band = crossing_band(fits, outdoor_target,
                                     horizon_years=horizon_years)
                if band.get('ok'):
                    entry.update(
                        alreadyCrossed=False,
                        crossingYearLow=band.get('low'),
                        crossingYearHigh=band.get('high'),
                        oneSided=bool(band.get('oneSided')))
                else:
                    entry.update(alreadyCrossed=False, refused=True,
                                 refusal=band.get('refusal', ''))
            if knob.get('ok'):
                entry['ventilationKnob'] = {
                    'baseAch': knob.get('baseAch'),
                    'doubledAch': knob.get('newAch'),
                    'ppmDelta': knob.get('deltaPpm'),
                    'note': ('doubling ventilation moves the indoor '
                             'level by this much; a crossing that '
                             'arrives at one ACH may never arrive '
                             'at another'),
                }
            rows_out.append(entry)

    return {'ok': True, 'presentPpm': round(present, 2),
            'rows': rows_out, 'offsets': offsets,
            'fits': _fit_summary(fits),
            'note': ('indoor = outdoor + emission/ventilation, so '
                     'every absolute line arrives EARLIER indoors '
                     'than outdoors for every room - if one ever '
                     'does not, the coupling has a sign error')}


def store_projections(manager, table, series_ref='',
                      fit_ref='', method='quadratic'):
    """Persist the crossing table as ExposureProjection rows, so
    the next ingest's answers can be compared against these and
    the page can show its own answers moving."""
    from climate.climate_basis import ExposureProjection
    from moduleService.seed_upsert import upsert_seed_pairs
    seeds = []
    for entry in table.get('rows', []) or table.get('crossings', []):
        if entry.get('skipped'):
            continue
        space = entry.get('space', '')
        thresh = entry.get('threshold', '')
        seeds.append({
            'name': f'proj--{thresh}--{space or "outdoor"}',
            'threshold_ref': thresh, 'space_ref': space,
            'series_ref': series_ref, 'fit_ref': fit_ref,
            'method': method,
            'crossing_year': entry.get('crossingYearLow') or 0.0,
            'crossing_year_low': entry.get('crossingYearLow') or 0.0,
            'crossing_year_high': (entry.get('crossingYearHigh')
                                   or 0.0),
            'already_crossed': bool(entry.get('alreadyCrossed')),
            'outdoor_ppm_at_crossing': entry.get(
                'absoluteTargetPpm', 0.0),
            'indoor_offset_ppm': entry.get('indoorOffsetPpm', 0.0),
            'ventilation_knob_note': (
                (entry.get('ventilationKnob') or {}).get('note', '')),
            'refused': bool(entry.get('refused')),
            'refusal': entry.get('refusal', ''),
            'computed_at': _now(), 'is_prior': False,
            'provenance_id': PROV,
            'notes': entry.get('note', ''),
        })
    if not seeds:
        return {'ok': False,
                'refusal': 'no projections to store'}
    reports = upsert_seed_pairs(
        manager, [('ExposureProjection', ExposureProjection, seeds)],
        tag='ClimateProjectionSeed')
    return {'ok': True, 'stored': len(seeds), 'reports': reports}


def monotonicity_check(crossings):
    """A guard the plan names: outdoor crossing years must be
    monotone in the threshold. A higher line cannot arrive
    earlier."""
    usable = [c for c in crossings
              if not c.get('skipped') and not c.get('refused')
              and not c.get('alreadyCrossed')
              and c.get('crossingYearLow') is not None]
    usable.sort(key=lambda c: c['targetPpm'])
    years = [c['crossingYearLow'] for c in usable]
    ok = all(b >= a for a, b in zip(years, years[1:]))
    return {'ok': ok, 'nChecked': len(usable), 'years': years,
            'note': ('a higher threshold must never arrive earlier '
                     'than a lower one')}
