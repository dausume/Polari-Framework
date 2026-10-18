"""
@module cmod.custom.editor.convert

ed-0 (FIRMWARE_GENERATION_MODULE_PLAN.md section 5b + 12): the LOSSLESS converter between the two forms of one C-atom template.

  JINJA FORM   what is on disk and what the generator renders. It is the ONLY source of truth.
  POLARI FORM  a VIEW computed from it (and parsed back): the same text, with every `{{ ... }}`, `{% ... %}` and `{# ... #}` shown as a
               CHIP written  ⟦ body ⟧  (U+27E6 / U+27E7). Literal C is untouched. The `hal.` prefix of a HAL variable is edited out:
               `{{ hal.button_pin|c_ident }}`  is shown  `⟦button_pin|c_ident⟧`.

  chip text   ⟦button_pin|c_ident⟧   a variable (HAL: `hal.` removed; a knob / context variable / macro call / expression: as written)
              ⟦for c in b.cites⟧ ... ⟦endfor⟧ , ⟦if x⟧ ⟦elif y⟧ ⟦else⟧ ⟦endif⟧   blocks
              ⟦import 'a/_common.j2' as L⟧ ⟦macro banner(file, b)⟧ ⟦endmacro⟧ ⟦call L.x('  ')⟧ ⟦endcall⟧ ⟦set ind = ...⟧   macros
              ⟦# text⟧   a comment

  The identity of a chip is carried by a TOKEN, not inferred from the text (a C identifier that shares a name is never turned into a
  variable): tokens = [{kind, name, family, filters, body, offset, end, lead, trail, jinja}], `offset`/`end` = where the chip sits in the
  polari text, `lead`/`trail` = the exact original delimiters with their whitespace and trim markers (`{%-  `, ` -%}`), `jinja` = the
  original spelling in full. kind: hal | knob | local | call | expr | block | macro | comment. `family` (drive / register / protocol / signal /
  execution) comes from the catom's `hal_contract`; a `local` is a name the template itself binds (macro argument, loop variable, set).

  A view edited in place keeps its chips and only changes bodies, so to_jinja pairs chips with tokens by ORDER when the counts agree and by the
  recorded `offset` otherwise (a chip inserted or removed).

  to_polari(jinja) -> {form, text, tokens, hal, refused: none};  to_jinja(polari) -> the jinja text, byte for byte for an unedited view.
  A chip with no token (one a person just inserted) is written in the canonical spelling `{{ body }}` / `{% body %}` / `{# body #}`; a
  HAL chip needs its token (text alone cannot tell `button_pin` the HAL variable from a knob of the same name).

  REFUSED, by name (RefusedForm), never normalised: text that is not valid jinja; a tag outside {if elif else endif for endfor import macro
  endmacro call endcall set endset} (raw, include, extends, block, from, with, filter, do ...); a filter that is not a jinja builtin or one of
  the generator's refusing C filters; `hal` used any way but `hal.<name>`; a HAL name the catom's hal_contract does not declare (when a
  contract is given); a literal ⟦ or ⟧ anywhere in the source; an empty `{{ }}`; a chip in a polari text that is unterminated or whose
  token disagrees with its text.
"""
import hashlib
import json
import os
import re
import sys

import jinja2
from jinja2 import nodes

from cmod.custom.generator import env as E

OPEN, CLOSE = '\u27e6', '\u27e7'
FORM = 'polari/1'
HERE = os.path.dirname(os.path.abspath(__file__))
MODULES = os.path.normpath(os.path.join(HERE, '..', '..', '..'))
ROOTS = (os.path.join(MODULES, 'cmod', 'custom', 'templates'), os.path.join(MODULES, 'board', 'custom', 'firmware'))
BLOCK_TAGS = frozenset('if elif else endif for endfor'.split())
MACRO_TAGS = frozenset('import macro endmacro call endcall set endset'.split())
FAMILIES = ('drive', 'register', 'protocol', 'signal', 'execution')
_HAL = re.compile(r'^hal\.([A-Za-z_][A-Za-z0-9_]*)(?![A-Za-z0-9_])')
_HEAD = re.compile(r'^[A-Za-z_][A-Za-z0-9_]*')
_WORD = re.compile(r'^([A-Za-z_]\w*)(?:\s|$)')


class RefusedForm(ValueError):
    """The converter cannot represent this losslessly. The message names what and where."""


# ------------------------------------------------------------------------------------------------ scanning the jinja form
def _line(text, pos):
    return text.count('\n', 0, pos) + 1


def _end_of(text, i, kind):
    """index just past the delimiter that closes the one opening at i (string literals inside `{{ }}` / `{% %}` are skipped)."""
    close = {'{{': '}}', '{%': '%}', '{#': '#}'}[kind]
    j = i + 2
    quote = None
    while j < len(text):
        ch = text[j]
        if kind != '{#':
            if quote:
                if ch == '\\':
                    j += 2
                    continue
                if ch == quote:
                    quote = None
            elif ch in '"\'':
                quote = ch
        if not quote and text.startswith(close, j):
            return j + 2
        j += 1
    raise RefusedForm('line %d: %s is never closed' % (_line(text, i), kind))


def _scan(text):
    """-> [(kind, raw)] with kind lit|var|stmt|com; the concatenation of the raws IS the text."""
    out, i, lit = [], 0, 0
    while i < len(text):
        if text[i] == '{' and i + 1 < len(text) and text[i + 1] in '{%#':
            k = text[i:i + 2]
            j = _end_of(text, i, k)
            if i > lit:
                out.append(('lit', text[lit:i]))
            out.append(({'{{': 'var', '{%': 'stmt', '{#': 'com'}[k], text[i:j]))
            i = lit = j
        else:
            i += 1
    if lit < len(text):
        out.append(('lit', text[lit:]))
    return out


def _split(raw):
    """raw delimiter text -> (lead, body, trail): lead/trail keep the delimiter, trim marker and the whitespace around the body."""
    inner = raw[2:-2]
    lm = inner[:1] if inner[:1] in ('-', '+') else ''
    inner = inner[len(lm):]
    tm = inner[-1:] if inner[-1:] in ('-', '+') else ''
    if tm:
        inner = inner[:-1]
    body = inner.strip()
    pre = inner[:len(inner) - len(inner.lstrip())]
    post = inner[len(inner.rstrip()):]
    return raw[:2] + lm + pre, body, post + tm + raw[-2:]


# ------------------------------------------------------------------------------------------------ checks over the whole template
def _check(text):
    try:
        env = E.environment()
        tree = env.parse(text)
    except jinja2.TemplateSyntaxError as e:
        raise RefusedForm('not valid jinja (line %s): %s' % (e.lineno, e.message))
    local = set()
    for n in tree.find_all(nodes.Filter):
        if n.name not in env.filters:
            raise RefusedForm('line %d: filter %r is neither a jinja builtin nor one of the generator\'s C filters' % (n.lineno, n.name))
    for n in tree.find_all(nodes.Test):
        if n.name not in env.tests:
            raise RefusedForm('line %d: test %r is unknown to jinja' % (n.lineno, n.name))
    for n in tree.find_all((nodes.Macro, nodes.CallBlock)):
        local.update(a.name for a in n.args)
    for n in tree.find_all(nodes.For):
        local.update(x.name for x in n.target.find_all(nodes.Name))
    for n in tree.find_all((nodes.Assign, nodes.AssignBlock)):
        local.update(x.name for x in n.target.find_all(nodes.Name))
    for n in tree.find_all(nodes.Import):
        local.add(n.target)
    for n in tree.find_all(nodes.Macro):
        local.add(n.name)
    return local


_STR = re.compile(r'("(?:\\.|[^"\\])*"|\'(?:\\.|[^\'\\])*\')')
_HALREF = re.compile(r'(?<![A-Za-z0-9_.])hal(?![A-Za-z0-9_])(\.[A-Za-z_][A-Za-z0-9_]*)?')


def _unhal(body, line):
    """body -> (display, [hal names]): every `hal.<name>` outside a string literal loses its prefix; a `hal` used any other way is refused."""
    names, parts = [], _STR.split(body)
    for k in range(0, len(parts), 2):
        def sub(m):
            if not m.group(1):
                raise RefusedForm('line %d: `hal` must be written hal.<name> (found %r)' % (line, body[:40]))
            names.append(m.group(1)[1:])
            return m.group(1)[1:]
        parts[k] = _HALREF.sub(sub, parts[k])
    return ''.join(parts), names


def _rehal(display, names):
    """the inverse of _unhal for a chip the person edited: the first-seen names get their `hal.` back (outside strings, not after a dot)."""
    if not names:
        return display
    parts = _STR.split(display)
    pat = re.compile(r'(?<![A-Za-z0-9_.])(%s)(?![A-Za-z0-9_])' % '|'.join(re.escape(n) for n in sorted(set(names), key=len, reverse=True)))
    for k in range(0, len(parts), 2):
        parts[k] = pat.sub(lambda m: 'hal.' + m.group(1), parts[k])
    return ''.join(parts)


def _classify(kind, body, locals_, contract, line):
    """-> token fields {kind, name, family, filters, hal_refs, display}. A `hal.<name>` anywhere in a chip is shown bare and listed in hal_refs."""
    if kind == 'com':
        return {'kind': 'comment', 'name': '', 'family': None, 'filters': [], 'hal_refs': [], 'display': '# ' + body}
    display, names = _unhal(body, line) if kind != 'com' else (body, [])
    fams = {h['name']: h.get('family') for h in contract} if contract is not None else {}
    for n in names:
        if contract is not None and n not in fams:
            raise RefusedForm('line %d: HAL variable %r is not declared in the catom\'s hal_contract (declare it first: name, family, kind)' % (line, n))
    refs = [{'name': n, 'family': fams.get(n)} for n in dict.fromkeys(names)]
    if kind == 'stmt':
        m = _HEAD.match(body)
        word = m.group(0) if m else ''
        if word not in BLOCK_TAGS and word not in MACRO_TAGS:
            raise RefusedForm('line %d: the tag {%% %s %%} cannot be shown in polari form (accepted: %s)'
                              % (line, word or body[:20], ' '.join(sorted(BLOCK_TAGS | MACRO_TAGS))))
        return {'kind': 'block' if word in BLOCK_TAGS else 'macro', 'name': word, 'family': refs[0]['family'] if refs else None, 'filters': [], 'hal_refs': refs, 'display': display}
    if not body:
        raise RefusedForm('line %d: an empty {{ }}' % line)
    filters = re.findall(r'\|\s*([A-Za-z_]\w*)', ''.join(_STR.split(body)[0::2]))
    m = _HAL.match(body)
    if m:
        return {'kind': 'hal', 'name': m.group(1), 'family': fams.get(m.group(1)), 'filters': filters, 'hal_refs': refs, 'display': display}
    fam = refs[0]['family'] if refs else None
    head = _HEAD.match(body)
    simple = re.match(r'^[A-Za-z_]\w*(\.[A-Za-z_]\w*|\[\s*\d+\s*\])*(\s*\|\s*[A-Za-z_]\w*(\([^()]*\))?)*$', body)
    if head and simple:
        return {'kind': 'local' if head.group(0) in locals_ else 'knob', 'name': head.group(0), 'family': None, 'filters': filters, 'hal_refs': refs, 'display': display}
    if head and re.match(r'^[A-Za-z_][\w.]*\(', body):
        return {'kind': 'call', 'name': re.match(r'^[A-Za-z_][\w.]*', body).group(0), 'family': fam, 'filters': filters, 'hal_refs': refs, 'display': display}
    return {'kind': 'expr', 'name': head.group(0) if head else '', 'family': fam, 'filters': filters, 'hal_refs': refs, 'display': display}


# ------------------------------------------------------------------------------------------------ the two conversions
def to_polari(jinja_text, contract=None):
    """jinja form -> {form, text, tokens, hal}. `contract` = the catom's hal_contract rows (or None: HAL names are then not checked)."""
    if OPEN in jinja_text or CLOSE in jinja_text:
        raise RefusedForm('line %d: the source contains a literal %s or %s, which the polari form uses as chip brackets' %
                          (_line(jinja_text, min(p for p in (jinja_text.find(OPEN), jinja_text.find(CLOSE)) if p >= 0)), OPEN, CLOSE))
    segs = _scan(jinja_text)
    locals_ = _check(jinja_text)
    out, tokens, pos, src = [], [], 0, 0
    for kind, raw in segs:
        if kind == 'lit':
            out.append(raw)
            pos += len(raw)
        else:
            line = _line(jinja_text, src)
            lead, body, trail = _split(raw)
            c = _classify(kind, body, locals_, contract, line)
            chip = OPEN + c.pop('display') + CLOSE
            tokens.append(dict(c, body=body, offset=pos, end=pos + len(chip), lead=lead, trail=trail, jinja=raw))
            out.append(chip)
            pos += len(chip)
        src += len(raw)
    text = ''.join(out)
    return {'form': FORM, 'text': text, 'tokens': tokens, 'hal': sorted({t['name'] for t in tokens if t['kind'] == 'hal'})}


def _chips(text):
    """-> [(start, end, display)] of the chips in a polari text; an unterminated or stray bracket is refused."""
    res, i = [], 0
    while i < len(text):
        o, c = text.find(OPEN, i), text.find(CLOSE, i)
        if o < 0 and c < 0:
            break
        if c >= 0 and (o < 0 or c < o):
            raise RefusedForm('polari text: a stray %s at offset %d' % (CLOSE, c))
        e = text.find(CLOSE, o + 1)
        n = text.find(OPEN, o + 1)
        if e < 0 or (0 <= n < e):
            raise RefusedForm('polari text: the chip opened at offset %d is never closed' % o)
        res.append((o, e + 1, text[o + 1:e]))
        i = e + 1
    return res


def _canonical(display):
    d = display.strip()
    if d.startswith('#'):
        return '{# %s #}' % d[1:].strip()
    w = _WORD.match(d)
    if w and w.group(1) in (BLOCK_TAGS | MACRO_TAGS):
        return '{%% %s %%}' % d
    if d in BLOCK_TAGS | MACRO_TAGS:
        return '{%% %s %%}' % d
    return '{{ %s }}' % d


def to_jinja(polari):
    """polari form ({text, tokens} or just the text) -> the jinja form. An unedited view gives back the original bytes."""
    text = polari if isinstance(polari, str) else polari['text']
    chips = _chips(text)
    given = [] if isinstance(polari, str) else sorted(polari.get('tokens', []), key=lambda t: t['offset'])
    # a view edited in place keeps its chips (only the bodies change, so later offsets shift): pair by order when the counts agree,
    # otherwise by the recorded offset (a chip inserted or removed) - a chip left with no token is written canonically
    toks = {c[0]: t for c, t in zip(chips, given)} if len(given) == len(chips) else {t['offset']: t for t in given}
    out, i = [], 0
    for s, e, disp in chips:
        out.append(text[i:s])
        t = toks.get(s)
        if t is None:
            out.append(_canonical(disp))
        else:
            body = disp[1:].strip() if t['kind'] == 'comment' else _rehal(disp, [r['name'] for r in t.get('hal_refs', [])])
            if t['kind'] == 'hal':
                m = _HAL.match(body)
                if not m or m.group(1) != t['name']:
                    raise RefusedForm('polari text: the HAL chip at offset %d no longer names %r (its token says so); insert a new chip instead' % (s, t['name']))
            out.append(t['jinja'] if body == t['body'] else t['lead'] + body + t['trail'])
        i = e
    out.append(text[i:])
    return ''.join(out)


# ------------------------------------------------------------------------------------------------ the templates of the repo
def _rel(path):
    return os.path.relpath(path, MODULES).replace(os.sep, '/')


def list_templates():
    """-> [{id, path, role, catom, isotope, bytes, sha256}] for every *.j2 under the cmod templates and the board firmware catoms."""
    rows = []
    for root in ROOTS:
        for d, _dirs, files in os.walk(root):
            for f in files:
                if f.endswith('.j2'):
                    p = os.path.join(d, f)
                    rid = _rel(p)
                    parts = rid.split('/')
                    cat = parts[parts.index('catoms') + 1] if 'catoms' in parts else ''
                    iso = parts[parts.index('isotopes') + 1] if 'isotopes' in parts else ''
                    data = open(p, 'rb').read()
                    rows.append({'id': rid, 'path': p, 'role': ('isotope-template' if iso else 'catom-macros' if cat else 'project-template'),
                                 'catom': cat, 'isotope': iso, 'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest()})
    return sorted(rows, key=lambda r: r['id'])


def resolve(tid):
    """a template id (modules-relative path) or any unambiguous path suffix -> its row; KeyError naming the choices otherwise."""
    rows = list_templates()
    exact = [r for r in rows if r['id'] == tid]
    hit = exact or [r for r in rows if r['id'].endswith('/' + tid.lstrip('/'))]
    if len(hit) != 1:
        raise KeyError('template %r: %s' % (tid, 'ambiguous: ' + ', '.join(r['id'] for r in hit) if hit else 'unknown (known: %d, see `show --list`)' % len(rows)))
    return hit[0]


def contract_of(row):
    """the catom's hal_contract rows for a catom template, else None."""
    if not row['catom']:
        return None
    p = os.path.join(MODULES, 'board', 'custom', 'firmware', 'uno', 'catoms', row['catom'], 'catom.json')
    try:
        return json.load(open(p)).get('hal_contract') or []
    except (OSError, ValueError):
        return None


def read_text(row):
    with open(row['path'], 'rb') as fh:
        return fh.read().decode('utf-8')


def view(tid, form='polari'):
    """-> {id, form, text, ...} for one template. form=jinja is the file as it is; form=polari adds tokens + the HAL names used."""
    row = resolve(tid)
    src = read_text(row)
    res = {'id': row['id'], 'role': row['role'], 'catom': row['catom'], 'isotope': row['isotope'], 'sha256': row['sha256']}
    if form == 'jinja':
        return dict(res, form='jinja', text=src)
    if form != 'polari':
        raise ValueError('form %r: polari | jinja' % form)
    p = to_polari(src, contract_of(row))
    return dict(res, **p)


def main(argv=None):
    import argparse
    ap = argparse.ArgumentParser(prog='python3 -m cmod.custom.editor.convert', description='ed-0: show a C-atom template in either form')
    sub = ap.add_subparsers(dest='verb', required=True)
    sh = sub.add_parser('show')
    sh.add_argument('template', nargs='?')
    sh.add_argument('--form', default='polari', choices=('polari', 'jinja'))
    sh.add_argument('--tokens', action='store_true')
    sh.add_argument('--list', action='store_true')
    sh.add_argument('--json', action='store_true')
    a = ap.parse_args(argv)
    if a.list or not a.template:
        for r in list_templates():
            print('%-100s %-16s %s' % (r['id'], r['role'], r['sha256'][:12]))
        return 0
    try:
        v = view(a.template, a.form)
    except (KeyError, RefusedForm, ValueError) as e:
        print('refused: %s' % (e.args[0] if e.args else e), file=sys.stderr)
        return 2
    if a.json:
        print(json.dumps(v, indent=1, ensure_ascii=False))
    else:
        sys.stdout.write(v['text'])
        if a.tokens:
            for t in v.get('tokens', []):
                print('%5d %-8s %-10s %-9s %s' % (t['offset'], t['kind'], t['family'] or '-', t['name'], t['jinja'].replace('\n', ' ')[:60]))
    return 0


if __name__ == '__main__':
    sys.exit(main())
