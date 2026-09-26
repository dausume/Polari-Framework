"""
IN PLAIN WORDS (bp-2d, his ask 2026-09-25: "description sections that are toward the average person in most of
these kinds of objects, so people who are non experts can try and come to an understanding of it that is rougher").

    GET /api/plain?classes=TensorMapping,MathClaim[&module=mathproofs]
        → {"ok": true, "Tensor mapping": "<a paragraph a non-expert can read>", …, "missing": [...]}

The words live ON THE CLASS — a `plain_words` class attribute (one or two plain sentences, no jargon), falling back
to the first paragraph of the class docstring (the expert description) with a flag saying so. Nothing is stored:
the page's configured `api-structured-panel` reads this door and renders each value as prose (its strings longer
than a chip become paragraphs), so every module page can carry a "For anyone" section with no new component.
A class is found through the manager's live tables (the type of its rows) or its typing registry; an unknown
name is reported under `missing`, never invented.
"""
import re

import falcon

from objectTreeDecorators import treeObject, treeObjectInit


def _title(name):
    """CamelCase → 'Camel case' (a heading a person reads, not an identifier)."""
    s = re.sub(r'(?<!^)(?=[A-Z])', ' ', name).replace('_', ' ')
    return s[:1].upper() + s[1:].lower()


def class_object(manager, name):
    rows = (getattr(manager, 'objectTables', None) or {}).get(name) or {}
    for r in (rows.values() if hasattr(rows, 'values') else rows):
        return type(r)
    typing = (getattr(manager, 'objectTypingDict', None) or {}).get(name)
    if typing is not None:
        for attr in ('classObj', 'objectClass', 'polariClass', 'cls', 'className'):
            v = getattr(typing, attr, None)
            if isinstance(v, type):
                return v
    # a registered class with NO rows yet (seen live: TensorDecomposition) — find the imported class by name
    import sys
    for mod in list(sys.modules.values()):
        v = getattr(mod, name, None)
        if isinstance(v, type) and v.__name__ == name and issubclass(v, treeObject):
            return v
    return None


def plain_words_of(cls):
    """(text, source) — source is 'plain_words' or 'docstring' or ''."""
    if cls is None:
        return '', ''
    pw = getattr(cls, 'plain_words', '')
    if isinstance(pw, str) and pw.strip():
        return ' '.join(pw.split()), 'plain_words'
    doc = (cls.__doc__ or '').strip()
    if doc:
        first = re.split(r'\n\s*\n', doc)[0]
        return ' '.join(first.split()), 'docstring'
    return '', ''


def plain_words(manager, names):
    out, missing, from_doc = {}, [], []
    for name in names:
        cls = class_object(manager, name)
        text, source = plain_words_of(cls)
        if cls is None:
            missing.append(name)
            continue
        if not text:
            missing.append(name)
            continue
        if source == 'docstring':
            from_doc.append(name)
        out[_title(name)] = text
    return out, missing, from_doc


class PlainWordsAPI(treeObject):
    """The plain-words door: GET /api/plain?classes=A,B — each class explained for a non-expert."""

    @treeObjectInit
    def __init__(self, polServer, manager=None):
        self.polServer = polServer
        self.apiName = '/api/plain'
        if polServer is not None:
            polServer.falconServer.add_route(self.apiName, self)

    def on_get(self, request, response):
        names = [c.strip() for c in (request.get_param('classes') or '').split(',') if c.strip()]
        if not names:
            response.status = falcon.HTTP_400
            response.media = {'ok': False, 'error': '?classes=<Class>,<Class> names the object kinds to explain'}
            return
        words, missing, from_doc = plain_words(self.manager, names)
        body = {'ok': True}
        body.update(words)
        if from_doc:
            body['note'] = 'no plain-words text yet for %s — the expert description is shown instead' % ', '.join(_title(n) for n in from_doc)
        if missing:
            body['missing'] = ', '.join(missing)
        response.status = falcon.HTTP_200
        response.media = body
        response.set_header('Powered-By', 'Polari')
