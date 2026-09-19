"""
op-0: the INSTANCE-level half of the permission gate — owner-defined permissions at the CRUDE layer.

`accessControl.app_permissions_gate.crude_permission_gate` runs BEFORE any instance is resolved, so it can only
ever answer "class × verb for these groups". This module runs AFTER resolution, in the same responders, and
answers "this caller, this ROW": own rows whole, other people's rows projected, rows they may not read at all
omitted from a list — never a 403 for a whole list because one row is private (design §3.4).

Core-resident so polariCRUDE can import it unconditionally; the MODEL lives in
`security.custom.security_owned` and is imported LAZILY — an instance without the security module (or with no
`OwnedClassPolicy` rows) degrades to exactly today's behaviour, stated. A class with no policy costs one dict
lookup and nothing else.

THE KNOB is the SAME answer as the class gate — `POLARI_APP_PERMISSIONS` = off | advisory | enforce, read
through `app_permissions_gate.gate_mode()`:

    off       nothing happens at all.
    advisory  the act still RUNS and the whole row is still returned; the response carries
                  X-Polari-Owner-Advisory: would-deny <Class>:<id>:<verb>
                  X-Polari-Owner-Advisory: would-project <Class>:<id>
              so a dev instance SHOWS what enforcement would hide, without hiding it (§17: dev warns, never
              blocks — the deployed mode).
    enforce   a refused verb is a 403 carrying the evidence dict; a projected read really is projected; an
              unreadable row really is omitted.

op-2 added the third of design §5's side channels here: a REFUSED WRITE is counted into the `SecurityEvent`
ledger, and its `target` is the CLASS NAME alone for an anonymised class (`security_owned.event_target`) — an
instance id beside a timestamp in a readable ledger is the third way to name the person, after the owner column
and the change broadcast. List READS are not ledgered: an omitted or projected row is not an act somebody took,
and a private list of a thousand rows would write a thousand events; the advisory header already says what
enforcement would have hidden, to the caller who asked.

Never raises: a broken owner gate must not take the API down. Every failure degrades to proceed-with-header,
exactly as the class gate does.
"""
from accessControl.app_permissions_gate import gate_mode

ADVISORY_HEADER = 'X-Polari-Owner-Advisory'
#: a header is not a log — say the first few and count the rest
MAX_ADVISORY_ITEMS = 12


def _model():
    """The owner model, or None when the security module is not on this instance."""
    try:
        from security.custom import security_owned
        return security_owned
    except Exception:                                   # noqa: BLE001
        return None


def _policy(manager, class_name):
    """(model, policy) — (None, None) when nothing owner-defined applies to this class."""
    if 'OwnedClassPolicy' not in (getattr(manager, 'objectTables', None) or {}):
        return None, None
    model = _model()
    if model is None:
        return None, None
    try:
        return model, model.policy_for(manager, class_name)
    except Exception:                                   # noqa: BLE001
        return None, None


def _user_info(request):
    return getattr(getattr(request, 'context', None), 'user_info', None)


def _advise(response, items):
    """Append to the advisory header (several rows in one response share it)."""
    if not items:
        return
    try:
        shown = items[:MAX_ADVISORY_ITEMS]
        text = '; '.join(shown)
        if len(items) > len(shown):
            text += '; +%d more' % (len(items) - len(shown))
        try:
            prior = (response.headers or {}).get(ADVISORY_HEADER) if hasattr(response, 'headers') else None
        except Exception:                               # noqa: BLE001
            prior = None
        response.set_header(ADVISORY_HEADER, ('%s; %s' % (prior, text)) if prior else text)
    except Exception:                                   # noqa: BLE001
        pass


def _event(manager, class_name, object_id, verb, verdict, mode):
    """op-2 (design §5, the third side channel): count a refused act into the SecurityEvent ledger.

    `target` comes from `security_owned.event_target`, which answers the CLASS NAME ALONE for an ANONYMISED
    class. An event row saying *`Ballot:b-7` was refused at 14:02* would be the third way to name a voter,
    after the owner column and the broadcast: an id plus a timestamp beside any "who was on the page" signal
    re-links them. The class and the verb are kept, which is what somebody reviewing the ledger acts on.

    Nothing about the caller's ACTOR is recorded here either: the refused act's actor is the person the owner
    rules are protecting a row FROM, not the row's owner, and the class-level permission ledger
    (`PermissionObservation`) already counts who performed which act. Never raises."""
    try:
        from security.custom.security_owned import event_target
        from security.custom.security_observe import record
        record(manager, 'authz', 'owner %s %s' % ('would-deny' if mode == 'advisory' else 'denied', verb),
               event_target(manager, class_name, object_id),
               reason=str(verdict.get('why', ''))[:400], outcome='observed' if mode == 'advisory' else 'denied',
               would_deny=True, source='accessControl.owner_gate')
    except Exception:                                   # noqa: BLE001 — a ledger failure must not break a request
        pass


def _refuse(response, verdict, class_name, object_id, verb):
    import falcon
    response.status = falcon.HTTP_403
    response.media = {'ok': False, 'error': 'owner-defined permission refused',
                      'why': verdict.get('why', ''), 'verdict': verdict,
                      'class': class_name, 'id': str(object_id or ''), 'verb': verb,
                      'mode': 'enforce'}
    try:
        response.set_header('Powered-By', 'Polari')
    except Exception:                                   # noqa: BLE001
        pass


# ---- READS: the list is filtered and projected, never refused wholesale -----------------------------------

def owner_gate_read(manager, request, response, class_name, instances, class_json):
    """Apply the owner rules to an already-serialised class payload.

    `instances` is the id -> live-object dict CRUDE resolved; `class_json` is what
    `manager.getJSONdictForClass` returned for them ([{'dataType': …, 'data': [ {…}, … ]}]). Returns the payload
    to send — unchanged whenever the class is not owned, the mode is off, or anything at all goes wrong."""
    try:
        if gate_mode() == 'off':
            return class_json
        model, policy = _policy(manager, class_name)
        if policy is None:
            return class_json
        if not isinstance(class_json, list) or not class_json:
            return class_json
        data = class_json[0].get('data') if isinstance(class_json[0], dict) else None
        if not isinstance(data, list):
            return class_json
        mode = gate_mode()
        user_info = _user_info(request)
        kept, notes = [], []
        for entry in data:
            if not isinstance(entry, dict):
                kept.append(entry)
                continue
            inst = (instances or {}).get(entry.get('id'))
            if inst is None:
                kept.append(entry)
                continue
            verdict = model.owner_verdict(manager, user_info, 'read', inst, policy=policy)
            ident = '%s:%s' % (class_name, entry.get('id'))
            if not verdict['allowed']:
                notes.append('would-deny %s:read' % ident)
                if mode == 'enforce':
                    continue                             # OMITTED, never a 403 for the whole list
                kept.append(entry)
                continue
            fields = verdict.get('projected_fields')
            if fields is None:
                kept.append(entry)
                continue
            notes.append('would-project %s' % ident)
            kept.append(model.project(entry, fields) if mode == 'enforce' else entry)
        if mode == 'advisory':
            _advise(response, notes)
        class_json[0]['data'] = kept
        return class_json
    except Exception as exc:                            # noqa: BLE001
        _advise(response, ['gate-error %s' % exc.__class__.__name__])
        return class_json


# ---- WRITES: update / delete on somebody else's instance ---------------------------------------------------

def owner_gate_write(manager, request, response, class_name, verb, instance):
    """True = proceed with the act; False = refused (403 already written). Advisory always proceeds."""
    try:
        mode = gate_mode()
        if mode == 'off' or instance is None:
            return True
        model, policy = _policy(manager, class_name)
        if policy is None:
            return True
        verdict = model.owner_verdict(manager, _user_info(request), verb, instance, policy=policy)
        if verdict['allowed']:
            return True
        object_id = getattr(instance, 'id', '') or getattr(instance, 'name', '')
        _event(manager, class_name, object_id, verb, verdict, mode)
        if mode == 'advisory':
            _advise(response, ['would-deny %s:%s:%s' % (class_name, object_id, verb)])
            return True
        _refuse(response, verdict, class_name, object_id, verb)
        return False
    except Exception as exc:                            # noqa: BLE001
        _advise(response, ['gate-error %s' % exc.__class__.__name__])
        return True


# ---- CREATE: the owner stamp -------------------------------------------------------------------------------

def _rollback(manager, class_name, instances):
    """Remove instances a refused create had already built. Never raises."""
    for inst in (instances or []):
        try:
            manager.deleteTreeNode(className=class_name, nodePolariId=getattr(inst, 'id', ''))
        except Exception:                               # noqa: BLE001
            try:
                (manager.objectTables.get(class_name) or {}).pop(getattr(inst, 'id', ''), None)
            except Exception:                           # noqa: BLE001
                pass



def owner_gate_stamp(manager, request, response, class_name, instances):
    """Stamp the owner on newly created instances of an owned class (design §2).

    Returns (ok, refusal): ok False only under `enforce`, when the class is owned and the request carried no
    identity — an instance with no owner has no owner-defined rule to apply. In `advisory` the create still
    happens, unstamped, and the header says what enforcement would have done."""
    try:
        if gate_mode() == 'off':
            return True, None
        model, policy = _policy(manager, class_name)
        if policy is None:
            return True, None
        mode = gate_mode()
        user_info = _user_info(request)
        notes = []
        for inst in (instances or []):
            outcome = model.stamp_owner(manager, inst, user_info)
            if outcome.get('stamped') or not outcome.get('refused'):
                if not outcome.get('stamped') and outcome.get('rule') == 'no-owner-column':
                    notes.append('no-owner-column %s (%s)' % (class_name, outcome.get('why', '')[:80]))
                continue
            if mode == 'advisory':
                notes.append('would-deny %s::create (anonymous create on an owned class)' % class_name)
                continue
            # enforce: the rows were built a moment ago by the create loop — take them back out of the tree,
            # or the refusal would leave exactly the ownerless instances it exists to prevent.
            _rollback(manager, class_name, instances)
            _advise(response, notes)
            import falcon
            response.status = falcon.HTTP_403
            response.media = {'ok': False, 'error': 'owner-defined permission refused',
                              'why': outcome.get('why', ''), 'verdict': outcome, 'class': class_name,
                              'verb': 'create', 'mode': mode}
            return False, outcome
        _advise(response, notes)
        return True, None
    except Exception as exc:                            # noqa: BLE001
        _advise(response, ['gate-error %s' % exc.__class__.__name__])
        return True, None
