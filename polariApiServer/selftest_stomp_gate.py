"""
Selftest — ct-6: STOMP SUBSCRIBE follows the CRUDE security posture.

Run from polari-framework/:
    PYTHONPATH=.:modules python3 polariApiServer/selftest_stomp_gate.py

NO NETWORK. `StompWebSocketServer.handle_subscribe()` is the sync half of the
SUBSCRIBE path on purpose, so the whole decision is driven here with a fake
connection and a fake manager — the wire itself is already covered by
`modules/testing/stomp_selftest.py`, which must stay green (the default knob is
`off`, i.e. today's behavior, and this file proves that too).

What is pinned:
  * off allows and says nothing;
  * advisory allows AND sends the MESSAGE notice frame carrying
    `X-Polari-Permission-Advisory: would-deny <Class>:read`, with the header
    also riding the RECEIPT when the client asked for one;
  * enforce refuses with an ERROR frame carrying the evidence, and the socket
    is NOT in the topic's subscriber set;
  * an admin passes in every mode (the same bypass CRUDE has);
  * a granted profile passes — through the SAME `permission_verdict`, for verb
    `read`, with `events` derived from it and never granted separately;
  * a bearer on CONNECT (and on the WS upgrade, header and
    Sec-WebSocket-Protocol) becomes `sub` + groups and NEVER a username;
  * anonymous gets the anonymous verdict, and subscribes anyway under advisory;
  * a permitted subscribe under an ARMED TraceTarget records exactly one
    `ws-subscribe` edge, and none when nothing is armed.
"""

import json
import os
import sys

sys.path.insert(0, os.path.dirname(
    os.path.dirname(os.path.abspath(__file__))))

from types import SimpleNamespace

from accessControl.stomp_gate import (class_of_topic, gate_subscribe,
                                      subscribe_verdict)
from accessControl.stomp_identity import (StompConnection, adopt_identity,
                                          bearer_from_upgrade, scrub_principal)
from polariApiServer.stompWebSocketServer import (StompWebSocketServer,
                                                  parse_stomp_frame)

PASS, FAIL = '\033[0;32mPASS\033[0m', '\033[0;31mFAIL\033[0m'
_results = []
CLASS_NAME = 'Ct6SubscribeProbe'
TOPIC = '/topic/%s' % CLASS_NAME


def check(label, cond, extra=''):
    _results.append(bool(cond))
    print(f'  [{PASS if cond else FAIL}] {label}'
          f'{("  " + extra) if extra else ""}')


def mode(value):
    os.environ['POLARI_APP_PERMISSIONS'] = value


# ---- doubles ---------------------------------------------------------------

class FakeProfile:
    """One AppPermissionProfile row, as `resolve_grants` reads it."""

    def __init__(self, name, groups, verbs, classes):
        self.name = name
        self.published = True
        self.kc_groups_json = json.dumps(groups)
        self.verbs_json = json.dumps(verbs)
        self.app_name = ''
        self.extra_classes_json = json.dumps(classes)


def manager_with(*profiles):
    tables = {'AppPermissionProfile': {p.name: p for p in profiles}}
    return SimpleNamespace(objectTables=tables, objectTypingDict={})


def conn(user_info=None, auth_failed=False, websocket=None):
    c = StompConnection(websocket=websocket or object(), client_id='probe')
    c.user_info = user_info
    c.auth_failed = auth_failed
    return c


def user(sub='11111111-2222-3333-4444-555555555555', groups=(), roles=()):
    return {'sub': sub, 'roles': list(roles),
            'raw_claims': {'groups': list(groups)}}


def frames_of(decision):
    return [(f['command'], f['headers'], f.get('body', ''))
            for f in decision.get('frames', [])]


ADVISORY = 'X-Polari-Permission-Advisory'


def main():
    print('\n=== ct-6: SUBSCRIBE follows the CRUDE posture ===\n')

    # --- 1. topic -> class ------------------------------------------
    print('1. the topic is the class')
    check('/topic/<Class> and /topic/<Class>/<fmt> are the same class',
          class_of_topic(TOPIC) == CLASS_NAME
          and class_of_topic(TOPIC + '/flatJson') == CLASS_NAME)
    check('a non-topic destination has no class and is never gated',
          class_of_topic('/queue/whatever') == ''
          and class_of_topic('') == '' and class_of_topic('/topic/') == '')

    # --- 2. ONE verdict, for `read`, `events` derived ---------------
    print('\n2. one verdict implementation — read, with events derived')
    reader = manager_with(FakeProfile('p-read', ['viewers'], ['read'],
                                      [CLASS_NAME]))
    v = subscribe_verdict(reader, user(groups=['viewers']), CLASS_NAME)
    check('a profile granting `read` admits the subscription',
          v and v['allowed'] and v['derivedFrom'] == 'read'
          and v['verb'] == 'events', str(v and v['why'])[:60])
    check('`events` is NOT granted separately — a profile with only '
          '`events` does not admit it',
          not subscribe_verdict(
              manager_with(FakeProfile('p-ev', ['viewers'], ['events'],
                                       [CLASS_NAME])),
              user(groups=['viewers']), CLASS_NAME)['allowed'])
    check('no profile table = no model to resolve against (None, not a guess)',
          subscribe_verdict(SimpleNamespace(objectTables={}), user(),
                            CLASS_NAME) is None)

    # --- 3. the three modes -----------------------------------------
    print('\n3. off | advisory | enforce — the same knob as CRUDE')
    denier = manager_with(FakeProfile('p-other', ['viewers'], ['read'],
                                      ['SomethingElse']))
    outsider = conn(user(groups=['viewers']))

    mode('off')
    d = gate_subscribe(denier, outsider, CLASS_NAME)
    check('off: allowed, nothing computed, nothing sent',
          d['allowed'] and d['mode'] == 'off' and not d['frames']
          and d['verdict'] is None)

    mode('advisory')
    d = gate_subscribe(denier, outsider, CLASS_NAME, sub_id='s-1')
    fr = frames_of(d)
    check('advisory: the subscription is ALLOWED (security warns, §17)',
          d['allowed'] and d['mode'] == 'advisory')
    check('advisory: one MESSAGE notice frame on the subscribed destination',
          len(fr) == 1 and fr[0][0] == 'MESSAGE'
          and fr[0][1].get('destination') == TOPIC
          and fr[0][1].get('subscription') == 's-1', str(fr and fr[0][0]))
    check('advisory: the notice carries '
          f'{ADVISORY}: would-deny <Class>:read',
          fr and fr[0][1].get(ADVISORY) == f'would-deny {CLASS_NAME}:read',
          str(fr and fr[0][1].get(ADVISORY)))
    body = json.loads(fr[0][2]) if fr else {}
    check('advisory: the body is the evidence, marked as a gate notice '
          '(not a change notification)',
          body.get('polariNotice') == 'permission-advisory'
          and body.get('className') == CLASS_NAME
          and body.get('verdict', {}).get('allowed') is False
          and 'suggestion' in body.get('verdict', {}))

    d = gate_subscribe(denier, outsider, CLASS_NAME, receipt='r-9',
                       sub_id='s-1')
    fr = frames_of(d)
    check('advisory: the advisory header ALSO rides the RECEIPT when the '
          'client asked for one',
          len(fr) == 2 and fr[1][0] == 'RECEIPT'
          and fr[1][1].get('receipt-id') == 'r-9'
          and fr[1][1].get(ADVISORY) == f'would-deny {CLASS_NAME}:read')

    mode('enforce')
    d = gate_subscribe(denier, outsider, CLASS_NAME)
    fr = frames_of(d)
    check('enforce: REFUSED with an ERROR frame',
          d['allowed'] is False and len(fr) == 1 and fr[0][0] == 'ERROR',
          str(fr and fr[0][0]))
    check('enforce: the ERROR frame carries the evidence and the header',
          fr and fr[0][1].get(ADVISORY) == f'would-deny {CLASS_NAME}:read'
          and fr[0][1].get('message') == 'permission refused'
          and json.loads(fr[0][2]).get('verdict', {}).get('why'))

    # --- 4. admin + granted pass in every mode ----------------------
    print('\n4. admin bypass and granted profiles — the same as CRUDE')
    admin = conn(user(roles=['admin']))
    granted = conn(user(groups=['viewers']))
    ok = True
    for m in ('off', 'advisory', 'enforce'):
        mode(m)
        ok = ok and gate_subscribe(denier, admin, CLASS_NAME)['allowed']
        ok = ok and gate_subscribe(reader, granted, CLASS_NAME)['allowed']
    check('admin passes and a granted profile passes in all three modes '
          '(and send no notice)', ok)
    mode('enforce')
    check('an allowed subscribe under enforce sends no frame at all',
          not gate_subscribe(reader, granted, CLASS_NAME)['frames'])

    # --- 5. anonymous -----------------------------------------------
    print('\n5. anonymous = the anonymous CRUDE answer, same path')
    anon = conn(None)
    mode('advisory')
    d = gate_subscribe(reader, anon, CLASS_NAME)
    fr = frames_of(d)
    check('anonymous under advisory still subscribes, and is told so',
          d['allowed'] and fr and fr[0][0] == 'MESSAGE'
          and fr[0][1].get(ADVISORY) == f'unauthenticated {CLASS_NAME}:read')
    check('the verdict names WHY: no identity, not a missing grant',
          d['verdict'].get('unauthenticated') is True
          and d['verdict'].get('auth') == 'no-token')
    expired = conn(None, auth_failed=True)
    d = gate_subscribe(reader, expired, CLASS_NAME)
    check('an EXPIRED bearer reads as invalid-or-expired, not as anonymous '
          '(§51 on the socket)',
          d['verdict'].get('auth') == 'invalid-or-expired'
          and 'expired' in d['advisory'])
    mode('enforce')
    check('anonymous under enforce is refused with the unauthenticated '
          'message',
          gate_subscribe(reader, anon, CLASS_NAME)['frames'][0]['headers']
          .get('message') == 'unauthenticated')

    # --- 6. identity on the socket ----------------------------------
    print('\n6. the bearer on the socket — sub + groups, never a username')
    claims = {'sub': 'aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee',
              'preferred_username': 'someone', 'email': 'someone@example.test',
              'groups': ['/viewers', 'ops'], 'realm_access': {}}
    principal = {'sub': claims['sub'], 'username': 'someone',
                 'email': claims['email'], 'roles': ['offline_access'],
                 'raw_claims': claims}

    class FakeValidator:
        def __init__(self, good='good-token'):
            self.good = good
            self.seen = []

        def validate(self, token):
            self.seen.append(token)
            return principal if token == self.good else None

    scrubbed = scrub_principal(principal)
    check('scrub_principal keeps sub + roles + groups and NOTHING else',
          set(scrubbed) == {'sub', 'roles', 'raw_claims'}
          and scrubbed['sub'] == claims['sub']
          and scrubbed['raw_claims'] == {'groups': ['/viewers', 'ops']},
          str(sorted(scrubbed)))
    check('no username, no e-mail, anywhere in what is kept',
          'someone' not in json.dumps(scrubbed)
          and 'example.test' not in json.dumps(scrubbed))

    val = FakeValidator()
    c = conn(None)
    adopt_identity(c, {'Authorization': 'Bearer good-token'}, validator=val)
    check('a bearer on the CONNECT frame becomes sub + groups',
          c.authenticated and c.sub == claims['sub']
          and c.groups == sorted({'viewers', 'ops', 'offline_access'}),
          str(c.groups))
    check('the connection object literally cannot hold a username '
          '(__slots__ = websocket, client_id, user_info, auth_failed)',
          set(StompConnection.__slots__)
          == {'websocket', 'client_id', 'user_info', 'auth_failed'})

    c = conn(None)
    adopt_identity(c, {'passcode': 'good-token'}, validator=val)
    check("STOMP's own `passcode` header works too (bare or Bearer-prefixed)",
          c.authenticated and c.sub == claims['sub'])
    c = conn(None)
    adopt_identity(c, {'login': 'someone', 'passcode': 'nope'}, validator=val)
    check('a refused token = anonymous + auth_failed; `login` is never read',
          c.user_info is None and c.auth_failed is True)

    upgrade = SimpleNamespace(request=SimpleNamespace(
        headers={'Authorization': 'Bearer good-token'}))
    check('the WS upgrade Authorization header is read',
          bearer_from_upgrade(upgrade) == 'good-token')
    upgrade = SimpleNamespace(request=SimpleNamespace(
        headers={'Sec-WebSocket-Protocol': 'v12.stomp, bearer.good-token'}))
    check('the browser convention (Sec-WebSocket-Protocol: bearer.<token>) '
          'is read',
          bearer_from_upgrade(upgrade) == 'good-token')
    check('a transport with no request exposes no bearer, and never raises',
          bearer_from_upgrade(object()) == ''
          and bearer_from_upgrade(None) == '')

    c = conn(None, websocket=SimpleNamespace(request=SimpleNamespace(
        headers={'Authorization': 'Bearer good-token'})))
    adopt_identity(c, {'passcode': 'ignored'}, validator=val)
    check('the upgrade bearer wins over the CONNECT frame',
          c.authenticated and 'ignored' not in val.seen)

    # --- 7. the server seam: registration honours the decision -------
    print('\n7. the server seam — who actually ends up in the topic')
    mode('enforce')
    server = StompWebSocketServer(port=0, manager=denier)
    allowed, frames, topic = server.handle_subscribe(
        outsider, {'destination': TOPIC, 'id': 's-2'})
    check('a refused SUBSCRIBE never reaches the subscriber set',
          allowed is False and not server._subscriptions.get(topic)
          and not server._client_subs.get(outsider.websocket))
    check('and the caller is handed a serialized ERROR frame',
          len(frames) == 1
          and parse_stomp_frame(frames[0])[0] == 'ERROR')
    allowed, frames, topic = server.handle_subscribe(
        admin, {'destination': TOPIC, 'id': 's-3'})
    check('a permitted SUBSCRIBE is registered exactly as it always was',
          allowed is True
          and admin.websocket in server._subscriptions[TOPIC]
          and (TOPIC, 's-3') in server._client_subs[admin.websocket])

    mode('off')
    server2 = StompWebSocketServer(port=0, manager=None)
    allowed, frames, topic = server2.handle_subscribe(
        conn(None), {'destination': TOPIC, 'id': 's-4'})
    check('off + no manager = today`s behavior byte for byte '
          '(what modules/testing/stomp_selftest.py drives)',
          allowed is True and not frames
          and server2._subscriptions[TOPIC])
    mode('enforce')
    allowed, _f, _t = server2.handle_subscribe(
        conn(None), {'destination': TOPIC, 'id': 's-5'})
    check('enforce with NO manager degrades to allow-and-say-so, never a '
          'refusal it cannot justify', allowed is True)

    # --- 8. the ws-subscribe edge -----------------------------------
    print('\n8. the ws-subscribe edge (the counterpart to ct-2`s ws-publish)')
    os.environ['POLARI_POSTURE'] = 'dev'
    os.environ.pop('POLARI_POSTURE_UNTIL', None)
    recorded = []
    armed = {'on': True}

    import security.custom.security_trace as trace_mod
    import security.custom.security_observe as obs_mod
    real_touch, real_edge = trace_mod.touch, trace_mod.record_edge
    real_observe = obs_mod.observe_permission

    trace_mod.touch = lambda m, c, v='': bool(armed['on']) and c == CLASS_NAME
    trace_mod.record_edge = (
        lambda m, cause, effect, means, detail='', run_as='':
        recorded.append((cause, effect, means, detail)))
    obs_mod.observe_permission = lambda *a, **k: None
    # the gate module resolved these names lazily, so patching the module works
    try:
        mode('advisory')
        server3 = StompWebSocketServer(port=0, manager=reader)
        server3.handle_subscribe(granted, {'destination': TOPIC, 'id': 's-6'})
        check('a permitted subscribe under an armed target records ONE '
              'ws-subscribe edge', len(recorded) == 1, str(recorded))
        check('the edge is endpoint:SUBSCRIBE /topic/<Class> -> '
              'object:<Class>:read, means ws-subscribe, detail = the groups',
              recorded and recorded[0][:3] == (
                  f'endpoint:SUBSCRIBE /topic/{CLASS_NAME}',
                  f'object:{CLASS_NAME}:read', 'ws-subscribe')
              and recorded[0][3] == ','.join(granted.groups),
              str(recorded and recorded[0]))

        recorded.clear()
        armed['on'] = False
        server3.handle_subscribe(granted, {'destination': TOPIC, 'id': 's-7'})
        check('nothing armed = no edge at all', not recorded)

        recorded.clear()
        armed['on'] = True
        mode('enforce')
        # anonymous IS refused against `reader` (no groups, no profile)
        server3.handle_subscribe(conn(None), {'destination': TOPIC,
                                              'id': 's-8'})
        check('a REFUSED subscribe records no edge (nothing was subscribed)',
              not recorded)

        recorded.clear()
        os.environ['POLARI_POSTURE'] = 'production'
        mode('advisory')
        server3.handle_subscribe(granted, {'destination': TOPIC, 'id': 's-9'})
        check('production posture records nothing — no tracing in production '
              '(design §10)', not recorded)
    finally:
        trace_mod.touch, trace_mod.record_edge = real_touch, real_edge
        obs_mod.observe_permission = real_observe
        os.environ['POLARI_POSTURE'] = 'dev'

    # --- 9. never raises --------------------------------------------
    print('\n9. a gate that breaks must not close a socket')
    mode('enforce')
    broken = SimpleNamespace(objectTables={'AppPermissionProfile': 'not-a-dict'})
    d = gate_subscribe(broken, granted, CLASS_NAME)
    check('a broken model degrades to allow, with the error named',
          d['allowed'] is True, d['advisory'])
    d = gate_subscribe(reader, object(), CLASS_NAME)
    check('a connection missing every attribute is treated as anonymous, '
          'never a crash', isinstance(d, dict) and 'allowed' in d)

    mode('off')
    failed = _results.count(False)
    print(f'\n{len(_results) - failed}/{len(_results)} passed')
    return 1 if failed else 0


if __name__ == '__main__':
    sys.exit(main())
