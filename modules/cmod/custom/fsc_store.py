"""
@module cmod.custom.fsc_store

fsc-1: WRITE the term values down as scoring-module rows - no new class. For a Mission it upserts, by name:
  ScoreContext          `hardware:<board>` (type hardware) and `purpose:<name>` (type purpose)
  ScoreSubject          `msol:<mission>:<candidate id>` (kind mission-solution; object_ref -> the FirmwareSolution / FirmwareVariant row when a built config realises it, else the Mission)
  ContextualizedValue   `<term>@<subject>@<context>`: pre_normalized_value, source `fsc:<kind>[:<state>]` (kind = measured | estimated | cited | stand-in), notes = the BASIS in words
Which solutions are written: every finished one plus the best `limit` plans by solver rank (default 40, the number sol-0 lists); the doors score the whole set in memory either way.
Also `engine_tables()` builds the same rows as plain objects for scoring.custom.scoring_engine.score_concept (the proof that the stored values score in the stock engine).
"""
import json
from types import SimpleNamespace

from cmod.custom import fsc_terms as T
from cmod.custom import fsc_values as V

DEFAULT_LIMIT = 40


def chosen(built, limit=DEFAULT_LIMIT):
    recs = sorted(built['records'], key=lambda r: r['rank'])
    fin = [r for r in recs if r['state'] == 'finished']
    plans = [r for r in recs if r['state'] != 'finished'][:limit]
    return fin + plans


def context_rows(built, recs):
    boards = sorted({r['candidate']['hardware']['board'] for r in recs})
    rows = [{'name': 'hardware:%s' % b, 'display_name': 'Hardware %s' % b, 'context_type': 'hardware', 'value_json': json.dumps({'board': b}), 'parent_name': '',
             'notes': 'fsc-1: a whole-solution value on this board'} for b in boards]
    rows += [{'name': 'purpose:%s' % p['purpose'], 'display_name': 'Purpose %s' % p['title'], 'context_type': 'purpose',
              'value_json': json.dumps({'purpose': p['purpose'], 'mission': built['mission'], 'importance': p['importance']}), 'parent_name': '',
              'notes': 'fsc-1: one Purpose\'s share of a solution'} for p in built['ctx']['purposes']]
    return rows


def subject_rows(built, recs):
    rows = []
    for r in recs:
        link = r['link'] if r['state'] == 'finished' else None
        ref = ({'kind': 'objectRef', 'className': link['kind'], 'name': link['config']} if link else {'kind': 'objectRef', 'className': 'HardwareMission', 'name': built['mission']})
        rows.append({'name': r['name'], 'display_name': r['label'], 'kind': 'mission-solution', 'object_ref_json': json.dumps(ref),
                     'description': '%s: %s' % (r['state'], r['candidate']['routes_text']), 'notes': r['state_why']})
    return rows


def value_rows(recs):
    out = []
    for r in recs:
        out += V.to_rows(r['name'], r['candidate']['hardware']['board'], r['values'], r['purpose_values'], r['state'])
    return out


def all_rows(built, limit=DEFAULT_LIMIT):
    recs = chosen(built, limit)
    return {'ScoreContext': context_rows(built, recs), 'ScoreSubject': subject_rows(built, recs), 'ContextualizedValue': value_rows(recs)}


def write(manager, built, limit=DEFAULT_LIMIT):
    """Upsert the rows into a live manager. -> {class: count}. Existing rows of the same name are updated in place."""
    from scoring.scoring_basis import ContextualizedValue, ScoreContext, ScoreSubject
    classes = {'ScoreContext': ScoreContext, 'ScoreSubject': ScoreSubject, 'ContextualizedValue': ContextualizedValue}
    counts = {}
    db = getattr(manager, 'db', None)
    for cname, rows in all_rows(built, limit).items():
        table = (manager.objectTables or {}).setdefault(cname, {})
        have = {getattr(o, 'name', ''): o for o in table.values()}
        for f in rows:
            row = have.get(f['name'])
            if row is not None:
                for k, v in f.items():
                    setattr(row, k, v)
            else:
                row = classes[cname](manager=manager, **f)
            if db is not None and hasattr(db, 'saveInstanceInDB'):
                try:
                    db.saveInstanceInDB(row)
                except Exception:  # noqa: BLE001 - logged by the DB layer
                    pass
        counts[cname] = len(rows)
    return counts


def engine_tables(built, profile_rows, limit=None):
    """Plain-object tables in the shape scoring_engine.score_concept reads (objectTables), for the stock-engine equality proof."""
    rows = all_rows(built, limit or 10 ** 6)
    from cmod.custom import fsc_profiles as P
    tables = {'ScoreTerm': {r['name']: SimpleNamespace(**r) for r in T.term_rows()}, 'ScoreConcept': {r['name']: SimpleNamespace(**r) for r in profile_rows}}
    for cname in ('ScoreContext', 'ScoreSubject', 'ContextualizedValue'):
        tables[cname] = {r['name']: SimpleNamespace(**r) for r in rows[cname]}
    del P
    return SimpleNamespace(objectTables=tables)
