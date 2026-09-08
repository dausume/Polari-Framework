"""
@module dmvdata.gov_sources_basis

The GOV SOURCES registry (Dustin 2026-07-16): "an easy way to know
what these acronyms are and to find their official websites" —
every official source the scorecard ingests from is a `GovSource`
row: acronym expanded, agency named, official website + data portal
cited, whether an API key is required (and WHICH env knob supplies
it — never a literal key, repos are public), and which registered
APIEndpoint rows pull from it.

Duplication attribution: when a Polari group (or an individual)
retrieves a source's data and duplicates it locally, a
`SourceRetrieval` row records the DATE-TIME and the ORIGIN — the
group or individual the data came through — so a copy is never
orphaned from its provenance. `terms_from_source` answers the
reverse question: which ScoreTerms (and how many values) ORIGINATE
from a given source, by matching acronym/full-name/official-domain
against the terms' and values' provenance strings.

Matching rules (deliberate): acronyms match CASE-SENSITIVELY on
word boundaries ('MACROS' never matches 'ACS'); full names match
case-insensitively; official domains (census.gov, huduser.gov…)
match case-insensitively anywhere — a provenance URL is the
strongest origin signal.

@consumers
  - dmvdata.custom.census_pull (records retrievals on ingest)
  - polariServer (registration + seed, wired by the main session)
  - the PSC sources/glossary page (col-6, later)
"""
# sap-2c INDEX (design §7): the classes live one-per-file under objects/gov_sources/;
# this file re-exports them (imports keep working) and holds what they share.
# The original imports stay: names this file imported were re-exported implicitly.

import json
import re
import threading
from datetime import datetime, timezone
from urllib.parse import urlparse
from objectTreeDecorators import treeObject, treeObjectInit

from dmvdata.objects.gov_sources._shared import JURISDICTIONS, SEED_GOV_SOURCES, SOURCE_TABLES, _RETRIEVAL_LOCK, _acronym_of, _domains, _identity_summary, _known_sources, _legal_identity, _match_evidence, _retrieval_dict, _rows, _source, _src, find_source, retrievals_for, source_glossary, source_report, terms_from_source, validate_source_names  # noqa: F401
from dmvdata.objects.gov_sources.GovSource import GovSource  # noqa: F401
from dmvdata.objects.gov_sources.SourceRetrieval import SourceRetrieval  # noqa: F401

from datetime import datetime, timezone
import re

def record_retrieval(manager, source_name, endpoint_name='',
                     what='', retrieved_by='',
                     retrieved_by_group='', row_count=0,
                     provenance_url='', retrieved_at=None,
                     notes=''):
    """Record one duplication event. The origin must NAME someone —
    an unattributed copy is exactly what this registry exists to
    prevent."""
    source, _kind = find_source(manager, source_name)
    if source is None:
        kinds = ', '.join(sorted(SOURCE_TABLES.values()))
        return {'ok': False,
                'error': f"no source named '{source_name}' in any "
                         f'legal source table ({kinds})',
                'knownSources': _known_sources(manager)}
    if not retrieved_by:
        return {'ok': False,
                'error': 'retrieved_by must name the Contributor '
                         'who retrieved the data (the origin is '
                         'the point of this record)'}
    # A real event gets a real stamp; tests pass retrieved_at for
    # determinism.
    stamp = retrieved_at or datetime.now(timezone.utc).isoformat()
    compact = re.sub(r'[^0-9T]', '', stamp)[:15]
    what_slug = re.sub(r'[^a-z0-9]+', '-',
                       (what or endpoint_name or 'pull').lower()
                       ).strip('-')[:40]
    with _RETRIEVAL_LOCK:
        table = manager.objectTables.setdefault('SourceRetrieval',
                                                {})
        # Uniqueness against row NAMES — real managers key tables
        # by random polari ids, so key-presence proves nothing.
        taken = {getattr(r, 'name', '') for r in table.values()}
        row_name = f'{source_name}--{what_slug}--{compact}'
        suffix = 2
        while row_name in taken:
            row_name = (f'{source_name}--{what_slug}--{compact}'
                        f'-{suffix}')
            suffix += 1
        row = SourceRetrieval(
            name=row_name, source_name=source_name,
            endpoint_name=endpoint_name, what=what,
            retrieved_at=stamp, retrieved_by=retrieved_by,
            retrieved_by_group=retrieved_by_group,
            row_count=int(row_count),
            provenance_url=provenance_url, notes=notes,
            manager=manager)
        if not any(existing is row for existing in table.values()):
            table[row_name] = row
    db = getattr(manager, 'db', None)
    persisted = True
    if db is not None:
        try:
            db.saveInstanceInDB(row)
        except Exception as exc:
            persisted = False
            print(f'[GovSource] retrieval save FAILED for '
                  f'{row_name}: {exc}', flush=True)
    result = {'ok': True, 'retrieval': _retrieval_dict(row)}
    if not persisted:
        result['persistWarning'] = ('the DB save FAILED — this '
                                    'attribution exists in memory '
                                    'only')
    return result
