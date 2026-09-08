"""
@cross-cutting
@module scoring.authority_api
@tags @xc:bindings @xc:accessControl

HTTP surface for scoring.group_authority_basis. Self-registering treeObject
(ScoringAPI pattern). Identity: every handler prefers the
Keycloak-verified principal placed on request.context by
AuthContextMiddleware; payload-supplied subjects are accepted as
fallback and stamped identity_source='payload-unverified' so the
verdict is honest about what was checked. The PSC backend forwards
the citizen's bearer token on its server-to-server calls, so the same
principal is verified independently on both sides.

@consumers
  - polariServer (instantiated beside ScoringAPI)
  - PSC backend PolariAuthorityService
@see /GROUP_AUTHORITY_PLAN.md
"""

import json

from objectTreeDecorators import treeObject, treeObjectInit


def _principal(request):
    """The Keycloak-verified principal, or None (middleware is
    lenient — anonymous/dev requests carry no user_info)."""
    info = getattr(request.context, 'user_info', None)
    if not info:
        return None
    return {'subject': info.get('sub', ''),
            'username': info.get('username', ''),
            'identity_source': 'keycloak-verified'}


def _identity(request, payload, subject_key, username_key):
    """Resolve (subject, username, identity_source): the verified
    principal always overrides payload-supplied identity."""
    principal = _principal(request)
    if principal is not None and principal['subject']:
        return (principal['subject'], principal['username'],
                'keycloak-verified')
    return (payload.get(subject_key, ''),
            payload.get(username_key, ''), 'payload-unverified')


class AuthorityAPI(treeObject):
    """Group/instance authority + term-availability endpoints."""

    @treeObjectInit
    def __init__(self, polServer):
        self.polServer = polServer
        self.apiName = '/api/scoring/authority'
        if polServer is not None:
            polServer.falconServer.add_route(
                '/api/scoring/authority/groups/grant', self,
                suffix='group_grant')
            polServer.falconServer.add_route(
                '/api/scoring/authority/groups/revoke', self,
                suffix='group_revoke')
            polServer.falconServer.add_route(
                '/api/scoring/authority/instances/grant', self,
                suffix='instance_grant')
            polServer.falconServer.add_route(
                '/api/scoring/authority/instances/revoke', self,
                suffix='instance_revoke')
            polServer.falconServer.add_route(
                '/api/scoring/authority/report', self,
                suffix='report')
            polServer.falconServer.add_route(
                '/api/scoring/authority/check', self,
                suffix='check')
            polServer.falconServer.add_route(
                '/api/scoring/authority/bindings/propose', self,
                suffix='binding_propose')
            polServer.falconServer.add_route(
                '/api/scoring/authority/bindings/{name}/'
                'confirm-remote', self,
                suffix='binding_confirm_remote')
            polServer.falconServer.add_route(
                '/api/scoring/authority/bindings/{name}/revoke',
                self, suffix='binding_revoke')
            polServer.falconServer.add_route(
                '/api/scoring/signals/term-availability', self,
                suffix='term_signals')
            polServer.falconServer.add_route(
                '/api/scoring/signals/term-availability/{name}',
                self, suffix='term_signal')

    def _payload(self, request, response):
        try:
            return json.load(request.bounded_stream)
        except Exception as e:
            response.status = '400 Bad Request'
            response.media = {'ok': False,
                              'error': f'bad JSON payload: {e}'}
            return None

    def on_post_group_grant(self, request, response):
        from scoring.group_authority_basis import grant_group_authority
        payload = self._payload(request, response)
        if payload is None:
            return
        granter_subject, granter_username, identity_source = \
            _identity(request, payload, 'granter_subject',
                      'granter_username')
        result = grant_group_authority(
            self.manager, payload.get('group_name', ''),
            payload.get('subject', ''),
            username=payload.get('username', ''),
            role=payload.get('role', 'shared'),
            granter_subject=granter_subject,
            granter_username=granter_username,
            identity_source=identity_source,
            notes=payload.get('notes', ''))
        if not result.get('ok'):
            response.status = '422 Unprocessable Entity'
        response.media = result

    def on_post_group_revoke(self, request, response):
        from scoring.group_authority_basis import revoke_group_authority
        payload = self._payload(request, response)
        if payload is None:
            return
        revoker_subject, _, _ = _identity(
            request, payload, 'revoker_subject', 'revoker_username')
        result = revoke_group_authority(
            self.manager, payload.get('group_name', ''),
            payload.get('subject', ''), revoker_subject)
        if not result.get('ok'):
            response.status = '422 Unprocessable Entity'
        response.media = result

    def on_post_instance_grant(self, request, response):
        from scoring.group_authority_basis import grant_instance_authority
        payload = self._payload(request, response)
        if payload is None:
            return
        granter_subject, granter_username, identity_source = \
            _identity(request, payload, 'granter_subject',
                      'granter_username')
        result = grant_instance_authority(
            self.manager,
            instance_name=payload.get('instance_name', ''),
            subject=payload.get('subject', ''),
            username=payload.get('username', ''),
            role=payload.get('role', 'shared'),
            granter_subject=granter_subject,
            granter_username=granter_username,
            identity_source=identity_source,
            notes=payload.get('notes', ''))
        if not result.get('ok'):
            response.status = '422 Unprocessable Entity'
        response.media = result

    def on_post_instance_revoke(self, request, response):
        from scoring.group_authority_basis import revoke_instance_authority
        payload = self._payload(request, response)
        if payload is None:
            return
        revoker_subject, _, _ = _identity(
            request, payload, 'revoker_subject', 'revoker_username')
        result = revoke_instance_authority(
            self.manager, payload.get('instance_name', ''),
            payload.get('subject', ''), revoker_subject)
        if not result.get('ok'):
            response.status = '422 Unprocessable Entity'
        response.media = result

    def on_get_report(self, request, response):
        from scoring.group_authority_basis import authority_report
        response.media = authority_report(
            self.manager,
            group_name=request.get_param('group') or '',
            instance_name=request.get_param('instance') or '',
            subject=request.get_param('subject') or '')

    def on_get_check(self, request, response):
        from scoring.group_authority_basis import authority_check
        principal = _principal(request)
        subject = ((principal or {}).get('subject')
                   or request.get_param('subject') or '')
        if not subject:
            response.status = '400 Bad Request'
            response.media = {'ok': False,
                              'error': 'no verified principal and no '
                                       "'subject' query param"}
            return
        result = authority_check(
            self.manager, subject,
            request.get_param('group') or '',
            request.get_param('instance') or '')
        result['identitySource'] = ('keycloak-verified' if principal
                                    else 'payload-unverified')
        response.media = result

    def on_post_binding_propose(self, request, response):
        from scoring.group_authority_basis import propose_binding
        payload = self._payload(request, response)
        if payload is None:
            return
        subject, username, identity_source = _identity(
            request, payload, 'proposed_by_subject',
            'proposed_by_username')
        result = propose_binding(
            self.manager, payload.get('group_name', ''),
            instance_name=payload.get('instance_name', ''),
            proposed_by_subject=subject,
            proposed_by_username=username,
            identity_source=identity_source,
            counterparty=payload.get('counterparty', 'psc'),
            notes=payload.get('notes', ''))
        if not result.get('ok'):
            response.status = '422 Unprocessable Entity'
        response.media = result

    def on_post_binding_confirm_remote(self, request, response,
                                       name):
        from scoring.group_authority_basis import confirm_binding_remote
        payload = self._payload(request, response)
        if payload is None:
            return
        principal = _principal(request)
        result = confirm_binding_remote(
            self.manager, name,
            confirmed_by=payload.get('confirmed_by', 'psc-backend'),
            identity_source='keycloak-verified' if principal
            else 'payload-unverified')
        if not result.get('ok'):
            response.status = '422 Unprocessable Entity'
        response.media = result

    def on_post_binding_revoke(self, request, response, name):
        from scoring.group_authority_basis import revoke_binding
        payload = self._payload(request, response)
        if payload is None:
            return
        subject, _, _ = _identity(request, payload,
                                  'revoked_by_subject',
                                  'revoked_by_username')
        result = revoke_binding(self.manager, name, subject)
        if not result.get('ok'):
            response.status = '422 Unprocessable Entity'
        response.media = result

    def on_get_term_signals(self, request, response):
        from scoring.group_authority_basis import list_signals
        response.media = list_signals(
            self.manager,
            group_name=request.get_param('group') or '',
            status=request.get_param('status') or '')

    def on_post_term_signals(self, request, response):
        from scoring.group_authority_basis import (
            submit_term_availability_signal,
        )
        payload = self._payload(request, response)
        if payload is None:
            return
        subject, username, identity_source = _identity(
            request, payload, 'requested_by_subject',
            'requested_by_username')
        result = submit_term_availability_signal(
            self.manager, payload.get('term_name', ''),
            payload.get('context_name', ''),
            payload.get('group_name', ''),
            instance_name=payload.get('instance_name', ''),
            concept_name=payload.get('concept_name', ''),
            requested_by_subject=subject,
            requested_by_username=username,
            identity_source=identity_source,
            notes=payload.get('notes', ''))
        if not result.get('ok'):
            response.status = '422 Unprocessable Entity'
        response.media = result

    def on_get_term_signal(self, request, response, name):
        from scoring.group_authority_basis import signal_report
        report = signal_report(self.manager, name)
        if not report.get('ok'):
            response.status = '404 Not Found'
        response.media = report
