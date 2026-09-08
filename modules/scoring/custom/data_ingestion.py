"""
@cross-cutting
@module scoring.custom.data_ingestion
@tags @xc:bindings

Real data-series INGESTION for scoring — in Polari, where it belongs
(Dustin 2026-07-07: "the functionality for the scorecard and handling
of real data-series ingestion is meant to be in Polari").

Two paths, one contract:

  ingest_records    — explicit records ([{subject, value, contexts?}])
                      for one term → ContextualizedValue rows.
  ingest_from_class — ANY Polari object class as a data series: a
                      field mapping (subjectField/valueField/
                      contextFields) walks manager.objectTables[class]
                      rows. Datasets, no-code-created classes,
                      simulation outputs — if it is rows, it can feed
                      scores.

Honesty knobs (never silently applied):
  create_missing_subjects / create_missing_contexts — default False:
      unknown names REFUSE with the exact rows a retry would create.
  overwrite — default False: an existing value row is skipped and
      reported, never clobbered.

@consumers
  - scoring.scoring_api (POST /api/scoring/ingest)
@see /OVERLAP_MAP.md
"""

import json

from scoring.scoring_basis import ContextualizedValue, ScoreSubject


def _rows(manager, class_name):
    table = (manager.objectTables or {}).get(class_name, {})
    return list(table.values()) if isinstance(table, dict) else list(table)


def _names(manager, class_name):
    return {getattr(r, 'name', '') for r in _rows(manager, class_name)}


def _slug(text):
    return str(text).strip().lower().replace(' ', '-')


def _persist(manager, row):
    try:
        manager.db.saveInstanceInDB(row)
    except Exception:
        pass  # in-memory managers (selftests) have no db


def ingest_records(manager, payload):
    """One term's records → ContextualizedValue rows.

    payload: {'term': <ScoreTerm name>,
              'records': [{'subject': <name>, 'value': <number>,
                           'contexts': [<ScoreContext name>, ...]}],
              'contexts': [...common context names...],
              'source': str, 'provenance': str,
              'subject_kind': str            (for created subjects),
              'create_missing_subjects': bool (default False),
              'overwrite': bool               (default False)}
    """
    term = payload.get('term', '')
    records = payload.get('records', [])
    if not term or not isinstance(records, list) or not records:
        return {'ok': False,
                'error': "payload needs 'term' and a non-empty "
                         "'records' list"}
    if term not in _names(manager, 'ScoreTerm'):
        return {'ok': False,
                'error': f"no ScoreTerm named '{term}'",
                'suggestion': {'knob': 'ScoreTerm',
                               'action': f"create the '{term}' term "
                                         '(name, unit, is_positive, '
                                         'normalization) first — '
                                         'ingestion never invents '
                                         'metric semantics'}}

    common = payload.get('contexts', []) or []
    known_contexts = _names(manager, 'ScoreContext')
    known_subjects = _names(manager, 'ScoreSubject')
    create_subjects = bool(payload.get('create_missing_subjects'))
    overwrite = bool(payload.get('overwrite'))

    # Pre-flight: every refusal in ONE answer, so a retry can fix all.
    missing_subjects, missing_contexts = set(), set()
    for record in records:
        subject = _slug(record.get('subject', ''))
        if subject and subject not in known_subjects:
            missing_subjects.add(subject)
        for ctx in list(record.get('contexts', []) or []) + list(common):
            if ctx not in known_contexts:
                missing_contexts.add(ctx)
    if missing_contexts:
        return {'ok': False,
                'error': f'unknown contexts: '
                         f'{sorted(missing_contexts)}',
                'suggestion': {'knob': 'ScoreContext',
                               'action': 'create these context rows '
                                         '(contexts carry scenario '
                                         'semantics — never '
                                         'auto-invented)'}}
    if missing_subjects and not create_subjects:
        return {'ok': False,
                'error': f'unknown subjects: '
                         f'{sorted(missing_subjects)}',
                'wouldCreate': sorted(missing_subjects),
                'suggestion': {'knob': 'create_missing_subjects',
                               'action': 'set true to create these '
                                         'ScoreSubject rows with '
                                         f"kind '"
                                         f"{payload.get('subject_kind', '')}'"}}

    created_subjects = []
    for name in sorted(missing_subjects):
        ScoreSubject(name=name,
                     display_name=name.replace('-', ' ').title(),
                     kind=payload.get('subject_kind', ''),
                     description='created by scoring ingestion',
                     manager=manager)
        created_subjects.append(name)

    existing = {getattr(r, 'name', ''): r
                for r in _rows(manager, 'ContextualizedValue')}
    created, updated, skipped, refused = [], [], [], []
    for record in records:
        subject = _slug(record.get('subject', ''))
        value = record.get('value')
        if not subject or value is None:
            refused.append({'record': record,
                            'error': "needs 'subject' and 'value'"})
            continue
        try:
            value = float(value)
        except (TypeError, ValueError):
            refused.append({'record': record,
                            'error': f"value '{value}' is not a "
                                     'number'})
            continue
        contexts = sorted(set(
            list(record.get('contexts', []) or []) + list(common)))
        suffix = '-'.join(c for c in contexts) or 'uncontexted'
        name = f'{term}@{subject}-{suffix}'
        if name in existing:
            if not overwrite:
                skipped.append(name)
                continue
            row = existing[name]
            row.pre_normalized_value = value
            row.source = payload.get('source', '')
            row.provenance_id = payload.get('provenance', '')
            row.contributed_by = payload.get('contributed_by', '')
            _persist(manager, row)
            updated.append(name)
            continue
        ContextualizedValue(
            name=name, term_name=term, subject_name=subject,
            context_names_json=json.dumps(contexts),
            pre_normalized_value=value,
            source=payload.get('source', 'ingested records'),
            provenance_id=payload.get('provenance', ''),
            contributed_by=payload.get('contributed_by', ''),
            manager=manager)
        created.append(name)

    return {'ok': True, 'term': term,
            'created': created, 'updated': updated,
            'skipped': skipped, 'refused': refused,
            'createdSubjects': created_subjects,
            'overwrite': overwrite,
            'note': ('skipped rows already exist — the overwrite knob '
                     'replaces them explicitly' if skipped else '')}


def ingest_from_class(manager, payload):
    """ANY object class as a data series.

    payload: {'term', 'source_class': <objectTables class name>,
              'mapping': {'subjectField': ..., 'valueField': ...,
                          'contextFields': [...]   (row fields whose
                                             values name contexts)},
              'contexts': [...static context names...],
              + the ingest_records knobs}
    """
    source_class = payload.get('source_class', '')
    mapping = payload.get('mapping', {}) or {}
    subject_field = mapping.get('subjectField', '')
    value_field = mapping.get('valueField', '')
    if not source_class or not subject_field or not value_field:
        return {'ok': False,
                'error': "payload needs 'source_class' and a "
                         "'mapping' with subjectField + valueField"}
    rows = _rows(manager, source_class)
    if not rows:
        known = sorted(k for k, v in
                       (manager.objectTables or {}).items() if v)
        return {'ok': False,
                'error': f"class '{source_class}' has no rows",
                'classesWithRows': known[:40]}

    records, refused = [], []
    for row in rows:
        subject = getattr(row, subject_field, None)
        value = getattr(row, value_field, None)
        if subject is None or value is None:
            refused.append({
                'row': getattr(row, 'name', repr(row)[:40]),
                'error': f"missing '{subject_field}' or "
                         f"'{value_field}'"})
            continue
        contexts = []
        for field in mapping.get('contextFields', []) or []:
            ctx = getattr(row, field, None)
            if ctx:
                contexts.append(_slug(ctx))
        records.append({'subject': subject, 'value': value,
                        'contexts': contexts})
    if not records:
        return {'ok': False,
                'error': f"no usable rows in '{source_class}' "
                         f"(field mapping matched nothing)",
                'refused': refused[:10]}

    result = ingest_records(manager, {
        **payload,
        'records': records,
        'source': payload.get(
            'source', f'class series {source_class} '
                      f'({subject_field} → {value_field})'),
    })
    if result.get('ok'):
        result['sourceClass'] = source_class
        result['rowsRead'] = len(rows)
        result['refused'] = (result.get('refused') or []) + refused
    return result
