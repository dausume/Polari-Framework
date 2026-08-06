"""
@cross-cutting
@module climate.biomarker_ingest
@tags @xc:bindings

Dustin 2026-08-05: "we needed blood bicarbonate levels from 1999 to
2012 at least" — the population biomarker the CO2/health question
turns on, fetched per NHANES cycle.

NHANES publishes serum bicarbonate (LBXSC3SI, mmol/L) in the
standard biochemistry profile, one SAS XPORT file per 2-year cycle.
This module owns the cycle table (which file, which years), seeds
the PopulationBiomarkerSeries row, and ingests one cycle at a time
through the SAME machinery the atmospheric series use
(fetch_and_parse -> the xpt_reader -> a recorded SourceRetrieval),
writing one BiomarkerCycleObservation per cycle: mean, SD, median,
n, and the 5th/95th percentiles.

🔑 THE PATH TRAP (already documented on the endpoint row and hit
again here): the retired /Nchs/Nhanes/<cycle>/<FILE>.XPT form
returns HTTP 200 with a ~20 KB HTML "Page Not Found" page. A 200 is
not a success. The endpoint's XPORT signature is what rejects it,
and the refusal is passed through verbatim rather than becoming a
zero.

@consumers climate.climate_api (POST /api/climate/biomarker/ingest)
"""

#: cycle key -> (start year, end year, YEAR PATH, XPT file).
#: 🔑 THE YEAR PATH IS THE CYCLE'S START YEAR ALONE. Verified
#: live 2026-08-05: .../Public/2017/DataFiles/BIOPRO_J.xpt is
#: the real 2.1 MB file, while .../Nchs/Nhanes/2017-2018/
#: BIOPRO_J.XPT returns HTTP 200 with the 20,905-byte HTML
#: 'Page Not Found' decoy the endpoint row documents.
#: 1999-2012 is Dustin's stated minimum; later cycles included
#: because they cost one call each and extend the same question.
NHANES_BICARB_CYCLES = {
    '1999-2000': (1999, 2000, '1999', 'LAB18'),
    '2001-2002': (2001, 2002, '2001', 'L40_B'),
    '2003-2004': (2003, 2004, '2003', 'L40_C'),
    '2005-2006': (2005, 2006, '2005', 'BIOPRO_D'),
    '2007-2008': (2007, 2008, '2007', 'BIOPRO_E'),
    '2009-2010': (2009, 2010, '2009', 'BIOPRO_F'),
    '2011-2012': (2011, 2012, '2011', 'BIOPRO_G'),
    '2013-2014': (2013, 2014, '2013', 'BIOPRO_H'),
    '2015-2016': (2015, 2016, '2015', 'BIOPRO_I'),
    '2017-2018': (2017, 2018, '2017', 'BIOPRO_J'),
}
BICARB_SERIES = 'nhanes-serum-bicarbonate'
BICARB_COLUMN = 'LBXSC3SI'
ENDPOINT = 'nhanes-biopro-xpt'

SEED_BIOMARKER_SERIES = [{
    'name': BICARB_SERIES,
    'display_name': 'Serum bicarbonate, US population (NHANES)',
    'biomarker': 'serum bicarbonate',
    'unit': 'mmol/L',
    'source_ref': 'cdc-nchs-nhanes',
    'endpoint_ref': ENDPOINT,
    'xpt_column': BICARB_COLUMN,
    'codebook_url': 'https://wwwn.cdc.gov/Nchs/Nhanes/'
                    '2017-2018/BIOPRO_J.htm',
    'status': 'prior',
    'population_note': 'Examined persons with a valid standard '
                       'biochemistry profile in the cycle; NHANES '
                       'sample weights are NOT applied — this is '
                       'the unweighted examined-sample mean, and '
                       'the difference matters for national '
                       'inference (named, not hidden).',
}]


def _rows(manager, class_name):
    table = (getattr(manager, 'objectTables', None) or {}).get(
        class_name, {})
    return list(table.values()) if isinstance(table, dict) else list(table)


def _named(manager, class_name, name):
    for r in _rows(manager, class_name):
        if getattr(r, 'name', '') == name:
            return r
    return None


def seed_biomarker_series(manager):
    from climate.climate_basis import PopulationBiomarkerSeries
    from composition.seed_upsert import upsert_seed_pairs
    return upsert_seed_pairs(
        manager,
        [('PopulationBiomarkerSeries', PopulationBiomarkerSeries,
          SEED_BIOMARKER_SERIES)], tag='BiomarkerSeed')


def ingest_bicarbonate_cycle(manager, cycle, fetcher=None):
    """Fetch ONE NHANES cycle's biochemistry file and write its
    bicarbonate summary. Refusals pass through verbatim."""
    # NOT fetch_and_parse: that decodes the body to TEXT, which
    # mangles a binary XPORT file, and no 'xport' parser is
    # registered. The raw-bytes path is the honest one here.
    from climate.series_ingest import record_retrieval_row
    from climate.xpt_reader import column_summary, read_xpt_bytes
    from polariApiProfiler.endpoint_fetch import fetch_endpoint
    spec = NHANES_BICARB_CYCLES.get(cycle)
    if spec is None:
        return {'ok': False,
                'refusal': f'unknown cycle {cycle!r}',
                'knownCycles': sorted(NHANES_BICARB_CYCLES)}
    start, end, year_path, xpt_file = spec
    endpoint = _named(manager, 'APIEndpoint', ENDPOINT)
    if endpoint is None:
        return {'ok': False,
                'refusal': f'no APIEndpoint row {ENDPOINT!r} — the '
                           f'source registry is not seeded here'}
    fetched = fetch_endpoint(
        endpoint, params={'year': year_path, 'file': xpt_file},
        fetcher=fetcher)
    if not fetched.get('ok'):
        # A 200 that is really an HTML 404 lands HERE, by signature.
        return {'ok': False, 'cycle': cycle,
                'refusal': fetched.get('refusal', 'fetch refused'),
                'urlRedacted': fetched.get('url_redacted', ''),
                'httpStatus': fetched.get('status', 0)}
    read = read_xpt_bytes(
        fetched.get('body'),
        column_map={BICARB_COLUMN: {
            'meaning': 'serum bicarbonate', 'unit': 'mmol/L'}})
    if not read.get('ok'):
        return {'ok': False, 'cycle': cycle,
                'refusal': read.get('refusal', 'xpt read refused'),
                'urlRedacted': fetched.get('url_redacted', '')}
    parsed = {'sha256': fetched.get('sha256', ''),
              'bytes': fetched.get('bytes', 0),
              'httpStatus': fetched.get('status', 200),
              'urlRedacted': fetched.get('url_redacted', ''),
              'points': []}
    summary = column_summary(read.get('frame'), BICARB_COLUMN)
    # a successful summary carries no 'ok' key — a refusal does.
    if summary.get('refusal'):
        return {'ok': False, 'cycle': cycle,
                'refusal': summary['refusal'],
                'column': BICARB_COLUMN}
    series = _named(manager, 'PopulationBiomarkerSeries',
                    BICARB_SERIES)
    retrieval = record_retrieval_row(
        manager, series, endpoint, parsed,
        note=f'NHANES {cycle} {xpt_file}.xpt, column '
             f'{BICARB_COLUMN}') if series is not None else None
    fields = {
        'name': f'{BICARB_SERIES}--{cycle}',
        'series_ref': BICARB_SERIES, 'cycle': cycle,
        'cycle_start_year': float(start),
        'cycle_end_year': float(end),
        'mean': round(float(summary.get('mean', 0.0) or 0.0), 4),
        'std_dev': round(float(summary.get('std_dev', 0.0) or 0.0),
                         4),
        'median': round(float(summary.get('median', 0.0) or 0.0), 4),
        'n': int(summary.get('n', 0) or 0),
        'pct_5': round(float(summary.get('pct_5', 0.0) or 0.0), 4),
        'pct_95': round(float(summary.get('pct_95', 0.0) or 0.0), 4),
        'retrieval_ref': (getattr(retrieval, 'name', '')
                          if retrieval is not None else ''),
        'is_prior': False, 'provenance_id': 'biomarker-ingest',
        'notes': f'unweighted examined-sample summary of '
                 f'{BICARB_COLUMN} from {xpt_file}.xpt'}
    _write_observation(manager, fields)
    if series is not None:
        series.status = 'ingested'
        db = getattr(manager, 'db', None)
        if db is not None:
            try:
                db.saveInstanceInDB(series)
            except Exception:
                pass
    return {'ok': True, 'cycle': cycle, 'series': BICARB_SERIES,
            'mean': fields['mean'], 'n': fields['n'],
            'stdDev': fields['std_dev'],
            'retrieval': fields['retrieval_ref'],
            'note': 'unweighted examined-sample mean; NHANES survey '
                    'weights not applied (named)'}


def _write_observation(manager, fields):
    from climate.climate_basis import BiomarkerCycleObservation
    table = manager.objectTables.setdefault(
        'BiomarkerCycleObservation', {})
    existing = next((r for r in table.values()
                     if getattr(r, 'name', '') == fields['name']),
                    None)
    db = getattr(manager, 'db', None)
    if existing is not None:
        for k, v in fields.items():
            setattr(existing, k, v)
        row = existing
    else:
        row = None
        try:
            row = BiomarkerCycleObservation(**fields, manager=manager)
        except Exception:
            row = None
        if row is None or fields['name'] not in {
                getattr(r, 'name', None) for r in table.values()}:
            from types import SimpleNamespace
            row = SimpleNamespace(**fields)
            table[fields['name']] = row
    if db is not None:
        try:
            db.saveInstanceInDB(row)
        except Exception:
            pass
    return row


def ingest_all_cycles(manager, cycles=None, fetcher=None):
    """Every cycle (or a named subset). Per-cycle refusals are
    REPORTED, never dropped — a missing cycle is a hole in the
    series and the reader must see it."""
    seed_biomarker_series(manager)
    wanted = cycles or sorted(NHANES_BICARB_CYCLES)
    done, refused = [], []
    for c in wanted:
        r = ingest_bicarbonate_cycle(manager, c, fetcher=fetcher)
        (done if r.get('ok') else refused).append(r)
    return {'ok': bool(done), 'cyclesIngested': len(done),
            'cyclesRefused': len(refused),
            'results': done, 'refusals': refused,
            'note': 'refused cycles are holes in the series, not '
                    'zeros — they are listed so the graph can show '
                    'the gap'}
