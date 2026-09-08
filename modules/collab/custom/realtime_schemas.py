"""
@cross-cutting
@module collab.custom.realtime_schemas
@tags @xc:bindings

mtg-4: the REALTIME WIRE PROTOCOL — versioned message schemas for
everything that travels over LiveKit's data channel (pose, presence,
cursor, speaking, drag previews).

Why this exists BEFORE the VR client (plan §6.5): pose/presence/
preview messages are a wire protocol between independently-deployed
clients — a browser page, a VR shell APK on a headset that updates on
its own schedule, later a desktop shell. Versioning a protocol after
two implementations exist means a flag day; versioning it first costs
one file.

THE LINE THIS FILE ENFORCES (plan §2):

    NOTHING THAT ARRIVES OVER LIVEKIT MAY MUTATE POLARI STATE.

Every kind here is ephemeral BY CONSTRUCTION: `EPHEMERAL_ONLY` is a
declaration this module makes about itself, `authoritative_kinds()`
returns an empty tuple, and a drag PREVIEW carries no committed
transform — the commit rides the normal propose→execute path and
names the proposal it became. A future kind that needed to write a
row would be a design error, not a new entry.

Compatibility rules (decode enforces all four):
  - unknown KIND            -> ignored, not an error (a newer peer may
                              speak kinds we do not; silence is the
                              forward-compatible answer)
  - unknown FIELD in a kind -> dropped, message still delivered
  - kind minor > ours       -> accepted, extra fields dropped
  - protocol MAJOR mismatch -> REFUSED by name, with the action

@consumers
  - collab.collab_api (GET /api/collab/realtime-schema)
  - collab.collab_selftest (catalog/codec invariants + file lockstep)
  - the Angular meeting client + the mtg-5 VR client, which validate
    against the SERVED catalog rather than a hand-copied mirror —
    there is no second copy to drift
@see modules/collab/polari-realtime.schema.json (generated artifact;
     regenerate with `python3 -m collab.custom.realtime_schemas --write`)
"""

import json
import os

#: Protocol envelope version. MAJOR changes are breaking (a peer on a
#: different major is refused by name); the minor moves when kinds are
#: added or gain optional fields.
PROTOCOL = 'polari-rt'
PROTOCOL_MAJOR = 1
PROTOCOL_MINOR = 0

#: This module carries ONLY ephemeral traffic. Stated as data so a
#: test can assert it rather than a comment nobody runs.
EPHEMERAL_ONLY = True

#: Field types the catalog uses. Deliberately tiny: a wire protocol
#: that needs a rich type system is carrying too much.
FIELD_TYPES = ('str', 'int', 'float', 'bool', 'vec3', 'quat', 'list')

_TYPE_CHECKS = {
    'str': lambda v: isinstance(v, str),
    'int': lambda v: isinstance(v, int) and not isinstance(v, bool),
    'float': lambda v: isinstance(v, (int, float))
    and not isinstance(v, bool),
    'bool': lambda v: isinstance(v, bool),
    'vec3': lambda v: isinstance(v, (list, tuple)) and len(v) == 3
    and all(isinstance(x, (int, float)) and not isinstance(x, bool)
            for x in v),
    'quat': lambda v: isinstance(v, (list, tuple)) and len(v) == 4
    and all(isinstance(x, (int, float)) and not isinstance(x, bool)
            for x in v),
    'list': lambda v: isinstance(v, (list, tuple)),
}


def _f(name, ftype, required=False, note=''):
    return {'name': name, 'type': ftype, 'required': required,
            'note': note}


#: THE CATALOG. Each kind declares its own version (independent of
#: the envelope's), its fields, a rate ceiling, and why it exists.
#: `maxHz` is guidance a sender honours and a receiver may enforce —
#: a headset streaming pose at 90Hz to eight peers is a bandwidth
#: decision, and the ledger cannot measure bandwidth yet (mtg-1).
MESSAGE_KINDS = {
    'presence': {
        'version': 1,
        'maxHz': 1,
        'purpose': 'I am here, and this is how to draw me. Sent on '
                   'join and on change — not a heartbeat (LiveKit '
                   'already reports connection state).',
        'fields': [
            _f('displayName', 'str', True),
            _f('client', 'str', True,
               "'web' | 'vr' | 'desktop' — what SURFACE the peer is "
               'on, so a browser can label the headset in the room'),
            _f('avatarRef', 'str', False,
               'a Polari asset row name (mtg-5 avatars); never a URL '
               '— the row is what carries licence + provenance'),
        ],
    },
    'pose': {
        'version': 1,
        'maxHz': 20,
        'purpose': 'Where a participant is looking/standing in a '
                   'shared scene. The VR client (mtg-5) is the first '
                   'producer; a browser may consume it to place a '
                   'marker without rendering a body.',
        'fields': [
            _f('head', 'vec3', True, 'metres, scene frame'),
            _f('headRot', 'quat', True, 'xyzw'),
            _f('leftHand', 'vec3', False),
            _f('rightHand', 'vec3', False),
            _f('leftHandRot', 'quat', False),
            _f('rightHandRot', 'quat', False),
        ],
    },
    'cursor': {
        'version': 1,
        'maxHz': 15,
        'purpose': "A 2D pointer on a shared page/scene — the flat "
                   'equivalent of a hand. Normalised 0..1 so peers '
                   'with different viewports agree.',
        'fields': [
            _f('x', 'float', True, '0..1 of the shared surface'),
            _f('y', 'float', True, '0..1'),
            _f('surface', 'str', False,
               'which shared surface (scene id / route)'),
        ],
    },
    'speaking': {
        'version': 1,
        'maxHz': 4,
        'purpose': 'Speaking state for surfaces that cannot read '
                   "LiveKit's own active-speaker signal (a VR scene "
                   'lighting an avatar). Advisory, never a mute '
                   'authority — muting is a MODERATION action through '
                   'the backend.',
        'fields': [
            _f('speaking', 'bool', True),
            _f('level', 'float', False, '0..1, for a meter'),
        ],
    },
    'drag-preview': {
        'version': 1,
        'maxHz': 20,
        'purpose': 'THE §2 case made concrete: an object moving '
                   'smoothly for everyone WHILE it is dragged. This '
                   'is a preview and says so — `proposalRef` names '
                   'the propose/execute entry that will make it real, '
                   'and a receiver that renders the preview as a '
                   'committed position is reading the protocol wrong.',
        'fields': [
            _f('objectRef', 'str', True,
               'class/name of the object being dragged'),
            _f('position', 'vec3', True),
            _f('rotation', 'quat', False),
            _f('phase', 'str', True,
               "'start' | 'move' | 'drop' — 'drop' means the DRAG "
               'ended, NOT that anything was committed'),
            _f('proposalRef', 'str', False,
               'the proposal this drag will become, once a human or '
               'an authorized service commits it'),
        ],
    },
}


def authoritative_kinds():
    """The kinds that may change Polari state: none, by design.
    A function rather than a constant so the answer is testable and
    the docstring travels with it."""
    return ()


def envelope_version():
    return f'{PROTOCOL_MAJOR}.{PROTOCOL_MINOR}'


def encode(kind, data, sender='', now=0.0):
    """Build one wire message. Refuses (never raises) when the kind is
    unknown or a required field is missing/mistyped — a malformed
    message is a bug at the SENDER, and it should be caught there
    rather than shipped for every peer to puzzle over."""
    spec = MESSAGE_KINDS.get(kind)
    if spec is None:
        return {'ok': False,
                'error': f'unknown message kind {kind!r}',
                'known': sorted(MESSAGE_KINDS)}
    payload = {}
    for field in spec['fields']:
        name = field['name']
        if name not in data or data[name] is None:
            if field['required']:
                return {'ok': False,
                        'error': f'{kind}: missing required field '
                                 f'{name!r}'}
            continue
        value = data[name]
        if not _TYPE_CHECKS[field['type']](value):
            return {'ok': False,
                    'error': f'{kind}.{name}: expected '
                             f'{field["type"]}, got '
                             f'{type(value).__name__}'}
        payload[name] = list(value) if field['type'] in ('vec3', 'quat') \
            else value
    return {'ok': True, 'message': {
        'p': PROTOCOL, 'v': PROTOCOL_MAJOR, 'k': kind,
        'kv': spec['version'], 't': round(float(now), 3),
        's': sender, 'd': payload}}


def decode(raw):
    """Read one wire message under the four compatibility rules.

    Returns one of:
      {'ok': True,  'kind', 'data', 'sender', 'sentAt', 'dropped'}
      {'ok': False, 'ignore': True,  'reason'}   — unknown kind
      {'ok': False, 'refused': True, 'reason', 'action'} — major
                                                  mismatch/garbage
    """
    if not isinstance(raw, dict):
        return {'ok': False, 'refused': True,
                'reason': 'message is not an object',
                'action': 'send JSON objects encoded by this catalog'}
    if raw.get('p') != PROTOCOL:
        return {'ok': False, 'refused': True,
                'reason': f'not a {PROTOCOL} message '
                          f'(p={raw.get("p")!r})',
                'action': 'check the sender is a Polari realtime '
                          'client and not another data-channel user'}
    major = raw.get('v')
    if major != PROTOCOL_MAJOR:
        return {'ok': False, 'refused': True,
                'reason': f'protocol major {major} != ours '
                          f'{PROTOCOL_MAJOR} — breaking difference',
                'action': 'upgrade the older peer; majors are not '
                          'negotiated, they are refused by name'}
    kind = raw.get('k')
    spec = MESSAGE_KINDS.get(kind)
    if spec is None:
        # A NEWER peer may legitimately speak kinds we do not know.
        return {'ok': False, 'ignore': True,
                'reason': f'unknown kind {kind!r} — ignored, which is '
                          'what forward compatibility looks like'}
    body = raw.get('d')
    if not isinstance(body, dict):
        return {'ok': False, 'refused': True,
                'reason': f'{kind}: payload d is not an object',
                'action': 'encode with this catalog'}
    known = {f['name']: f for f in spec['fields']}
    data, dropped = {}, []
    for name, value in body.items():
        field = known.get(name)
        if field is None:
            dropped.append(name)          # newer minor: drop, deliver
            continue
        if not _TYPE_CHECKS[field['type']](value):
            return {'ok': False, 'refused': True,
                    'reason': f'{kind}.{name}: expected '
                              f'{field["type"]}',
                    'action': 'fix the sender; a mistyped field is a '
                              'bug, not a version difference'}
        data[name] = value
    missing = [f['name'] for f in spec['fields']
               if f['required'] and f['name'] not in data]
    if missing:
        return {'ok': False, 'refused': True,
                'reason': f'{kind}: missing required '
                          f'{", ".join(missing)}',
                'action': 'fix the sender'}
    return {'ok': True, 'kind': kind, 'data': data,
            'sender': raw.get('s', ''), 'sentAt': raw.get('t', 0),
            'kindVersion': raw.get('kv', spec['version']),
            'dropped': dropped}


def catalog_document():
    """The canonical served/vendored contract. Clients validate
    against THIS rather than a hand-copied mirror — there is no second
    copy, so there is nothing to drift."""
    return {
        'kind': 'polari-realtime-catalog',
        'protocol': PROTOCOL,
        'schemaVersion': PROTOCOL_MAJOR,
        'protocolVersion': envelope_version(),
        'ephemeralOnly': EPHEMERAL_ONLY,
        'authoritativeKinds': list(authoritative_kinds()),
        'rule': 'Nothing that arrives over LiveKit may mutate Polari '
                'state. These messages are transient, lossy and '
                'unvalidated by design; committed changes ride the '
                'propose/execute path.',
        'compatibility': {
            'unknownKind': 'ignore',
            'unknownField': 'drop, deliver the rest',
            'newerKindMinor': 'accept, extra fields dropped',
            'majorMismatch': 'refuse by name',
        },
        'envelope': {
            'p': 'protocol id (const "polari-rt")',
            'v': 'protocol MAJOR (int)',
            'k': 'message kind',
            'kv': "that kind's own version",
            't': 'sender clock, seconds (advisory — never trusted for '
                 'ordering across peers)',
            's': 'sender identity as LiveKit knows it',
            'd': 'payload object',
        },
        'kinds': {
            name: {
                'version': spec['version'],
                'maxHz': spec['maxHz'],
                'purpose': spec['purpose'],
                'fields': spec['fields'],
            }
            for name, spec in sorted(MESSAGE_KINDS.items())
        },
    }


#: The generated artifact other repos vendor (VR shell, future
#: clients). Regenerate with `python3 -m collab.custom.realtime_schemas
#: --write`; the selftest fails when it drifts from this module.
CATALOG_FILE = os.path.join(os.path.dirname(os.path.dirname(__file__)),
                            'polari-realtime.schema.json')


def catalog_json():
    return json.dumps(catalog_document(), indent=2, sort_keys=False) + '\n'


if __name__ == '__main__':
    import sys
    if '--write' in sys.argv:
        with open(CATALOG_FILE, 'w') as handle:
            handle.write(catalog_json())
        print(f'wrote {CATALOG_FILE}')
    else:
        print(catalog_json(), end='')
