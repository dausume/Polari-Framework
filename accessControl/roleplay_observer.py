"""
accessControl.roleplay_observer — the ROLE-PLAY header and the endpoint ledger (his ask 2026-09-16).

While a person role-plays a group in dev mode the frontend sends `X-Polari-Roleplay: <role>` on every request. This
middleware plumbs it onto `req.context.roleplay` (the CRUDE gate attributes its observations to the role) and, once
the response is out, counts the ENDPOINT the role used (method + route template) as a UsageObservation — the
"functionality" half of the picture, beside the objects (PermissionObservation) and the frontend's apps/pages/actions.
Only when the instance is in dev posture AND recording is on; never raises; never touches the response.
"""

ROLEPLAY_HEADER = 'X-Polari-Roleplay'


def roleplay_of(req):
    try:
        v = (req.get_header(ROLEPLAY_HEADER) or '').strip().lower()
    except Exception:
        v = ''
    return v[:64]


class RoleplayObserverMiddleware:
    def __init__(self, server=None):
        self.server = server

    def process_request(self, req, resp):
        try:
            req.context.roleplay = roleplay_of(req)
        except Exception:
            pass

    def process_response(self, req, resp, resource, req_succeeded):
        try:
            role = getattr(req.context, 'roleplay', '') or ''
            if not role:
                return
            path = getattr(req, 'uri_template', None) or req.path
            if path.startswith('/api/security/observe'):
                return          # the recording doors themselves are not "functionality used"
            from security.custom.security_observe import recording_on, observe_usage
            manager = getattr(self.server, 'manager', None)
            if manager is None or not recording_on(manager):
                return
            user_info = getattr(req.context, 'user_info', None)
            actor = (user_info or {}).get('preferred_username') or (user_info or {}).get('sub') or '' if isinstance(user_info, dict) else ''
            observe_usage(manager, role, 'endpoint', f'{req.method} {path}', actor=actor, detail=str(getattr(resp, 'status', ''))[:12])
        except Exception:
            pass
