"""
@module climate.co2_settings_seed

THE 2x2 THE APP WAS MISSING: urban/non-urban x indoor/outdoor,
plus the MEASURED levels that check the modelled ones.

Dustin: "we apparently also need urban conditions which can reach
500 ppm outdoor, meaning a 3rd and 4th category urban vs
non-urban & indoor vs outdoor, and then different indoor
conditions and rooms".

🔑 THIS IS A CORRECTION, NOT AN ADDITION. Every indoor projection
in this app added a room's ventilation offset to the MAUNA LOA
background. Mauna Loa is chosen by NOAA precisely because it is
clean, mid-Pacific, 3400 m up and nothing local contaminates it.
Almost nobody breathes that air. Seating a city classroom on it
understated the classroom by tens of ppm and pushed every indoor
crossing date LATER than it should be. Rooms now sit on their
LOCAL outdoor level, and the local level is a row.

WHAT THE MEASUREMENTS SAY (surface in situ, all cited):
- Baltimore, 5-year record: mean urban enhancement +66 ppm.
- Phoenix: city centre to 555 ppm against ~370 ppm rural in the
  same study; a later cold-season centre maximum of 619 ppm,
  67 percent above rural background.
- Paris: a dome of "several tens of ppm" at peri-urban stations
  when wind is under 3 m/s.
- Tokyo: 406-444 ppm against a 380 ppm rural background.

⚠ AND ONE TRAP, NAMED SO NOBODY WALKS INTO IT. Satellite column
(XCO2) urban enhancements are single-digit ppm - Los Angeles peaks
around 4-6 ppm - because a column averages through kilometres of
clean air above the city. Surface enhancements are tens of ppm.
They are DIFFERENT QUANTITIES. Putting them on one axis, or
citing the satellite number as "the urban enhancement", would
understate what a person on the pavement breathes by an order of
magnitude. Every row here is `surface-in-situ` and says so.

@consumers climate.co2_indoor_seed, climate.custom.co2_crossing,
climate.climate_views_seed, climate.climate_api, polariServer
"""

from composition.custom.seed_upsert import upsert_seed_pairs

PROV = 'co2-E'

_MEASURE_IT = ('measure it: a CO2 meter on a windowsill for a '
               'week gives the local enhancement directly, and no '
               'published city average can substitute for the '
               'street you actually live on')


def _setting(name, display, locality, typ, low, high, basis,
             citation='', source='', notes=''):
    return {
        'name': name, 'display_name': display, 'setting': 'outdoor',
        'locality': locality, 'enhancement_ppm': typ,
        'enhancement_ppm_low': low, 'enhancement_ppm_high': high,
        'measurement_kind': 'surface-in-situ',
        'source_ref': source, 'citation_text': citation,
        'basis': basis, 'replaces_with': _MEASURE_IT,
        'is_prior': True, 'provenance_id': PROV, 'notes': notes,
    }


#: OUTDOOR, by how built-up the place is. Enhancement is ppm ABOVE
#: the global background, so these rows stay true as the
#: background rises - which is the whole reason they are stored as
#: offsets rather than absolute levels.
SEED_AMBIENT_SETTINGS = [
    _setting('outdoor-remote-background',
             'Remote background (what the record measures)',
             'remote-background', 0.0, 0.0, 0.0,
             'BY DEFINITION zero: this is the baseline the global '
             'record is measured at.',
             citation='NOAA GML, Mauna Loa Observatory.',
             source='noaa-gml',
             notes='THE NUMBER EVERY HEADLINE QUOTES, and the one '
                   'almost nobody breathes. Mauna Loa is chosen '
                   'for being clean, remote and 3400 m up. Using '
                   'it as the air outside a house is the mistake '
                   'this whole file exists to fix.'),
    _setting('outdoor-rural', 'Rural / open countryside', 'rural',
             5.0, 0.0, 15.0,
             'Close to background by day; can sit BELOW it over '
             'growing crops in daytime and above it on calm '
             'nights when respiration pools near the ground.',
             notes='The only setting here that can go NEGATIVE '
                   'against background - a daytime field is a '
                   'carbon sink you are standing in.'),
    _setting('outdoor-suburban', 'Suburban', 'suburban',
             20.0, 10.0, 40.0,
             'Between the rural and urban-residential cases; '
             'traffic and heating without the density.'),
    _setting('outdoor-urban-residential',
             'Urban residential', 'urban-residential',
             45.0, 20.0, 70.0,
             'The Baltimore five-year mean urban enhancement of '
             '+66 ppm is at the top of this band; quieter '
             'residential districts sit below it.',
             citation='Baltimore urban CO2 dome, 5-year record: '
                      'mean urban enhancement +66 ppm.',
             notes='THE BAND A TYPICAL CITY-DWELLING HOME SITS '
                   'ON. At a 427 ppm background this is roughly '
                   '450-500 ppm outdoors before anyone goes '
                   'inside.'),
    _setting('outdoor-urban-core', 'Urban core / city centre',
             'urban-core', 120.0, 60.0, 250.0,
             'Phoenix measured 555 ppm at the city centre against '
             '~370 ppm rural in the same study - an enhancement '
             'near +185 ppm - and a later cold-season centre '
             'maximum of 619 ppm, 67 percent above rural.',
             citation='Idso CD, Idso SB, Balling RC. An intensive '
                      'two-week study of an urban CO2 dome in '
                      'Phoenix, Arizona, USA. Atmos Environ. '
                      '2001;35(6):995-1000. And subsequent '
                      'seasonal/diurnal residential-sector work in '
                      'the same city.',
             notes='THIS IS THE SETTING DUSTIN NAMED: urban '
                   'outdoor readily reaches 500 ppm and beyond. '
                   'The enhancement is strongly diurnal and '
                   'seasonal - worst on calm cold mornings, '
                   'largely gone in a stiff breeze.'),
    _setting('outdoor-street-canyon',
             'Street canyon at traffic peak', 'street-canyon',
             250.0, 100.0, 600.0,
             'Kerbside in a built-up street during rush hour, '
             'where vehicle exhaust has nowhere to disperse.',
             notes='A SHORT-EXPOSURE setting, not a place anyone '
                   'lives - relevant to a commute, not to a '
                   'chronic dose. Widest band on this list '
                   'because it depends almost entirely on wind '
                   'and geometry.'),
]


def _observed(name, display, setting, space_kind, low, high,
              typical, citation, locality='', note='', notes=''):
    return {
        'name': name, 'display_name': display, 'setting': setting,
        'locality': locality, 'space_kind': space_kind,
        'ppm_low': low, 'ppm_high': high, 'ppm_typical': typical,
        'source_ref': '', 'citation_text': citation,
        'measurement_note': note, 'is_prior': True,
        'provenance_id': PROV, 'notes': notes,
    }


#: WHAT PEOPLE HAVE ACTUALLY MEASURED. These are the reality check
#: the modelled room numbers get scored against - see
#: `validate_against_observed`.
SEED_OBSERVED_LEVELS = [
    _observed('obs-outdoor-preindustrial',
              'Pre-industrial outdoor (global)', 'outdoor', '',
              275.0, 285.0, 280.0,
              'Antarctic ice-core composite (Bereiter et al. '
              '2015); Holocene band 269.5 +/- 8.8 ppm, '
              'pre-industrial 1700-1800 CE observed 273.1-282.8 '
              'ppm.',
              locality='remote-background',
              note='Measured in this app from the ingested ice '
                   'core, not quoted from a summary.',
              notes='THE REFERENCE EVERY OTHER ROW SHOULD BE READ '
                    'AGAINST. There was no urban/rural split '
                    'worth modelling: pre-industrial cities were '
                    'smaller and had no fossil traffic, though '
                    'wood and coal smoke made their INDOOR air '
                    'far worse than anything here.'),
    _observed('obs-outdoor-background-now',
              'Global background outdoor, today', 'outdoor', '',
              425.0, 429.0, 427.35,
              'NOAA GML Mauna Loa annual mean, 2025 = 427.35 '
              '+/- 0.12 ppm.',
              locality='remote-background',
              note='Ingested by this app.'),
    _observed('obs-outdoor-urban-now', 'Urban outdoor, today',
              'outdoor', '', 450.0, 620.0, 500.0,
              'Phoenix city centre 555 ppm (rural ~370 in the '
              'same study); cold-season centre maximum 619 ppm. '
              'Baltimore mean urban enhancement +66 ppm. Tokyo '
              '406-444 ppm against 380 ppm rural.',
              locality='urban-core',
              note='Surface in situ. Highly variable by hour, '
                   'season and wind.',
              notes='At a 427 ppm background, an urban core '
                    'routinely reads 500+ ppm - which is already '
                    'past the lowest threshold on this page '
                    'before anyone steps indoors.'),
    _observed('obs-indoor-bedroom-closed',
              'Bedroom overnight, door and windows closed',
              'indoor', 'bedroom', 1200.0, 2500.0, 1800.0,
              'Indoor air literature: closed-window bedrooms '
              'commonly reach 1200-2500 ppm by morning; two '
              'occupants over an 8-hour night in tight '
              'construction without mechanical ventilation '
              'typically 1500-2500 ppm.',
              note='Morning peak, not a night average.',
              notes='THE MODEL SHOULD BE CHECKED AGAINST THIS. '
                    'This app\'s bedroom archetype computes ~3100 '
                    'ppm, which is ABOVE the measured range - so '
                    'the archetype is pessimistic and its 0.3 ACH '
                    'prior is the likely reason.'),
    _observed('obs-indoor-classroom', 'Occupied classroom',
              'indoor', 'classroom', 763.0, 2000.0, 1335.0,
              'Classroom ventilation intervention study: baseline '
              'mean 1335 ppm, range 763-2000 ppm.',
              note='Occupied-hours mean.',
              notes='The app\'s classroom archetype computes ~2100 '
                    'ppm on an urban background, which sits just '
                    'above the measured range - again '
                    'pessimistic, and again the ventilation prior '
                    'is the suspect.'),
    _observed('obs-indoor-office', 'Office, occupied', 'indoor',
              'office', 600.0, 1200.0, 900.0,
              'Guidance and measurement literature converge on '
              'roughly 800-1000 ppm as the occupied steady state '
              'for offices meeting ventilation guidance.',
              note='Occupied-hours steady state.'),
    _observed('obs-indoor-preindustrial-dwelling',
              'Pre-industrial dwelling (MODELLED - the evidence '
              'does not exist)',
              'indoor', 'dwelling', 345.0, 900.0, 400.0,
              'NO DIRECT MEASUREMENTS EXIST, and the reason is '
              'itself a finding: the household-air-pollution '
              'literature measures PM2.5 and carbon monoxide '
              'exhaustively and CO2 almost never. Checked '
              'directly against Pollard et al., a widely cited '
              'study of 86 biomass-burning and non-biomass homes '
              'in Puno, Peru (PMC3978088): it reports median '
              '24-hour PM2.5 of 130 ug/m3 and CO of 5.8 ppm in '
              'rural biomass homes and DOES NOT MEASURE CO2 AT '
              'ALL.',
              note='MODELLED, and revised DOWN from an earlier '
                   '600 ppm estimate. There is no ice core for '
                   'indoor air.',
              notes='THE REVISION IS THE POINT. The first version '
                    'of this row said 400-900 ppm and carried a '
                    'caveat that "a CO2-only comparison across '
                    'eras flatters the past". That caveat was '
                    'wrong on CO2 specifically. The same '
                    'draughtiness that failed to clear smoke also '
                    'prevented CO2 accumulating: ventilation '
                    'removes CO2 as fast as a fire and its '
                    'occupants add it, and an unsealed dwelling '
                    'has a very high air-change rate. Modern '
                    'tight construction accumulates CO2 BECAUSE '
                    'it is tight. So on CO2 the past was probably '
                    'BETTER indoors as well as out - while being '
                    'far worse on the pollutants that actually '
                    'killed people. REVISED AGAIN after Dustin '
                    'pointed out that a wood fire provably makes '
                    'CO2: climate.custom.co2_combustion now DERIVES this '
                    'band from the measured PM2.5 and CO in those '
                    'homes rather than from a draughtiness '
                    'assumption. A 0.5 kg/h fire makes 31x one '
                    'adult\'s CO2, so the source is large; the '
                    'tracers bound how much of it reached the '
                    'room at +5 to +110 ppm on a daily average. '
                    'The daily average is 345-450 ppm; the '
                    'COOKING PEAK is higher and is the number '
                    'that matters, which is why ppm_high is 900 '
                    'rather than the daily figure.'),
]


def seed_co2_settings(manager):
    from climate.climate_basis import (
        AmbientSettingProfile, ObservedLevelReference,
    )
    return upsert_seed_pairs(manager, [
        ('AmbientSettingProfile', AmbientSettingProfile,
         SEED_AMBIENT_SETTINGS),
        ('ObservedLevelReference', ObservedLevelReference,
         SEED_OBSERVED_LEVELS),
    ], tag='ClimateSettingSeed')


def _rows(manager, class_name):
    from composition.custom.data_refs import rows
    return rows(manager, class_name)


def _named(manager, class_name, name):
    for row in _rows(manager, class_name):
        if getattr(row, 'name', '') == name:
            return row
    return None


def local_outdoor_ppm(manager, background_ppm, setting_name,
                      band='typical'):
    """Background + local enhancement = the air outside THIS door.

    `band` selects 'low' | 'typical' | 'high', because an urban
    enhancement swings with wind and hour and a single number
    would be the wrong shape.
    """
    setting = _named(manager, 'AmbientSettingProfile', setting_name)
    if setting is None:
        known = sorted(getattr(r, 'name', '')
                       for r in _rows(manager,
                                      'AmbientSettingProfile'))
        return {'ok': False,
                'refusal': (f'no AmbientSettingProfile named '
                            f'{setting_name!r}; known: {known}')}
    if getattr(setting, 'measurement_kind', '') != 'surface-in-situ':
        return {'ok': False,
                'refusal': ('this setting is not a surface '
                            'measurement, and a satellite column '
                            'enhancement cannot be added to a '
                            'surface background - they are '
                            'different quantities')}
    key = {'low': 'enhancement_ppm_low',
           'high': 'enhancement_ppm_high'}.get(
               band, 'enhancement_ppm')
    enhancement = float(getattr(setting, key, 0.0) or 0.0)
    return {'ok': True, 'setting': setting_name,
            'locality': getattr(setting, 'locality', ''),
            'backgroundPpm': float(background_ppm),
            'enhancementPpm': enhancement, 'band': band,
            'localOutdoorPpm': float(background_ppm) + enhancement,
            'citation': getattr(setting, 'citation_text', ''),
            'note': ('an enhancement is stored ABOVE background, '
                     'so this row stays true as the background '
                     'rises')}


def setting_ladder(manager, background_ppm):
    """Every outdoor setting at today's background - the
    urban/non-urban half of the 2x2."""
    out = []
    for row in _rows(manager, 'AmbientSettingProfile'):
        name = getattr(row, 'name', '')
        typical = local_outdoor_ppm(manager, background_ppm, name)
        low = local_outdoor_ppm(manager, background_ppm, name,
                                'low')
        high = local_outdoor_ppm(manager, background_ppm, name,
                                 'high')
        if not typical.get('ok'):
            continue
        out.append({
            'setting': name,
            'displayName': getattr(row, 'display_name', ''),
            'locality': getattr(row, 'locality', ''),
            'enhancementPpm': typical['enhancementPpm'],
            'localOutdoorPpm': typical['localOutdoorPpm'],
            'lowPpm': low.get('localOutdoorPpm'),
            'highPpm': high.get('localOutdoorPpm'),
            'basis': getattr(row, 'basis', ''),
            'citation': getattr(row, 'citation_text', ''),
            'notes': getattr(row, 'notes', ''),
        })
    out.sort(key=lambda s: s['localOutdoorPpm'])
    return {'ok': True, 'backgroundPpm': float(background_ppm),
            'settings': out, 'count': len(out),
            'note': ('"outdoor" is not one number. The spread '
                     'between a remote baseline and a city centre '
                     'is comparable to decades of global rise, '
                     'which is why a room must be seated on its '
                     'LOCAL outdoor level and not on the '
                     'headline one')}


def validate_against_observed(manager, space_kind, modelled_ppm):
    """Score a MODELLED room level against what has been MEASURED
    in rooms like it. Disagreement is a finding about the model,
    not about the world."""
    if not space_kind:
        # An empty space_kind used to match the OUTDOOR reference
        # rows, which carry no space_kind either - so a room with
        # no published counterpart was silently scored against
        # outdoor air. A room with no cross-check must say so.
        return {'ok': False,
                'refusal': ('this room has no published '
                            'counterpart to be checked against; '
                            'that is a gap in the measurements, '
                            'not a pass')}
    refs = [r for r in _rows(manager, 'ObservedLevelReference')
            if getattr(r, 'space_kind', '') == space_kind]
    if not refs:
        return {'ok': False,
                'refusal': (f'no ObservedLevelReference for space '
                            f'kind {space_kind!r} - the model has '
                            f'nothing to be checked against')}
    if modelled_ppm is None:
        return {'ok': False,
                'refusal': ('no modelled level was supplied, so '
                            'there is nothing to check against '
                            'the measurements')}
    ref = refs[0]
    low = float(getattr(ref, 'ppm_low', 0.0))
    high = float(getattr(ref, 'ppm_high', 0.0))
    inside = low <= modelled_ppm <= high
    if inside:
        verdict = ('the modelled level sits inside the measured '
                   'range')
    elif modelled_ppm > high:
        verdict = (f'THE MODEL IS PESSIMISTIC: it computes '
                   f'{modelled_ppm:.0f} ppm where measurements of '
                   f'rooms like this run {low:.0f}-{high:.0f}. The '
                   f'ventilation prior is the usual suspect, not '
                   f'the equation.')
    else:
        verdict = (f'THE MODEL IS OPTIMISTIC: it computes '
                   f'{modelled_ppm:.0f} ppm where measurements run '
                   f'{low:.0f}-{high:.0f}.')
    return {'ok': True, 'spaceKind': space_kind,
            'modelledPpm': modelled_ppm,
            'observedLow': low, 'observedHigh': high,
            'observedTypical': float(getattr(ref, 'ppm_typical',
                                             0.0)),
            'insideObservedRange': inside, 'verdict': verdict,
            'citation': getattr(ref, 'citation_text', ''),
            'measurementNote': getattr(ref, 'measurement_note', ''),
            'note': ('a model that disagrees with the measurement '
                     'is wrong even when its arithmetic is '
                     'right - these rows are what make that '
                     'visible')}


def era_comparison(manager):
    """Pre-industrial vs today, indoors and out - the four-cell
    table, with what is measured and what is modelled labelled
    apart."""
    cells = []
    for row in _rows(manager, 'ObservedLevelReference'):
        cells.append({
            'name': getattr(row, 'name', ''),
            'displayName': getattr(row, 'display_name', ''),
            'setting': getattr(row, 'setting', ''),
            'locality': getattr(row, 'locality', ''),
            'spaceKind': getattr(row, 'space_kind', ''),
            'ppmLow': getattr(row, 'ppm_low', 0.0),
            'ppmHigh': getattr(row, 'ppm_high', 0.0),
            'ppmTypical': getattr(row, 'ppm_typical', 0.0),
            'citation': getattr(row, 'citation_text', ''),
            'isModelled': 'MODELLED' in getattr(
                row, 'measurement_note', '').upper(),
        })
    cells.sort(key=lambda c: c['ppmTypical'])
    return {'ok': True, 'levels': cells, 'count': len(cells),
            'note': ('rows marked isModelled have no measurements '
                     'behind them - there is no ice core for '
                     'indoor air, so the pre-industrial dwelling '
                     'is an estimate and is labelled as one'),
            'caveat': ('comparing eras on CO2 ALONE is '
                       'incomplete in both directions. A '
                       'pre-industrial room had far worse smoke, '
                       'carbon monoxide and particulate - the '
                       'pollutants that shortened lives. But it '
                       'probably had LOWER CO2 than a modern '
                       'sealed room, because the draughtiness '
                       'that failed to clear the smoke also '
                       'stopped CO2 accumulating. Different '
                       'pollutants, opposite directions, one '
                       'cause.')}


def space_level(manager, space_row, background_ppm, band='typical'):
    """A room's level computed on ITS OWN local outdoor.

    THE FIX. `co2_indoor.space_offset` takes whatever outdoor
    number it is handed, and every caller used to hand it the
    global background. This resolves the room's `setting_ref`
    first, so a city classroom is seated on city air.
    """
    from climate.co2_indoor_seed import space_offset
    setting_name = (getattr(space_row, 'setting_ref', '')
                    or 'outdoor-suburban')
    local = local_outdoor_ppm(manager, background_ppm,
                              setting_name, band=band)
    if not local.get('ok'):
        return local
    offset = space_offset(space_row, local['localOutdoorPpm'])
    if not offset.get('ok'):
        return offset
    naive = space_offset(space_row, float(background_ppm))
    understated = (local['localOutdoorPpm']
                   - float(background_ppm))
    return {
        'ok': True,
        'space': getattr(space_row, 'name', ''),
        'displayName': getattr(space_row, 'display_name', ''),
        'category': getattr(space_row, 'category', ''),
        'setting': setting_name,
        'locality': local['locality'],
        'backgroundPpm': float(background_ppm),
        'localOutdoorPpm': local['localOutdoorPpm'],
        'enhancementPpm': local['enhancementPpm'],
        'ventilationOffsetPpm': offset.get('offsetPpm'),
        'indoorPpm': offset.get('indoorPpm'),
        'indoorPpmOnGlobalBackground': naive.get('indoorPpm')
        if naive.get('ok') else None,
        'understatedByPpm': understated,
        'band': band,
        'note': ('indoorPpmOnGlobalBackground is what this app '
                 'reported before settings existed - the '
                 'difference is exactly the urban enhancement, '
                 'and it was missing from every indoor number'),
    }


def all_space_levels(manager, background_ppm, band='typical'):
    """Every room on its own local outdoor, ordered - the indoor
    half of the 2x2, with the measured cross-check attached where
    one exists."""
    out = []
    for row in _rows(manager, 'IndoorSpaceProfile'):
        level = space_level(manager, row, background_ppm, band)
        if not level.get('ok'):
            out.append({'space': getattr(row, 'name', ''),
                        'refused': True,
                        'refusal': level.get('refusal', '')})
            continue
        kind = (getattr(row, 'category', '') or '')
        check = validate_against_observed(
            manager, _space_kind_of(getattr(row, 'name', '')),
            level['indoorPpm'])
        if check.get('ok'):
            level['observedCheck'] = {
                'observedLow': check['observedLow'],
                'observedHigh': check['observedHigh'],
                'insideObservedRange': check['insideObservedRange'],
                'verdict': check['verdict'],
            }
        level['categoryLabel'] = kind
        out.append(level)
    out.sort(key=lambda s: s.get('indoorPpm') or 0.0)
    return {'ok': True, 'backgroundPpm': float(background_ppm),
            'band': band, 'spaces': out, 'count': len(out),
            'note': ('every room is seated on its OWN local '
                     'outdoor. Before settings existed they were '
                     'all seated on the Mauna Loa background, '
                     'which understated every indoor number by '
                     'the urban enhancement')}


#: Room name -> the ObservedLevelReference space_kind that checks
#: it. Only rooms with published measurements appear; the rest
#: simply have no cross-check, which is reported rather than
#: faked.
_SPACE_KIND = {
    'bedroom-overnight-closed': 'bedroom',
    'classroom-occupied': 'classroom',
    'open-plan-office': 'office',
}
#: DELIBERATELY SHORT. The INTERVENTION rooms (window ajar,
#: mechanically ventilated) are not mapped, because the published
#: references describe the BASELINE condition - a closed bedroom,
#: a classroom before its ventilation was fixed. Scoring the
#: window-open room against a closed-window measurement would
#: report the intervention working as a model error. The crowded
#: meeting room is unmapped for the same reason: the office
#: reference describes open-plan space meeting ventilation
#: guidance, which is a different room, not a smaller one.


def _space_kind_of(space_name):
    return _SPACE_KIND.get(space_name, '')


#: The 800 kyr ice-core maximum, computed by this app from the
#: ingested Bereiter composite (excluding the last millennium).
#: Stated here so the escapability argument has a hard number.
RECORD_MAX_PPM_800KYR = 298.6


def era_exposure_comparison(manager, background_ppm,
                            urban_setting='outdoor-urban-core'):
    """DID PEOPLE IN THE PAST BREATHE AS MUCH CO2 AS WE DO?

    The question splits in two, and the halves have different
    answers:

    THE FLOOR - the level you return to, and cannot get below.
    Unambiguously new. The ice cores cap the entire 800,000 years
    before the last millennium at 298.6 ppm; today's global
    background is above 427 and a city centre is above 500. No
    human before roughly 1900 ever breathed today's outdoor air,
    and nobody alive today can step outside and find 280 ppm.

    THE PEAK - the worst level you hit in a room. Probably ALSO
    higher today, which is the counter-intuitive half. The
    draughtiness of an unsealed dwelling that failed to clear
    woodsmoke also stopped CO2 accumulating; modern tight
    construction accumulates CO2 precisely because it is tight. A
    modern closed bedroom MEASURES 1200-2500 ppm. What a
    pre-industrial dwelling reached is essentially unmeasured -
    the household-air-pollution literature tracks PM2.5 and CO,
    not CO2 - so this half is a physical argument, not a
    measurement, and is labelled that way.

    WHY THE FLOOR IS THE PHYSIOLOGICALLY INTERESTING ONE: chronic
    acid-base compensation responds to SUSTAINED partial pressure,
    not to transient peaks. A smoky hut you could walk out of is an
    episodic exposure. A raised global background is not
    escapable, and it is the genuinely novel exposure.
    """
    from climate.custom.series_ingest import series_points
    urban = local_outdoor_ppm(manager, background_ppm,
                              urban_setting)
    if not urban.get('ok'):
        return urban

    ice = series_points(manager, 'co2-ice-core-composite')
    record_max = RECORD_MAX_PPM_800KYR
    record_measured = False
    if ice:
        older = [p['value'] for p in ice if p['year'] < 1000.0]
        if older:
            record_max = max(older)
            record_measured = True

    refs = {getattr(r, 'name', ''): r
            for r in _rows(manager, 'ObservedLevelReference')}

    def _typ(name):
        row = refs.get(name)
        return float(getattr(row, 'ppm_typical', 0.0)) \
            if row is not None else None

    past_indoor = _typ('obs-indoor-preindustrial-dwelling')
    now_indoor = _typ('obs-indoor-bedroom-closed')
    past_outdoor = _typ('obs-outdoor-preindustrial')

    floor_rise = float(background_ppm) - (past_outdoor or 280.0)
    return {
        'ok': True,
        'question': ('were people in the past dealing with CO2 '
                     'levels as high as today, or is this new?'),
        'floor': {
            'label': 'the level you cannot get below',
            'pastPpm': past_outdoor,
            'presentBackgroundPpm': float(background_ppm),
            'presentUrbanPpm': urban['localOutdoorPpm'],
            'recordMaxPpm800kyr': record_max,
            'recordMaxIsMeasuredHere': record_measured,
            'riseSincePreindustrialPpm': floor_rise,
            'verdict': (
                f'NEW, and not marginally. The entire 800,000 '
                f'years before the last millennium cap at '
                f'{record_max:.1f} ppm. Today\'s background is '
                f'{float(background_ppm):.0f} and a city centre is '
                f'{urban["localOutdoorPpm"]:.0f}. Nobody alive can '
                f'step outside and find the air their ancestors '
                f'breathed.'),
            'evidence': 'MEASURED - Antarctic ice cores plus the '
                        'instrumental record, both ingested here.',
        },
        'peak': {
            'label': 'the worst level you hit indoors',
            'pastIndoorPpmModelled': past_indoor,
            'presentIndoorPpmMeasured': now_indoor,
            'verdict': (
                'MUCH CLOSER THAN THE FLOOR, and probably NOT '
                'novel at the peak. A wood fire is a large CO2 '
                'source - about 31 times one adult - and the '
                'smoke measured in such dwellings proves '
                'combustion products reached the occupants. '
                'Tracing the CO2 from the PM2.5 and CO that WERE '
                'measured puts a hearth dwelling near 345-450 ppm '
                'as a daily average, below a modern sealed '
                'bedroom at 1200-2500. But cooking is episodic, '
                'and a cooking-period peak plausibly reached or '
                'exceeded that bedroom. So the indoor PEAK is '
                'probably not new; what is new is that today\'s '
                'elevation is continuous and cannot be left.'),
            'evidence': ('ASYMMETRIC and the asymmetry matters: '
                         'the modern figure is MEASURED, the '
                         'pre-industrial one is MODELLED. The '
                         'household-air-pollution literature '
                         'measures PM2.5 and CO, not CO2 - '
                         'verified directly against a widely '
                         'cited 86-home biomass study that does '
                         'not report CO2 at all.'),
        },
        'whatWasWorseInThePast': (
            'Smoke. Open hearths produced PM2.5 and carbon '
            'monoxide at levels that would close a modern '
            'building - median 130 ug/m3 PM2.5 and 5.8 ppm CO in '
            'measured rural biomass homes. Those are the exposures '
            'that shortened pre-industrial lives, and they are '
            'not CO2. The SAME draughtiness that made the smoke '
            'survivable is why the CO2 stayed low: one cause, '
            'opposite directions, two different pollutants.'),
        'whyTheFloorMatters': (
            'Chronic acid-base compensation responds to SUSTAINED '
            'partial pressure, not to transient peaks. A smoky hut '
            'was escapable; a raised global background is not. '
            'That is what makes the floor - not the peak - the '
            'genuinely novel exposure, and it is why this app '
            'projects crossing dates from the background series '
            'rather than from a worst-room number.'),
        'answer': (
            'THE FLOOR IS NEW; THE PEAK PROBABLY IS NOT. Outdoor '
            'is definitively new and measured: the 800,000-year '
            'record caps below 300 ppm and today is 427 global, '
            '547 urban, and inescapable. Indoors is a closer '
            'call than it first appears - a wood fire provably '
            'makes CO2, about 31 times what an adult exhales, and '
            'tracing it from the smoke that WAS measured puts a '
            'hearth dwelling near 345-450 ppm daily average with '
            'cooking peaks plausibly at or above a modern sealed '
            'bedroom. So people have breathed high indoor CO2 '
            'before. What no one had before is a raised BASELINE '
            'they cannot step outside of - and chronic '
            'compensation answers to the baseline, not the '
            'peak.'),
        'whatWouldSettleIt': (
            'CO2 logging in dwellings still heated and cooked in '
            'the traditional way, alongside the PM2.5 and CO that '
            'such studies already collect. It is one more sensor '
            'on an instrument package that is already deployed - '
            'which is why the gap is an oversight rather than a '
            'hard problem.'),
        'headline': [
            {'label': 'Outdoor, pre-industrial',
             'value': f'{past_outdoor:.0f} ppm'
             if past_outdoor else 'unknown',
             'note': 'measured, ice cores', 'verdict': 'ok'},
            {'label': '800,000-year maximum',
             'value': f'{record_max:.1f} ppm',
             'note': 'the cap on everything any ancestor breathed',
             'verdict': 'ok'},
            {'label': 'Outdoor today (background / urban)',
             'value': f'{float(background_ppm):.0f} / '
                      f'{urban["localOutdoorPpm"]:.0f} ppm',
             'note': f'+{floor_rise:.0f} ppm on the floor, and '
                     f'inescapable',
             'verdict': 'bad'},
            {'label': 'Indoor today, closed bedroom',
             'value': f'{now_indoor:.0f} ppm'
             if now_indoor else 'unknown',
             'note': 'MEASURED', 'verdict': 'warn'},
            {'label': 'Indoor pre-industrial dwelling',
             'value': f'~{past_indoor:.0f} ppm'
             if past_indoor else 'unknown',
             'note': 'MODELLED - no measurement exists',
             'verdict': 'ok'},
        ],
    }
