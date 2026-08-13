"""
@cross-cutting
@module reticulum.reticulum_api
@tags @xc:bindings @xc:accessControl

HTTP surface for ret-1. Rows are plain CRUDE for create/list/read;
this adds what CRUDE can't:

  GET  /api/reticulum/capability
        honest availability, *_remote-style: sidecar URL resolved
        (knob → topology), reachable, the LICENCE PINS surfaced (so
        nobody has to remember why rns is 0.9.4), operator-licence
        states, and RECEIVE-FIRST posture stated — RX needs no
        licence and is the default (§5i).
  GET  /api/reticulum/arch
        `.arch` — who we can ACTUALLY reach right now: every node
        with measured reachability (fresh within the horizon) split
        from hopeful names. The declared-vs-measured split as an
        endpoint.
  POST /api/reticulum/inbound
        THE ret-8 SEAM (LiveKit §2 rule inherited VERBATIM): nothing
        arriving from another isle may mutate Polari state. The
        sidecar/gateway POSTs inbound app data here; it becomes a
        PROPOSAL ('rns_inbound', level 4 network-service — above the
        auto-approve ceiling, so applying is ALWAYS a confirmed act).

Deliberately ABSENT: any endpoint that writes rows from mesh data,
and any transmit control on an rx-only surface.

@consumers
  - ret-3 gateway (inbound seam), frontend reticulum page (later arc)
@see reticulum.rns_remote (ladder), collab.collab_api (idiom walked
     before this one; commit_drag is the seam's first walk)
"""

import time

import falcon

from objectTreeDecorators import treeObject, treeObjectInit
from reticulum.arch_basis import reachable_now
from reticulum.operator_basis import license_state, license_warning


class ReticulumAPI(treeObject):
    """ret-1 endpoints."""

    @treeObjectInit
    def __init__(self, polServer, manager=None):
        self.polServer = polServer
        self.apiName = '/api/reticulum'
        if polServer is not None:
            add = polServer.falconServer.add_route
            add('/api/reticulum/capability', self, suffix='capability')
            add('/api/reticulum/arch', self, suffix='arch')
            add('/api/reticulum/resolve/{name}', self, suffix='resolve')
            add('/api/reticulum/inbound', self, suffix='inbound')

    # ---- helpers ----------------------------------------------------

    def _rows(self, class_name):
        table = (self.manager.objectTables or {}).get(class_name, {})
        return list(table.values())

    def _refuse(self, response, error, status=falcon.HTTP_400,
                suggestion=None):
        response.status = status
        body = {'ok': False, 'error': error}
        if suggestion:
            body['suggestion'] = suggestion
        response.media = body

    # ---- routes -----------------------------------------------------

    def on_get_capability(self, request, response):
        from reticulum import rns_remote as rr
        url = rr.server_url()
        alive = rr.reachable() if url else None
        today = time.strftime('%Y-%m-%d')
        licenses = []
        for row in self._rows('OperatorLicense'):
            state = license_state(getattr(row, 'expiry_date', ''), today)
            licenses.append({
                'name': row.name,
                'callsign': getattr(row, 'callsign', ''),
                'state': state,
                'warning': license_warning(
                    state, getattr(row, 'callsign', '')) or None,
            })
        report = {
            'ok': True,
            'sidecarUrl': url or None,
            'sidecarReachable': alive,
            'stackPins': rr.STACK_PINS,
            'posture': 'receive-first: RX needs no licence and is the '
                       'default; transmit is a deliberate, per-'
                       'interface enablement (§5i)',
            'operatorLicenses': licenses,
            'licenseNote': ('states are the operator\'s own recorded '
                            'assertion — tracked and surfaced, never '
                            'validated online, never a transmit gate '
                            '(an emergency tool cannot depend on a '
                            'reachable server)'),
        }
        if not licenses:
            report['licenseWarning'] = license_warning('none')
        gaps = []
        if not url:
            gaps.append('RETICULUM_URL unset and the topology resolves '
                        "no provider for 'reticulum.mesh'")
        elif alive is False:
            gaps.append(f'{url} did not answer /status')
        if gaps:
            report['suggestion'] = rr.unavailable_suggestion(
                '; '.join(gaps))
        response.media = report

    def on_get_arch(self, request, response):
        """Who can I actually reach RIGHT NOW — measured, timestamped,
        split from hopeful names."""
        now_ms = int(time.time() * 1000)
        reachable, stale = [], []
        for row in self._rows('ArchipelagoNode'):
            fact = {'last_heard_ms': getattr(row, 'last_heard_ms', 0)}
            entry = {
                'name': row.name,
                'archName': getattr(row, 'arch_name', ''),
                'kind': getattr(row, 'node_kind', ''),
                'destination': getattr(row, 'destination_name', ''),
                'lastHeardMs': fact['last_heard_ms'],
                'hopCount': getattr(row, 'hop_count', 0),
                'linkQuality': getattr(row, 'link_quality', ''),
                'trust': getattr(row, 'trust_name', ''),
                'fidelity': getattr(row, 'fidelity', 'declared'),
            }
            (reachable if reachable_now(fact, now_ms)
             else stale).append(entry)
        response.media = {
            'ok': True, 'nowMs': now_ms,
            'reachable': reachable,
            'unmeasuredOrStale': stale,
            'note': ('reachability is a MEASUREMENT with a timestamp; '
                     'past the freshness horizon the honest answer is '
                     '"unknown, measure first", not the last good '
                     'number'),
        }

    def on_get_resolve(self, request, response, name):
        """ret-3: THE NAME REGISTRY as an endpoint — what the isle's
        resolver (router-side, isle-core's half) queries before
        answering a *.rns.isle / .arch name with a synthetic IP.
        An unmapped name is refused BY NAME — never guessed, never a
        silent black hole (§3)."""
        # A destination row by name, or an .arch node by arch_name.
        for row in self._rows('ReticulumDestination'):
            if getattr(row, 'name', '') == name:
                return self._respond_resolved(response, name, row.name,
                                              row)
        for node in self._rows('ArchipelagoNode'):
            if getattr(node, 'arch_name', '') == name \
                    or getattr(node, 'name', '') == name:
                dest_name = getattr(node, 'destination_name', '')
                for row in self._rows('ReticulumDestination'):
                    if getattr(row, 'name', '') == dest_name:
                        return self._respond_resolved(
                            response, name, dest_name, row,
                            arch=getattr(node, 'arch_name', ''))
                return self._refuse(
                    response, f'.arch node {name!r} names destination '
                              f'{dest_name!r}, which has no row — the '
                              'mapping is incomplete, not guessed',
                    falcon.HTTP_404)
        return self._refuse(
            response, f'no mapping for {name!r} — unmapped names are '
                      'refused by name, never routed hopefully',
            falcon.HTTP_404,
            suggestion={
                'evidence': f'{name!r} matches no ReticulumDestination '
                            'name and no ArchipelagoNode arch_name',
                'knob': 'ReticulumDestination / ArchipelagoNode rows '
                        '(CRUDE)',
                'action': 'create the destination row (and its .arch '
                          'node if it is a peer), then resolve again',
            })

    def _respond_resolved(self, response, asked, dest_name, row,
                          arch=''):
        response.media = {
            'ok': True, 'asked': asked, 'destination': dest_name,
            'archName': arch,
            'destHash': getattr(row, 'dest_hash', ''),
            'destType': getattr(row, 'dest_type', ''),
            'scope': getattr(row, 'scope', ''),
            'direction': getattr(row, 'direction', ''),
            'note': ('the synthetic IP for this name comes from the '
                     'netledger-reserved pool on the resolving host '
                     '(ret-3); this endpoint answers WHAT the name '
                     'is, the resolver answers WHERE to send packets'),
        }

    def on_post_inbound(self, request, response):
        """ret-8: inbound mesh data becomes a PROPOSAL, never a write.

        The caller is the LOCAL sidecar/gateway (KC-verified service
        account or user) — a remote isle is not authorized merely by
        being on the mesh, and its trust grade only raises what may be
        auto-approved LATER, on the proposal side; it buys no direct
        write here or anywhere."""
        user = getattr(request.context, 'user_info', None)
        if not user or not user.get('sub'):
            # Identity FIRST, shape second (401-vs-400/404 must not
            # leak which watched objects exist).
            return self._refuse(
                response, 'inbound mesh data requires a Keycloak-'
                          'verified LOCAL caller — arrival on the mesh '
                          'is not authorization', falcon.HTTP_401)
        try:
            body = request.media or {}
        except Exception:
            body = {}
        arch_name = (body.get('archName') or '').strip()
        kind = (body.get('kind') or '').strip()
        payload = body.get('payload')
        if not arch_name or not kind:
            return self._refuse(
                response, 'archName (the sending .arch node) and kind '
                          '(what this data claims to be) are required')
        if not isinstance(payload, dict) or not payload:
            return self._refuse(
                response, 'payload must be a non-empty object — the '
                          'data as received, verbatim')
        try:
            from polariApiServer.ai_actions import kernel
        except Exception as exc:
            return self._refuse(
                response, f'the proposal kernel is unavailable: {exc}',
                falcon.HTTP_503)
        who = user.get('username') or user['sub']
        proposal = kernel.propose(
            'rns_inbound',
            f'mesh data ({kind}) from {arch_name!r} via {who}',
            {'archName': arch_name, 'kind': kind, 'payload': payload,
             'watchedName': (body.get('watchedName') or '').strip()})
        response.status = falcon.HTTP_202
        response.media = {
            'ok': True, 'applied': False, 'proposal': proposal,
            'from': arch_name, 'by': who,
            'note': ('PROPOSED, not applied. Nothing arriving over '
                     'Reticulum mutates Polari state; applying is a '
                     'separate confirmed act in the same provenance '
                     'log as every other change (level 4 — above the '
                     'auto-approve ceiling by design).'),
        }
