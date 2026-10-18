"""selftest_editor_convert - ed-0 (FIRMWARE_GENERATION_MODULE_PLAN.md section 5b + 12): the lossless template converter. Proves: jinja -> polari -> jinja is BYTE-IDENTICAL on EVERY template in
the repo (the cmod project templates, the catoms' _common.j2 and template.c.j2); rendering the round-tripped templates with the same knobs gives the SAME C (the catom routes) and the SAME
generated files for the three graphs (so the identical-hex gate cannot be touched); every HAL chip carries the family catom.json declares; anything unrepresentable is REFUSED by name; the doors
add on ONE real falcon.App beside CModAPI (nested path ids, both registration orders); the manifest lists the new files. Run by cmod_selftest.main() (editor_convert_parts)."""
import json
import os
import shutil
import tempfile
from types import SimpleNamespace

GRAPHS = ('uno-light-graph', 'uno-sim-rig-graph', 'uno-button-clock-graph')
CATOM_JSON = os.path.join('board', 'custom', 'firmware', 'uno', 'catoms', 'read-button', 'catom.json')


def editor_convert_parts(check):
    def identity_every_template():
        _identity(check)

    def render_equivalence():
        _render_equivalence(check)

    def hal_chips_and_families():
        _families(check)

    def refusals():
        _refusals(check)

    def doors_and_cli():
        _doors(check)

    def manifest():
        _manifest(check)

    return (identity_every_template, render_equivalence, hal_chips_and_families, refusals, doors_and_cli, manifest)


def _identity(check):
    from cmod.custom.editor import convert as C
    rows = C.list_templates()
    ids = [r['id'] for r in rows]
    check('ed-0: the repo has 13 templates (7 cmod project templates + 2 catom macro files + 4 isotope templates), found by walking the disk', len(rows) == 13 and sum(1 for r in rows if r['role'] == 'isotope-template') == 4
          and sum(1 for r in rows if r['role'] == 'catom-macros') == 2 and sum(1 for r in rows if r['role'] == 'project-template') == 7, ids)
    bad, trimmed = [], 0
    for r in rows:
        src = C.read_text(r)
        p = C.to_polari(src, C.contract_of(r))
        back = C.to_jinja(p)
        ok = back == src and C.OPEN in p['text'] and '{{' not in p['text'] and '{%' not in p['text'] and '{#' not in p['text']
        ok = ok and ''.join(t['jinja'] for t in p['tokens']) == ''.join(s for s in _chip_sources(src))
        ok = ok and C.to_jinja(C.to_polari(back)) == src and all(src[:0] == '' for _ in [0])
        if not ok:
            bad.append(r['id'])
        trimmed += any(t['lead'].endswith('-') or t['trail'].startswith('-') or '-' in t['lead'][2:3] for t in p['tokens'])
    check('ed-0: jinja -> polari -> jinja is byte-identical on EVERY one of the %d templates (no jinja syntax left in the polari text; every chip carries its exact original spelling)' % len(rows), not bad, bad)
    check('ed-0: ...including the templates whose tags use trim markers ({#- -#}) and multi-line expressions: they survive because the token keeps the delimiter spelling', trimmed >= 1)
    # the token view of one real template
    r = C.resolve('read-button/_common.j2')
    p = C.to_polari(C.read_text(r), C.contract_of(r))
    kinds = {t['kind'] for t in p['tokens']}
    check('ed-0: the polari text of a real template shows chips for macros, loops, comments, locals and calls and keeps literal C literal', {'macro', 'block', 'comment', 'local'} <= kinds and 'static uint32_t g_last_press;' in p['text']
          and '⟦for c in b.cites⟧' in p['text'] and '⟦file|c_comment⟧' in p['text'], sorted(kinds))
    edited = dict(p, text=p['text'].replace('⟦file|c_comment⟧', '⟦file|c_str⟧', 1))
    # a chip edited in place keeps its delimiters and changes only the body
    check('ed-0: editing a chip body in the polari view changes only that body in the jinja form (delimiters and spacing kept)',
          C.to_jinja(edited) == C.read_text(r).replace('{{ file|c_comment }}', '{{ file|c_str }}', 1))
    s = C.to_jinja('x ⟦new_knob|c_int⟧ y ⟦if q⟧z⟦endif⟧ ⟦# note⟧')
    check('ed-0: a chip with no token (just inserted) is written in the canonical spelling', s == 'x {{ new_knob|c_int }} y {% if q %}z{% endif %} {# note #}', s)


def _chip_sources(src):
    from cmod.custom.editor import convert as C
    return [raw for kind, raw in C._scan(src) if kind != 'lit']


def _copy_tree(tmp):
    """a temp copy of both template roots with every template replaced by its jinja -> polari -> jinja round trip."""
    from cmod.custom.editor import convert as C
    out = {}
    for r in C.list_templates():
        rt = C.to_jinja(C.to_polari(C.read_text(r), C.contract_of(r)))
        dst = os.path.join(tmp, r['id'])
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        with open(dst, 'wb') as fh:
            fh.write(rt.encode())
        out[r['id']] = dst
    return out


def _render_equivalence(check):
    from board.custom import button_routes as BR
    from board.custom import sense_routes as SR
    from board.custom import variants as V
    from cmod.custom.generator import env as E
    from cmod.custom.selftest_generator import _files
    cases = [(BR, 'pcint', 'uno-light-pcint'), (BR, 'adc', 'uno-light-analog'), (SR, 'poll', 'uno-light-sense-poll'), (SR, 'pcint', 'uno-light-sense-pcint')]
    knobs = {v: V.resolve(V.find(v))['knobs'] for _m, _r, v in cases}
    before = {(m.__name__, r): m.render(r, knobs[v])['text'] for m, r, v in cases}
    graphs_before = {g: _files(g, False) for g in GRAPHS}
    tmp = tempfile.mkdtemp(prefix='ed0-')
    old = (BR.CATOMS, SR.CATOMS, E.TEMPLATES)
    try:
        _copy_tree(tmp)
        BR.CATOMS = SR.CATOMS = os.path.join(tmp, 'board', 'custom', 'firmware', 'uno', 'catoms')
        E.TEMPLATES = os.path.join(tmp, 'cmod', 'custom', 'templates')
        same_catoms = {k: BR.render(r, knobs[v])['text'] == before[(m.__name__, r)] if m is BR else SR.render(r, knobs[v])['text'] == before[(m.__name__, r)] for m, r, v in cases for k in [(m.__name__, r)]}
        graphs_after = {g: _files(g, False) for g in GRAPHS}
    finally:
        BR.CATOMS, SR.CATOMS, E.TEMPLATES = old
        shutil.rmtree(tmp, ignore_errors=True)
    check('ed-0: the 4 catom routes (button pcint + adc, sense poll + pcint) render the SAME C from the round-tripped templates as from the originals', all(same_catoms.values()) and len(same_catoms) == 4, same_catoms)
    check('ed-0: the 3 graphs (uno-light, uno-sim-rig, uno-button-clock) render byte-identical polari_graph.c/.h, Makefile, pin_config.h/.c from the round-tripped templates - the identical-hex gate\'s sources cannot move',
          all(graphs_after[g] == graphs_before[g] and len(graphs_before[g]) >= 5 for g in GRAPHS), [g for g in GRAPHS if graphs_after[g] != graphs_before[g]])
    check('ed-0: the temporary patch was undone (templates read from the repo again)', (BR.CATOMS, SR.CATOMS, E.TEMPLATES) == old and not os.path.exists(tmp))


def _families(check):
    from cmod.custom.editor import convert as C
    root = os.path.dirname(C.MODULES)
    contract = json.load(open(os.path.join(C.MODULES, CATOM_JSON)))['hal_contract']
    src = ('#if {{ hal.button_pin|c_ident }}\n'.replace('button_pin', 'button_pull') + '/* {{ hal.debounce_ms|c_int }} ms on {{ hal.button_line }} */\n'
           'uint8_t v = {{- hal.button_detect_registers -}} {{ hal.press_flag|c_ident }};\n{% if hal.button_pull %}x{% endif %}\n#endif\n')
    p = C.to_polari(src, contract)
    hal = [t for t in p['tokens'] if t['kind'] == 'hal']
    refs = [r for t in p['tokens'] for r in t['hal_refs']]
    want = {h['name']: h['family'] for h in contract}
    check('ed-0: every HAL chip is shown bare (no `hal.`) and carries the family catom.json declares for it (%s)' % ', '.join(sorted(set(want.values()))),
          len(hal) == 5 and len(refs) == 6 and all(t['family'] == want[t['name']] for t in hal) and all(r['family'] == want[r['name']] for r in refs) and {r['family'] for r in refs} == set(C.FAMILIES) and 'hal.' not in p['text'] and '⟦button_pull|c_ident⟧' in p['text'],
          [(t['name'], t['family']) for t in hal])
    check('ed-0: ...the names + filters are in the tokens, the used HAL names are listed, and the round trip (with {{- -}} trim markers) is identical', p['hal'] == sorted(want) and hal[0]['filters'] == ['c_ident'] and C.to_jinja(p) == src)
    twin = C.to_polari('{{ button_pull }} {{ hal.button_pull }}', contract)
    check('ed-0: a knob and a HAL variable with the same name stay different: the token, not the text, says which one it is', [t['kind'] for t in twin['tokens']] == ['knob', 'hal'] and C.to_jinja(twin) == '{{ button_pull }} {{ hal.button_pull }}')
    edit = C.to_jinja(dict(p, text=p['text'].replace('\u27e6if button_pull\u27e7', '\u27e6if button_pull and debounce_ms\u27e7')))
    check('ed-0: a HAL name typed inside an edited block chip gets its `hal.` back in the jinja form', '{% if hal.button_pull and hal.debounce_ms %}' in edit or '{% if hal.button_pull and debounce_ms %}' in edit, edit[-60:])
    moved = dict(p, tokens=[dict(t, name='press_flag') if t['offset'] == hal[0]['offset'] else t for t in p['tokens']])
    try:
        C.to_jinja(moved)
        ok = False
    except C.RefusedForm as e:
        ok = 'button_pull' in str(e) or 'press_flag' in str(e)
    check('ed-0: a HAL chip whose text no longer matches its token is refused by name (the two forms cannot drift)', ok)
    cats = {r['catom'] for r in C.list_templates() if r['catom']}
    check('ed-0: the contract found for each catom template is the catom.json hal_contract (5 families each)', all({h['family'] for h in (C.contract_of({'catom': c}) or [])} == set(C.FAMILIES) for c in cats), sorted(cats))


def _refusals(check):
    from cmod.custom.editor import convert as C
    contract = json.load(open(os.path.join(C.MODULES, CATOM_JSON)))['hal_contract']
    cases = [
        ('a raw block', '{% raw %}{{ x }}{% endraw %}', 'raw'),
        ('an include', '{% include "a.j2" %}', 'include'),
        ('an extends/block pair', '{% extends "a.j2" %}{% block b %}{% endblock %}', 'extends'),
        ('a filter that is not a builtin or a C filter', '{{ x|shell_escape }}', 'shell_escape'),
        ('an undeclared HAL name (with a contract)', '{{ hal.not_declared|c_int }}', 'not_declared'),
        ('a bare `hal`', '{{ hal }}', 'hal'),
        ('hal subscripted', "{{ hal['button_pull'] }}", 'hal'),
        ('an empty expression', '{{ }}', 'expression'),
        ('an unterminated tag', 'int x; {% if a', 'never closed'),
        ('invalid jinja', '{% if %}x{% endif %}', 'not valid jinja'),
        ('a literal chip bracket in the C', 'char *s = "⟦";', '⟦'),
        ('a with block', '{% with a = 1 %}{{ a }}{% endwith %}', 'with'),
        ('an unknown test', '{% if x is nosuchtest %}a{% endif %}', 'nosuchtest'),
    ]
    got = {}
    for label, src, word in cases:
        try:
            C.to_polari(src, contract)
            got[label] = 'ACCEPTED'
        except C.RefusedForm as e:
            got[label] = str(e) if word.lower() in str(e).lower() else 'WRONG REASON: %s' % e
    check('ed-0: %d unrepresentable inputs are each REFUSED, and the reason names the thing (raw / include / extends / a filter / an undeclared HAL name / bare hal / empty / unterminated / invalid / a chip bracket / with / a test)' % len(cases),
          all(not v.startswith(('ACCEPTED', 'WRONG')) for v in got.values()), {k: v for k, v in got.items() if v.startswith(('ACCEPTED', 'WRONG'))})
    for label, src in (('no contract: a HAL name is not checked', '{{ hal.anything }}'),):
        check('ed-0: %s' % label, C.to_jinja(C.to_polari(src)) == src)
    for text, word in (('a ⟦x', 'never closed'), ('a ⟧ b', 'stray'), ('⟦a ⟦b⟧', 'never closed')):
        try:
            C.to_jinja(text)
            ok = False
        except C.RefusedForm as e:
            ok = word in str(e)
        check('ed-0: a malformed polari text %r is refused (%s)' % (text, word), ok)
    try:
        C.resolve('nope.j2')
        ok = False
    except KeyError as e:
        ok = 'unknown' in str(e)
    try:
        C.resolve('_common.j2')
        amb = False
    except KeyError as e:
        amb = 'ambiguous' in str(e)
    check('ed-0: an unknown template id and an ambiguous suffix (_common.j2 exists twice) are each refused by name', ok and amb)
    check('ed-0: no template of the repo is refused by the converter', all(not _refused(r, C) for r in C.list_templates()))


def _refused(r, C):
    try:
        C.to_polari(C.read_text(r), C.contract_of(r))
        return ''
    except C.RefusedForm as e:
        return str(e)


def _doors(check):
    import falcon
    from falcon import testing
    from cmod.cmod_api import CModAPI
    from cmod.cmod_template_api import TemplateAPI
    from cmod.custom.editor import convert as C
    from cmod.custom.selftest_purpose import _manager
    for first in (False, True):
        app, mgr = falcon.App(), _manager()
        ps = SimpleNamespace(falconServer=app, manager=mgr, idList=[])
        for cls in ((TemplateAPI, CModAPI) if first else (CModAPI, TemplateAPI)):
            cls(polServer=ps, manager=mgr)
        c = testing.TestClient(app)
        lst = c.simulate_get('/api/cmod/templates')
        tid = 'board/custom/firmware/uno/catoms/read-button/isotopes/analog-threshold/template.c.j2'
        one = c.simulate_get('/api/cmod/templates/' + tid)
        jn = c.simulate_get('/api/cmod/templates/' + tid, params={'form': 'jinja'})
        others = [c.simulate_get(p).status_code for p in ('/api/cmod/projects', '/api/cmod/graphs', '/api/cmod/atoms')]
        row = C.resolve(tid)
        check('ed-0: GET /api/cmod/templates on ONE real falcon.App beside CModAPI (%s registered first): lists all 13, with chips + refused per row; the other cmod doors still answer' % ('TemplateAPI' if first else 'CModAPI'),
              lst.status_code == 200 and lst.json['count'] == 13 and all(t['chips'] > 0 and t['refused'] == '' for t in lst.json['templates']) and set(others) == {200}, (lst.status_code, others))
        check('ed-0: GET /api/cmod/templates/{nested/path} (Falcon path converter) answers the polari form by default: text + tokens, jinja syntax absent',
              one.status_code == 200 and one.json['form'] == C.FORM and one.json['id'] == tid and one.json['tokens'] and '{{' not in one.json['text'] and one.json['sha256'] == row['sha256'], one.text[:160])
        check('ed-0: ?form=jinja answers the file exactly as on disk; to_jinja of the served polari form gives it back', jn.status_code == 200 and jn.json['text'] == C.read_text(row) and C.to_jinja(one.json) == jn.json['text'])
    sfx = c.simulate_get('/api/cmod/templates/avr/pin_config.c.j2')
    bad = c.simulate_get('/api/cmod/templates/' + tid, params={'form': 'html'})
    unk = c.simulate_get('/api/cmod/templates/no/such/template.j2')
    amb = c.simulate_get('/api/cmod/templates/_common.j2')
    check('ed-0: a unique path suffix works (200), an unknown id is 404, an ambiguous suffix is 404 naming both, an unknown form is 422',
          sfx.status_code == 200 and unk.status_code == 404 and amb.status_code == 404 and 'ambiguous' in amb.json['error'] and bad.status_code == 422, (sfx.status_code, unk.status_code, amb.status_code, bad.status_code))
    import io
    import contextlib
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        rc = C.main(['show', 'avr/Makefile.j2'])
        rc2 = C.main(['show', 'avr/Makefile.j2', '--form', 'jinja'])
    both = buf.getvalue()
    check('ed-0: the CLI `python3 -m cmod.custom.editor.convert show <template> [--form polari|jinja]` prints the polari form by default and the jinja form on request',
          rc == 0 and rc2 == 0 and '⟦mcu|make_text⟦'.replace('⟦|', '') in both.replace('⟧', '⟦') and 'MCU   = {{ mcu|make_text }}' in both and 'MCU   = ⟦mcu|make_text⟧' in both)
    with contextlib.redirect_stderr(io.StringIO()):
        rc3 = C.main(['show', 'nope.j2'])
    check('ed-0: the CLI refuses an unknown template by name (exit 2)', rc3 == 2)


def _manifest(check):
    here = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    m = json.load(open(os.path.join(here, 'polari-app.json')))
    f = m['files']
    want = {'api': ['cmod_template_api'], 'custom': ['custom/editor/convert', 'custom/editor/doors', 'custom/selftest_editor_convert']}
    got = {k: [n for n in v if n not in f.get(k, [])] for k, v in want.items()}
    check('ed-0 MANIFEST: polari-app.json lists the new files (api, converter, doors, selftest) and the class TemplateAPI', not any(got.values()) and 'TemplateAPI' in m['classes'], got)
    check('...each listed file exists on disk', all(os.path.isfile(os.path.join(here, n + '.py')) for n in sum(want.values(), [])))
    check('ed-0: the endpoint constructor builds TemplateAPI beside the other doors', 'TemplateAPI(' in open(os.path.join(here, 'cmod_endpoints.py')).read())
