"""
@module cmod.custom.generator.filters

The ONLY ways a value becomes C in a template. Each REFUSES (GenError, naming the value) rather than escaping:
a template never interpolates raw text into C.

  c_ident   a valid C identifier ([A-Za-z_][A-Za-z0-9_]*, not a C keyword)
  c_type    a C type: identifiers/keywords + `*` + spaces only (e.g. `const uint8_t *`)
  c_expr    a conservative C expression: identifiers, numbers, string/char literals, operators, parentheses, commas, `.` `->`
            `[]` — never `;`, braces, `#`, comments, backslashes or newlines; parentheses/brackets must balance
  c_int     an integer literal (decimal, optional u/U/l/L suffix) or a Python int
  c_hex     a Python int -> 0xNN (at least 2 digits, upper-case)
  c_comment / c_str / make_text   text that may sit in a /* */ comment, a "string", a Makefile line (no breakout)
  c_block   an already-extracted verbatim C block (glue.extract): non-empty, no NUL, braces balance outside comments/strings
"""
import functools
import re

import jinja2

IDENT = re.compile(r'^[A-Za-z_][A-Za-z0-9_]*$')
KEYWORDS = frozenset('auto break case char const continue default do double else enum extern float for goto if inline int long '
                     'register restrict return short signed sizeof static struct switch typedef union unsigned void volatile while'.split())
_TYPE_WORDS = frozenset('char const double float int long short signed struct unsigned void volatile enum union'.split())
_EXPR_OK = re.compile(r'^[A-Za-z0-9_\s+\-*/%()<>&|^~!=?:.,\[\]"\']*$')
_INT = re.compile(r'^(0[xX][0-9A-Fa-f]+|[0-9]+)[uUlL]{0,3}$')


class GenError(ValueError):
    pass


def c_ident(v):
    s = v if isinstance(v, str) else ''
    if not IDENT.match(s) or s in KEYWORDS:
        raise GenError('c_ident: %r is not a valid C identifier' % (v,))
    return s


def c_type(v):
    s = v if isinstance(v, str) else ''
    words = re.findall(r'[A-Za-z_][A-Za-z0-9_]*|\*|\S', s)
    if not words or any(w != '*' and not IDENT.match(w) for w in words):
        raise GenError('c_type: %r is not a C type (identifiers, keywords and * only)' % (v,))
    bare = [w for w in words if w != '*']
    if any(w in KEYWORDS and w not in _TYPE_WORDS for w in bare) or all(w in ('const', 'volatile', 'struct', 'enum', 'union') for w in bare):
        raise GenError('c_type: %r names no base type or uses a non-type keyword' % (v,))
    return s


def c_expr(v):
    s = v if isinstance(v, str) else ''
    if not s.strip() or not _EXPR_OK.match(s) or '/*' in s or '//' in s or '\\' in s:
        raise GenError('c_expr: %r is not an accepted C expression' % (v,))
    # a string / char literal must close on its own; quotes never nest
    if s.count('"') % 2 or s.count("'") % 2:
        raise GenError('c_expr: %r has an unterminated literal' % (v,))
    bare = re.sub(r'"[^"]*"|\'[^\']*\'', '', s)
    for o, c in (('(', ')'), ('[', ']')):
        if bare.count(o) != bare.count(c):
            raise GenError('c_expr: %r has unbalanced %s%s' % (v, o, c))
    depth = 0
    for ch in bare:
        depth += (ch == '(') - (ch == ')')
        if depth < 0:
            raise GenError('c_expr: %r closes a parenthesis it never opened' % (v,))
    return s


def c_int(v):
    if isinstance(v, bool):
        raise GenError('c_int: %r is a bool' % (v,))
    if isinstance(v, int):
        return str(v)
    if not isinstance(v, str) or not _INT.match(v):
        raise GenError('c_int: %r is not an integer literal' % (v,))
    return v


def c_hex(v, digits=2):
    if isinstance(v, bool) or not isinstance(v, int) or v < 0:
        raise GenError('c_hex: %r is not a non-negative int' % (v,))
    return '0x%0*X' % (digits, v)


def c_block(v):
    from cmod.custom import glue
    if not isinstance(v, str) or not v.strip() or '\x00' in v:
        raise GenError('c_block: empty or non-text block')
    masked = glue._code_mask(v)
    if masked.count('{') != masked.count('}'):
        raise GenError('c_block: braces do not balance')
    return v


def c_comment(v):
    s = v if isinstance(v, str) else ''
    if '*/' in s or '/*' in s or '\n' in s or '\r' in s or '\x00' in s:
        raise GenError('c_comment: %r would break out of a C comment' % (v,))
    return s


def c_str(v):
    s = v if isinstance(v, str) else ''
    if '"' in s or '\\' in s or '\n' in s or '\r' in s or '\x00' in s:
        raise GenError('c_str: %r cannot sit inside a C string literal' % (v,))
    return s


def make_text(v):
    s = v if isinstance(v, str) else ''
    if '\n' in s or '\r' in s or '\x00' in s:
        raise GenError('make_text: %r is not a single Makefile line' % (v,))
    return s


def _named(fn):
    """A filter applied to a MISSING context key (StrictUndefined) fails by the key's name, not as 'not an identifier'."""
    @functools.wraps(fn)
    def wrapper(v, *a, **k):
        if isinstance(v, jinja2.Undefined):
            raise GenError("context key missing — %s" % v._undefined_message)
        return fn(v, *a, **k)
    return wrapper


FILTERS = {'c_ident': c_ident, 'c_type': c_type, 'c_expr': c_expr, 'c_int': c_int, 'c_hex': c_hex, 'c_block': c_block,
           'c_comment': c_comment, 'c_str': c_str, 'make_text': make_text}
FILTERS = {k: _named(f) for k, f in FILTERS.items()}
