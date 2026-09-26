"""
EXPLAIN ONE ROW (bp-3, his ask 2026-09-25: "source ref and other refs and conditions don't really make coherent sense
to me … Per row we likely need a human explainable row and an understanding of what was done and how to duplicate it").

    GET /api/explain?class=CharacterizationMapping&name=lod1:%20rv32_add%20gate%20count
    GET /api/explain/{class}/{name}
        → {"ok": true,
           "in one sentence":  "...",                       what this row says, for a person
           "what was done":    "...",                       the act: who did what to what, with which tool
           "inputs":           {"source": ..., ...},        the things it was done TO / under (conditions in words)
           "result":           "220 cells",
           "how to reproduce": ["cd polari-rf-node/polari-framework", "PYTHONPATH=.:modules python3 -m ... run", ...],
           "evidence":         "...",                       where the number was read from
           "how far to trust it": "...",                    the evidence level / status, in words
           "related":          [{"class": ..., "name": ...}],
           "explained_by":     "computelod.custom.explain" | "generic (the class's field comments)"}

A module explains its own rows: `<module>.custom.explain` exports `EXPLAINERS = {'<Class>': fn(manager, row) -> dict}`.
Any class without one gets the GENERIC explanation: every field as a sentence, labelled by the comment the class
source carries beside it (`self.method = method  # OpenSTA | ngspice | …`), so nothing is a bare column name.
The object detail page (/object/:class/:name) reads this door first and shows it above the record.
"""
import importlib
import inspect
import json
import re

import falcon

from objectTreeDecorators import treeObject, treeObjectInit
from polariApiServer.plainWordsAPI import class_object, plain_words_of, _title

_FIELD_COMMENT = re.compile(r'^\s*self\.(\w+)\s*=\s*\w+\s*#\s*(.+?)\s*$')


def field_comments(cls):
    """{field: the comment beside its assignment in __init__} — the class's own words for each column."""
    out = {}
    try:
        src = inspect.getsource(cls)
    except Exception:
        return out
    for line in src.splitlines():
        m = _FIELD_COMMENT.match(line)
        if m:
            out[m.group(1)] = m.group(2)
    return out


def words(value, depth=0):
    """A JSON-ish value as words: {"voltage": 1.8, "corner": "tt"} → 'voltage 1.8; corner tt'."""
    if value is None or value == '':
        return ''
    if isinstance(value, str):
        s = value.strip()
        if s[:1] in '{[' and depth == 0:
            try:
                return words(json.loads(s), depth + 1)
            except Exception:
                return s
        return s
    if isinstance(value, bool):
        return 'yes' if value else 'no'
    if isinstance(value, (int, float)):
        return ('%g' % value) if isinstance(value, float) else str(value)
    if isinstance(value, dict):
        return '; '.join('%s %s' % (k.replace('_', ' '), words(v, depth + 1)) for k, v in value.items())
    if isinstance(value, (list, tuple)):
        return ', '.join(words(v, depth + 1) for v in value)
    return str(value)


def generic_explain(manager, row):
    cls = type(row)
    comments = field_comments(cls)
    plain, _src = plain_words_of(cls)
    fields = {}
    for k, v in vars(row).items():
        if k.startswith('_') or k in ('id', 'manager', 'name') or v in (None, '', '[]', '{}'):
            continue
        label = k.replace('_json', '').replace('_', ' ')
        note = comments.get(k, '')
        fields[label + ((' (' + note + ')') if note else '')] = words(v)
    desc = str(getattr(row, 'description', '') or '')
    return {'in one sentence': desc or ('%s %r%s' % (_title(cls.__name__), str(row.name), (' — ' + plain) if plain else '')),
            'what was done': 'no module-specific account exists for %s yet; the fields below carry the class\'s own comment for each column' % _title(cls.__name__),
            'inputs': fields, 'how to reproduce': ['no reproduction recipe is written for %s rows yet — the row\'s provenance / evidence fields above say where it came from' % cls.__name__],
            'explained_by': 'generic (the class\'s field comments)'}


def explainer_for(cls):
    pkg = (cls.__module__ or '').split('.')[0]
    if not pkg:
        return None
    try:
        mod = importlib.import_module('%s.custom.explain' % pkg)
    except Exception:
        return None
    return (getattr(mod, 'EXPLAINERS', None) or {}).get(cls.__name__)


def explain(manager, class_name, name):
    rows = (getattr(manager, 'objectTables', None) or {}).get(class_name) or {}
    row = next((r for r in rows.values() if str(getattr(r, 'name', '')) == name), None)
    if row is None:
        cls = class_object(manager, class_name)
        return {'ok': False, 'status': 404, 'error': ('no %s named %r on this instance' % (class_name, name)) if cls is not None else ('no class %r on this instance' % class_name)}
    cls = type(row)
    fn = explainer_for(cls)
    body = None
    if fn is not None:
        try:
            body = fn(manager, row)
            body.setdefault('explained_by', '%s.custom.explain' % cls.__module__.split('.')[0])
        except Exception as exc:
            body = None
            fallback_note = 'the module explainer failed (%s); the generic account follows' % exc
    if body is None:
        body = generic_explain(manager, row)
        if fn is not None:
            body['note'] = fallback_note
    plain, _src = plain_words_of(cls)
    out = {'ok': True, 'class': class_name, 'name': name, 'kind of object': plain}
    for k in ('in one sentence', 'what was done', 'inputs', 'result', 'how to reproduce', 'evidence', 'how far to trust it', 'related', 'note', 'explained_by'):
        if k in body:
            out[k] = body[k]
    for k, v in body.items():
        out.setdefault(k, v)
    return out


class ExplainAPI(treeObject):
    """The explain door: GET /api/explain?class=&name= or /api/explain/{class}/{name}."""

    @treeObjectInit
    def __init__(self, polServer, manager=None):
        self.polServer = polServer
        self.apiName = '/api/explain'
        if polServer is not None:
            polServer.falconServer.add_route(self.apiName, self)
            polServer.falconServer.add_route(self.apiName + '/{class_name}/{name}', self, suffix='path')

    def _answer(self, response, class_name, name):
        if not class_name or not name:
            response.status = falcon.HTTP_400
            response.media = {'ok': False, 'error': '?class=<Class>&name=<row name>'}
            return
        body = explain(self.manager, class_name, name)
        response.status = falcon.HTTP_404 if body.get('status') == 404 else falcon.HTTP_200
        response.media = body
        response.set_header('Powered-By', 'Polari')

    def on_get(self, request, response):
        self._answer(response, (request.get_param('class') or '').strip(), (request.get_param('name') or '').strip())

    def on_get_path(self, request, response, class_name, name):
        self._answer(response, class_name, name)
