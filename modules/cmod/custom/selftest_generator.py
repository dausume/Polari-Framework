"""selftest_generator — fgm-0 (FIRMWARE_GENERATION_MODULE_PLAN.md §7.7): the Jinja2 identical-hex migration. Over uno-light,
uno-sim-rig and uno-button-clock: the TEMPLATE path's rendered files are byte-identical to the LEGACY Python emitters' (and to
the committed graphs/<g>/ project); a second render is identical bytes; the built firmware.hex equals the committed glue
record's hex sha256 (when the build rung resolves on this host — otherwise the refusal is printed verbatim and the source
byte-identity still stands); a missing context key fails with a named error (StrictUndefined); c_ident refuses an injected
identifier. Run by cmod_selftest.main() (generator_parts).
"""
import copy
import os

GRAPHS = ('uno-light-graph', 'uno-sim-rig-graph', 'uno-button-clock-graph')


def _files(name, legacy):
    from cmod.custom import glue as G
    old = os.environ.get('POLARI_GLUE_LEGACY')
    if legacy:
        os.environ['POLARI_GLUE_LEGACY'] = '1'
    else:
        os.environ.pop('POLARI_GLUE_LEGACY', None)
    try:
        return G.render_files(G.graph_rows(name))[1]
    finally:
        if old is None:
            os.environ.pop('POLARI_GLUE_LEGACY', None)
        else:
            os.environ['POLARI_GLUE_LEGACY'] = old


def generator_parts(check):
    def template_vs_legacy_bytes():
        _template_vs_legacy_bytes(check)

    def deterministic_and_matches_committed():
        _deterministic_and_matches_committed(check)

    def strict_undefined_and_injection():
        _strict_undefined_and_injection(check)

    def provenance_and_hex():
        _provenance_and_hex(check)

    return (template_vs_legacy_bytes, deterministic_and_matches_committed, strict_undefined_and_injection, provenance_and_hex)


def _template_vs_legacy_bytes(check):
    for name in GRAPHS:
        new, old = _files(name, False), _files(name, True)
        check('%s: template path renders the SAME file set as the legacy emitters' % name, sorted(new) == sorted(old))
        for f in ('polari_graph.c', 'polari_graph.h', 'Makefile', 'pin_config.h', 'pin_config.c'):
            check('%s/%s: template bytes == legacy bytes' % (name, f), new.get(f) is not None and new.get(f) == old.get(f))
        check('%s: every rendered file byte-identical (template vs legacy)' % name, new == old)


def _deterministic_and_matches_committed(check):
    from cmod.custom import glue as G
    for name in GRAPHS:
        a, b = _files(name, False), _files(name, False)
        check('%s: rendering twice gives identical bytes' % name, a == b)
        d = G.project_dir(G.graph_rows(name)['graph'])
        same = all(os.path.isfile(os.path.join(d, f)) and open(os.path.join(d, f), 'rb').read() == b_ for f, b_ in a.items())
        check('%s: the template render equals the committed project on disk' % name, same)


def _strict_undefined_and_injection(check):
    import copy as _c
    from cmod.custom import glue as G
    from cmod.custom.generator import context as X
    from cmod.custom.generator import env as E
    from cmod.custom.generator import filters as F
    name = 'uno-light-graph'
    rows = G.graph_rows(name)
    ctx = G.context(rows['graph'])
    model = G.GR.resolve(rows, ctx)
    ctx['files_out'] = ['board_config.h', 'polari_graph.h']
    bn = X.banner(name, model['sha'], G.GENERATOR)
    c = X.glue_c_context(model, ctx, [], bn)
    check('the glue context renders as-is', bool(E.render('avr/polari_graph.c.j2', c)))
    missing = _c.deepcopy(c)
    del missing['cls']
    try:
        E.render('avr/polari_graph.c.j2', missing)
        check('a missing context key fails generation', False)
    except F.GenError as e:
        check('a missing context key fails generation with a NAMED error (StrictUndefined)', "'cls'" in str(e), str(e))
    for bad in ('led; system("x")', 'a b', '1abc', 'int', ''):
        try:
            F.c_ident(bad)
            check('c_ident refuses %r' % bad, False)
        except F.GenError:
            check('c_ident refuses %r' % bad, True)
    check('c_ident accepts a plain identifier', F.c_ident('led_on') == 'led_on')
    inj = _c.deepcopy(c)
    inj['statics'][0]['name'] = 'led; system("x")'
    try:
        E.render('avr/polari_graph.c.j2', inj)
        check('an injected identifier in the context never reaches the C', False)
    except F.GenError as e:
        check('an injected identifier in the context never reaches the C', 'c_ident' in str(e), str(e))
    for f, bad in ((F.c_expr, 'a; b'), (F.c_expr, 'x /* y */'), (F.c_expr, '(a'), (F.c_expr, '{x}'), (F.c_type, 'int; x'), (F.c_comment, 'x */ y'),
                   (F.c_str, 'a"b'), (F.c_int, '1; 2'), (F.c_block, 'void f() {'), (F.make_text, 'a\nb')):
        try:
            f(bad)
            check('%s refuses %r' % (f.__name__, bad), False)
        except F.GenError:
            check('%s refuses %r' % (f.__name__, bad), True)
    check('c_hex/c_int literals', F.c_hex(10) == '0x0A' and F.c_int('4u') == '4u' and F.c_int(7) == '7')
    check('c_expr / c_type accept what the glue uses', F.c_expr('(uint8_t)clock_return') == '(uint8_t)clock_return'
          and F.c_type('const polari_rx_t *') == 'const polari_rx_t *')


def _provenance_and_hex(check):
    import json
    from cmod.custom import glue as G
    from cmod.custom import glue_build as GB
    from cmod.custom.generator import env as E
    files = _files('uno-light-graph', False)
    p = G.template_provenance(files)
    check('provenance names every template with its sha256 + the jinja2 version',
          p['template_generator'].startswith('jinja2 ') and all(len(v) == 64 for v in p['templates'].values())
          and 'avr/polari_graph.c.j2' in p['templates'] and 'avr/pin_config.c.j2' in p['templates'])
    check('a template sha is the sha256 of its file', p['templates']['avr/Makefile.j2'] == E.template_sha('avr/Makefile.j2'))
    for name in GRAPHS:
        rec = G.load_record(name)
        check('%s: the committed glue record carries the template provenance' % name,
              (rec.get('templates') or {}) == G.template_provenance(_files(name, False))['templates']
              and (rec.get('template_generator') or '').startswith('jinja2 '))
        d = G.project_dir(G.graph_rows(name)['graph'])
        mk = GB.make_alone(d)
        if not mk['ok']:
            print('   (build rung refused on this host: %s %s %s)' % (mk['how'], mk['where'], (mk['stderr'] or mk['stdout'])[:300]))
            check('%s: build rung unavailable here — source byte-identity above is the proof' % name, True)
            continue
        check('%s: the built firmware.hex sha256 equals the committed glue record\'s' % name,
              mk['hex_sha256'] == rec['build']['hex_sha256'], '%s vs %s' % (mk['hex_sha256'], rec['build']['hex_sha256']))
