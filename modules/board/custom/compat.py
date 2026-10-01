"""
@module board.custom.compat

"POLARI-COMPATIBLE FIRMWARE" (brd-fi, plan §7a): may this build be installed for THIS server? brd-1's finding decides
how: `contract_hash` covers field → type only, so a fresh server's v1 (alphabetical tags) and the staging ledger's v2
share hash 2bcc9d1a2774ef33 yet put the fields on the wire in a different ORDER. So the check never trusts the hash
alone — it compares, per class, the generated header's own sha256 and its tag (= wire) order against the header THIS
server would generate NOW for the same class, msg_type and target:

  compatible      every class's header is byte-identical to what the server generates now
  stale-header    a class's header differs (the order differs — they would misread each other — or only the
                  contract line differs: same wire, but generated from another contract version; regenerate)
  unknown-class   the server knows no contract for a class the firmware speaks (no exposure, no pinned snapshot)

"What the server generates now" = its live gRPC exposure's field map (the ProtoContractVersion row the exposure points
at) — the same source `GET /api/grpc/exposures/<class>/c-header` renders from. With NO exposure for a class, the
module's pinned snapshot (custom/contracts/<class>.v<N>.json) stands in, labelled `pinned`: the firmware matches what
this code ships, but no bridge can attach until the exposure is enabled (the installer's attach step says so).
"""
import hashlib
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
CONTRACTS = os.path.join(HERE, 'contracts')
VERDICTS = ('compatible', 'stale-header', 'unknown-class')


def sha256(text):
    return hashlib.sha256(text.encode() if isinstance(text, str) else text).hexdigest()


def tag_order(field_map):
    f = (field_map or {}).get('fields') or {}
    return [n for n in sorted(f, key=lambda n: int(f[n]['tag']))]


def pinned_contract(cls):
    if os.path.isdir(CONTRACTS):
        for fn in sorted(os.listdir(CONTRACTS), reverse=True):
            if fn.startswith(cls + '.v') and fn.endswith('.json'):
                p = os.path.join(CONTRACTS, fn)
                return json.load(open(p)), p
    return None, ''


def _live(manager, cls):
    """(field_map, version, contract_hash) of the class's current exposure on this server, or None."""
    if manager is None:
        return None
    try:
        from grpcbridge.custom.proto_gen import get_exposure, get_versions
    except Exception:   # grpcbridge absent: no live contracts on this server
        return None
    exp = get_exposure(manager, cls)
    if exp is None or not int(getattr(exp, 'proto_version', 0) or 0):
        return None
    want = int(getattr(exp, 'proto_version', 0) or 0)
    for row in get_versions(manager, cls):
        if int(getattr(row, 'version', 0) or 0) == want:
            try:
                fm = json.loads(getattr(row, 'field_map_json', '{}') or '{}')
            except ValueError:
                fm = None
            if fm and fm.get('fields'):
                return fm, want, getattr(exp, 'contract_hash', '')
    return None


def server_header(manager, cls, msg_type=1, target='avr', allow_pinned=True):
    """What THIS server would generate now: {text, sha256, tag_order, source live|pinned, contract_version,
    contract_hash, field_map} — or None (unknown class). Live first; the pinned snapshot only with no exposure."""
    from grpcbridge.custom.c_twin import render_c_header
    live = _live(manager, cls)
    if live is not None:
        fm, ver, h = live
        src = {'source': 'live', 'where': 'this server\'s gRPC exposure (contract v%d)' % ver}
    elif allow_pinned:
        c, path = pinned_contract(cls)
        if c is None:
            return None
        fm, ver, h = c['field_map'], c['contract_version'], c['contract_hash']
        src = {'source': 'pinned', 'where': os.path.relpath(path, os.path.dirname(os.path.dirname(HERE))),
               'path': os.path.relpath(path, os.path.dirname(os.path.dirname(HERE))), 'sha256': sha256(open(path, 'rb').read())}
    else:
        return None
    text = render_c_header(cls, fm, int(msg_type), version=ver, contract_hash=h, target=target)
    return dict(src, text=text, sha256=sha256(text), tag_order=tag_order(fm), contract_version=ver, contract_hash=h, field_map=fm)


def combined_sha(class_rows):
    """The build-level header_sha256: the one header's sha, or a sha over 'class:sha' lines for several classes."""
    if len(class_rows) == 1:
        return class_rows[0]['header_sha256']
    return sha256('\n'.join('%s:%s' % (c['class'], c['header_sha256']) for c in class_rows))


def _plain_order(order):
    return ', '.join(order) if order else '(none)'


def check(build, manager=None):
    """build: a FirmwareBuild row or dict (classes_json carries per-class header_sha256 / msg_type / target; the row's
    tag_order_json the order at gen time). → {verdict, classes: [...], plain}."""
    get = (lambda k, d='': build.get(k, d)) if isinstance(build, dict) else (lambda k, d='': getattr(build, k, d))
    try:
        classes = json.loads(get('classes_json', '[]') or '[]')
        orders = json.loads(get('tag_order_json', '{}') or '{}')
    except ValueError:
        classes, orders = [], {}
    if not classes:
        return {'verdict': 'unknown-class', 'classes': [], 'plain': 'this build lists no classes — it is not Polari firmware (nothing a bridge could read)'}
    out, worst = [], 'compatible'
    for i, c in enumerate(classes):
        cls = c.get('class', '')
        mt, target = int(c.get('msg_type') or (i + 1)), c.get('target') or 'avr'
        built_sha, built_order = c.get('header_sha256', ''), orders.get(cls) or c.get('tag_order') or []
        now = server_header(manager, cls, mt, target)
        row = {'class': cls, 'msg_type': mt, 'target': target, 'built_sha256': built_sha, 'built_order': built_order}
        if now is None:
            row.update(verdict='unknown-class', why='this server knows no contract for %s (no gRPC exposure and no pinned snapshot) — '
                                                    'the firmware speaks a class the server cannot read' % cls)
            worst = 'unknown-class'
        else:
            row.update(now_sha256=now['sha256'], now_order=now['tag_order'], source=now['source'], where=now['where'],
                       contract_version=now['contract_version'], contract_hash=now['contract_hash'])
            if built_sha and built_sha == now['sha256']:
                row.update(verdict='compatible', why='the %s header is byte-identical to what this server generates now (%s)' % (cls, now['where']))
            elif built_order and built_order != now['tag_order']:
                row.update(verdict='stale-header', why='the firmware puts %s on the wire as %s; this server now expects %s — they would '
                                                       'misread each other\'s bytes. Regenerate it against this server.'
                                                       % (cls, _plain_order(built_order), _plain_order(now['tag_order'])))
            else:
                row.update(verdict='stale-header', why='the %s header differs from what this server generates now (same field order, but '
                                                       'generated from another contract version or msg_type) — regenerate it' % cls)
            if row['verdict'] != 'compatible' and worst == 'compatible':
                worst = 'stale-header'
        out.append(row)
    plain = '; '.join(r['why'] for r in out)
    return {'verdict': worst, 'classes': out, 'plain': plain}
