"""
security.custom.security_owned_manifest — the `app.owned` stanza, converged into policy rows (op-4).

Design: AI-Notes/designs/OWNER_DEFINED_PERMISSIONS_DESIGN.md §7. *"validated by `moduleService.manifests` like
`app.roles`, converged into `OwnedClassPolicy` rows on every read exactly as `app.roles` becomes
`RoleAppBinding`, and **never overwriting a policy an administrator set**."*

    declarations()                  -> [{'module', 'entry'}] — every module's app.owned entries, in module order
    ensure_policies(manager)        -> {'created', 'updated', 'kept', 'conflicts'} — the convergence, idempotent
    start_owned_converge(manager, polServer) -> the boot-time run, after the rows are restored

WHICH SOURCE WINS, and why (this is the question op-0's seed left open). A policy row carries `source`:

    source = 'manifest'   the module said so. RE-DERIVED on every read of the owner doors, so editing a
                          manifest reaches a running instance without anybody acting — exactly what
                          `ensure_bindings` does for `RoleAppBinding` (§57).
           = 'admin'      a person POSTed it to `/api/security/owned/<Class>`. NEVER overwritten. A deployment
                          that has decided something about its own data outranks the app that shipped it.
           = ''           an op-0 seed row, written before this file existed. Treated as re-derivable, because
                          the seed IS this derivation's earlier spelling: `UserAppPreference` was seeded by
                          `security_seed` and is now DECLARED by `polariapps`, the module that owns the class.
                          One source of truth, and it is the module that owns the class — a policy is a
                          statement about a class, and the module defining the class is the only place that
                          statement can be kept beside the thing it describes.

So `SEED_OWNED_CLASS_POLICIES` is now empty and `polariapps/polari-app.json` carries the declaration. On an
instance that already has the seeded row, the first read converges it in place (same content, `source` set to
`manifest`), and on a fresh one the row appears at boot with nobody touching an admin door. If an
administrator later POSTs that class, their row stops being re-derived and the manifest becomes a suggestion
the answer names as a CONFLICT rather than silently applying.
"""
from security.custom.security_observe import _schedule_persist

#: the manifest keys that map straight onto `set_policy`'s field names
_PASS_THROUGH = ('enabled', 'owner_verbs', 'others_verbs', 'others_fields', 'owner_visible', 'owner_may_grant',
                 'grantable_verbs', 'grantee_kinds', 'transfer', 'anonymised', 'owner_field', 'notes')


def _manifests():
    from moduleService import manifests as M
    return M.all_manifests()


def declarations():
    """Every `app.owned` entry on this instance, with the module that declared it.

    A class declared by two modules is a real conflict — two apps claiming the same rows — and it is REPORTED
    rather than resolved by import order: the first declaration wins and the second is named."""
    out, seen = [], {}
    for pkg, manifest in sorted((_manifests() or {}).items()):
        entries = ((manifest or {}).get('app') or {}).get('owned')
        if not isinstance(entries, list):
            continue
        for entry in entries:
            if not isinstance(entry, dict):
                continue
            cls = str(entry.get('class') or '').strip()
            if not cls:
                continue
            if cls in seen:
                out.append({'module': pkg, 'entry': entry, 'class': cls, 'duplicate_of': seen[cls]})
                continue
            seen[cls] = pkg
            out.append({'module': pkg, 'entry': entry, 'class': cls, 'duplicate_of': ''})
    return out


def _fields_of(entry):
    """The manifest entry as `set_policy` wants it — every key it does not carry left at the row's default."""
    fields = {'enabled': True}
    for key in _PASS_THROUGH:
        if key in entry:
            fields[key] = entry[key]
    frozen = entry.get('frozen_when')
    if isinstance(frozen, dict):
        import json
        fields['frozen_when'] = json.dumps(frozen, sort_keys=True)
    elif isinstance(frozen, str):
        fields['frozen_when'] = frozen
    return fields


def _same(row, fields, derived_from):
    """Is the stored row already what the manifest says? (Avoids a write — and a persist — on every read.)"""
    import json
    if str(getattr(row, 'derived_from', '') or '') != derived_from:
        return False
    for key, column in (('owner_verbs', 'owner_verbs_json'), ('others_verbs', 'others_verbs_json'),
                        ('others_fields', 'others_fields_json'), ('grantable_verbs', 'grantable_verbs_json'),
                        ('grantee_kinds', 'grantee_kinds_json')):
        want = [str(v) for v in (fields.get(key) or ([] if key != 'owner_verbs' else ['read', 'update', 'delete']))]
        try:
            have = [str(v) for v in json.loads(getattr(row, column, '[]') or '[]')]
        except (ValueError, TypeError):
            return False
        if have != want:
            return False
    for key, default in (('enabled', True), ('owner_visible', False), ('owner_may_grant', False),
                         ('anonymised', False)):
        if bool(getattr(row, key, default)) != bool(fields.get(key, default)):
            return False
    for key, default in (('frozen_when', ''), ('transfer', 'nobody'), ('owner_field', 'owner'), ('notes', '')):
        if str(getattr(row, key, default) or default) != str(fields.get(key, default) or default):
            return False
    return True


def ensure_policies(manager, save=True):
    """Converge `app.owned` into `OwnedClassPolicy` rows. Idempotent, cheap, and never raises.

    Returns {'created', 'updated', 'kept', 'conflicts', 'duplicates'} — evidence the doors and the selftest
    print, in the shape `ensure_bindings` uses (§57)."""
    report = {'created': [], 'updated': [], 'kept': [], 'conflicts': [], 'duplicates': []}
    if getattr(manager, 'objectTables', None) is None:
        return report
    from security.custom.security_owned import _rows, set_policy
    existing = {str(getattr(r, 'class_name', '') or getattr(r, 'name', '')): r
                for r in _rows(manager, 'OwnedClassPolicy')}
    wrote = False
    for decl in declarations():
        cls, module, entry = decl['class'], decl['module'], decl['entry']
        if decl['duplicate_of']:
            report['duplicates'].append({'class': cls, 'declared_by': module, 'kept_from': decl['duplicate_of']})
            continue
        row = existing.get(cls)
        if row is not None and str(getattr(row, 'source', '') or '') == 'admin':
            report['conflicts'].append({
                'class': cls, 'declared_by': module,
                'why': ('an administrator set this policy through POST /api/security/owned/%s, so the '
                        'manifest declaration is a SUGGESTION here, not the rule. A person\'s decision '
                        'outranks a derivation (the RoleAppBinding discipline).' % cls)})
            report['kept'].append(cls)
            continue
        fields = _fields_of(entry)
        if row is not None and _same(row, fields, module):
            report['kept'].append(cls)
            continue
        result = set_policy(manager, cls, fields, by='', source='manifest', derived_from=module)
        if not result.get('ok'):
            report['conflicts'].append({'class': cls, 'declared_by': module,
                                        'why': 'the declaration was refused: %s' % result.get('refusal', '')})
            continue
        (report['updated'] if row is not None else report['created']).append(cls)
        wrote = True
    if wrote and save:
        _schedule_persist(manager)
    return report


def summary(manager):
    """What `GET /api/security/owned` says about the manifest half — the declarations and the last convergence."""
    decls = declarations()
    return {
        'declared': [{'module': d['module'], 'class': d['class'],
                      'duplicate_of': d['duplicate_of']} for d in decls],
        'converge': ensure_policies(manager),
        'how': ('a module declares its owned classes in `app.owned` (polari-app.json) and the policy rows are '
                're-derived from it on every read of this door — the same discipline `app.roles` follows into '
                'RoleAppBinding. A policy an ADMINISTRATOR set (source `admin`) is never overwritten; the '
                'manifest declaration is then listed as a conflict rather than applied.'),
    }


def start_owned_converge(manager, polServer=None, wait_s=300, rows_wait_s=120, tick=2.0):
    """Run `ensure_policies` once, AFTER the tree's rows are restored — the same reasoning, and the same shape,
    as `security_page.start_page_converge`: the endpoint constructor runs while falcon's routes are built, long
    before lazy boot's Phase B restores `OwnedClassPolicy`, so converging inline would walk an empty table and
    create a second row for a policy that already exists. Daemon thread, never raises into the boot."""
    import threading
    import time

    def _rows_present():
        return len((getattr(manager, 'objectTables', None) or {}).get('OwnedClassPolicy', {}) or {})

    def _run():
        start = time.time()
        while time.time() - start < wait_s:
            registry = getattr(polServer, 'bootRegistry', None)
            try:
                pending = bool(registry.is_data_pending('security')) if registry is not None else False
            except Exception:                           # noqa: BLE001
                pending = False
            if not pending and (_rows_present() or time.time() - start >= rows_wait_s):
                break
            time.sleep(tick)
        try:
            r = ensure_policies(manager)
            if r['created'] or r['updated'] or r['conflicts']:
                print('[OwnedPolicyConverge] app.owned: +%d ~%d =%d, %d conflict(s)'
                      % (len(r['created']), len(r['updated']), len(r['kept']), len(r['conflicts'])), flush=True)
        except Exception as exc:                        # noqa: BLE001
            print('[OwnedPolicyConverge] failed: %s' % exc, flush=True)

    t = threading.Thread(target=_run, name='security-owned-converge', daemon=True)
    t.start()
    return t
