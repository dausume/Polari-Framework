"""
@module cmod.custom.editor.doors

ed-0 doors, plain functions over a TemplateAPI (`cmod_template_api` registers the routes and delegates here). Read-only.

GET /api/cmod/templates                         {ok, count, templates[{id, role, catom, isotope, bytes, sha256, chips, hal[], refused}]}
GET /api/cmod/templates/{id:path}[?form=polari|jinja]
        one template; the id is its modules-relative path (a unique path suffix also works). form=jinja (the file as it is on disk) |
        polari (default: {text, tokens[], hal[]}, see cmod.custom.editor.convert). 404 unknown / ambiguous id; 422 unknown form or a
        template the converter REFUSES (the reason names what and where).
"""
import falcon

from cmod.custom.editor import convert as C


def _fail(response, status, text):
    response.status = status
    response.media = {'ok': False, 'error': text}


def get_list(api, request, response):
    rows = []
    for r in C.list_templates():
        row = {k: r[k] for k in ('id', 'role', 'catom', 'isotope', 'bytes', 'sha256')}
        try:
            p = C.to_polari(C.read_text(r), C.contract_of(r))
            row.update(chips=len(p['tokens']), hal=p['hal'], refused='')
        except C.RefusedForm as e:
            row.update(chips=0, hal=[], refused=str(e))
        rows.append(row)
    response.media = {'ok': True, 'count': len(rows), 'templates': rows}


def get_one(api, request, response, tid):
    form = request.get_param('form') or 'polari'
    if form not in ('polari', 'jinja'):
        return _fail(response, falcon.HTTP_422, 'form %r: polari | jinja' % form)
    try:
        v = C.view(tid, form)
    except KeyError as e:
        return _fail(response, falcon.HTTP_404, str(e.args[0]))
    except C.RefusedForm as e:
        return _fail(response, falcon.HTTP_422, 'refused: %s' % e)
    response.media = dict(v, ok=True)
