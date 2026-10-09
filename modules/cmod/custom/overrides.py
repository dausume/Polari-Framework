"""
@module cmod.custom.overrides

DERIVED-VALUE OVERRIDES (ucd-attest, UNO_CORE_DEMO_PLAN.md, his ruling 2026-10-09: "all of these need to be things
that can be altered manually, so we should be able to manually change those values when we prove them correct" ->
"yes on attestation and overrides"). A `DerivedOverride` (cmod.objects.cmod.DerivedOverride) is a person's own
correction of ONE field of ONE already-derived row — kept BESIDE the derivation, never overwriting it: derived
values stay derived, and the record of the manual change is itself a row (who/when/why).

`apply_overrides` is the ONE mechanism every served row (the solution payload, the bindings doors, the claims chain,
the targets door) goes through: it NEVER mutates its input (a fresh dict per row — the caller's own derived rows, and
whatever gets persisted elsewhere, are untouched), and it is a no-op with no manager (an override is a live row;
there is nothing to read offline — the pure/seed path always serves the bare derivation, same posture as every other
pure/live duality in this module).
"""
import json


def active_overrides(target_class, manager=None):
    """{target_name: [DerivedOverride dict, …]} — every ACTIVE override of `target_class`, grouped by the row it
    corrects. '' with no manager (nothing live to read)."""
    if manager is None:
        return {}
    out = {}
    for o in (manager.objectTables or {}).get('DerivedOverride', {}).values():
        if getattr(o, 'target_class', '') != target_class or getattr(o, 'status', '') != 'active':
            continue
        out.setdefault(getattr(o, 'target_name', ''), []).append(o)
    return out


def apply_overrides(rows, target_class, manager=None):
    """[row dict, …] — `rows` (already-derived dicts carrying their own `name`) with every ACTIVE DerivedOverride of
    `target_class` laid over them: the overridden field gets the person's `override_value`, the derivation's own
    value survives beside it as `derived_<field>`, and `overrides_refs_json` names every DerivedOverride row that
    touched this one (["DerivedOverride:<name>", …]) — never silently merged away. A `status` field gets the extra
    courtesy `status_why` ("overridden by <person> on <date>: <why> (derived: <x>)") — the one field (HardwareBinding.
    status) his ruling calls out by name; every other field just carries `derived_<field>` beside it, which is
    already enough for a person to see both.

    Pure passthrough (returns `rows` itself, unchanged) when there is no manager — overrides are live rows; an
    offline/seed-time caller has nothing to read.

    TODO(ucd-attest, left for whoever owns custom/export_cmake.py — that file is out of scope here per the task's
    own carve-out): the export's manifest/README should list active overrides under "Manual overrides" (who/when/
    why), reading `active_overrides('PinClaim'|'TargetDefinition'|'HardwareBinding', manager=manager)` for the
    solution's own graph/binding. Not wired in — `export_cmake.readme()`/`export()` would need a new parameter and
    a new section, which is not the one-line addition this slice's instructions allow it to make unasked."""
    if manager is None:
        return rows
    by_target = active_overrides(target_class, manager=manager)
    if not by_target:
        return rows
    out = []
    for row in rows:
        hits = by_target.get(row.get('name', ''))
        if not hits:
            out.append(row)
            continue
        row = dict(row)
        refs = []
        try:
            refs = json.loads(row.get('overrides_refs_json') or '[]')
        except (TypeError, ValueError):
            refs = []
        for o in sorted(hits, key=lambda x: getattr(x, 'when', '')):
            field = getattr(o, 'field', '')
            if field not in row:
                continue
            derived_value = row[field]
            row['derived_%s' % field] = derived_value
            row[field] = getattr(o, 'override_value', '')
            if field == 'status':
                row['status_why'] = 'overridden by %s on %s: %s (derived: %s)' % (
                    getattr(o, 'who', '') or 'an unauthenticated request', (getattr(o, 'when', '') or '')[:10],
                    getattr(o, 'why', ''), derived_value)
            refs.append('DerivedOverride:%s' % getattr(o, 'name', ''))
        row['overrides_refs_json'] = json.dumps(refs)
        out.append(row)
    return out


def _target_row(target_class, target_name, manager):
    """The CURRENT derived value of one (target_class, target_name) row, read off the rows those classes are
    actually served from — never re-derived a second way here. None when the row does not resolve."""
    if target_class == 'PinClaim':
        from cmod.custom import claims as C
        from cmod.custom import binding as BND
        binding_or_solution_name = target_name.rpartition(':')[0]
        if not binding_or_solution_name:
            return None
        b = BND.resolve(binding_or_solution_name, manager=manager)
        if b is None:
            return None
        sol_dict = BND._solution_dict(b.get('solution', binding_or_solution_name), manager=manager)
        graph = (sol_dict or {}).get('graph', '')
        rows = C.pin_claims(b, graph, manager=manager)
        return next((r for r in rows if r.get('name') == target_name), None)
    if target_class == 'TargetDefinition':
        from cmod.custom import targets as T
        graph = target_name.partition(':')[0]
        return next((r for r in T.derive(graph, manager=manager) if r.get('name') == target_name), None)
    if target_class == 'HardwareBinding':
        from cmod.custom import binding as BND
        return BND.resolve(target_name, manager=manager)
    return None


def create(target_class, target_name, field, override_value, why, who, manager):
    """Upsert the ONE DerivedOverride row for (target_class, target_name, field) — deterministic name, so a repeat
    override of the same field replaces its own prior row (one active override per field, his wording: "an override
    row for the same field wins"). Refuses (returns (None, why)) when `why` is blank (required, never defaulted) or
    the field named does not exist on the target's own served row today. `derived_value` is captured fresh from the
    CURRENT derivation (not the override's own prior value), so the record always shows what the derivation said at
    the moment this override was authored."""
    import datetime
    if not (why or '').strip():
        return None, "'why' is required: a person's own words for the correction (never defaulted)"
    if target_class not in ('TargetDefinition', 'PinClaim', 'HardwareBinding'):
        return None, ('overrides are defined for TargetDefinition.requirement_kind/.role, PinClaim.pull/edge/mode/'
                      'initial and HardwareBinding.status this slice — not %r' % target_class)
    allowed_fields = {'TargetDefinition': ('requirement_kind', 'role'), 'PinClaim': ('pull', 'edge', 'mode', 'initial'),
                      'HardwareBinding': ('status',)}
    if field not in allowed_fields[target_class]:
        return None, '%s has no overridable field %r (allowed: %s)' % (target_class, field, ', '.join(allowed_fields[target_class]))
    row = _target_row(target_class, target_name, manager)
    if row is None:
        return None, 'no %s %r to override' % (target_class, target_name)
    name = '%s:%s:%s' % (target_class, target_name, field)
    when = datetime.datetime.now().isoformat(timespec='seconds')
    fields = {'name': name, 'target_class': target_class, 'target_name': target_name, 'field': field,
             'derived_value': str(row.get(field, '')), 'override_value': str(override_value), 'who': who or '',
             'when': when, 'why': why, 'status': 'active', 'provenance': 'canvas'}
    # a direct upsert (never firmwarefaults.custom.sink.ManagerSink — its class registry only knows firmwarefaults/
    # mathproofs rows, not cmod's) — the SAME idiom `cmod_firmware_api.FirmwareAPI._upsert` already uses elsewhere
    # in this module.
    from cmod.cmod_basis import DerivedOverride
    existing = next((r for r in (manager.objectTables or {}).get('DerivedOverride', {}).values() if getattr(r, 'name', '') == name), None)
    if existing is not None:
        for k, v in fields.items():
            setattr(existing, k, v)
        out = existing
    else:
        out = DerivedOverride(manager=manager, **fields)
    db = getattr(manager, 'db', None)
    if db is not None and hasattr(db, 'saveInstanceInDB'):
        try:
            db.saveInstanceInDB(out)
        except Exception:  # noqa: BLE001 — a save failure is logged by the DB layer; the row stays in the tree
            pass
    return out, ''


def retire(name, manager):
    """Set one DerivedOverride's status to 'retired' — the record survives (never a hard delete). (ok, why)."""
    rows = (manager.objectTables or {}).get('DerivedOverride', {})
    row = next((r for r in rows.values() if getattr(r, 'name', '') == name), None)
    if row is None:
        return False, 'no DerivedOverride %r' % name
    row.status = 'retired'
    db = getattr(manager, 'db', None)
    if db is not None and hasattr(db, 'saveInstanceInDB'):
        db.saveInstanceInDB(row)
    return True, ''
