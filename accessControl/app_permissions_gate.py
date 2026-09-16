"""
sep-7: the CRUDE-layer permission gate (separation plan decision 10
made enforceable). Core-resident so polariCRUDE can import it
unconditionally; the MODEL lives in polariapps.apps_permissions_basis and
is imported lazily — an instance without the polariapps module (or
without profile rows) degrades to today's behavior, stated.

THE KNOB (never auto-applied — knobs-and-suggestions discipline):
  POLARI_APP_PERMISSIONS = off       (default — no checks at all)
                         | advisory  (verdicts computed; would-deny
                                      rides a response header; never
                                      refuses)
                         | enforce   (disallowed verbs get 403 with
                                      the evidence-bearing verdict)

Sequencing honesty (plan sep-7): sep-0's clamp shipped
permission-BLIND; this gate makes the same acts permission-DRIVEN
without touching the clamp's rendering machinery. 'events' (STOMP)
is in the verb vocabulary but NOT enforced here — stated.
"""

import json
import os

MODE_ENV = 'POLARI_APP_PERMISSIONS'
MODES = ('off', 'advisory', 'enforce')
ADVISORY_HEADER = 'X-Polari-Permission-Advisory'


def gate_mode():
    mode = (os.environ.get(MODE_ENV, '') or 'off').strip().lower()
    return mode if mode in MODES else 'off'


def crude_permission_gate(manager, request, response, verb,
                          class_name):
    """True = proceed with the CRUDE act; False = refused (403
    already written). Never raises — a broken gate must not take
    the API down; failures degrade to proceed-with-header."""
    try:
        mode = gate_mode()
        # DEV MODE (his ask 2026-09-15): log which roles / profiles perform which acts — even with the gate off —
        # so app-level permission profiles can be WORKED OUT from evidence (/api/security/observations derives them)
        dev = False
        try:
            from moduleService.posture import is_dev
            dev = is_dev()
        except Exception:
            dev = False
        user_info = getattr(getattr(request, 'context', None),
                            'user_info', None)
        tables = getattr(manager, 'objectTables', None) or {}
        verdict_fn = None
        if 'AppPermissionProfile' in tables:
            try:
                from polariapps.apps_permissions_basis import (
                    permission_verdict as verdict_fn)
            except ImportError:
                verdict_fn = None
        if dev:
            try:
                from security.custom.security_observe import observe_permission
                observe_permission(manager, user_info, class_name, verb,
                                   verdict=(verdict_fn(manager, user_info, class_name, verb) if verdict_fn else None),
                                   roleplay=getattr(getattr(request, 'context', None), 'roleplay', '') or '')
            except Exception:
                pass
        if mode == 'off':
            return True
        if 'AppPermissionProfile' not in tables:
            # polariapps absent/not admitted here — nothing to
            # resolve against; today's behavior, stated.
            if mode == 'advisory':
                response.set_header(ADVISORY_HEADER,
                                    'no-profile-table')
            return True
        if verdict_fn is None:
            if mode == 'advisory':
                response.set_header(ADVISORY_HEADER,
                                    'model-unimportable')
            return True
        verdict = verdict_fn(manager, user_info, class_name, verb)
        if verdict['allowed']:
            return True
        if mode == 'advisory':
            response.set_header(
                ADVISORY_HEADER,
                f'would-deny {class_name}:{verb}')
            return True
        # enforce — unless this instance is a DEV BUILD (ISLE_HARDENING_PLAN §17): then
        # the act RUNS, the would-deny is recorded as a SecurityEvent and the notice bar
        # counts it. The decision is the security module's; the gate only asks.
        try:
            from security.custom.security_observe import decide
            who = ''
            if isinstance(user_info, dict):
                who = user_info.get('preferred_username') or user_info.get('sub') or ''
            proceed, outcome = decide(manager, 'authz', f'{verb} {class_name}', class_name,
                                      denied=True, reason=str(verdict.get('reason') or verdict.get('why') or 'permission refused')[:300],
                                      actor=who, source='crude permission gate')
        except Exception:
            proceed, outcome = False, 'denied'
        if proceed:
            response.set_header(ADVISORY_HEADER,
                                f'observed {class_name}:{verb} (dev build: production would deny)')
            return True
        response.status = '403 Forbidden'
        response.media = {'ok': False,
                          'error': 'permission refused',
                          'verdict': verdict,
                          'mode': mode}
        try:
            response.set_header('Powered-By', 'Polari')
        except Exception:
            pass
        return False
    except Exception as e:  # noqa: BLE001
        try:
            response.set_header(ADVISORY_HEADER,
                                f'gate-error {e.__class__.__name__}')
        except Exception:
            pass
        return True
