"""
accessControl.stomp_gate — SUBSCRIBE follows the CRUDE posture (ct-6).

His ruling, 2026-09-18 (design §10): *"STOMP should just follow from the CRUDE
security posture … they should be the same."* So:

  * the SAME verdict function the CRUDE gate calls
    (`polariapps.apps_permissions_basis.permission_verdict`) — never a second
    permission model;
  * the SAME verb: subscribing to `/topic/<Class>` is allowed exactly when
    **`read`** on that class is. The `events` verb stays in the vocabulary for
    compatibility and is DERIVED from `read`, not granted separately, so a
    profile that already says "this role may read MealEntry" does not need a
    second grant before that role may be told MealEntry changed;
  * the SAME knob and the same three answers —
    `POLARI_APP_PERMISSIONS = off | advisory | enforce`
    (`accessControl.app_permissions_gate.gate_mode()`), *advisory* being the
    deployed mode: security WARNS, it does not block (ISLE_HARDENING_PLAN §17);
  * the SAME admin bypass and the same anonymous answer — an anonymous socket
    is not special-cased here, it goes down the identical verdict path with no
    groups, which is what `permission_verdict` already answers for.

HOW A SUBSCRIBER IS TOLD (the mechanism question, answered with what the server
already has). A STOMP server can say three things to a client: MESSAGE, ERROR
and RECEIPT. This gate uses all three and invents nothing:

  * **advisory** → the subscription IS registered, and the client receives a
    `MESSAGE` frame on the very destination it just subscribed to, carrying
    `X-Polari-Permission-Advisory: would-deny <Class>:read` as a frame header
    and the evidence-bearing verdict as its JSON body, marked
    `"polariNotice": "permission-advisory"` so a client can tell it from a
    change notification. If the SUBSCRIBE asked for a `receipt`, the same
    advisory header ALSO rides the `RECEIPT` frame — which is the closest thing
    STOMP has to the HTTP response header the CRUDE gate sets.
  * **enforce** → an `ERROR` frame carrying the same header, the same verdict
    body, and `receipt-id` when one was asked for. The socket is NOT added to
    the topic.
  * **off** → nothing is computed, nothing is sent, exactly today's behavior.

This module is frame-SPEC only: it returns `{'command', 'headers', 'body'}`
dicts and lets `polariApiServer.stompWebSocketServer` serialize and send them.
That keeps asyncio and the websockets package out of accessControl, and lets
the selftest drive the whole decision with no socket at all.
"""

import json

from accessControl.app_permissions_gate import (
    ADVISORY_HEADER, AUTH_HEADER, AUTH_INVALID, gate_mode)

#: the CRUDE verb a subscription IS. `events` is derived from it (his ruling).
SUBSCRIBE_VERB = 'read'
#: the vocabulary verb a subscription is RECORDED as, for compatibility
EVENTS_VERB = 'events'
#: body marker so a client can tell a gate notice from a change notification
NOTICE_KEY = 'polariNotice'
NOTICE_ADVISORY = 'permission-advisory'
NOTICE_REFUSED = 'permission-refused'


def class_of_topic(topic):
    """`/topic/MealEntry` and `/topic/MealEntry/flatJson` are both the class
    `MealEntry`. Anything that is not a `/topic/...` destination has no class
    and is never gated (it is not a Polari change topic)."""
    raw = str(topic or '').strip()
    if not raw.startswith('/topic/'):
        return ''
    rest = raw[len('/topic/'):].strip('/')
    if not rest:
        return ''
    return rest.split('/', 1)[0]


def _verdict_fn(manager):
    """The ONE verdict implementation, resolved exactly as the CRUDE gate
    resolves it: only when the profile table is actually here."""
    tables = getattr(manager, 'objectTables', None) or {}
    if 'AppPermissionProfile' not in tables:
        return None, 'no-profile-table'
    try:
        from polariapps.apps_permissions_basis import permission_verdict
    except ImportError:
        return None, 'model-unimportable'
    return permission_verdict, ''


def subscribe_verdict(manager, user_info, class_name):
    """The admission verdict for ONE subscription, evidence-bearing.

    It is `permission_verdict(..., 'read')` — the same call, the same admin
    bypass, the same profile resolution as a CRUDE read — with the derivation
    stated on the dict so a reader of the evidence never wonders whether
    `events` was granted somewhere else. Returns None when there is no model to
    resolve against (no polariapps / no profile rows), which the caller reports
    rather than guessing at.
    """
    verdict_fn, _reason = _verdict_fn(manager)
    if verdict_fn is None:
        return None
    read = verdict_fn(manager, user_info, class_name, SUBSCRIBE_VERB)
    out = dict(read)
    out['verb'] = EVENTS_VERB
    out['derivedFrom'] = SUBSCRIBE_VERB
    out['why'] = ('%s — subscribing to /topic/%s is allowed exactly when '
                  '`read` on %s is; the `events` verb is derived from `read`, '
                  'not granted separately'
                  % (read.get('why') or '', class_name, class_name))
    return out


def _frame(command, headers, body=''):
    return {'command': command, 'headers': dict(headers), 'body': body}


def _notice_body(class_name, verdict, mode, connection):
    return json.dumps({
        NOTICE_KEY: (NOTICE_ADVISORY if mode == 'advisory'
                     else NOTICE_REFUSED),
        'className': class_name,
        'verb': EVENTS_VERB,
        'derivedFrom': SUBSCRIBE_VERB,
        'mode': mode,
        'authenticated': bool(getattr(connection, 'authenticated', False)),
        'verdict': verdict,
        'how': ('subscription follows the CRUDE posture: grant a published '
                'AppPermissionProfile whose app covers %s and whose verbs '
                'include `read`, to a Keycloak group this caller belongs to'
                % class_name),
    })


def gate_subscribe(manager, connection, class_name, receipt='', sub_id=''):
    """Decide ONE SUBSCRIBE. Never raises — a broken gate must not take the
    websocket server down; every failure degrades to allow-and-say-so.

    Returns::

        {'allowed': bool, 'mode': str, 'advisory': str,
         'verdict': dict | None, 'frames': [frame-spec, ...]}

    `frames` are spec dicts for the caller to serialize and send, in order.
    """
    mode = 'off'
    try:
        mode = gate_mode()
        if mode == 'off' or not class_name:
            return {'allowed': True, 'mode': mode, 'advisory': '',
                    'verdict': None,
                    'frames': ([_frame('RECEIPT', {'receipt-id': receipt})]
                               if receipt else [])}
        user_info = getattr(connection, 'user_info', None)
        verdict = subscribe_verdict(manager, user_info, class_name)
        if verdict is None:
            # polariapps absent / no profile rows here — nothing to resolve
            # against; today's behavior, stated (the CRUDE gate says the same).
            _fn, reason = _verdict_fn(manager)
            headers = {'receipt-id': receipt} if receipt else {}
            if mode == 'advisory':
                headers[ADVISORY_HEADER] = reason
            return {'allowed': True, 'mode': mode, 'advisory': reason,
                    'verdict': None,
                    'frames': [_frame('RECEIPT', headers)] if receipt else []}
        if verdict.get('allowed'):
            return {'allowed': True, 'mode': mode, 'advisory': '',
                    'verdict': verdict,
                    'frames': ([_frame('RECEIPT', {'receipt-id': receipt})]
                               if receipt else [])}

        # refused by the model. §51's distinction holds here too: no identity
        # at all is not a permission verdict, and an EXPIRED bearer is not the
        # same thing as never having sent one.
        unauthenticated = user_info is None
        auth_failed = bool(getattr(connection, 'auth_failed', False))
        if unauthenticated:
            verdict = dict(verdict)
            verdict['unauthenticated'] = True
            verdict['auth'] = AUTH_INVALID if auth_failed else 'no-token'
        advisory = (('unauthenticated %s:%s%s'
                     % (class_name, SUBSCRIBE_VERB,
                        ' (token invalid or expired)' if auth_failed else ''))
                    if unauthenticated else
                    'would-deny %s:%s' % (class_name, SUBSCRIBE_VERB))

        headers = {ADVISORY_HEADER: advisory}
        if auth_failed:
            headers[AUTH_HEADER] = AUTH_INVALID
        if mode == 'advisory':
            # WARN, never block (§17): the socket subscribes, and is told.
            notice = dict(headers)
            notice.update({'destination': '/topic/%s' % class_name,
                           'content-type': 'application/json',
                           'message-id': 'permission-advisory'})
            if sub_id:
                notice['subscription'] = sub_id
            frames = [_frame('MESSAGE', notice,
                             _notice_body(class_name, verdict, mode,
                                          connection))]
            if receipt:
                receipt_headers = dict(headers)
                receipt_headers['receipt-id'] = receipt
                frames.append(_frame('RECEIPT', receipt_headers))
            return {'allowed': True, 'mode': mode, 'advisory': advisory,
                    'verdict': verdict, 'frames': frames}

        # enforce
        error_headers = dict(headers)
        error_headers.update({
            'message': ('unauthenticated' if unauthenticated
                        else 'permission refused'),
            'destination': '/topic/%s' % class_name,
            'content-type': 'application/json'})
        if receipt:
            error_headers['receipt-id'] = receipt
        return {'allowed': False, 'mode': mode, 'advisory': advisory,
                'verdict': verdict,
                'frames': [_frame('ERROR', error_headers,
                                  _notice_body(class_name, verdict, mode,
                                               connection))]}
    except Exception as exc:      # noqa: BLE001 — a gate error never closes a socket
        return {'allowed': True, 'mode': mode,
                'advisory': 'gate-error %s' % exc.__class__.__name__,
                'verdict': None, 'frames': []}


# ---- the trace half (design §3: the subscribe seam of the causal map) -------

def record_subscribe(manager, connection, class_name):
    """ct-6's map edge: `endpoint:SUBSCRIBE /topic/<Class>` →
    `object:<Class>:read`, means `ws-subscribe` — the counterpart to ct-2's
    `ws-publish`, which deliberately left "who subscribes" to this slice.

    A complete no-op unless the security module is present, the posture is dev
    and a `TraceTarget` is armed on this class. Mints its OWN root cause: the
    STOMP server runs in its own thread and contextvars do not cross one
    (design §4), so there is no request chain here to inherit.

    Also counts the act as a `PermissionObservation` through the security
    module's existing public `observe_permission(...)`, under the vocabulary
    verb `events` — so the observations that DERIVE profiles include what a
    role subscribed to, not only what it read over HTTP.

    Never raises, and never returns anything a caller must handle.
    """
    if not class_name:
        return
    try:
        from moduleService.posture import is_dev
        if not is_dev():
            return
    except Exception:             # noqa: BLE001 — an unreadable posture is production
        return

    user_info = getattr(connection, 'user_info', None)
    try:
        groups = list(getattr(connection, 'groups', None) or [])
    except Exception:             # noqa: BLE001
        groups = []

    try:
        from security.custom.security_observe import actor_of, observe_permission
    except Exception:             # noqa: BLE001 — no security module: nothing to record into
        return

    try:
        observe_permission(manager, user_info, class_name, EVENTS_VERB,
                           verdict=subscribe_verdict(manager, user_info,
                                                     class_name))
    except Exception:             # noqa: BLE001
        pass

    try:
        from accessControl.cause_context import pop_cause, root_cause
        from security.custom.security_trace import record_edge, touch
    except Exception:             # noqa: BLE001
        return
    token = None
    try:
        token = root_cause('api', 'SUBSCRIBE /topic/%s' % class_name,
                           actor=actor_of(user_info), groups=tuple(groups))
        if touch(manager, class_name, SUBSCRIBE_VERB):
            record_edge(manager,
                        'endpoint:SUBSCRIBE /topic/%s' % class_name,
                        'object:%s:%s' % (class_name, SUBSCRIBE_VERB),
                        'ws-subscribe', detail=','.join(groups))
    except Exception:             # noqa: BLE001 — a recorder NEVER raises into the thing it observes
        pass
    finally:
        try:
            pop_cause(token)
        except Exception:         # noqa: BLE001
            pass
