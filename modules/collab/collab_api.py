"""
@cross-cutting
@module collab.collab_api
@tags @xc:bindings @xc:accessControl

HTTP surface for mtg-2. Rows are plain CRUDE for create/list/read;
this module adds what CRUDE can't:

  GET  /api/collab/capability
        honest availability, recon_remote-style: signing keys
        present, server URL resolved (knob → topology), reachable,
        client URL declared — each half carries its own refusal
        suggestion instead of a bare false.
  POST /api/collab/sessions/{name}/token
        THE door onto LiveKit (plan §1: tokens are minted by Polari
        from a KC-authenticated session, short-lived, never issued
        to a client Polari has not just authorized):
          - REFUSES 401 without a verified Keycloak caller — a
            payload-asserted identity never reaches a token.
          - first verified minter self-claims moderator (the
            group-authority first-come precedent), stamped with
            identity_source evidence.
          - moderation grant (roomAdmin) for the moderator subject
            or any caller holding the row's moderator_role.
          - REFUSES 409 on closed sessions, 503 without keys.
  GET  /api/collab/sessions/{name}/join-info
        what a client needs to dial: the wss client URL + room name.
        Refuses honestly when LIVEKIT_CLIENT_URL is undeclared.

Deliberately ABSENT: anything that lets the media plane write rows
(the §2 line), and any recording surface (§7 — out of v1).

@consumers
  - mtg-3 Angular meeting client; mtg-5 VR client (same endpoints)
@see collab.livekit_remote (ladder + signing),
     scanning.scanning_api (the API idiom walked before this one)
"""

import json
from datetime import datetime, timezone

import falcon

from objectTreeDecorators import treeObject, treeObjectInit
from collab.collab_basis import moderation_grant, safe_room_name


class CollabAPI(treeObject):
    """mtg-2 endpoints."""

    @treeObjectInit
    def __init__(self, polServer, manager=None):
        self.polServer = polServer
        self.apiName = '/api/collab'
        if polServer is not None:
            add = polServer.falconServer.add_route
            add('/api/collab/capability', self, suffix='capability')
            add('/api/collab/realtime-schema', self,
                suffix='realtime_schema')
            add('/api/collab/sessions/for-surface', self,
                suffix='for_surface')
            add('/api/collab/sessions/{name}/commit-drag', self,
                suffix='commit_drag')
            add('/api/collab/sessions/{name}/token', self, suffix='token')
            add('/api/collab/sessions/{name}/join-info', self,
                suffix='join_info')
            add('/api/collab/sessions/{name}/participants', self,
                suffix='participants')
            add('/api/collab/sessions/{name}/participants/'
                '{identity}/mute', self, suffix='participant_mute')
            add('/api/collab/sessions/{name}/participants/'
                '{identity}/remove', self, suffix='participant_remove')

    # ---- helpers ----------------------------------------------------

    def _find(self, class_name, name):
        table = (self.manager.objectTables or {}).get(class_name, {})
        for row in table.values():
            if getattr(row, 'name', '') == name:
                return row
        return None

    def _save(self, row):
        try:
            self.manager.db.saveInstanceInDB(row)
        except Exception:
            pass  # in-memory row stays authoritative until next save

    def _refuse(self, response, error, status=falcon.HTTP_400,
                suggestion=None):
        response.status = status
        body = {'ok': False, 'error': error}
        if suggestion:
            body['suggestion'] = suggestion
        response.media = body

    # ---- routes -----------------------------------------------------

    def on_get_capability(self, request, response):
        from collab import livekit_remote as lk
        keys = lk.signing_keys()
        url = lk.server_url()
        client = lk.client_url()
        alive = lk.reachable() if url else None
        report = {
            'ok': True,
            'keysConfigured': keys is not None,
            'serverUrl': url or None,
            'serverReachable': alive,
            'clientUrl': client or None,
        }
        gaps = []
        if keys is None:
            gaps.append('LIVEKIT_KEYS unset/unparseable — no token '
                        'can be signed')
        if not url:
            gaps.append('LIVEKIT_URL unset and the topology resolves '
                        "no provider for 'collab.media'")
        elif alive is False:
            gaps.append(f'{url} did not answer')
        if not client:
            gaps.append('LIVEKIT_CLIENT_URL undeclared — clients have '
                        'nothing to dial (never derived: a TLS name a '
                        'device must trust is posture, not a guess)')
        if gaps:
            report['suggestion'] = lk.unavailable_suggestion(
                '; '.join(gaps))
        response.media = report

    def on_post_token(self, request, response, name):
        from collab import livekit_remote as lk
        # Identity FIRST, existence second: answering 404-vs-401 to an
        # unauthenticated caller tells them which sessions exist, and
        # a meeting's guest list is not public (caught by live probing
        # 2026-08-12). ONLY the Keycloak middleware's verdict counts.
        user = getattr(request.context, 'user_info', None)
        if not user or not user.get('sub'):
            return self._refuse(
                response, 'a LiveKit token requires a Keycloak-'
                          'verified caller — payload identities are '
                          'evidence, not authorization',
                falcon.HTTP_401)
        session = self._find('CollaborationSession', name)
        if session is None:
            return self._refuse(
                response, f'no CollaborationSession named {name!r}',
                falcon.HTTP_404)
        if session.status != 'open':
            return self._refuse(
                response, f'session {name!r} is {session.status} — '
                          'no new tokens', falcon.HTTP_409)
        subject = user['sub']
        username = user.get('username') or subject
        roles = getattr(request.context, 'roles', []) or []

        # First verified minter self-claims moderation (group-authority
        # first-come precedent), with the evidence stamped.
        if not session.moderator_subject:
            session.moderator_subject = subject
            session.moderator_username = username
            session.moderator_source = 'keycloak-verified'
            self._save(session)

        admin = moderation_grant(subject, roles,
                                 session.moderator_subject,
                                 session.moderator_role)
        room = session.room_name or session.name
        if not safe_room_name(room):
            return self._refuse(
                response, f'room name {room!r} is not a safe segment')
        minted = lk.mint_token(identity=username, room=room,
                               admin=bool(admin), name=username)
        if not minted.get('ok'):
            return self._refuse(response, minted['error'],
                                falcon.HTTP_503,
                                suggestion=minted.get('suggestion'))
        response.media = {
            'ok': True, 'token': minted['token'],
            'expiresAt': minted['expires_at'], 'ttlS': minted['ttl_s'],
            'room': room, 'identity': username,
            'moderation': bool(admin),
            'moderator': session.moderator_username or None,
            'mintedAt': datetime.now(timezone.utc).isoformat(),
        }

    def on_get_realtime_schema(self, request, response):
        """mtg-4: THE realtime contract, served. Clients validate
        against this rather than a hand-copied mirror — a VR shell
        that updates on its own schedule reads the same catalog a
        browser does, so there is nothing to drift."""
        from collab.realtime_schemas import catalog_document
        response.media = dict(catalog_document(), ok=True)

    def on_get_for_surface(self, request, response):
        """mtg-6: which OPEN meeting belongs to this page/object?

        A simulation page asks by its own route (or the object it is
        showing) and gets back the session to offer — the binding is a
        row, so neither side hardcodes the other. An empty list is a
        normal answer, not an error: most pages have no meeting, and
        the page renders nothing rather than an apology."""
        route = (request.get_param('route') or '').strip()
        ref = (request.get_param('ref') or '').strip()
        if not route and not ref:
            return self._refuse(
                response, 'ask by ?route= (a page path) or ?ref= '
                          '(Class/name) — an unfiltered list is what '
                          'CRUDE /CollaborationSession is for')
        table = (self.manager.objectTables or {}).get(
            'CollaborationSession', {})
        matches = []
        for row in table.values():
            if getattr(row, 'status', '') != 'open':
                continue
            bound_route = getattr(row, 'bound_route', '') or ''
            bound_ref = getattr(row, 'bound_ref', '') or ''
            if (route and bound_route and bound_route == route) \
                    or (ref and bound_ref and bound_ref == ref):
                matches.append({
                    'name': row.name,
                    'title': getattr(row, 'title', '') or row.name,
                    'room': getattr(row, 'room_name', '') or row.name,
                    'boundRoute': bound_route,
                    'boundRef': bound_ref,
                    'moderator': getattr(row, 'moderator_username', '')
                    or None,
                })
        response.media = {'ok': True, 'route': route or None,
                          'ref': ref or None, 'sessions': matches}

    def _moderator_or_refuse(self, request, response, name):
        """(session, subject) for a VERIFIED caller holding the
        moderation grant, or None having already refused."""
        # Identity before existence — same reason as the token route.
        user = getattr(request.context, 'user_info', None)
        if not user or not user.get('sub'):
            self._refuse(response,
                         'moderation requires a Keycloak-verified '
                         'caller', falcon.HTTP_401)
            return None
        session = self._find('CollaborationSession', name)
        if session is None:
            self._refuse(response,
                         f'no CollaborationSession named {name!r}',
                         falcon.HTTP_404)
            return None
        roles = getattr(request.context, 'roles', []) or []
        if not moderation_grant(user['sub'], roles,
                                session.moderator_subject,
                                session.moderator_role):
            self._refuse(response,
                         'only this session\'s moderator may moderate '
                         f'(moderator: {session.moderator_username or "unclaimed"})',
                         falcon.HTTP_403)
            return None
        return (session, user)

    def on_get_participants(self, request, response, name):
        """The roster AS THE SERVER SEES IT — the client's own list
        comes from its LiveKit connection; this is the authoritative
        second opinion moderation acts on."""
        from collab import livekit_remote as lk
        session = self._find('CollaborationSession', name)
        if session is None:
            return self._refuse(
                response, f'no CollaborationSession named {name!r}',
                falcon.HTTP_404)
        room = session.room_name or session.name
        result = lk.room_service('ListParticipants', {'room': room})
        if not result.get('ok'):
            return self._refuse(response, result['error'],
                                falcon.HTTP_503,
                                suggestion=result.get('suggestion'))
        people = (result['result'] or {}).get('participants') or []
        response.media = {
            'ok': True, 'room': room,
            'participants': [
                {'identity': p.get('identity'),
                 'name': p.get('name'),
                 'joinedAt': p.get('joined_at'),
                 'tracks': len(p.get('tracks') or [])}
                for p in people],
        }

    def on_post_participant_mute(self, request, response, name,
                                 identity):
        """Mute every audio track a participant publishes. Runs
        SERVER-side with an internally-minted admin token — the
        browser never holds room-admin rights."""
        from collab import livekit_remote as lk
        checked = self._moderator_or_refuse(request, response, name)
        if checked is None:
            return
        session, user = checked
        room = session.room_name or session.name
        listed = lk.room_service('ListParticipants', {'room': room})
        if not listed.get('ok'):
            return self._refuse(response, listed['error'],
                                falcon.HTTP_503,
                                suggestion=listed.get('suggestion'))
        target = next((p for p in (listed['result'] or {}).get(
            'participants') or [] if p.get('identity') == identity), None)
        if target is None:
            return self._refuse(
                response, f'{identity!r} is not in room {room!r}',
                falcon.HTTP_404)
        muted = []
        for track in target.get('tracks') or []:
            if (track.get('type') or '').upper() != 'AUDIO' \
                    and track.get('type') != 1:
                continue
            result = lk.room_service('MutePublishedTrack', {
                'room': room, 'identity': identity,
                'track_sid': track.get('sid'), 'muted': True})
            if not result.get('ok'):
                return self._refuse(response, result['error'],
                                    falcon.HTTP_503,
                                    suggestion=result.get('suggestion'))
            muted.append(track.get('sid'))
        response.media = {
            'ok': True, 'room': room, 'identity': identity,
            'mutedTracks': muted,
            'moderatedBy': user.get('username') or user['sub'],
            'note': ('a muted participant can unmute themselves — '
                     'this is moderation, not a gag'),
        }

    def on_post_participant_remove(self, request, response, name,
                                   identity):
        """Remove a participant from the room. They keep their token
        until it expires (short TTL is the bound) — close the session
        to stop re-entry for good."""
        from collab import livekit_remote as lk
        checked = self._moderator_or_refuse(request, response, name)
        if checked is None:
            return
        session, user = checked
        room = session.room_name or session.name
        result = lk.room_service('RemoveParticipant',
                                 {'room': room, 'identity': identity})
        if not result.get('ok'):
            return self._refuse(response, result['error'],
                                falcon.HTTP_503,
                                suggestion=result.get('suggestion'))
        response.media = {
            'ok': True, 'room': room, 'identity': identity,
            'removedBy': user.get('username') or user['sub'],
            'note': ('their token stays valid until it expires (TTL '
                     'is the bound); close the session to stop '
                     're-entry'),
        }

    def on_post_commit_drag(self, request, response, name):
        """mtg-8: THE §2 RULE MADE TANGIBLE.

        A dragged object moves smoothly for everyone over LiveKit —
        those are `drag-preview` messages, ephemeral and unvalidated,
        and NOTHING here reads them. To make a drag real, the client
        POSTs the final transform to this endpoint, which:

          - requires a Keycloak-verified caller (a preview arriving on
            a socket is not a person),
          - PROPOSES through the ordinary ai_actions path and returns
            the proposal — it does NOT apply it. Applying is a
            separate, confirmed act by a human or an authorized
            service, recorded in the same provenance log every other
            change goes through.

        So an object moves smoothly for everyone via LiveKit, and
        BECOMES moved via Polari — no second write path, no message
        that mutates state."""
        user = getattr(request.context, 'user_info', None)
        if not user or not user.get('sub'):
            return self._refuse(
                response, 'committing a drag requires a Keycloak-'
                          'verified caller — a preview on a socket is '
                          'not authorization', falcon.HTTP_401)
        session = self._find('CollaborationSession', name)
        if session is None:
            return self._refuse(
                response, f'no CollaborationSession named {name!r}',
                falcon.HTTP_404)
        try:
            body = request.media or {}
        except Exception:
            body = {}
        object_ref = (body.get('objectRef') or '').strip()
        updates = body.get('updateData')
        if '/' not in object_ref:
            return self._refuse(
                response, "objectRef must be 'ClassName/polariId' — "
                          'the row this drag moved')
        if not isinstance(updates, dict) or not updates:
            return self._refuse(
                response, 'updateData must be a non-empty object of '
                          'the fields the drag changed')
        class_name, _, polari_id = object_ref.partition('/')
        try:
            from polariApiServer.ai_actions import kernel
        except Exception as exc:
            return self._refuse(
                response, f'the proposal kernel is unavailable: {exc}',
                falcon.HTTP_503)
        who = user.get('username') or user['sub']
        proposal = kernel.propose(
            'object_transform',
            f'{who} dragged {object_ref} in meeting {name!r}',
            {'class': class_name, 'polariId': polari_id,
             'updateData': updates})
        response.status = falcon.HTTP_202
        response.media = {
            'ok': True, 'applied': False, 'proposal': proposal,
            'session': name, 'by': who,
            'note': ('PROPOSED, not applied. The drag moved smoothly '
                     'for everyone over LiveKit; it becomes real only '
                     'when this proposal is executed with confirm — '
                     'the same path and the same provenance log as '
                     'every other change.'),
        }

    def on_get_join_info(self, request, response, name):
        from collab import livekit_remote as lk
        session = self._find('CollaborationSession', name)
        if session is None:
            return self._refuse(
                response, f'no CollaborationSession named {name!r}',
                falcon.HTTP_404)
        client = lk.client_url()
        if session.scope == 'web':
            return self._refuse(
                response, "scope 'web' is declared but not enabled — "
                          'off-LAN needs the EXTERNAL_APPS ladder + '
                          'TURN (its own arc); LAN is the 2026 story',
                falcon.HTTP_501)
        if not client:
            return self._refuse(
                response, 'LIVEKIT_CLIENT_URL undeclared',
                falcon.HTTP_503,
                suggestion=lk.unavailable_suggestion(
                    'the wss:// client URL is a declaration, never '
                    'derived'))
        response.media = {
            'ok': True, 'url': client,
            'room': session.room_name or session.name,
            'scope': session.scope, 'status': session.status,
            'tokenEndpoint': f'/api/collab/sessions/{name}/token',
        }
