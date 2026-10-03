"""
@module cmod.custom.annotation

THE ATOM ANNOTATION (C_MODULARIZATION_PLAN.md §4, D-cmod-2): what a person writes in a NORMAL C file to make a function
an atom with declared ports. Two forms, one grammar:

  macro    POLARI_NODE(hal_adc_read, in(channel, "", "A0..A5"), out(return, "count", "0..1023, 10-bit"), uses(ADC))
           on its own line(s) right above the function. `POLARI_NODE(...)` expands to NOTHING (hal.h:
           `#define POLARI_NODE(...)`), so a plain `make` never sees it — the .hex is byte-identical.
  comment  /* @polari-node(hal_adc_read, in(channel), out(return, "count")) */  — for a file that must not depend on
           any header of ours.

Clauses after the name (each at most once per port; anything else is REFUSED, never guessed):
  in(<param>[, "<unit>"[, "<meaning>"]])      a value the node consumes
  out(<param>|return[, "<unit>"[, …]])        a value it produces (a pointer parameter it writes, or the return)
  inout(<param>[, "<unit>"[, …]])             a pointer it reads and writes
  uses(<resource>, …)                         a resource the scan cannot see (a pin, a peripheral by name)
  role("<words>")                             one line: what the node is for

What needs no annotation is DERIVED (signature, globals, registers, calls, ISR); the annotation only adds what the C
cannot say: the direction of a pointer, the unit, the meaning.
"""
import re

MACRO = 'POLARI_NODE'
COMMENT_TAG = '@polari-node'
CLAUSES = ('in', 'out', 'inout', 'uses', 'role')
DIRECTIONS = ('in', 'out', 'inout')
_TOK = re.compile(r'\s*(?:(?P<str>"(?:[^"\\]|\\.)*")|(?P<id>[A-Za-z_][A-Za-z0-9_.:\-]*)|(?P<num>-?\d+(?:\.\d+)?)|(?P<p>[(),]))')


class AnnotationRefused(ValueError):
    """A malformed annotation — the parser refuses the project rather than guess (file:line in the message)."""


def _strip_comments(text):
    """Comments → spaces (newlines kept, so line numbers hold); string literals left alone."""
    out, i, n = [], 0, len(text)
    while i < n:
        if text.startswith('/*', i):
            j = text.find('*/', i + 2)
            j = n if j < 0 else j + 2
            out.append(re.sub(r'[^\n]', ' ', text[i:j]))
            i = j
        elif text.startswith('//', i):
            j = text.find('\n', i)
            j = n if j < 0 else j
            out.append(' ' * (j - i))
            i = j
        elif text[i] == '"':
            j = i + 1
            while j < n and text[j] != '"':
                j += 2 if text[j] == '\\' else 1
            out.append(text[i:j + 1])
            i = j + 1
        else:
            out.append(text[i])
            i += 1
    return ''.join(out)


def _balanced(text, start):
    """text[start] == '(' → index just past the matching ')' (strings respected), or -1."""
    depth, i = 0, start
    while i < len(text):
        c = text[i]
        if c == '"':
            i += 1
            while i < len(text) and text[i] != '"':
                i += 2 if text[i] == '\\' else 1
        elif c == '(':
            depth += 1
        elif c == ')':
            depth -= 1
            if depth == 0:
                return i + 1
        i += 1
    return -1


def _tokens(body, where):
    toks, i = [], 0
    while i < len(body):
        if body[i:].strip() == '':
            break
        m = _TOK.match(body, i)
        if not m:
            raise AnnotationRefused('%s: cannot read %r in the annotation' % (where, body[i:i + 20]))
        kind = 'str' if m.group('str') else 'id' if m.group('id') else 'num' if m.group('num') else 'p'
        toks.append((kind, m.group(kind)))
        i = m.end()
    return toks


def parse_body(body, where='?'):
    """The text between POLARI_NODE( and its ) → {'name', 'ports': [{name, direction, unit, meaning}], 'uses', 'role'}."""
    toks = _tokens(body, where)
    if not toks or toks[0][0] != 'id':
        raise AnnotationRefused('%s: the annotation must start with the function name' % where)
    out = {'name': toks[0][1], 'ports': [], 'uses': [], 'role': ''}
    i = 1
    seen = set()
    while i < len(toks):
        if toks[i] != ('p', ','):
            raise AnnotationRefused('%s: expected "," after %r' % (where, toks[i - 1][1]))
        i += 1
        if i >= len(toks) or toks[i][0] != 'id' or toks[i][1] not in CLAUSES:
            raise AnnotationRefused('%s: unknown clause %r — one of %s' % (where, toks[i][1] if i < len(toks) else '', ', '.join(CLAUSES)))
        clause = toks[i][1]
        i += 1
        if i >= len(toks) or toks[i] != ('p', '('):
            raise AnnotationRefused('%s: %s needs (…)' % (where, clause))
        i += 1
        args = []
        while i < len(toks) and toks[i] != ('p', ')'):
            if toks[i] == ('p', ','):
                i += 1
                continue
            if toks[i][0] == 'p':
                raise AnnotationRefused('%s: nested parentheses inside %s(…)' % (where, clause))
            args.append(toks[i])
            i += 1
        if i >= len(toks):
            raise AnnotationRefused('%s: %s( is not closed' % (where, clause))
        i += 1
        if clause in DIRECTIONS:
            if not args or args[0][0] != 'id' or len(args) > 3 or any(a[0] != 'str' for a in args[1:]):
                raise AnnotationRefused('%s: %s(<param>[, "unit"[, "meaning"]]) — got %s' % (where, clause, [a[1] for a in args]))
            pname = args[0][1]
            if pname in seen:
                raise AnnotationRefused('%s: port %r is declared twice' % (where, pname))
            if pname == 'return' and clause != 'out':
                raise AnnotationRefused('%s: the return value can only be out(return, …)' % where)
            seen.add(pname)
            strs = [a[1][1:-1] for a in args[1:]]
            out['ports'].append({'name': pname, 'direction': clause, 'unit': strs[0] if strs else '', 'meaning': strs[1] if len(strs) > 1 else ''})
        elif clause == 'uses':
            if not args:
                raise AnnotationRefused('%s: uses() names at least one resource' % where)
            out['uses'] += [a[1][1:-1] if a[0] == 'str' else a[1] for a in args]
        else:   # role
            if len(args) != 1 or args[0][0] != 'str':
                raise AnnotationRefused('%s: role("<words>") takes one string' % where)
            out['role'] = args[0][1][1:-1]
    return out


def find(text, filename='?'):
    """Every annotation in one source file → [{name, ports, uses, role, form, line, end_line, raw}]. The macro form is
    found in code (comments stripped; a `#define POLARI_NODE` line is the definition, not a use); the comment form inside
    comments."""
    found = []
    code = _strip_comments(text)
    for m in re.finditer(r'(?m)^[ \t]*%s[ \t]*\(' % MACRO, code):
        line_start = code.rfind('\n', 0, m.start()) + 1
        if code[line_start:m.start()].strip().startswith('#'):
            continue
        open_at = code.index('(', m.start())
        end = _balanced(code, open_at)
        line = code.count('\n', 0, m.start()) + 1
        where = '%s:%d' % (filename, line)
        if end < 0:
            raise AnnotationRefused('%s: %s( is not closed' % (where, MACRO))
        a = parse_body(code[open_at + 1:end - 1], where)
        a.update(form='macro', line=line, end_line=code.count('\n', 0, end) + 1, raw=' '.join(text[m.start():end].split()))
        found.append(a)
    for m in re.finditer(re.escape(COMMENT_TAG) + r'\s*\(', text):
        open_at = text.index('(', m.start())
        end = _balanced(text, open_at)
        line = text.count('\n', 0, m.start()) + 1
        where = '%s:%d' % (filename, line)
        if end < 0:
            raise AnnotationRefused('%s: %s( is not closed' % (where, COMMENT_TAG))
        cstart = text.rfind('/*', 0, m.start())
        cline = text.rfind('\n', 0, m.start())
        if (cstart < 0 or text.find('*/', cstart) < m.start()) and '//' not in text[cline + 1:m.start()]:
            continue   # the tag outside a comment is not the comment form
        a = parse_body(' '.join(text[open_at + 1:end - 1].replace('*', ' ').split()), where)
        a.update(form='comment', line=line, end_line=text.count('\n', 0, end) + 1, raw=' '.join(text[m.start():end].split()))
        found.append(a)
    names = [a['name'] for a in found]
    dup = sorted({n for n in names if names.count(n) > 1})
    if dup:
        raise AnnotationRefused('%s: %s annotated more than once' % (filename, ', '.join(dup)))
    return sorted(found, key=lambda a: a['line'])
