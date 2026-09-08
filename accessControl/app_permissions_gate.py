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
        if mode == 'off':
            return True
        tables = getattr(manager, 'objectTables', None) or {}
        if 'AppPermissionProfile' not in tables:
            # polariapps absent/not admitted here — nothing to
            # resolve against; today's behavior, stated.
            if mode == 'advisory':
                response.set_header(ADVISORY_HEADER,
                                    'no-profile-table')
            return True
        try:
            from polariapps.apps_permissions_basis import (
                permission_verdict)
        except ImportError:
            if mode == 'advisory':
                response.set_header(ADVISORY_HEADER,
                                    'model-unimportable')
            return True
        user_info = getattr(getattr(request, 'context', None),
                            'user_info', None)
        verdict = permission_verdict(manager, user_info,
                                     class_name, verb)
        if verdict['allowed']:
            return True
        if mode == 'advisory':
            response.set_header(
                ADVISORY_HEADER,
                f'would-deny {class_name}:{verb}')
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
