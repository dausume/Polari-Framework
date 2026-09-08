"""
@module composition.custom.seed_upsert

arch-1 (PART_ARCHETYPES_PLAN): the upsert-changed-fields seed path.

Polari's historical seeding only INSERTS by name — it never diffs an
existing row against the current seed, so adding a property, changing
a value, or flipping a default silently fails to reach live rows.
That gotcha has now bitten ten separate times (see
seed-field-addition-gotcha; the workaround is a hand-built CRUDE PUT
per field per row after every deploy). Composition tables are the
first to ship with the fix designed in rather than worked around.

THE RULES (knobs ethos — seeds are priors, people's edits are not):

- A row missing from the table is CREATED from its seed.
- An existing row whose `is_prior` is EXPLICITLY False (or 0) is
  NEVER touched: the flag means a human customized it or a
  measurement replaced the prior, and a seed must not clobber
  either. Reported as `skipped_custom`, loudly. A row restored with
  is_prior=None predates the column (NULL backfill) — that is NOT a
  human's mark, so it counts as a prior; treating NULL as customized
  would silently exempt exactly the legacy rows this module exists
  to converge (caught live on PolariAppDefinition, nav-1).
- An existing prior row is DIFFED field-by-field against the seed
  dict; only fields present in the seed AND different on the row are
  written. Fields the seed does not mention survive untouched.
- Every outcome is reported: {inserted, updated (with the field
  names), unchanged, skipped_custom, errors}. Silence is the failure
  mode this module exists to end.

@consumers composition.composition_seed, polariServer seed passes
(adoptable by any module that wants its seeds to converge)
"""


def diff_fields(row, seed, skip=('name',)):
    """Fields present in `seed`, absent from `skip`, whose value
    differs from the row's current attribute. Missing attributes
    count as different (that is exactly the new-field case the
    gotcha is about)."""
    _MISSING = object()
    changed = []
    for field, want in seed.items():
        if field in skip or field == 'manager':
            continue
        have = getattr(row, field, _MISSING)
        if have is _MISSING or have != want:
            changed.append(field)
    return changed


def upsert_seed_rows(manager, class_name, cls, seed_list,
                     tag='SeedUpsert'):
    """Converge the live `class_name` table toward `seed_list`.

    Returns a report dict; never raises for a single bad row — the
    row lands in `errors` and the rest of the seed still converges.
    """
    report = {'class': class_name, 'inserted': [], 'updated': [],
              'unchanged': [], 'skipped_custom': [], 'errors': []}
    existing = manager.objectTables.get(class_name, {}) or {}
    by_name = {getattr(o, 'name', None): o for o in existing.values()}
    for seed in seed_list:
        name = seed.get('name')
        row = by_name.get(name)
        if row is None:
            try:
                cls(**seed, manager=manager)
                report['inserted'].append(name)
                print(f'[{tag}] {class_name} "{name}" created',
                      flush=True)
            except Exception as e:
                report['errors'].append({'name': name, 'op': 'insert',
                                         'error': str(e)})
                print(f'[{tag}] {class_name} "{name}" INSERT FAILED: '
                      f'{e}', flush=True)
            continue
        prior_flag = getattr(row, 'is_prior', True)
        if prior_flag is not None and not prior_flag:
            report['skipped_custom'].append(name)
            print(f'[{tag}] {class_name} "{name}" is_prior=False — '
                  f'customized/measured, seed will not touch it',
                  flush=True)
            continue
        changed = diff_fields(row, seed)
        if not changed:
            report['unchanged'].append(name)
            continue
        try:
            for field in changed:
                setattr(row, field, seed[field])
            db = getattr(manager, 'db', None)
            if db is not None:
                db.saveInstanceInDB(row)
            report['updated'].append({'name': name, 'fields': changed})
            print(f'[{tag}] {class_name} "{name}" updated: '
                  f'{", ".join(changed)}', flush=True)
        except Exception as e:
            report['errors'].append({'name': name, 'op': 'update',
                                     'error': str(e)})
            print(f'[{tag}] {class_name} "{name}" UPDATE FAILED: {e}',
                  flush=True)
    return report


def upsert_seed_pairs(manager, pairs, tag='SeedUpsert'):
    """Run upsert_seed_rows over (class_name, cls, seed_list) tuples,
    skipping classes absent from objectTypingDict (not booted /
    gated off) — skipped loudly, mirroring the core seed passes."""
    reports = []
    typing = getattr(manager, 'objectTypingDict', None)
    for class_name, cls, seed_list in pairs:
        if typing is not None and class_name not in typing:
            print(f'[{tag}] {class_name} not in objectTypingDict — '
                  f'skipping (module gated off?)', flush=True)
            reports.append({'class': class_name, 'skipped': True})
            continue
        reports.append(
            upsert_seed_rows(manager, class_name, cls, seed_list,
                             tag=tag))
    return reports
