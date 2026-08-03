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

from climate.biomarker_link import (
    RENAL_COMPENSATION_MMOL_PER_10MMHG, attribution_test,
    biomarker_question, correlate, cycle_trend,
    explainable_bicarbonate_shift, monotonicity_warning,
)
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
from climate.sim_binding import (
    SEED_ATMOSPHERE_BINDINGS, AtmosphereSeriesBinding, apply_all,
    apply_binding, binding_report,
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


# --------------------------------------------------------------
print('== suite: co2-B — the bicarbonate question, answered '
      'with arithmetic ==')

#: NHANES 1999-2023, mean serum bicarbonate (LBXSC3SI, mmol/L)
#: per 2-year cycle. These are the parsed values the module's
#: docstring quotes; the test and the prose must agree or one of
#: them is stale.
BIC_BY_CYCLE = {
    '1999-2000': 23.672, '2001-2002': 23.475, '2003-2004': 24.643,
    '2005-2006': 24.556, '2007-2008': 24.859, '2009-2010': 25.460,
    '2011-2012': 25.005, '2013-2014': 25.168, '2015-2016': 24.410,
    '2017-2018': 25.541, '2021-2023': 24.449,
}
#: Percent of the same sampling frame scoring PHQ-9 >= 10. Only 8
#: cycles: the screener starts in 2005-2006.
DEP_BY_CYCLE = {
    '2005-2006': 6.19, '2007-2008': 9.66, '2009-2010': 9.43,
    '2011-2012': 8.93, '2013-2014': 9.51, '2015-2016': 8.08,
    '2017-2018': 9.06, '2021-2023': 13.25,
}
#: Cycle midpoints. 2021-2023 is a THREE-year cycle, so its
#: midpoint is 2022.5 — treating it as 2022 would quietly bend
#: every slope through the newest and largest point.
CYCLE_MIDPOINTS = {
    '1999-2000': 2000.0, '2001-2002': 2002.0, '2003-2004': 2004.0,
    '2005-2006': 2006.0, '2007-2008': 2008.0, '2009-2010': 2010.0,
    '2011-2012': 2012.0, '2013-2014': 2014.0, '2015-2016': 2016.0,
    '2017-2018': 2018.0, '2021-2023': 2022.5,
}
#: Ambient CO2 over the same window, and the pooled within-cycle
#: spread of the biomarker itself.
CO2_PPM_1999, CO2_PPM_2023 = 368.14, 421.08
BIC_WITHIN_CYCLE_SD = 2.26

_bic_tr = cycle_trend(BIC_BY_CYCLE, CYCLE_MIDPOINTS)
check('bicarbonate DID rise across the 11 cycles: +0.0507 mmol/L '
      'per year at r=+0.54 — the trend the question starts from '
      'is real and is not being argued away',
      _bic_tr.get('ok') and _bic_tr['nCycles'] == 11
      and abs(_bic_tr['slopePerYear'] - 0.0507) < 5e-5
      and abs(_bic_tr['r'] - 0.542) < 5e-3
      and abs(_bic_tr['totalChange'] - 1.140) < 5e-3,
      json.dumps({k: v for k, v in _bic_tr.items()
                  if k != 'values'})[:220])

_dep_tr = cycle_trend(DEP_BY_CYCLE, CYCLE_MIDPOINTS)
check('depression prevalence DID rise too: +0.254 PHQ-9 points '
      'per year at r=+0.70 across its 8 cycles',
      _dep_tr.get('ok') and _dep_tr['nCycles'] == 8
      and abs(_dep_tr['slopePerYear'] - 0.254) < 5e-4
      and abs(_dep_tr['r'] - 0.704) < 5e-3,
      json.dumps({k: v for k, v in _dep_tr.items()
                  if k != 'values'})[:220])

_corr = correlate(BIC_BY_CYCLE, DEP_BY_CYCLE,
                  'serum bicarbonate', 'PHQ-9 >=10 prevalence')
check('THE CENTRAL CHECK: across the 8 shared cycles the two '
      'rising series correlate at |r| < 0.1 — effectively ZERO, '
      'and the wrong sign. Both rising against TIME is not the '
      'same as rising WITH EACH OTHER, and this near-zero number '
      'is stronger evidence against a shared cause than either '
      'trend is for one',
      _corr.get('ok') and _corr['n'] == 8
      and abs(_corr['r']) < 0.1
      and _corr['strength'] == 'effectively none',
      json.dumps({k: v for k, v in _corr.items()
                  if k != 'note'})[:220])

_thin_corr = correlate({'a': 1.0, 'b': 2.0}, {'a': 3.0, 'b': 4.0},
                       'x', 'y')
check('fewer than 3 shared cycles REFUSES and NAMES the count — '
      'a correlation over two points is a line, not a finding',
      _thin_corr.get('ok') is False
      and '2 cycles' in _thin_corr['refusal']
      and 'at least 3' in _thin_corr['refusal'],
      _thin_corr.get('refusal', ''))

_exp = explainable_bicarbonate_shift(CO2_PPM_1999, CO2_PPM_2023)
check('52.9 ppm of ambient CO2 is 0.0402 mmHg of partial '
      'pressure, which the renal constant turns into a 0.00161 '
      'mmol/L bicarbonate shift — the whole question is a unit '
      'conversion away from its answer',
      _exp.get('ok')
      and abs(_exp['deltaPco2Mmhg'] - 0.0402) < 5e-5
      and abs(_exp['explainableShiftMmolL'] - 0.00161) < 5e-6,
      json.dumps(_exp)[:220])

_attr = attribution_test(1.1404, CO2_PPM_1999, CO2_PPM_2023)
check('THE UNIT CHECK — the one that separates "the rise is '
      'real" from "ambient CO2 caused it": the observed 1.14 '
      'mmol/L is ~709x larger than ambient CO2 could produce, so '
      'mechanismAdmissible is False and the verdict SAYS the '
      'mechanism is too small rather than hedging',
      _attr.get('ok')
      and _attr['mechanismAdmissible'] is False
      and 600.0 < _attr['ratio'] < 800.0
      and 'too small by orders of magnitude' in _attr['verdict'],
      json.dumps(_attr)[:260])

_small = attribution_test(0.002, CO2_PPM_1999, CO2_PPM_2023)
check('and the test is NOT rigged to always fail: a small '
      'observed shift at the same ppm range comes back '
      'ADMISSIBLE — a check that cannot pass proves nothing when '
      'it fails',
      _small.get('ok') and _small['mechanismAdmissible'] is True
      and 'ARITHMETICALLY ADMISSIBLE' in _small['verdict'],
      json.dumps(_small)[:220])

_flat = attribution_test(1.1404, 421.08, 421.08)
check('ppm_from == ppm_to REFUSES — with no ambient change there '
      'is no ratio to report, and dividing by it would print an '
      'infinity as a finding',
      _flat.get('ok') is False
      and 'no ratio is defined' in _flat['refusal'],
      _flat.get('refusal', ''))

_warn = monotonicity_warning(_bic_tr, BIC_WITHIN_CYCLE_SD)
check('THE HONEST CAVEAT: the real bicarbonate trend is NOT '
      'trustworthy on its own — it carries at least 2 warnings, '
      'one of them naming assay/calibration change between '
      'cycles, because a sawtooth across survey cycles is exactly '
      'what a method change looks like',
      _warn.get('ok') and _warn['trustworthy'] is False
      and len(_warn['warnings']) >= 2
      and any('assay' in w and 'calibration' in w
              for w in _warn['warnings']),
      json.dumps(_warn['warnings'])[:240])
check('and the sawtooth is really there in the data, so the '
      'warning is earned rather than boilerplate',
      _bic_tr.get('monotonic') is False)

_bq = biomarker_question(BIC_BY_CYCLE, DEP_BY_CYCLE,
                         CYCLE_MIDPOINTS, CO2_PPM_1999,
                         CO2_PPM_2023, BIC_WITHIN_CYCLE_SD)
_HEAD_KEYS = {'label', 'value', 'note', 'verdict'}
check('biomarker_question answers as ONE payload: a headline '
      'where every row has exactly {label,value,note,verdict}, so '
      'no number can reach a page without the note that qualifies '
      'it',
      _bq.get('ok') is True and len(_bq['headline']) >= 4
      and all(set(h) == _HEAD_KEYS for h in _bq['headline']),
      str([sorted(set(h) ^ _HEAD_KEYS) for h in _bq['headline']
           if set(h) != _HEAD_KEYS]))
check('the answer is stated in words and says the PREDICTION IS '
      'NOT SUPPORTED — the payload does not leave the reader to '
      'infer the conclusion from four statistics',
      _bq['answer'].strip()
      and 'not supported' in _bq['answer'],
      _bq.get('answer', '')[:160])
check('and both confounder lists are non-empty: the alternatives '
      'that could produce either trend are named ON the answer, '
      'not left for a reader to think of',
      len(_bq['bicarbonateConfounders']) >= 3
      and len(_bq['depressionConfounders']) >= 3,
      f"{len(_bq['bicarbonateConfounders'])} / "
      f"{len(_bq['depressionConfounders'])}")

check('the compensation constant is the CHRONIC figure (0.4 '
      'mmol/L per 10 mmHg), the most generous assumption '
      'available to the hypothesis under test — the acute figure '
      'is smaller still, so a hypothesis that fails here fails '
      'with any constant',
      RENAL_COMPENSATION_MMOL_PER_10MMHG == 0.4
      and 'CHRONIC' in _exp['note'].upper(),
      str(RENAL_COMPENSATION_MMOL_PER_10MMHG))


# --------------------------------------------------------------
print('== suite: co2-9 — the simulation binding ==')

_BIND_SERIES = 'co2-mauna-loa-annual'
#: A short synthetic instrumental record. Deliberately starts in
#: 2020 so nothing in it is anywhere near pre-industrial.
_BIND_POINTS = [(2020.0, 414.24), (2021.0, 416.45),
                (2022.0, 418.56), (2023.0, 421.08),
                (2024.0, 424.61), (2025.0, 427.35)]

_bind_mgr = types.SimpleNamespace()
_bind_mgr.objectTables = {
    'AtmosphereDefinition': {
        'open-greenhouse': types.SimpleNamespace(
            name='open-greenhouse', outside_co2_ppm=420.0),
        'ventilated-grow-tent': types.SimpleNamespace(
            name='ventilated-grow-tent', outside_co2_ppm=420.0),
    },
    'AtmosphereSeriesBinding': _table(SEED_ATMOSPHERE_BINDINGS),
    'AtmosphericSeriesDefinition': _table([
        {'name': _BIND_SERIES, 'status': 'prior',
         'endpoint_ref': 'noaa-gml-co2-annual-mean',
         'first_year': 0.0, 'last_year': 0.0},
    ]),
    'AtmosphericObservation': {
        f'{_BIND_SERIES}--{_i:04d}': _ns(
            {'name': f'{_BIND_SERIES}--{_i:04d}',
             'series_ref': _BIND_SERIES, 'span_ref': 'fx-span-mlo',
             'year': _y, 'value': _v, 'uncertainty': 0.12})
        for _i, (_y, _v) in enumerate(_BIND_POINTS)
    },
}
_bind_mgr.objectTypingDict = {k: object()
                              for k in _bind_mgr.objectTables}
_GH = _bind_mgr.objectTables['AtmosphereDefinition'][
    'open-greenhouse']


def _bind_row(**over):
    """A standalone binding row for the refusal cases, so the
    seeded table's own results stay uncontaminated."""
    base = dict(SEED_ATMOSPHERE_BINDINGS[0])
    base.update(over)
    return _ns(base)


_prior_apply = apply_all(_bind_mgr)
check('THE MOST IMPORTANT CHECK IN THIS SUITE: while the series '
      'is still "prior", every binding refuses, NOTHING is '
      'applied, and the greenhouse row STILL HOLDS ITS SEEDED '
      '420.0 — a refused binding never half-applies, and the '
      'typed constant is the working fallback rather than a '
      'failure',
      _prior_apply.get('ok') and _prior_apply['applied'] == 0
      and _prior_apply['refused'] == len(SEED_ATMOSPHERE_BINDINGS)
      and _GH.outside_co2_ppm == 420.0,
      json.dumps({k: v for k, v in _prior_apply.items()
                  if k != 'results'}) + f' ppm={_GH.outside_co2_ppm}')
check('and the refusal NAMES the series and points at the ingest '
      'that would open it — "not ingested" with no next step is '
      'a dead end',
      all(_BIND_SERIES in r.get('refusal', '')
          and 'ingested' in r.get('refusal', '')
          and 'fetch it from' in r.get('refusal', '')
          for r in _prior_apply['results']),
      str([r.get('refusal', '')[:90]
           for r in _prior_apply['results']])[:240])

_bind_mgr.objectTables['AtmosphericSeriesDefinition'][
    _BIND_SERIES].status = 'ingested'

_dry = apply_all(_bind_mgr, dry_run=True)
check('a DRY RUN reports what it WOULD write and leaves the '
      'target alone — the preview and the write are the same '
      'code path, which is the only way a preview can be trusted',
      _dry.get('ok') and _dry['applied'] == 2
      and all(abs(r['wouldWrite'] - 427.35) < 1e-9
              and abs(r['currentValue'] - 420.0) < 1e-9
              for r in _dry['results'])
      and _GH.outside_co2_ppm == 420.0,
      json.dumps(_dry['results'])[:220])

_applied = apply_all(_bind_mgr)
_gh_result = [r for r in _applied['results']
              if r.get('binding')
              == 'bind-open-greenhouse-outside-co2'][0]
check('with the series INGESTED the bindings apply: the '
      'greenhouse ambient CO2 becomes the measured 427.35 and '
      'the result reports previousValue 420.0, appliedValue '
      '427.35 and a delta of +7.35 — the simulation input is now '
      'a measurement with a source year',
      _applied.get('ok') and _applied['applied'] == 2
      and _applied['refused'] == 0
      and abs(_GH.outside_co2_ppm - 427.35) < 1e-9
      and abs(_gh_result['previousValue'] - 420.0) < 1e-9
      and abs(_gh_result['appliedValue'] - 427.35) < 1e-9
      and abs(_gh_result['delta'] - 7.35) < 1e-9
      and _gh_result['sourceYear'] == 2025.0,
      json.dumps(_gh_result)[:260])

_gh_bind = _bind_mgr.objectTables['AtmosphereSeriesBinding'][
    'bind-open-greenhouse-outside-co2']
check('the binding row RECORDS the displaced constant in '
      'replaced_value (420.0), so the binding is reversible and '
      'the distance between the guess and the measurement is on '
      'the row rather than lost',
      abs(_gh_bind.replaced_value - 420.0) < 1e-9,
      str(_gh_bind.replaced_value))

_reapply = apply_all(_bind_mgr)
check('RE-APPLYING DOES NOT OVERWRITE replaced_value with 427.35 '
      '— the provenance of the ORIGINAL constant survives every '
      'later run, which is what makes it provenance instead of a '
      '"previous value" cache',
      _reapply['applied'] == 2
      and abs(_gh_bind.replaced_value - 420.0) < 1e-9
      and abs(_gh_bind.last_applied_value - 427.35) < 1e-9,
      f'replaced={_gh_bind.replaced_value} '
      f'applied={_gh_bind.last_applied_value}')

_no_row = apply_binding(_bind_mgr,
                        _bind_row(name='fx-bind-missing-row',
                                  target_row='no-such-room'))
check('a binding whose target_row does not exist REFUSES naming '
      'the row and ASKING WHETHER THE OWNING MODULE IS ENABLED — '
      'the usual cause is a module that is not booted, not a typo',
      _no_row.get('ok') is False
      and 'no-such-room' in _no_row['refusal']
      and 'owning module' in _no_row['refusal'],
      _no_row.get('refusal', ''))

_no_field = apply_binding(
    _bind_mgr, _bind_row(name='fx-bind-missing-field',
                         target_field='outside_co2_ppmm'))
check('a binding naming a field the row does not have REFUSES by '
      'FIELD NAME — setattr would otherwise invent an attribute '
      'nothing reads and report success',
      _no_field.get('ok') is False
      and 'outside_co2_ppmm' in _no_field['refusal']
      and not hasattr(_GH, 'outside_co2_ppmm'),
      _no_field.get('refusal', ''))

_disabled = apply_binding(_bind_mgr,
                          _bind_row(name='fx-bind-disabled',
                                    enabled=False,
                                    target_row='open-greenhouse'))
check('a DISABLED binding is refused as disabled and writes '
      'nothing — enabled is a knob, not a comment',
      _disabled.get('ok') is False
      and 'disabled' in _disabled['refusal']
      and abs(_GH.outside_co2_ppm - 427.35) < 1e-9,
      _disabled.get('refusal', ''))

_pre = apply_binding(_bind_mgr,
                     _bind_row(name='fx-bind-preindustrial',
                               mode='preindustrial'))
check('mode "preindustrial" against an INSTRUMENTAL-ONLY series '
      'REFUSES, says the instrumental record does not reach '
      'pre-industrial, and points at the ice-core series — the '
      'binding cannot silently hand a 1750 counterfactual the '
      'nearest modern year it happens to own',
      _pre.get('ok') is False
      and 'does not reach pre-industrial' in _pre['refusal']
      and 'ice-core' in _pre['refusal'],
      _pre.get('refusal', ''))

_far_year = apply_binding(_bind_mgr,
                          _bind_row(name='fx-bind-far-year',
                                    mode='year', year=1990.0))
check('mode "year" more than 5 years from any observation '
      'REFUSES and NAMES the nearest year it does have (2020) — '
      'silently snapping to it would reproduce a 1990 run with '
      '2020 air',
      _far_year.get('ok') is False
      and '1990' in _far_year['refusal']
      and '2020' in _far_year['refusal'],
      _far_year.get('refusal', ''))

_at_year = apply_binding(_bind_mgr,
                         _bind_row(name='fx-bind-2023',
                                   mode='year', year=2023.0),
                         dry_run=True)
check('mode "year" on a year that IS in the record returns THAT '
      'year\'s value (421.08 for 2023), which is what makes a '
      'historical run reproducible',
      _at_year.get('ok')
      and abs(_at_year['wouldWrite'] - 421.08) < 1e-9
      and _at_year['sourceYear'] == 2023.0,
      json.dumps(_at_year))

_bind_params = _init_params(AtmosphereSeriesBinding)
check('every AtmosphereSeriesBinding seed key matches the class\' '
      '__init__ signature exactly — an unknown key is silently '
      'dropped on construction (the ten-strikes seed gotcha)',
      all(set(s) == _bind_params
          for s in SEED_ATMOSPHERE_BINDINGS),
      str([sorted(set(s) ^ _bind_params)
           for s in SEED_ATMOSPHERE_BINDINGS
           if set(s) != _bind_params]))

_report = binding_report(_bind_mgr)
check('binding_report puts replacedValue BESIDE appliedValue on '
      'every row, so the gap between the number somebody typed '
      'and the number the world had stays visible on the page '
      'instead of being overwritten by it',
      _report.get('ok')
      and _report['count'] == len(SEED_ATMOSPHERE_BINDINGS)
      and all('replacedValue' in b and 'appliedValue' in b
              and 'sourceYear' in b and 'series' in b
              for b in _report['bindings'])
      and abs([b for b in _report['bindings']
               if b['name']
               == 'bind-open-greenhouse-outside-co2'][0]
              ['replacedValue'] - 420.0) < 1e-9,
      json.dumps(_report['bindings'])[:240])


print('== suite: co2-C — citing NON-government sources ==')

from climate.climate_sources import SEED_CLIMATE_GOV_SOURCES
from climate.climate_citations import (
    SEED_CLIMATE_ACADEMIC_SOURCES, SEED_CLIMATE_JOURNALISTIC_SOURCES,
    SEED_CLIMATE_NONPROFIT_SOURCES, resolve_citation,
    threshold_citations,
)
from dmvdata.gov_sources import SOURCE_TABLES
from dmvdata.legal_sources import AcademicSource, JournalisticSource

_cm = types.SimpleNamespace(objectTables={
    'GovSource': _table(SEED_CLIMATE_GOV_SOURCES),
    'AcademicSource': _table(SEED_CLIMATE_ACADEMIC_SOURCES),
    'NonProfitSource': _table(SEED_CLIMATE_NONPROFIT_SOURCES),
    'JournalisticSource': _table([{
        'name': 'fixture-md-explainer', 'short_name': 'MD piece',
        'full_name': 'A physician explains indoor CO2',
        'official_website': '', 'data_portal_url': '',
        'requires_api_key': False, 'api_key_env': '',
        'api_endpoint_names_json': '[]',
        'outlet': 'A health magazine', 'author_name': 'A Physician',
        'author_credentials': 'MD', 'author_affiliation': '',
        'published_date': '2024', 'article_url': '',
        'editorially_reviewed': True, 'is_opinion': False,
        'primary_sources_json':
            '["satish-2012-co2-decision-making"]',
        'unsourced_claims_noted': False,
        'commercial_interest': '', 'publisher_sells': '',
        'description': '', 'notes': ''}]
        + SEED_CLIMATE_JOURNALISTIC_SOURCES),
    'CompanySource': {}, 'PoliticalGroupSource': {},
    'IndividualSource': {},
    'CO2HealthThreshold': _table(SEED_CO2_THRESHOLDS),
})
_cm.objectTypingDict = {k: object() for k in _cm.objectTables}

check('the source registry now spans SEVEN kinds, not just '
      'government — "source" was never a synonym for "government" '
      'and the schema now says so',
      SOURCE_TABLES.get('AcademicSource') == 'academic'
      and SOURCE_TABLES.get('JournalisticSource') == 'journalistic'
      and len(SOURCE_TABLES) == 7)

_res = [resolve_citation(_cm, t['source_ref'])
        for t in SEED_CO2_THRESHOLDS]
check('EVERY threshold now resolves its source to a real row — '
      'the cognitive rows used to carry an empty source_ref '
      'because a journal is not a government agency, so their '
      'citation survived only as prose a page cannot follow',
      all(r.get('ok') for r in _res),
      str([t['name'] for t, r in zip(SEED_CO2_THRESHOLDS, _res)
           if not r.get('ok')]))

_kinds = {r.get('kind') for r in _res}
check('and they resolve across FOUR different registries — a '
      'peer-reviewed study, a nonprofit standards body, a federal '
      'occupational limit and a credentialed press piece — which '
      'is the shape of the evidence, made visible',
      _kinds == {'academic', 'nonprofit', 'government',
                 'journalistic'}, str(_kinds))

_sat = resolve_citation(_cm, 'satish-2012-co2-decision-making')
check('an academic citation carries its DESIGN, its n and its '
      'replication status — a study that failed to replicate is '
      'still a real citation and is not the same evidence it was '
      'on publication day',
      _sat['ok'] and _sat['sampleSize'] == 22
      and _sat['replicationStatus'] == 'failed-to-replicate'
      and len(_sat['replicationRefs']) == 3)

check('the failed replications are NAMED as rows, not prose, so '
      'the contest can be followed',
      all(resolve_citation(_cm, ref).get('ok')
          for ref in _sat['replicationRefs']))

_jr = resolve_citation(_cm, 'fixture-md-explainer')
check('a credentialed journalist resolves, and the CREDENTIAL and '
      'the VENUE stay separate facts — expertise and peer review '
      'are different guarantees',
      _jr['ok'] and _jr['kind'] == 'journalistic'
      and _jr['authorCredentials'] == 'MD'
      and 'not peer-reviewed' in _jr['credentialCaveat'])

check('and it names the PRIMARY studies it reports on, so a claim '
      'can be followed to the evidence rather than stopping at '
      'the person who repeated it',
      _jr['primarySources'] == ['satish-2012-co2-decision-making'])

check('ASHRAE is filed as a NONPROFIT, not a government agency — '
      'it was originally mis-seeded as a GovSource carrying a note '
      'apologising that it was not one, which is a comment doing a '
      'schema\'s job',
      resolve_citation(_cm, 'ashrae-society').get('kind')
      == 'nonprofit'
      and 'ashrae' not in {g['name']
                           for g in SEED_CLIMATE_GOV_SOURCES})

check('the Global Carbon Project likewise — an international '
      'research consortium, not a US federal body',
      resolve_citation(_cm, 'global-carbon-project-org').get('kind')
      == 'nonprofit'
      and 'global-carbon-project' not in {
          g['name'] for g in SEED_CLIMATE_GOV_SOURCES})

check('a source_ref naming nothing REFUSES by name rather than '
      'resolving to a plausible-looking blank',
      not resolve_citation(_cm, 'no-such-source').get('ok')
      and 'no source row named' in
      resolve_citation(_cm, 'no-such-source').get('refusal', ''))

check('an EMPTY source_ref refuses too, and says what that costs: '
      'nothing can follow the claim',
      not resolve_citation(_cm, '').get('ok'))

check('secondary-reporting is a real evidence grade, ranked BELOW '
      'every study and every standard — a magazine paragraph must '
      'never outrank a trial',
      'secondary-reporting' in EVIDENCE_GRADES
      and grade_rank('secondary-reporting')
      > grade_rank('standard-or-guideline')
      and grade_rank('secondary-reporting')
      > grade_rank('contested-controlled-study'))

_tc = threshold_citations(_cm)
check('threshold_citations resolves every row and groups by '
      'source kind, so a reader can see at a glance which lines '
      'are studies and which are standards',
      _tc['ok'] and not _tc['unresolved']
      and set(_tc['bySourceKind']) == {'academic', 'nonprofit',
                                       'government',
                                       'journalistic'})

_ag = resolve_citation(_cm, 'airgradient-2025-hidden-health-risks')
check('the AirGradient article resolves as a journalistic source '
      'and its COMMERCIAL INTEREST is recorded: the publisher '
      'sells CO2 monitors, which does not make the piece wrong '
      'but is something a reader weighing it would want',
      _ag.get('ok') and _ag['kind'] == 'journalistic'
      and 'sells' in getattr(
          _cm.objectTables['JournalisticSource'][
              'airgradient-2025-hidden-health-risks'],
          'commercial_interest', '').lower())

check('its author credential is recorded EXACTLY as the byline '
      'states it — "Dr." with no degree type — because writing '
      '"MD" would be inventing a credential to make the citation '
      'look stronger',
      'degree type not stated' in _ag['authorCredentials'])

check('all FOUR papers it cites are seeded as academic rows, so '
      'every claim it makes can be followed to a primary source',
      len(_ag['primarySources']) == 4
      and all(resolve_citation(_cm, r).get('ok')
              for r in _ag['primarySources']))

check('but unsourcedClaimsNoted is True: the article does not say '
      'WHICH of its four papers each threshold came from, so the '
      'per-figure mapping cannot be reconstructed — which is '
      'exactly why its thresholds are graded secondary-reporting',
      _ag['unsourcedClaimsNoted'] is True)

_by_grade = {}
for _t in SEED_CO2_THRESHOLDS:
    _by_grade.setdefault(_t['evidence_grade'], []).append(_t['name'])
check('the two thresholds sourced to the vendor blog are the ONLY '
      'secondary-reporting rows, and the ones sourced to a '
      'peer-reviewed review are graded observational instead — '
      'the grade follows the EVIDENCE, not where it was read',
      set(_by_grade.get('secondary-reporting', [])) ==
      {'co2-oxidative-stress-1400',
       'co2-metabolic-dysregulation-2000'}
      and 'co2-building-symptoms-700'
      in _by_grade.get('observational', []))

check('Stumm 2023 is graded expert-judgement, NOT a study grade: '
      'a single-author MODEL is an argument, not an observation, '
      'and its own onset figure (~3000 ppm) sits above typical '
      'indoor levels',
      [t for t in SEED_CO2_THRESHOLDS
       if t['name'] == 'co2-modelled-hypercapnia-3000'
       ][0]['evidence_grade'] == 'expert-judgement')

_seven = [t for t in SEED_CO2_THRESHOLDS if t['ppm'] == 700.0]
check('TWO different 700 ppm thresholds coexist — ASHRAE\'s '
      'DIFFERENTIAL above outdoor and Azuma\'s ABSOLUTE '
      'epidemiological level — and is_differential is what stops '
      'a page treating unrelated quantities that share a number '
      'as the same line',
      len(_seven) == 2
      and {t['is_differential'] for t in _seven} == {True, False})

check('Satish 2012 carries n=22 as PUBLISHED, not the 24 a '
      'secondary summary reported — the correction is the whole '
      'discipline in miniature',
      [a for a in SEED_CLIMATE_ACADEMIC_SOURCES
       if a['name'] == 'satish-2012-co2-decision-making'
       ][0]['sample_size'] == 22)

check('and it records that THE AUTHORS THEMSELVES called the '
      '2500 ppm effects barely credible and asked for '
      'replication — fair to them, and stronger than any outside '
      'criticism',
      'defy credibility' in [
          a for a in SEED_CLIMATE_ACADEMIC_SOURCES
          if a['name'] == 'satish-2012-co2-decision-making'
      ][0]['notes'])

# This list SHIPPED EMPTY until a real article arrived, and the
# check that pinned that has been replaced — not deleted — by the
# rule it was protecting all along: a journalistic row must name
# the primary research it reports on, or it is an assertion with a
# byline. Pinning "empty" once a real source exists would be
# cargo-culting the old guard past its purpose.
check('EVERY seeded journalistic row names the primary studies it '
      'reports on, and every one of those resolves — a claim must '
      'be followable to the evidence, not just to the person who '
      'repeated it',
      all(json.loads(j['primary_sources_json'] or '[]')
          and all(resolve_citation(_cm, r).get('ok')
                  for r in json.loads(
                      j['primary_sources_json'] or '[]'))
          for j in SEED_CLIMATE_JOURNALISTIC_SOURCES))

check('and every seeded journalistic row declares whether its '
      'publisher has a commercial interest in the conclusion — '
      'the field may be empty, but it must have been considered',
      all('commercial_interest' in j
          for j in SEED_CLIMATE_JOURNALISTIC_SOURCES))


print('== suite: co2-S — the cited symptom ladder ==')

from climate.co2_symptoms import (
    SEED_HEALTH_SYMPTOMS, SEED_SYMPTOM_CLAIMS, ladder_for_space,
    symptom_ladder,
)
from climate.climate_basis import (
    HealthSymptomDefinition, SymptomOnsetClaim, SYMPTOM_SEVERITY,
)

# The ladder cites OSHA, whose GovSource row is seeded by dmvdata
# rather than by climate — both land in the same table in
# production, so the fixture unions them. A fixture narrower than
# production is how a green suite hides a broken page.
from dmvdata.gov_sources import SEED_GOV_SOURCES as _DMV_GOV

_sym_mgr = types.SimpleNamespace(objectTables=dict(
    _cm.objectTables,
    **{'HealthSymptomDefinition': _table(SEED_HEALTH_SYMPTOMS),
       'SymptomOnsetClaim': _table(SEED_SYMPTOM_CLAIMS),
       'GovSource': _table(SEED_CLIMATE_GOV_SOURCES + _DMV_GOV)}))
_sym_mgr.objectTypingDict = {k: object()
                             for k in _sym_mgr.objectTables}
_L = symptom_ladder(_sym_mgr)

check('the symptom ladder builds and EVERY claim resolves its '
      'source — a cited symptom whose citation does not resolve '
      'is just an assertion with a footnote',
      _L['ok'] and not _L['unresolvedSources'],
      str(_L.get('unresolvedSources')))

check('the ladder is ORDERED by concentration, so a reader can '
      'walk it',
      [c['ppmFrom'] for c in _L['ladder']]
      == sorted(c['ppmFrom'] for c in _L['ladder']))

check('symptoms are OBJECTS, not strings: the same symptom '
      '(reduced decision-making) is claimed at two different '
      'levels by the same study, and headache is claimed by BOTH '
      'epidemiology at 700 ppm and occupational medicine far '
      'higher — one row per claim, not per symptom',
      len([c for c in _L['ladder']
           if c['symptom'] == 'sym-cognitive-decrement']) == 2)

check('every claim carries its own evidence grade, because the '
      'grade belongs to the CLAIM: "headache at 700 ppm" and '
      '"unconsciousness at 100000 ppm" are not equally certain',
      all(c['evidenceGrade'] in EVIDENCE_GRADES
          for c in _L['ladder']))

check('the LETHAL rungs are marked, and they begin at the IDLH '
      '(40000 ppm) — two orders of magnitude above any indoor '
      'level on this page',
      _L['lethalFrom'] == 40000.0
      and any(c['isLethal'] for c in _L['ladder']))

check('DEATH is the only irreversible row — OSHA states low-level '
      'CO2 intoxication is "sudden and reversible", and a ladder '
      'that hid that would frighten rather than inform',
      [s_['name'] for s_ in SEED_HEALTH_SYMPTOMS
       if not s_['is_reversible']] == ['sym-death'])

check('unconsciousness is marked REVERSIBLE — true only if the '
      'person is removed — which is why confusion, the symptom '
      'that removes the judgement to leave, sits BELOW it and '
      'matters more operationally',
      [s_ for s_ in SEED_HEALTH_SYMPTOMS
       if s_['name'] == 'sym-unconsciousness'][0]['is_reversible']
      and [s_ for s_ in SEED_HEALTH_SYMPTOMS
           if s_['name'] == 'sym-confusion'][0]['severity_rank']
      < [s_ for s_ in SEED_HEALTH_SYMPTOMS
         if s_['name'] == 'sym-unconsciousness'][0]['severity_rank'])

check('the OSHA lethal claim quotes the source VERBATIM rather '
      'than paraphrasing — a paraphrase of a health claim is a '
      'new claim',
      'generally agreed upon as posing an immediate physiologic '
      'threat' in [c['quote'] for c in _L['ladder']
                   if c['claim']
                   == 'claim-immediate-threat-100000'][0])

check('the ladder REFUSES to interpolate: its note says so '
      'explicitly, because below ~5000 ppm these are contested '
      'chronic claims and above ~40000 they are uncontroversial '
      'acute toxicology — different questions, different evidence',
      'not interpolated' in _L['note'])

check('and it carries OSHA\'s own admission that the literature '
      'varies widely, which is why each claim is a BAND with a '
      'source rather than one asserted onset per symptom',
      'wide variation' in _L['disagreementNote'])

_bed = ladder_for_space(_sym_mgr, 3093.5)
check('a closed bedroom at today\'s outdoor level has "reached" '
      'several claimed symptoms but NO lethal rung — the ladder '
      'connects to the coupled indoor model without exaggerating '
      'it',
      _bed['ok'] and _bed['anyLethalReached'] is False
      and _bed['worstSeverityRank'] == 3)

check('and the room report says plainly that "reached" means a '
      'source CLAIMED it at that level, not that anyone in the '
      'room has it',
      'NOT that anyone in this room has it' in _bed['note'])

check('a well-ventilated public building has reached only the '
      'rank-1 instrument-detectable claim — the ladder '
      'discriminates between rooms rather than alarming about '
      'all of them',
      ladder_for_space(_sym_mgr, 689.3)['worstSeverityRank'] == 1)

check('every symptom seed key matches HealthSymptomDefinition and '
      'every claim key matches SymptomOnsetClaim exactly (the '
      'ten-strikes seed gotcha)',
      all(set(x) <= _init_params(HealthSymptomDefinition)
          for x in SEED_HEALTH_SYMPTOMS)
      and all(set(x) <= _init_params(SymptomOnsetClaim)
              for x in SEED_SYMPTOM_CLAIMS))

check('every symptom severity rank is a real SYMPTOM_SEVERITY '
      'level, so the ladder can always be ordered',
      all(s_['severity_rank'] in SYMPTOM_SEVERITY
          for s_ in SEED_HEALTH_SYMPTOMS))


print('== suite: co2-E — urban/non-urban x indoor/outdoor ==')

from climate.co2_settings import (
    SEED_AMBIENT_SETTINGS, SEED_OBSERVED_LEVELS, all_space_levels,
    era_comparison, era_exposure_comparison, local_outdoor_ppm,
    setting_ladder, validate_against_observed,
)
from climate.climate_basis import (
    AmbientSettingProfile, ObservedLevelReference,
)

_set_mgr = _ns_mgr = types.SimpleNamespace(objectTables={
    'AmbientSettingProfile': _table(SEED_AMBIENT_SETTINGS),
    'ObservedLevelReference': _table(SEED_OBSERVED_LEVELS),
    'IndoorSpaceProfile': _table(SEED_INDOOR_SPACES)})
_set_mgr.objectTypingDict = {k: object()
                             for k in _set_mgr.objectTables}
_BG = 427.35
_SL = setting_ladder(_set_mgr, _BG)

check('the remote background enhancement is EXACTLY zero — it is '
      'the baseline the record is measured at, so anything else '
      'would be double-counting',
      local_outdoor_ppm(_set_mgr, _BG,
                        'outdoor-remote-background'
                        )['enhancementPpm'] == 0.0)

check('URBAN OUTDOOR REACHES 500+ ppm at today\'s background, '
      'which is the whole point: "outdoor" is not one number, and '
      'the spread from remote baseline to city centre is '
      'comparable to decades of global rise',
      local_outdoor_ppm(_set_mgr, _BG, 'outdoor-urban-core'
                        )['localOutdoorPpm'] > 500.0)

check('the outdoor ladder is ordered and every setting is a '
      'SURFACE measurement — satellite column enhancements are '
      'single-digit ppm and must never share this axis',
      [x['localOutdoorPpm'] for x in _SL['settings']]
      == sorted(x['localOutdoorPpm'] for x in _SL['settings'])
      and all(s_['measurement_kind'] == 'surface-in-situ'
              for s_ in SEED_AMBIENT_SETTINGS))

check('enhancements are stored ABOVE background, not as absolute '
      'levels — so every row stays true as the background rises',
      local_outdoor_ppm(_set_mgr, 500.0, 'outdoor-urban-core'
                        )['localOutdoorPpm']
      - local_outdoor_ppm(_set_mgr, 400.0, 'outdoor-urban-core'
                          )['localOutdoorPpm'] == 100.0)

_AL = all_space_levels(_set_mgr, _BG)

check('EVERY room is now seated on its own local outdoor, and '
      'every one was UNDERSTATED before settings existed — the '
      'app was adding room offsets to clean mid-Pacific air',
      _AL['ok'] and all(s_['understatedByPpm'] > 0
                        for s_ in _AL['spaces']
                        if not s_.get('refused')))

check('and the understatement is exactly the local enhancement, '
      'not an arbitrary fudge',
      all(abs(s_['understatedByPpm'] - s_['enhancementPpm']) < 1e-9
          for s_ in _AL['spaces'] if not s_.get('refused')))

check('the paired intervention rooms prove ventilation is the '
      'knob: the SAME bedroom with a window ajar sits far below '
      'the closed one, and the same classroom with its '
      'ventilation running sits far below the one without',
      [s_ for s_ in _AL['spaces']
       if s_['space'] == 'bedroom-window-ajar'][0]['indoorPpm']
      < [s_ for s_ in _AL['spaces']
         if s_['space'] == 'bedroom-overnight-closed'
         ][0]['indoorPpm']
      and [s_ for s_ in _AL['spaces']
           if s_['space'] == 'classroom-mechanically-ventilated'
           ][0]['indoorPpm']
      < [s_ for s_ in _AL['spaces']
         if s_['space'] == 'classroom-occupied'][0]['indoorPpm'])

check('a room with NO published counterpart reports no '
      'cross-check rather than a pass — an empty space_kind used '
      'to match the OUTDOOR reference rows and silently score a '
      'room against outdoor air',
      not validate_against_observed(_set_mgr, '', 900.0).get('ok'))

check('the three rooms that DO have counterparts are checked, and '
      'the model is scored honestly: the office lands inside the '
      'measured range while the bedroom and classroom are flagged '
      'PESSIMISTIC rather than quietly tuned to fit',
      [s_ for s_ in _AL['spaces']
       if s_['space'] == 'open-plan-office'
       ][0]['observedCheck']['insideObservedRange'] is True
      and 'PESSIMISTIC' in [
          s_ for s_ in _AL['spaces']
          if s_['space'] == 'bedroom-overnight-closed'
          ][0]['observedCheck']['verdict'])

check('the INTERVENTION rooms are deliberately unmapped: scoring '
      'a window-open bedroom against a closed-window measurement '
      'would report the intervention working as a model error',
      'observedCheck' not in [
          s_ for s_ in _AL['spaces']
          if s_['space'] == 'bedroom-window-ajar'][0])

_ERA = era_comparison(_set_mgr)
check('the era table spans pre-industrial outdoor (280 ppm) to a '
      'closed bedroom today, and MARKS which rows are modelled — '
      'there is no ice core for indoor air',
      _ERA['ok']
      and any(c['isModelled'] for c in _ERA['levels'])
      and min(c['ppmTypical'] for c in _ERA['levels']) == 280.0)

# CORRECTED. This check previously pinned the claim that a
# CO2-only era comparison "flatters the past" — i.e. that the past
# was worse and CO2 alone hid it. Investigating Dustin's question
# showed that is wrong on CO2 specifically: the draughtiness that
# failed to clear woodsmoke also stopped CO2 accumulating, so the
# past was probably BETTER on CO2 and far worse on smoke. The
# check now pins the corrected, two-directional statement, and
# this comment stays so the reversal is not silently rewritten.
check('the era caveat runs in BOTH directions: the past was far '
      'worse on smoke, CO and particulate, and probably BETTER on '
      'CO2 than a modern sealed room — different pollutants, '
      'opposite directions, one cause',
      'incomplete in both directions' in _ERA['caveat']
      and 'LOWER CO2' in _ERA['caveat']
      and 'smoke' in _ERA['caveat'])

_EX = era_exposure_comparison(_set_mgr, _BG)

check('THE QUESTION IS ANSWERED IN TWO HALVES, because it has two '
      'answers: the FLOOR you cannot get below, and the PEAK you '
      'hit in a room',
      _EX['ok'] and 'floor' in _EX and 'peak' in _EX)

check('the FLOOR is unambiguously new and MEASURED: the whole '
      '800,000-year record caps below 300 ppm, today\'s '
      'background is over 425 and a city centre over 500',
      _EX['floor']['recordMaxPpm800kyr'] < 300.0
      and _EX['floor']['presentBackgroundPpm'] > 425.0
      and _EX['floor']['presentUrbanPpm'] > 500.0
      and 'MEASURED' in _EX['floor']['evidence'])

check('the PEAK half was REVISED after the combustion arithmetic: '
      'a wood fire provably makes CO2, so the honest verdict is '
      'that the indoor peak is probably NOT novel and only the '
      'floor is',
      'not novel' in _EX['peak']['verdict'].lower())

check('and the top-line answer now separates them explicitly — '
      'the floor is new, the peak probably is not, and chronic '
      'compensation answers to the BASELINE not the peak',
      'FLOOR IS NEW' in _EX['answer']
      and 'baseline' in _EX['answer'].lower())

check('and the two halves are labelled with DIFFERENT evidence '
      'strength — the modern indoor figure is measured, the '
      'pre-industrial one is modelled, and the payload says so '
      'rather than presenting them as one comparison',
      'ASYMMETRIC' in _EX['peak']['evidence']
      and 'MODELLED' in _EX['peak']['evidence'])

check('the pre-industrial indoor estimate was REVISED DOWN and '
      'the old caveat CORRECTED: the draughtiness that failed to '
      'clear woodsmoke also stopped CO2 accumulating, so on CO2 '
      'the past was probably better indoors too — the opposite of '
      'the intuition this row first encoded',
      [r for r in SEED_OBSERVED_LEVELS
       if r['name'] == 'obs-indoor-preindustrial-dwelling'
       ][0]['ppm_typical'] == 400.0)

check('the evidence GAP is recorded as a finding, not glossed: '
      'the household-air-pollution literature measures PM2.5 and '
      'CO and not CO2, verified against a specific 86-home '
      'biomass study that reports neither',
      'PMC3978088' in [
          r for r in SEED_OBSERVED_LEVELS
          if r['name'] == 'obs-indoor-preindustrial-dwelling'
      ][0]['citation_text'])

check('the answer names what the past WAS worse at — smoke, not '
      'CO2 — so the correction does not swing into pretending '
      'pre-industrial air was clean',
      'Smoke' in _EX['whatWasWorseInThePast']
      and 'PM2.5' in _EX['whatWasWorseInThePast'])

check('and it explains WHY the floor is the physiologically '
      'novel exposure: chronic compensation responds to sustained '
      'partial pressure, and a smoky hut was escapable where a '
      'raised background is not',
      'escapable' in _EX['whyTheFloorMatters']
      and 'SUSTAINED' in _EX['whyTheFloorMatters'])

check('and it names what would settle the unmeasured half — one '
      'more sensor on an instrument package already deployed',
      'CO2 logging' in _EX['whatWouldSettleIt'])

check('every settings and observed-level seed key matches its '
      'class __init__ exactly (the ten-strikes seed gotcha)',
      all(set(x) <= _init_params(AmbientSettingProfile)
          for x in SEED_AMBIENT_SETTINGS)
      and all(set(x) <= _init_params(ObservedLevelReference)
              for x in SEED_OBSERVED_LEVELS))

check('every room names a setting that exists, so no room can '
      'silently fall back to a default outdoor',
      all(r['setting_ref'] in {s_['name']
                               for s_ in SEED_AMBIENT_SETTINGS}
          for r in SEED_INDOOR_SPACES))


print('== suite: co2-F — what a wood fire did to indoor CO2 ==')

from climate.co2_combustion import (
    CO2_PER_CARBON, WOOD_CARBON_FRACTION, co_tracer_offset_ppm,
    combustion_offset_band, direct_burn_offset_ppm,
    hearth_dwelling_estimate, pm_tracer_offset_ppm,
    wood_fire_co2_mg_per_day,
)
from climate.co2_indoor import person_co2_mg_per_day

_fire = wood_fire_co2_mg_per_day(0.5)
_adult = person_co2_mg_per_day(1.0)

check('A WOOD FIRE IS PROVABLY A LARGE CO2 SOURCE — a 0.5 kg/h '
      'fire makes roughly 30x what one adult exhales, so the '
      'earlier "draughtiness handles it" argument could not be '
      'left as an assertion',
      _fire['ok'] and _fire['mgPerDay'] / _adult > 20.0,
      f'ratio {_fire["mgPerDay"] / _adult:.1f}')

check('and the source term is stoichiometric, not a fudge: half '
      'the dry mass is carbon and each carbon leaves as CO2 at '
      '44/12 its mass',
      abs(CO2_PER_CARBON - 44.0 / 12.0) < 1e-12
      and WOOD_CARBON_FRACTION == 0.50)

_a5 = direct_burn_offset_ppm(0.5, 40.0, 5.0)
_a30 = direct_burn_offset_ppm(0.5, 40.0, 30.0)
check('the UNFLUED upper bound is enormous — thousands of ppm at '
      'low air change — and falls with ventilation exactly as the '
      'shared mass balance requires',
      _a5['offsetPpm'] > 2000.0 and _a30['offsetPpm'] < 500.0
      and _a5['offsetPpm'] > _a30['offsetPpm'])

check('but it is LABELLED an upper bound, because it assumes no '
      'flue — and a chimney is precisely the thing that makes it '
      'one',
      'UPPER BOUND' in _a5['note'] and 'flue' in _a5['note'])

_pm = pm_tracer_offset_ppm(130.0)
_co = co_tracer_offset_ppm(5.8)
check('the TRACER routes sidestep the flue entirely: they measure '
      'what is in the ROOM, which is the quantity nobody can '
      'reconstruct for a dwelling that no longer exists',
      _pm.get('ok') and _co.get('ok')
      and _pm['offsetPpm'] > 0 and _co['offsetPpm'] > 0)

check('CO and CO2 are both gases, so the CO tracer uses a MOLAR '
      'ratio and does no density conversion — a units error here '
      'would move the answer by nearly two',
      'no density conversion' in _co['note'])

_band = combustion_offset_band(130.0, 5.8)
check('the two tracers DISAGREE about fivefold, and the payload '
      'says so rather than averaging them — averaging two '
      'estimates that differ fivefold manufactures a precision '
      'neither has',
      _band['ok'] and _band['tracersAgree'] is False
      and _band['routesAgreeWithinFactor'] > 2.0
      and 'NOT averaged' in _band['note'])

check('and the disagreement is EXPLAINED, not just flagged: the '
      'measured CO:PM ratio in those homes is far above what '
      'wood-smoke emission factors predict',
      'CO:PM' in _band['disagreementNote'])

_hearth = hearth_dwelling_estimate()
check('the hearth dwelling estimate is DERIVED from the '
      'measurements that exist (PM2.5 and CO) rather than from a '
      'draughtiness assumption — which is what makes it an '
      'estimate rather than a preference',
      _hearth['ok'] and 345.0 <= _hearth['dwellingLowPpm'] <= 400.0
      and _hearth['dwellingHighPpm'] < 600.0)

check('THE PEAK CAVEAT IS THE HONEST PART: a cooking-period peak '
      'plausibly reached or exceeded a modern sealed bedroom, so '
      'the indoor PEAK is probably not novel — what is novel is '
      'that today\'s elevation cannot be left',
      'not novel' in _hearth['peakCaveat'].lower()
      and 'cannot be left' in _hearth['peakCaveat'])

check('and the module states plainly what changed: the smoke in '
      'those rooms PROVES combustion products reached the '
      'occupants, so citing the smoke while claiming the CO2 '
      'stayed outside was having it both ways',
      'narrows the gap' in _hearth['whatThisChanges'])

check('a tracer route with nothing measured REFUSES rather than '
      'falling back on the flue-dependent direct burn',
      not combustion_offset_band(None, None).get('ok'))

check('an MCE of exactly 1.0 REFUSES — it would mean no CO at '
      'all, and then CO cannot be a tracer of anything',
      not co_tracer_offset_ppm(5.8, mce=1.0).get('ok'))


failed = _results.count(False)
print(f'\n{len(_results) - failed}/{len(_results)} checks passed')
raise SystemExit(1 if failed else 0)
