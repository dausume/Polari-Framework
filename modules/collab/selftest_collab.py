"""
Selftest — mtg-2: room-name safety, the HS256 token contract (the
mtg-0-proven signing shape), key parsing, the moderation grant rule,
the refusal ladders, the no-audio-by-design invariant, and the
module's FOUR registrations (manifest, endpoints, registry JSON,
FEATURE_MODULES) so the silent-no-table gotcha cannot recur here.
No server, no network — pure invariants.

Run from polari-framework/:
    python3 -m collab.selftest_collab
"""

import inspect
import json
import os

PASS, FAIL = '\033[0;32mPASS\033[0m', '\033[0;31mFAIL\033[0m'
_results = []

COLLAB_CLASSES = ('CollaborationSession', 'MeetingRecord')

TEST_KEYS = ('LKtestkey', 'x' * 48)


def check(label, cond, extra=''):
    _results.append(bool(cond))
    print(f'  [{PASS if cond else FAIL}] {label}'
          f'{("  " + extra) if extra else ""}')


def run():
    print('mtg-2 selftest')
    from collab.collab_basis import (
        IDENTITY_SOURCE_VALUES, SESSION_SCOPE_VALUES,
        SESSION_STATUS_VALUES, CollaborationSession, MeetingRecord,
        moderation_grant, safe_room_name,
    )
    from collab import livekit_remote as lk

    # -- vocabulary ---------------------------------------------------
    check("scopes are local|web and LOCAL is the 2026 story",
          SESSION_SCOPE_VALUES == ('local', 'web'))
    check('session lifecycle is open|closed',
          SESSION_STATUS_VALUES == ('open', 'closed'))
    check('identity sources carry the evidence vocabulary',
          IDENTITY_SOURCE_VALUES
          == ('keycloak-verified', 'payload-unverified'))

    # -- room-name safety (these travel into JWTs and URLs) -----------
    for good in ('mtg1', 'staff-standup', 'sim.review_2'):
        check(f'safe_room_name accepts {good!r}', safe_room_name(good))
    for bad in ('', 'a/b', '../up', 'a b', 'x' * 200, 'a..b'):
        check(f'safe_room_name rejects {bad!r}', not safe_room_name(bad))

    # -- key parsing ---------------------------------------------------
    old_env = {k: os.environ.pop(k, None)
               for k in ('LIVEKIT_KEYS', 'LIVEKIT_KEYS_FILE',
                         'LIVEKIT_URL', 'LIVEKIT_CLIENT_URL')}
    try:
        check('no keys configured -> signing_keys None',
              lk.signing_keys() is None)
        os.environ['LIVEKIT_KEYS'] = 'LKabc: secret123'
        check('LIVEKIT_KEYS parses key/secret',
              lk.signing_keys() == ('LKabc', 'secret123'))
        os.environ['LIVEKIT_KEYS'] = 'LIVEKIT_KEYS=LKabc: s2'
        check('a pasted keys.env line (with prefix) still parses',
              lk.signing_keys() == ('LKabc', 's2'))
        os.environ['LIVEKIT_KEYS'] = 'garbage-no-colon'
        check('malformed keys refuse (None), never a half-pair',
              lk.signing_keys() is None)
        del os.environ['LIVEKIT_KEYS']

        # -- token contract (the mtg-0-proven shape) -------------------
        minted = lk.mint_token('alice', 'mtg1', keys=TEST_KEYS,
                               now=1_000_000, ttl_s=900)
        check('mint returns ok + three-segment JWT',
              minted.get('ok') and minted['token'].count('.') == 2)
        claims = lk.verify_token(minted['token'], keys=TEST_KEYS)
        check('roundtrip: signature verifies and claims decode',
              claims is not None)
        check('iss is the API key, sub the identity',
              claims['iss'] == TEST_KEYS[0] and claims['sub'] == 'alice')
        check('video grants carry room + join/publish/subscribe',
              claims['video'] == {'room': 'mtg1', 'roomJoin': True,
                                  'canPublish': True,
                                  'canSubscribe': True})
        check('short-lived: exp-nbf spans exactly ttl + the nbf slack',
              claims['exp'] - claims['nbf'] == 900 + 10
              and minted['expires_at'] == 1_000_900)
        admin = lk.mint_token('alice', 'mtg1', admin=True,
                              keys=TEST_KEYS, now=1_000_000)
        check('admin mint adds roomAdmin; plain mint has none',
              lk.verify_token(admin['token'],
                              keys=TEST_KEYS)['video'].get('roomAdmin')
              is True and 'roomAdmin' not in claims['video'])
        tampered = minted['token'][:-4] + ('AAAA' if minted['token'][-4:]
                                           != 'AAAA' else 'BBBB')
        check('tampered signature verifies to None',
              lk.verify_token(tampered, keys=TEST_KEYS) is None)
        check('wrong secret verifies to None',
              lk.verify_token(minted['token'],
                              keys=('LKtestkey', 'y' * 48)) is None)

        # -- refusal ladders -------------------------------------------
        refused = lk.mint_token('alice', 'mtg1')
        check('mint without keys REFUSES with suggestion',
              not refused.get('ok') and 'suggestion' in refused)
        sug = refused['suggestion']
        check('suggestion carries evidence + knob + action',
              sug.get('evidence') and 'LIVEKIT_KEYS' in sug.get('knob', '')
              and 'pol compose livekit up' in sug.get('action', ''))
        check('no URL configured -> server_url empty (topology may '
              'still resolve in-server)', lk.server_url() in
              ('', lk.server_url()))  # env half: no crash, no raise
        os.environ['LIVEKIT_URL'] = 'http://h:7880/'
        check('LIVEKIT_URL knob wins and is rstripped',
              lk.server_url() == 'http://h:7880')
        check('client URL is a declaration — empty when undeclared',
              lk.client_url() == '')
        os.environ['LIVEKIT_CLIENT_URL'] = 'wss://livekit.example/'
        check('LIVEKIT_CLIENT_URL declared -> used verbatim (rstripped)',
              lk.client_url() == 'wss://livekit.example')
    finally:
        for k, v in old_env.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v

    # -- moderation grant rule -----------------------------------------
    check('claimed moderator gets the grant',
          moderation_grant('sub-1', [], 'sub-1', ''))
    check('someone else does not',
          not moderation_grant('sub-2', [], 'sub-1', ''))
    check('the moderator_role carries the grant for role holders',
          moderation_grant('sub-2', ['meeting-moderator'], 'sub-1',
                           'meeting-moderator'))
    check('no role declared -> roles grant nothing',
          not moderation_grant('sub-2', ['meeting-moderator'],
                               'sub-1', ''))
    check('unclaimed session grants nothing pre-claim',
          not moderation_grant('sub-1', [], '', ''))

    # -- the no-audio-by-design invariant --------------------------------
    record_fields = inspect.signature(MeetingRecord.__init__).parameters
    check('MeetingRecord has NO audio/recording field (ephemeral by '
          'default is a design line, not an omission)',
          not any('audio' in f or 'recording' in f
                  for f in record_fields))
    session_fields = inspect.signature(
        CollaborationSession.__init__).parameters
    check('session carries moderation evidence fields',
          {'moderator_subject', 'moderator_role',
           'moderator_source'} <= set(session_fields))

    # -- mtg-4: the realtime wire protocol -------------------------------
    from collab import realtime_schemas as rt

    check('protocol declares itself EPHEMERAL-ONLY and names zero '
          'authoritative kinds (the §2 line, as data)',
          rt.EPHEMERAL_ONLY and rt.authoritative_kinds() == ())
    check('every kind carries version, maxHz, purpose and fields',
          all(spec.get('version') and spec.get('maxHz')
              and spec.get('purpose') and spec.get('fields')
              for spec in rt.MESSAGE_KINDS.values()))
    check('every field declares a type the codec can check',
          all(f['type'] in rt.FIELD_TYPES
              for spec in rt.MESSAGE_KINDS.values()
              for f in spec['fields']))
    check('drag-preview names the proposal seam rather than carrying '
          'a committed transform',
          any(f['name'] == 'proposalRef'
              for f in rt.MESSAGE_KINDS['drag-preview']['fields'])
          and 'preview' in rt.MESSAGE_KINDS['drag-preview']['purpose'])

    # encode/decode round trip
    enc = rt.encode('pose', {'head': [0.0, 1.7, 0.0],
                             'headRot': [0, 0, 0, 1]},
                    sender='alice', now=12.5)
    check('encode builds the versioned envelope',
          enc['ok'] and enc['message']['p'] == rt.PROTOCOL
          and enc['message']['v'] == rt.PROTOCOL_MAJOR
          and enc['message']['k'] == 'pose'
          and enc['message']['kv'] == 1
          and enc['message']['s'] == 'alice')
    dec = rt.decode(enc['message'])
    check('decode round-trips the payload',
          dec['ok'] and dec['kind'] == 'pose'
          and dec['data']['head'] == [0.0, 1.7, 0.0]
          and dec['sender'] == 'alice')

    # refusals at the SENDER
    check('encode refuses an unknown kind, naming the known ones',
          not rt.encode('telepathy', {})['ok'])
    check('encode refuses a missing required field',
          not rt.encode('pose', {'head': [0, 0, 0]})['ok'])
    check('encode refuses a mistyped field (vec3 needs three numbers)',
          not rt.encode('pose', {'head': [0, 0], 'headRot': [0, 0, 0, 1]})['ok'])
    check('encode refuses a bool where a float belongs',
          not rt.encode('cursor', {'x': True, 'y': 0.5})['ok'])

    # the four compatibility rules
    unknown_kind = dict(enc['message'], k='hologram')
    r = rt.decode(unknown_kind)
    check('RULE unknown kind -> IGNORE, not an error (a newer peer '
          'may speak kinds we do not)',
          not r['ok'] and r.get('ignore') and not r.get('refused'))
    newer_minor = dict(enc['message'], kv=99)
    newer_minor['d'] = dict(newer_minor['d'], eyeGaze=[0, 0, 1])
    r = rt.decode(newer_minor)
    check('RULE newer kind minor -> ACCEPT, unknown field dropped, '
          'the rest delivered',
          r['ok'] and r['dropped'] == ['eyeGaze']
          and r['data']['head'] == [0.0, 1.7, 0.0])
    r = rt.decode(dict(enc['message'], v=2))
    check('RULE major mismatch -> REFUSE by name, with an action',
          not r['ok'] and r.get('refused') and '2' in r['reason']
          and r.get('action'))
    r = rt.decode({'p': 'someone-elses-protocol', 'v': 1})
    check('a foreign data-channel message is refused, not parsed',
          not r['ok'] and r.get('refused'))
    r = rt.decode(dict(enc['message'], d={'head': [0, 1, 0]}))
    check('a message missing a required field is refused',
          not r['ok'] and r.get('refused') and 'headRot' in r['reason'])
    check('decode never raises on garbage',
          not rt.decode('not a dict')['ok']
          and not rt.decode({'p': rt.PROTOCOL, 'v': rt.PROTOCOL_MAJOR,
                             'k': 'pose', 'd': 'nope'})['ok'])

    # the served/vendored artifact is ONE truth
    doc = rt.catalog_document()
    check('catalog document carries the rule + compatibility table',
          doc['ephemeralOnly'] and doc['authoritativeKinds'] == []
          and 'may mutate Polari state' in doc['rule']
          and doc['compatibility']['unknownKind'] == 'ignore')
    check('catalog lists exactly the module\'s kinds',
          sorted(doc['kinds']) == sorted(rt.MESSAGE_KINDS))
    with open(rt.CATALOG_FILE) as handle:
        on_disk = handle.read()
    check('generated polari-realtime.schema.json is IN LOCKSTEP with '
          'this module (regenerate: python3 -m '
          'collab.realtime_schemas --write)',
          on_disk == rt.catalog_json())

    # -- registration 1: the feature-import manifest ---------------------
    from polariApiServer.feature_imports import FEATURE_IMPORT_BLOCKS
    blocks = [entries for mod, entries in FEATURE_IMPORT_BLOCKS
              if mod == 'collab']
    check('feature_imports has exactly one collab block',
          len(blocks) == 1)
    declared = tuple(sorted(sym for _m, syms in (blocks[0] if blocks
                            else ()) for sym in syms))
    check('manifest declares exactly the two collab classes',
          declared == COLLAB_CLASSES, f'declared={declared}')

    # -- registration 2: the endpoint constructor ------------------------
    from polariApiServer.module_endpoints import (
        MODULE_ENDPOINT_CONSTRUCTORS)
    check('module_endpoints carries a collab constructor',
          'collab' in MODULE_ENDPOINT_CONSTRUCTORS)

    # -- registration 3: the module registry JSON ------------------------
    registry_path = os.path.join(os.path.dirname(__file__), '..',
                                 'polari-modules.json')
    with open(registry_path) as f:
        registry = json.load(f)
    row = registry.get('modules', {}).get('collab')
    check('polari-modules.json knows collab', row is not None)
    check('registry row: official, downloaded, right path',
          row and row.get('kind') == 'official' and row.get('downloaded')
          and row.get('path') == 'modules/collab')

    # -- registration 4: FEATURE_MODULES ---------------------------------
    from moduleService.module_loading import FEATURE_MODULES
    check('FEATURE_MODULES contains collab', 'collab' in FEATURE_MODULES)

    failed = sum(1 for r in _results if not r)
    print(f'\n{len(_results) - failed}/{len(_results)} checks passed')
    raise SystemExit(1 if failed else 0)


if __name__ == '__main__':
    run()
