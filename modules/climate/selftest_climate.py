"""
@module climate.selftest_climate

Climate & Atmosphere selftests — the offline pins for the CO2
health study. Everything here runs from INLINE fixtures: no
network, no checked-in binary, no file read. An injected fetcher
stands in for the wire.

What this suite exists to prevent, in order of how badly it would
hurt:

1. A DECOY INGESTED AS DATA. Two federal agencies answer dead
   URLs with HTTP 200 and an HTML page. The acceptance gate on
   the APIEndpoint row (minBytes / rejectSignature /
   contentSignature) is the only thing standing between that
   webpage and a lab result, and on every refusal `body` is None
   so a caller physically cannot parse it.
2. A MIRRORED RECORD. Ice cores publish cal BP, present fixed at
   1950. Getting `year_ce = 1950 - age_bp` backwards flips the
   whole of human prehistory; age 0 is 1950 and age -51 is 2001.
3. A CROSSING YEAR WITH NO BAND — or worse, a band that reports
   ok with both bounds None. That shape reaches a page as the
   string "None" and reads as a value. It was a real bug; it is
   pinned here so it cannot come back.
4. A SIGN ERROR IN THE COUPLING. indoor = outdoor + emission /
   ventilation, so every absolute line must arrive EARLIER
   indoors than outdoors, for every room and every threshold.
5. A SECOND MASS BALANCE. The crop that depletes CO2 and the
   people who emit it are ONE equation with one sign flipped;
   the two callers' offsets must mirror exactly.

Run from polari-framework/: python3 -m climate.selftest_climate
"""

import inspect
import json
import os
import types

from climate.climate_basis import (
    AtmosphericSeriesDefinition, CO2HealthThreshold, EVIDENCE_GRADES,
    HumanEraDefinition, IndoorSpaceProfile,
)
from climate.climate_export import (
    EXPORT_FORMATS, export_csv, export_markdown, export_series,
    export_svg,
)
from climate.climate_history import (
    COGNITION_QUESTION, SEED_HUMAN_ERAS, splice_series,
)
from climate.climate_series import (
    SEED_CLIMATE_SERIES, SERIES_PARSERS,
)
from climate.climate_sources import (
    HTML_DECOY, SEED_CLIMATE_ENDPOINTS, TEXT_SIG, XPORT_SIG,
)
from climate.co2_crossing import (
    coupled_crossings, monotonicity_check, outdoor_crossings,
)
from climate.co2_indoor import (
    SEED_INDOOR_SPACES, guard_two_callers, space_offset,
    steady_state_ppm, ventilation_knob,
)
from climate.co2_thresholds import (
    SEED_CO2_THRESHOLDS, absolute_ppm, grade_rank,
)
from climate.co2_trend import (
    compare_velocity, crossing_band, crossing_year, fit_trend,
)
from climate.series_parsers import (
    PARSERS, get_parser, parse_ice_core_composite, parse_noaa_annual,
)
from climate.xpt_reader import make_min_xport, read_xpt_bytes
from polariApiProfiler.apiEndpoint import APIEndpoint
from polariApiProfiler.endpoint_fetch import (
    fetch_endpoint, resolve_endpoint_url,
)

PASS = '\033[92mPASS\033[0m'
FAIL = '\033[91mFAIL\033[0m'
_results = []


def check(label, cond, extra=''):
    _results.append(bool(cond))
    print(f'{PASS if cond else FAIL}: {label}'
          + (f'  [{extra}]' if extra and not cond else ''))


def _ns(seed):
    return types.SimpleNamespace(**seed)


def _table(seeds):
    return {s['name']: _ns(s) for s in seeds}


def _init_params(cls):
    """The kwargs a treeObject class actually accepts. A seed key
    that is not here is silently dropped on construction."""
    sig = inspect.signature(cls.__init__)
    return {n for n in sig.parameters
            if n not in ('self', 'manager', 'kwargs')}


def _seed_by_name(seeds, name):
    for row in seeds:
        if row['name'] == name:
            return row
    return None


# --------------------------------------------------------------
# FIXTURES — built inline. Nothing here touches disk or network.
# --------------------------------------------------------------

#: NOAA GML annual-mean shape: a '#' banner then whitespace
#: columns. Row four is deliberately unreadable.
NOAA_TEXT = '\n'.join([
    '# ------------------------------------------------------',
    '# USE OF NOAA GML DATA',
    '# year     mean      unc',
    '  1959   315.98     0.12',
    '  1960   316.91     0.12',
    '  1961   317.64     0.12',
    '  bad    row        here',
    '  1962   318.45     0.12',
    '',
])

#: NCEI paleo shape: a '#' banner, a BARE column-name line with no
#: comment marker, then tab-delimited rows. Ages are cal BP.
ICE_TEXT = '\n'.join([
    '# Antarctic Ice Cores Revised 800KYr CO2 Data',
    '# Bereiter et al. 2015',
    '#',
    'age_gas_calBP\tco2_ppm\tco2_1s_ppm',
    '-51\t368.02\t0.06',
    '0\t311.51\t0.10',
    '1000\t279.60\t0.15',
    'bad\trow\there',
    '',
])

_XPORT_HEAD = XPORT_SIG.encode('ascii')
#: A real payload: the right signature, comfortably over minBytes.
GOOD_XPORT_BYTES = _XPORT_HEAD + b' ' * 120000
#: The decoy, sized ABOVE minBytes on purpose so the reject
#: signature — not the byte count — is what catches it.
HTML_DECOY_BYTES = (HTML_DECOY.encode('ascii')
                    + b'><html><head><title>Page Not Found</title>'
                    + b'</head><body>' + b'x' * 120000
                    + b'</body></html>')
#: Right size, wrong file.
WRONG_SIG_BYTES = b'# this is a NOAA text banner' + b' ' * 120000
#: Under minBytes.
SHORT_BYTES = _XPORT_HEAD + b' ' * 400

_FETCH_BODY = {'value': GOOD_XPORT_BYTES}


def fake_fetcher(url, timeout=120, headers=None):
    """The injected wire. Returns whatever the current case set."""
    return 200, _FETCH_BODY['value'], ''


def _fetch(endpoint, body, params=None):
    _FETCH_BODY['value'] = body
    return fetch_endpoint(endpoint, params=params,
                          fetcher=fake_fetcher)


NHANES_EP = _ns(_seed_by_name(SEED_CLIMATE_ENDPOINTS,
                              'nhanes-biopro-xpt'))


# --------------------------------------------------------------
print('== suite: endpoint_fetch — the decoy guard ==')

_html = _fetch(NHANES_EP, HTML_DECOY_BYTES)
check('an HTML body served with HTTP 200 REFUSES — a status code '
      'is not evidence that a payload is the data',
      _html.get('ok') is False and _html.get('status') == 200,
      json.dumps({k: v for k, v in _html.items()
                  if k != 'body'})[:200])
check('and the refusal SAYS it is an error/landing page, not a '
      'vague signature mismatch',
      'landing page' in _html.get('refusal', '')
      and 'success status' in _html.get('refusal', ''),
      _html.get('refusal', ''))

_short = _fetch(NHANES_EP, SHORT_BYTES)
check('a body under minBytes refuses and NAMES the byte count '
      'and the minimum',
      _short.get('ok') is False
      and str(len(SHORT_BYTES)) in _short.get('refusal', '')
      and str(NHANES_EP.minBytes) in _short.get('refusal', ''),
      _short.get('refusal', ''))

_wrong = _fetch(NHANES_EP, WRONG_SIG_BYTES)
check('a big enough payload with the WRONG contentSignature '
      'still refuses — size is not identity',
      _wrong.get('ok') is False
      and 'does not begin with' in _wrong.get('refusal', ''),
      _wrong.get('refusal', ''))

_good = _fetch(NHANES_EP, GOOD_XPORT_BYTES)
check('the real payload passes the gate',
      _good.get('ok') is True and _good.get('status') == 200,
      _good.get('refusal', ''))
check('a passing retrieval carries a sha256 of the right length '
      'and a BYTES body (decoding to identify a payload corrupts '
      'the binary formats this path exists to fetch)',
      len(_good.get('sha256', '')) == 64
      and isinstance(_good.get('body'), bytes)
      and len(_good['body']) == len(GOOD_XPORT_BYTES),
      f"sha={len(_good.get('sha256', ''))} "
      f"type={type(_good.get('body')).__name__}")
check('ON EVERY REFUSAL body IS None — a caller physically '
      'cannot parse a decoy',
      all(r.get('body') is None
          for r in (_html, _short, _wrong)),
      str([type(r.get('body')).__name__
           for r in (_html, _short, _wrong)]))

_live, _safe = resolve_endpoint_url(NHANES_EP)
check('resolve_endpoint_url fills {year}/{file} from '
      'paramsTemplate — one row covers every NHANES cycle',
      _live == ('https://wwwn.cdc.gov/Nchs/Data/Nhanes/Public/'
                '2017/DataFiles/BIOPRO_J.xpt')
      and _safe == _live, _live)
_live2, _ = resolve_endpoint_url(NHANES_EP,
                                 {'year': '2021',
                                  'file': 'BIOPRO_L'})
check('call params override the template defaults',
      _live2.endswith('/2021/DataFiles/BIOPRO_L.xpt'), _live2)

_missing_err = ''
try:
    resolve_endpoint_url({'name': 'fx-missing-param',
                          'url': 'https://example.invalid',
                          'endpointPath': '{cycle}/file.xpt',
                          'paramsTemplate': '{}'})
except ValueError as exc:
    _missing_err = str(exc)
check('an unfilled placeholder RAISES by name rather than '
      'fetching a URL with a literal {cycle} in it',
      'cycle' in _missing_err and 'paramsTemplate' in _missing_err,
      _missing_err)

_VAR = 'POLARI_TEST_UNSET_CLIMATE_KEY'
os.environ.pop(_VAR, None)
_bearer = APIEndpoint(name='fx-bearer-endpoint', authType='bearer',
                      authConfig=f'env:{_VAR}', manager=None)
_secret, _refusal = _bearer.resolve_secret()
check('authConfig is a POINTER: an unset env var resolves to NO '
      'secret and a refusal NAMING the variable — the literal '
      'string is never sent as a credential',
      _secret == '' and _VAR in _refusal
      and 'unset' in _refusal, f'{_secret!r} / {_refusal}')
check('and no Authorization header is built from it',
      'Authorization' not in _bearer.get_headers_with_auth(),
      str(_bearer.get_headers_with_auth()))


# --------------------------------------------------------------
print('== suite: series_parsers ==')

_noaa = parse_noaa_annual(NOAA_TEXT)
check('parse_noaa_annual reads the NOAA annual-mean shape: '
      '4 points, comment banner skipped',
      _noaa.get('ok') and len(_noaa['points']) == 4,
      json.dumps(_noaa)[:200])
check('the years and values are the file\'s, exactly',
      [p['year'] for p in _noaa['points']]
      == [1959.0, 1960.0, 1961.0, 1962.0]
      and [p['value'] for p in _noaa['points']]
      == [315.98, 316.91, 317.64, 318.45]
      and _noaa['points'][0]['uncertainty'] == 0.12,
      str(_noaa['points']))
check('a MALFORMED ROW IS COUNTED, not silently dropped — '
      '"we parsed 4 of 5 rows" is a finding, "we parsed 4" is '
      'not',
      _noaa.get('skippedCount') == 1
      and any('bad' in s for s in _noaa.get('skipped', [])),
      str(_noaa.get('skippedCount')) + ' ' + str(_noaa.get('skipped')))

_ice = parse_ice_core_composite(ICE_TEXT)
_years = [p['year'] for p in _ice.get('points', [])]
check('parse_ice_core_composite reads the tab-delimited paleo '
      'shape (3 points)',
      _ice.get('ok') and len(_ice['points']) == 3,
      json.dumps(_ice)[:200])
check('THE SIGN CONVENTION: cal BP -> CE is 1950 - age, so age 0 '
      'is 1950, age -51 is 2001 and age 1000 is 950. Backwards '
      'here mirrors the entire record',
      _years == [2001.0, 1950.0, 950.0], str(_years))
check('and every point keeps its original ageBp beside the '
      'converted year',
      [p['ageBp'] for p in _ice['points']] == [-51.0, 0.0, 1000.0],
      str([p.get('ageBp') for p in _ice['points']]))
check('the BARE column-header line (no "#") is skipped by '
      'failing to parse as a number — banner length is not '
      'stable across NCEI studies, so line counting would break',
      _ice.get('skippedCount') == 2
      and any('age_gas_calBP' in s for s in _ice.get('skipped', [])),
      str(_ice.get('skipped')))

_fn, _why = get_parser('nope')
check('get_parser refuses an unknown parser and NAMES the ones '
      'that exist (the Law Dome endpoint is deliberately in this '
      'state)',
      _fn is None and 'nope' in _why
      and all(k in _why for k in PARSERS), _why)


# --------------------------------------------------------------
print('== suite: co2_trend — velocity, acceleration, the band ==')

_LIN = [{'year': 2000.0 + i, 'value': 300.0 + 2.0 * i,
         'uncertainty': 0.1} for i in range(11)]
_lin_q = fit_trend(_LIN, method='quadratic')
check('a PURE LINEAR series fitted as a quadratic returns '
      'acceleration identically zero (|a| < 1e-9) and the exact '
      'velocity — curvature is not invented out of noise',
      _lin_q.get('ok') and abs(_lin_q['acceleration']) < 1e-9
      and abs(_lin_q['velocity'] - 2.0) < 1e-9
      and abs(_lin_q['level'] - 320.0) < 1e-9,
      json.dumps(_lin_q)[:220])

_A, _V, _L, _BASE = 0.03, 2.0, 400.0, 2025.0
_QUAD = [{'year': y,
          'value': _L + _V * (y - _BASE)
                   + 0.5 * _A * (y - _BASE) ** 2,
          'uncertainty': 0.0}
         for y in range(1980, 2026)]
_qf = fit_trend(_QUAD, method='quadratic')
check('a KNOWN quadratic is recovered to 1e-6 in level, velocity '
      'and acceleration',
      _qf.get('ok') and abs(_qf['level'] - _L) < 1e-6
      and abs(_qf['velocity'] - _V) < 1e-6
      and abs(_qf['acceleration'] - _A) < 1e-6,
      json.dumps(_qf)[:220])

_lin_f = fit_trend(_LIN, method='linear')
_cross = crossing_year(_lin_f, 340.0)
check('crossing_year on a rising linear fit is analytically '
      'exact: level 320 at 2010 rising 2/yr reaches 340 in 2020',
      _cross.get('ok') and _cross['alreadyCrossed'] is False
      and abs(_cross['crossingYear'] - 2020.0) < 1e-9
      and abs(_cross['yearsAway'] - 10.0) < 1e-9,
      json.dumps(_cross))

_past = crossing_year(_lin_f, 300.0)
check('a target BELOW the present level reports alreadyCrossed '
      'and NEVER a negative yearsAway',
      _past.get('ok') and _past['alreadyCrossed'] is True
      and _past['yearsAway'] == 0.0
      and _past['crossingYear'] is None, json.dumps(_past))

_thin = fit_trend(_LIN[:4], method='quadratic')
check('4 points refuse a quadratic fit, naming the count and the '
      'minimum — too few years becomes a REFUSAL, never a small '
      'number',
      _thin.get('ok') is False and '4' in _thin['refusal']
      and '5' in _thin['refusal'], _thin.get('refusal', ''))

_far = crossing_year(_lin_f, 10000.0, horizon_years=200)
check('a target beyond the horizon refuses — a quadratic fit is '
      'not a climate model and will not print a year for 2300',
      _far.get('ok') is False and 'horizon' in _far['refusal'],
      _far.get('refusal', ''))

_fits = {'linear': _lin_f,
         'quadratic': fit_trend(_QUAD, method='quadratic')}
_band = crossing_band(_fits, 1.0e6, horizon_years=200)
check('THE REGRESSION PIN: a band NEITHER fit reaches returns ok '
      'FALSE — not ok-with-None-bounds, which reaches a page as '
      'the string "None" and reads as a value',
      _band.get('ok') is False and _band.get('low') is None
      and _band.get('high') is None
      and _band.get('bandWidthYears') is None,
      json.dumps(_band)[:220])
check('and that refusal CARRIES BOTH SIDES\' reasons so the '
      'caller can see why',
      'linear:' in _band.get('refusal', '')
      and 'quadratic:' in _band.get('refusal', ''),
      _band.get('refusal', ''))

_two = crossing_band(_fits, 500.0, horizon_years=400)
check('when both fits solve, the band is a BRACKET with a width '
      '— one number with no band is the documented failure mode',
      _two.get('ok') and _two.get('low') is not None
      and _two.get('high') >= _two.get('low')
      and _two.get('oneSided') is False, json.dumps(_two)[:200])

_cmp = compare_velocity(2.5, 2.0, tolerance=0.15)
check('compare_velocity flags a 25 percent gap as a FINDING, '
      'not an averaging problem',
      _cmp.get('ok') and _cmp['agree'] is False
      and 'DISAGREEMENT IS A FINDING' in _cmp['verdict'],
      _cmp.get('verdict', ''))
check('and agreement inside tolerance is stated as two '
      'independent paths landing on one number',
      compare_velocity(2.05, 2.0)['agree'] is True)


# --------------------------------------------------------------
print('== suite: co2_thresholds — the graded table ==')

_TH_ROWS = [_ns(s) for s in SEED_CO2_THRESHOLDS]
_ashrae = _seed_by_name(SEED_CO2_THRESHOLDS, 'ashrae-differential-700')
_ashrae_row = _ns(_ashrae)
check('THE MOST IMPORTANT ROW ON THE PAGE: ASHRAE\'s +700 is a '
      'DIFFERENTIAL, so absolute_ppm gives 980.0 at a 280 ppm '
      'background and 1127.35 today — a fully compliant room '
      'rises with the air fed into it, with nothing about the '
      'room having changed',
      abs(absolute_ppm(_ashrae_row, 280.0) - 980.0) < 1e-9
      and abs(absolute_ppm(_ashrae_row, 427.35) - 1127.35) < 1e-9,
      f'{absolute_ppm(_ashrae_row, 280.0)} / '
      f'{absolute_ppm(_ashrae_row, 427.35)}')

_niosh_row = _ns(_seed_by_name(SEED_CO2_THRESHOLDS,
                               'niosh-rel-twa-5000'))
check('an ABSOLUTE row is returned unchanged whatever outdoor '
      'is — the two kinds must never be mixed',
      absolute_ppm(_niosh_row, 0.0) == 5000.0
      and absolute_ppm(_niosh_row, 427.35) == 5000.0
      and absolute_ppm(_niosh_row, 9999.0) == 5000.0)

check('every seeded threshold carries a KNOWN evidence grade',
      all(s['evidence_grade'] in EVIDENCE_GRADES
          for s in SEED_CO2_THRESHOLDS),
      str([s['evidence_grade'] for s in SEED_CO2_THRESHOLDS
           if s['evidence_grade'] not in EVIDENCE_GRADES]))
check('both ASHRAE rows are graded standard-or-guideline, NOT a '
      'health-study grade — the standard explicitly declines to '
      'assert harm',
      all(_seed_by_name(SEED_CO2_THRESHOLDS, n)['evidence_grade']
          == 'standard-or-guideline'
          for n in ('ashrae-differential-700',
                    'ashrae-indicator-1000')))
_cog = [s for s in SEED_CO2_THRESHOLDS
        if s['name'].startswith('co2-cognitive-decrement')]
check('the two chamber-study rows are graded '
      'contested-controlled-study AND carry a non-empty '
      'contested_by — a page showing only the supporting '
      'citation is advocacy',
      len(_cog) == 2
      and all(s['evidence_grade'] == 'contested-controlled-study'
              and s['contested_by'].strip() for s in _cog),
      str([(s['name'], s['evidence_grade']) for s in _cog]))
_neg = _seed_by_name(SEED_CO2_THRESHOLDS,
                     'co2-preindustrial-baseline')
check('THE NEGATIVE ROW exists at 280 ppm with no claimed '
      'effect — a table listing only harms implies harm '
      'everywhere and bounds nothing',
      _neg is not None and _neg['ppm'] == 280.0
      and 'no evidence' in _neg['effect'].lower())

check('grade_rank orders a controlled human study STRICTLY '
      'stronger than a ventilation guideline, and an unknown '
      'grade sorts last',
      grade_rank('controlled-human-study')
      < grade_rank('standard-or-guideline')
      < grade_rank('typo-grade'),
      f"{grade_rank('controlled-human-study')} "
      f"{grade_rank('standard-or-guideline')} "
      f"{grade_rank('typo-grade')}")

_th_params = _init_params(CO2HealthThreshold)
_th_extra = {k for s in SEED_CO2_THRESHOLDS for k in s
             if k not in _th_params}
check('every CO2HealthThreshold seed key is a real __init__ '
      'parameter — an unknown key is silently dropped on '
      'construction (the ten-strikes seed gotcha)',
      not _th_extra, str(sorted(_th_extra)))


# --------------------------------------------------------------
print('== suite: co2_indoor — ONE equation, two callers ==')

_guard = guard_two_callers()
check('THE GUARD: a crop DEPLETING and people EMITTING the same '
      'magnitude produce exact mirror offsets to 1e-9 — if this '
      'ever breaks, someone has written a second mass balance',
      _guard.get('ok') and _guard['symmetric']
      and abs(_guard['plusOffset'] + _guard['minusOffset']) <= 1e-9,
      json.dumps(_guard))

_sealed = steady_state_ppm(427.35, 1.0e6, 30.0, 0.0)
check('a SEALED room (ach 0) REFUSES rather than returning a '
      'steady state — with no ventilation the level accumulates '
      'without bound, so the honest answer is a time-to-level',
      _sealed.get('ok') is False
      and 'SEALED' in _sealed['refusal'],
      _sealed.get('refusal', ''))
_novol = steady_state_ppm(427.35, 1.0e6, 0.0, 1.0)
check('volume <= 0 refuses — a source with no air to mix into '
      'has no concentration at all',
      _novol.get('ok') is False
      and 'volume_m3' in _novol['refusal'],
      _novol.get('refusal', ''))

_SPACE_ROWS = [_ns(s) for s in SEED_INDOOR_SPACES]
_knobs = [ventilation_knob(s, 427.35, factor=2.0)
          for s in _SPACE_ROWS]
check('DOUBLING VENTILATION STRICTLY LOWERS indoor CO2 in every '
      'archetype — the knob the page needs so a reader can act '
      'instead of only worry',
      all(k.get('ok') and k['deltaPpm'] < 0.0
          and k['newAch'] == 2.0 * k['baseAch'] for k in _knobs),
      str([round(k.get('deltaPpm', 0.0), 2) for k in _knobs]))

_sp_params = _init_params(IndoorSpaceProfile)
check('every IndoorSpaceProfile seed key matches the class\' '
      '__init__ signature exactly',
      all(set(s) == _sp_params for s in SEED_INDOOR_SPACES),
      str([sorted(set(s) ^ _sp_params)
           for s in SEED_INDOOR_SPACES if set(s) != _sp_params]))
check('every room archetype is flagged is_prior with a non-empty '
      'replaces_with — an archetype is the start of a question, '
      'never an answer about a real room',
      all(s['is_prior'] is True and s['replaces_with'].strip()
          for s in SEED_INDOOR_SPACES))

_offsets = [space_offset(s, 427.35) for s in _SPACE_ROWS]
check('PLAUSIBILITY GUARD: every archetype\'s steady state at '
      'today\'s outdoor sits above outdoor and below 15000 ppm — '
      'a 20000 ppm car cabin shipped once and the implausible '
      'output is what caught the bad ACH prior',
      all(o.get('ok') and 427.35 < o['indoorPpm'] < 15000.0
          for o in _offsets),
      str([(o.get('space'), round(o.get('indoorPpm', -1.0), 1))
           for o in _offsets]))
check('and each offset is the ventilation quotient, positive '
      'because people are a POSITIVE source',
      all(o['offsetPpm'] > 0.0
          and abs(o['indoorPpm'] - (427.35 + o['offsetPpm']))
          < 1e-9 for o in _offsets))


# --------------------------------------------------------------
print('== suite: co2_crossing — the coupled projection ==')

_SYN = [{'year': float(y),
         'value': 300.0 + 1.0 * (y - 1960) + 0.014 * (y - 1960) ** 2,
         'uncertainty': 0.1} for y in range(1960, 2026)]
_HORIZON = 400

_out = outdoor_crossings(_SYN, _TH_ROWS, horizon_years=_HORIZON)
check('outdoor_crossings runs on a synthetic rising series and '
      'the real threshold rows',
      _out.get('ok'), json.dumps(_out)[:200])
_mono = monotonicity_check(_out.get('crossings', []))
check('MONOTONICITY: outdoor crossing years are non-decreasing '
      'in the threshold ppm — a higher line can never arrive '
      'earlier',
      _mono.get('ok') and _mono['nChecked'] >= 2,
      json.dumps(_mono))

_diff_entries = [c for c in _out['crossings']
                 if c.get('threshold') == 'ashrae-differential-700']
check('a DIFFERENTIAL threshold is SKIPPED in outdoor_crossings '
      'with a stated reason — "700 ppm above outdoor" is not a '
      'level the outdoor record can ever reach',
      len(_diff_entries) == 1
      and _diff_entries[0].get('skipped') is True
      and 'differential' in _diff_entries[0].get('reason', ''),
      str(_diff_entries))

_cpl = coupled_crossings(_SYN, _TH_ROWS, _SPACE_ROWS,
                         horizon_years=_HORIZON)
check('coupled_crossings builds the threshold x space table',
      _cpl.get('ok') and _cpl.get('rows'),
      json.dumps(_cpl)[:200])

_out_by_name = {c['threshold']: c for c in _out['crossings']
                if not c.get('skipped')}
_violations = []
for _row in _cpl['rows']:
    if _row.get('refused') or _row.get('isDifferential'):
        continue
    _o = _out_by_name.get(_row['threshold'])
    if _o is None or _o.get('refused'):
        continue
    if _o.get('alreadyCrossed'):
        if not _row.get('alreadyCrossed'):
            _violations.append((_row['space'], _row['threshold'],
                                'outdoor crossed, indoor not'))
        continue
    if _row.get('alreadyCrossed'):
        continue           # indoor earlier — the expected case
    _lo_in, _lo_out = _row.get('crossingYearLow'), _o.get(
        'crossingYearLow')
    if _lo_in is None or _lo_out is None:
        continue
    if _lo_in > _lo_out + 1e-9:
        _violations.append((_row['space'], _row['threshold'],
                            f'{_lo_in} > {_lo_out}'))
check('THE SIGN GUARD: for EVERY (threshold, space) the indoor '
      'crossing is earlier than or equal to the outdoor crossing '
      'of the same absolute line — indoor = outdoor + '
      'emission/ventilation, so if one is ever later the coupling '
      'has a sign error',
      not _violations, str(_violations[:5]))

_already = [r for r in _cpl['rows'] if r.get('alreadyCrossed')]
check('rooms already past a line report alreadyCrossed — for '
      'several archetypes that IS the answer, and it is the '
      'finding',
      len(_already) >= 1, str(len(_already)))
check('and no row anywhere carries a negative or nonsensical '
      'crossing year: a row is EXACTLY ONE of already-crossed, '
      'refused, or bounded by two real years',
      all((r.get('alreadyCrossed')
           and r.get('crossingYearLow') is None
           and r.get('crossingYearHigh') is None)
          or r.get('refused')
          or (r.get('crossingYearLow') is not None
              and r.get('crossingYearHigh') is not None
              and r['crossingYearLow'] >= _cpl['presentPpm'] * 0.0
              and r['crossingYearLow'] > 1900.0)
          for r in _cpl['rows']),
      str([r for r in _cpl['rows']
           if not r.get('alreadyCrossed') and not r.get('refused')
           and r.get('crossingYearLow') is None][:2]))
check('every coupled row states the absolute target it solved '
      'and the offset it used, so the arithmetic is auditable',
      all('absoluteTargetPpm' in r and 'indoorOffsetPpm' in r
          for r in _cpl['rows'] if not r.get('refused')))


# --------------------------------------------------------------
print('== suite: climate_history — the splice and the eras ==')

_SEG_ICE = {'span': 'span-ice', 'measurementKind': 'ice-core',
            'points': [{'year': 1900.0 + 10 * i,
                        'value': 296.0 + 1.5 * i}
                       for i in range(7)]}
_SEG_INS = {'span': 'span-mlo',
            'measurementKind': 'direct-instrument',
            'points': [{'year': 1950.0 + 10 * i,
                        'value': 314.0 + 4.0 * i}
                       for i in range(6)]}
_spl = splice_series([_SEG_ICE, _SEG_INS])
check('splice_series keeps BOTH spans\' points — nothing is '
      'dropped where the archives overlap',
      _spl.get('ok')
      and len(_spl['points']) == (len(_SEG_ICE['points'])
                                  + len(_SEG_INS['points'])),
      str(len(_spl.get('points', []))))
check('every spliced point carries its span and measurementKind, '
      'so the renderer can draw the SEAM instead of one smooth '
      'line',
      all(p.get('span') and p.get('measurementKind')
          for p in _spl['points'])
      and {p['span'] for p in _spl['points']}
      == {'span-ice', 'span-mlo'})
check('the overlap is reported as a CROSS-CHECK with a mean '
      'difference — agreement there is what makes the curve a '
      'measurement rather than an assumption',
      len(_spl['overlaps']) == 1
      and _spl['overlaps'][0]['nMatched'] >= 2
      and _spl['overlaps'][0]['meanDifference'] is not None,
      json.dumps(_spl.get('overlaps')))
check('and the direct instrument wins the preference order over '
      'the ice core where they overlap',
      all(p['preferred'] for p in _spl['points']
          if p['measurementKind'] == 'direct-instrument'))

_era_params = _init_params(HumanEraDefinition)
check('every HumanEraDefinition seed key matches the class\' '
      '__init__ signature exactly',
      all(set(e) == _era_params for e in SEED_HUMAN_ERAS),
      str([sorted(set(e) ^ _era_params) for e in SEED_HUMAN_ERAS
           if set(e) != _era_params]))
_prehistoric = [e for e in SEED_HUMAN_ERAS if e['from_year'] < 0.0]
check('EVERY prehistoric era carries life_expectancy_at_birth '
      '0.0 with a basis saying it is NOT SET — no invented '
      'paleodemography, because a skeletal-age estimate is not a '
      'period life table',
      len(_prehistoric) >= 6
      and all(e['life_expectancy_at_birth'] == 0.0
              and 'NOT SET' in e['life_expectancy_basis']
              for e in _prehistoric),
      str([(e['name'], e['life_expectancy_at_birth'])
           for e in _prehistoric
           if e['life_expectancy_at_birth'] != 0.0]))
check('population_estimate is 0.0 everywhere for the same '
      'reason — a seeded reconstruction would look measured',
      all(e['population_estimate'] == 0.0
          for e in SEED_HUMAN_ERAS))
check('COGNITION_QUESTION names the FAILED replications '
      '(Rodeheffer, Scully, Du) — the question must not be '
      'presented as settled in either direction',
      all(n in COGNITION_QUESTION
          for n in ('Rodeheffer', 'Scully', 'Du'))
      and 'cannot be answered' in COGNITION_QUESTION)


# --------------------------------------------------------------
print('== suite: climate_export — provenance or it is not an '
      'export ==')


def _obs(idx, series, span, year, value, unc=0.1):
    return {'name': f'{series}--{idx:04d}', 'series_ref': series,
            'span_ref': span, 'year': year, 'value': value,
            'uncertainty': unc}


_EXP_SERIES = 'fx-co2-spliced'
_PRIOR_SERIES = 'fx-co2-unfetched'
_exp_obs = []
for _i in range(7):
    _exp_obs.append(_obs(_i, _EXP_SERIES, 'fx-span-ice',
                         1900.0 + 10 * _i, 296.0 + 1.5 * _i))
for _i in range(6):
    _exp_obs.append(_obs(100 + _i, _EXP_SERIES, 'fx-span-mlo',
                         1950.0 + 10 * _i, 314.0 + 4.0 * _i))

_exp_mgr = types.SimpleNamespace()
_exp_mgr.objectTables = {
    'AtmosphericSeriesDefinition': _table([
        {'name': _EXP_SERIES, 'display_name': 'Fixture CO2 splice',
         'measure': 'co2-mole-fraction', 'unit': 'ppm',
         'cadence': 'annual', 'location': 'fixture',
         'source_ref': 'noaa-gml', 'endpoint_ref': 'fx-endpoint',
         'status': 'ingested', 'description': 'A two-span fixture.',
         'first_year': 1900.0, 'last_year': 2000.0},
        {'name': _PRIOR_SERIES, 'display_name': 'Never fetched',
         'measure': 'co2-mole-fraction', 'unit': 'ppm',
         'cadence': 'annual', 'location': 'fixture',
         'source_ref': 'noaa-gml', 'endpoint_ref': 'fx-endpoint',
         'status': 'prior', 'description': 'Seeded, not ingested.',
         'first_year': 0.0, 'last_year': 0.0},
    ]),
    'SourceCoverageSpan': _table([
        {'name': 'fx-span-ice', 'series_ref': _EXP_SERIES,
         'display_name': 'Antarctic composite (fixture)',
         'measurement_kind': 'ice-core', 'from_year': 1900.0,
         'to_year': 1960.0, 'archive_name': 'EPICA Dome C',
         'instrument': 'gas chromatography',
         'resolution_years': 10.0, 'typical_uncertainty': 1.2,
         'citation_text': 'Bereiter et al. 2015, NCEI study 17975',
         'doi_or_url': 'https://example.invalid/ice',
         'color': '#3f6f8f'},
        {'name': 'fx-span-mlo', 'series_ref': _EXP_SERIES,
         'display_name': 'Mauna Loa (fixture)',
         'measurement_kind': 'direct-instrument',
         'from_year': 1950.0, 'to_year': 2000.0,
         'archive_name': 'Mauna Loa Observatory',
         'instrument': 'NDIR', 'resolution_years': 10.0,
         'typical_uncertainty': 0.12,
         'citation_text': 'Lan, Tans, Thoning; NOAA GML',
         'doi_or_url': 'https://example.invalid/mlo',
         'color': '#c04030'},
    ]),
    'AtmosphericObservation': {o['name']: _ns(o) for o in _exp_obs},
}
_exp_mgr.objectTypingDict = {k: object()
                             for k in _exp_mgr.objectTables}

_csv = export_csv(_exp_mgr, _EXP_SERIES)
_header = _csv.get('content', '').splitlines()[0] if _csv.get(
    'ok') else ''
check('export_csv carries PROVENANCE COLUMNS — span, '
      'measurement_kind and citation. A CSV of bare year,value is '
      'number laundry: it strips exactly what made the number '
      'trustworthy',
      _csv.get('ok')
      and all(c in _header for c in ('span', 'measurement_kind',
                                     'citation')),
      _header)
check('and every point is present with its span attached',
      _csv.get('rowCount') == len(_exp_obs)
      and 'fx-span-ice' in _csv['content']
      and 'fx-span-mlo' in _csv['content'],
      str(_csv.get('rowCount')))

_md = export_markdown(_exp_mgr, _EXP_SERIES)
check('export_markdown emits a "## Citations" section — an '
      'export carries its provenance or it is not an export',
      _md.get('ok') and '## Citations' in _md['content']
      and 'Bereiter' in _md['content']
      and 'NOAA GML' in _md['content'])
check('a TWO-SPAN series is declared a SPLICE in the prose — a '
      'reader who cannot see the seam cannot judge the curve',
      _md.get('ok') and 'splice' in _md['content'].lower()
      and _md.get('isSplice') is True)

_bad_fmt = export_series(_exp_mgr, _EXP_SERIES, fmt='pdf')
check('an unknown export format REFUSES by name and lists the '
      'available ones — a caller who asked for PDF and silently '
      'got markdown has been lied to',
      _bad_fmt.get('ok') is False
      and "'pdf'" in _bad_fmt['refusal']
      and all(f in _bad_fmt['refusal'] for f in EXPORT_FORMATS),
      _bad_fmt.get('refusal', ''))

_svg = export_svg(_exp_mgr, _EXP_SERIES)
check('export_svg refuses AND suggests the fix (serialize the '
      'on-screen SVG) — two renderers would be two truths',
      _svg.get('ok') is False
      and 'XMLSerializer' in _svg['refusal']
      and _svg.get('suggestion', {}).get('why')
      == 'one renderer, one truth',
      json.dumps(_svg)[:200])

_prior_results = {f: export_series(_exp_mgr, _PRIOR_SERIES, fmt=f)
                  for f in EXPORT_FORMATS}
check('an UN-INGESTED series refuses on every format — a '
      'placeholder must never be exported as if it were data',
      all(r.get('ok') is False and 'ingested' in r.get('refusal', '')
          for r in _prior_results.values()),
      json.dumps({k: v.get('refusal', '')[:60]
                  for k, v in _prior_results.items()}))


# --------------------------------------------------------------
print('== suite: climate_series + climate_sources — the rows ==')

_ser_params = _init_params(AtmosphericSeriesDefinition)
check('every AtmosphericSeriesDefinition seed key matches the '
      'class\' __init__ signature exactly',
      all(set(s) == _ser_params for s in SEED_CLIMATE_SERIES),
      str([sorted(set(s) ^ _ser_params) for s in SEED_CLIMATE_SERIES
           if set(s) != _ser_params]))
check('every series is seeded EMPTY: status "prior" with '
      'first_year/last_year 0.0 — bounds DERIVE from the rows '
      'that land, and a measurement a seed pass can conjure is '
      'not a measurement',
      all(s['status'] == 'prior' and s['first_year'] == 0.0
          and s['last_year'] == 0.0 and s['is_prior'] is True
          for s in SEED_CLIMATE_SERIES),
      str([(s['name'], s['status'], s['first_year'])
           for s in SEED_CLIMATE_SERIES
           if s['status'] != 'prior' or s['first_year'] != 0.0]))

_ep_names = {e['name'] for e in SEED_CLIMATE_ENDPOINTS}
check('every series\' endpoint_ref names a REAL endpoint row — a '
      'citation pointing at nothing is a lie with a footnote',
      all(s['endpoint_ref'] in _ep_names
          for s in SEED_CLIMATE_SERIES),
      str([s['endpoint_ref'] for s in SEED_CLIMATE_SERIES
           if s['endpoint_ref'] not in _ep_names]))
check('every series in SERIES_PARSERS names a parser that '
      'EXISTS, and every seeded series has an entry',
      all(ref in PARSERS for ref, _kw in SERIES_PARSERS.values())
      and all(s['name'] in SERIES_PARSERS
              for s in SEED_CLIMATE_SERIES),
      str([ref for ref, _ in SERIES_PARSERS.values()
           if ref not in PARSERS]))

check('every endpoint row carries a contentSignature, a '
      'rejectSignature and a verifiedOn — content validation is '
      'not optional when two federal agencies serve error pages '
      'with HTTP 200',
      all(e['contentSignature'] and e['rejectSignature']
          and e['verifiedOn'] for e in SEED_CLIMATE_ENDPOINTS),
      str([e['name'] for e in SEED_CLIMATE_ENDPOINTS
           if not (e['contentSignature'] and e['rejectSignature']
                   and e['verifiedOn'])]))
_law = _seed_by_name(SEED_CLIMATE_ENDPOINTS, 'ncei-law-dome-co2')
check('the LAW DOME endpoint\'s signature is NOT the generic "#" '
      '— that file is prose followed by stacked tables, so the '
      'generic signature would have accepted it and the generic '
      'parser would have read the wrong columns',
      _law['contentSignature'] != TEXT_SIG
      and _law['contentSignature'] == 'Law Dome Ice Core',
      _law['contentSignature'])
check('the NHANES rows declare responseFormat xport with the '
      'XPORT library signature and an HTML rejectSignature — the '
      'retired-path trap, encoded as data',
      all(e['responseFormat'] == 'xport'
          and e['contentSignature'] == XPORT_SIG
          and e['rejectSignature'] == HTML_DECOY
          for e in SEED_CLIMATE_ENDPOINTS
          if e['name'].startswith('nhanes-')))


# --------------------------------------------------------------
print('== suite: xpt_reader — SAS XPORT, offline ==')

_XPT_ROWS = [[1.0, 24.0], [2.0, 26.5], [3.0, 22.0], [4.0, 25.0]]
_xpt = make_min_xport(['SEQN', 'LBXSC3SI'], _XPT_ROWS)
_read = read_xpt_bytes(
    _xpt, column_map={'LBXSC3SI': {'meaning': 'bicarbonate',
                                   'unit': 'mmol/L'}})
check('make_min_xport ROUND-TRIPS through read_xpt_bytes — a '
      'fixture you cannot regenerate is a fixture nobody can '
      'audit',
      _read.get('ok') and _read['rowCount'] == len(_XPT_ROWS)
      and _read['columns'] == ['SEQN', 'LBXSC3SI'],
      json.dumps({k: v for k, v in _read.items()
                  if k != 'frame'})[:200])
check('and the VALUES survive the IBM-360 hex float encoding',
      _read.get('ok')
      and [float(v) for v in _read['frame']['LBXSC3SI']]
      == [24.0, 26.5, 22.0, 25.0],
      str(_read.get('frame')))
check('THE READER NEVER GUESSES WHAT A COLUMN MEANS: an unmapped '
      'column is REPORTED, never dropped — silence about it is '
      'how a unit error survives to a chart',
      _read.get('ok') and _read['unmappedColumns'] == ['SEQN']
      and 'LBXSC3SI' in _read['mappedColumns'],
      str(_read.get('unmappedColumns')))

_html_xpt = read_xpt_bytes(HTML_DECOY_BYTES[:4000])
check('an HTML body refuses and the refusal SAYS it is an HTML '
      'page, not XPORT, and quotes what arrived',
      _html_xpt.get('ok') is False
      and 'HTML page, not a SAS XPORT file'
      in _html_xpt['refusal']
      and 'DOCTYPE' in _html_xpt['refusal'],
      _html_xpt.get('refusal', '')[:160])
_trunc = read_xpt_bytes(_xpt[:40])
check('a body under one 80-byte XPORT record refuses NAMING the '
      'byte count — it cannot even carry a header',
      _trunc.get('ok') is False and '40 bytes' in _trunc['refusal'],
      _trunc.get('refusal', '')[:160])
check('an empty body refuses too, and says an empty 200 is a '
      'proxy or a truncated download, not a data set',
      read_xpt_bytes(b'').get('ok') is False
      and 'empty body' in read_xpt_bytes(b'')['refusal'])


failed = _results.count(False)
print(f'\n{len(_results) - failed}/{len(_results)} checks passed')
raise SystemExit(1 if failed else 0)
