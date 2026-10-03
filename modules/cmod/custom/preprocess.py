"""
@module cmod.custom.preprocess

THE PREPROCESSOR FOR THE ATOM PARSER (C_MODULARIZATION_PLAN.md §3, D-cmod-1 recommended: pycparser). pycparser parses
preprocessed C99 only, and the REAL avr-libc headers do not parse (measured 2026-10-02: `avr-gcc -E hal.c` fails at the
first `__attribute__` of <stdint.h>'s mode typedefs; the registers expand to `(*(volatile uint8_t *)(0xC6))`, which loses
their names). So the parser preprocesses with:

  * pycparser's own bundled PLY preprocessor (`pycparser.ply.cpp`, pure Python — no `cpp` binary, which the framework
    image does not carry), with two fixes written down below (`!=` in #if, line tracking per source file);
  * FAKE system headers (FAKE_HEADERS, the pycparser recipe): the AVR fixed-width types with their AVR widths, and the
    avr-libc macros the atoms are DETECTED by — `ISR(v)` becomes `void __polari_isr_<v>(void)` and `ATOMIC_BLOCK(t)`
    becomes `if (__polari_atomic_block(t))`, so the parser sees an ISR and an atomic region as plain C; register names
    (UDR0, TCCR2A, …) stay undeclared IDENTIFIERS, which pycparser accepts (it does no semantic check) and the resource
    scan reads by name;
  * the project's own headers, as written (board_config.h, hal.h, the generated <class>_packets.h).

This is a parse for STRUCTURE (signatures, globals, registers, calls), never a build: the build is avr-gcc's (the engine),
and `make` alone builds the project. Output carries `#line` markers so every function keeps its file and line.
"""
import hashlib
import os
import tempfile

#: name → content. AVR widths (avr-gcc: int 2 B, long 4 B, double 4 B, pointers 2 B — `avr-gcc -dM -E` __SIZEOF_*__).
FAKE_HEADERS = {
    'stdint.h': ('typedef signed char int8_t; typedef unsigned char uint8_t; typedef int int16_t; typedef unsigned int uint16_t;\n'
                 'typedef long int32_t; typedef unsigned long uint32_t; typedef long long int64_t; typedef unsigned long long uint64_t;\n'
                 'typedef int16_t intptr_t; typedef uint16_t uintptr_t;\n'),
    'stddef.h': 'typedef unsigned int size_t; typedef int ptrdiff_t;\n#define NULL ((void *)0)\n',
    'stdbool.h': '#define bool _Bool\n#define true 1\n#define false 0\n',
    'string.h': '#include <stddef.h>\n',
    'stdlib.h': '#include <stddef.h>\n',
    'math.h': '',
    'avr/io.h': ('#define _BV(bit) (1 << (bit))\n'   # avr/sfr_defs.h, as avr-libc defines them (bit names stay identifiers)
                 '#define bit_is_set(sfr, bit) ((sfr) & _BV(bit))\n#define bit_is_clear(sfr, bit) (!((sfr) & _BV(bit)))\n'
                 '#define loop_until_bit_is_set(sfr, bit) do { } while (bit_is_clear(sfr, bit))\n'
                 '#define loop_until_bit_is_clear(sfr, bit) do { } while (bit_is_set(sfr, bit))\n'),
    'avr/pgmspace.h': '#define PROGMEM\n',
    'avr/eeprom.h': '',
    'avr/wdt.h': '',
    'avr/sleep.h': '',
    'util/delay.h': '',
    'avr/interrupt.h': '#define ISR(vector, ...) void __polari_isr_##vector(void)\n#define ISR_NAKED\n#define ISR_BLOCK\n#define ISR_NOBLOCK\n',
    'util/atomic.h': '#define ATOMIC_BLOCK(type) if (__polari_atomic_block(type))\n#define NONATOMIC_BLOCK(type) if (__polari_nonatomic_block(type))\n',
}
#: GCC extensions erased before parsing (pycparser is C99); written here so the parse is reproducible
EXTENSION_DEFINES = ('__attribute__(x)', '__extension__', '__inline__ inline', '__inline inline', '__volatile__ volatile',
                     '__restrict', '__restrict__')
ISR_PREFIX = '__polari_isr_'
ATOMIC_MARK = '__polari_atomic_block'
_DIR = None


def fake_headers_sha():
    h = hashlib.sha256()
    for k in sorted(FAKE_HEADERS):
        h.update(k.encode() + b'\0' + FAKE_HEADERS[k].encode() + b'\0')
    for d in EXTENSION_DEFINES:
        h.update(d.encode() + b'\0')
    return h.hexdigest()


def fake_dir():
    """The fake headers written once per process into a temp dir (PLY's include() reads files from paths)."""
    global _DIR
    if _DIR and os.path.isdir(_DIR):
        return _DIR
    d = tempfile.mkdtemp(prefix='cmod-fake-libc-')
    for name, text in FAKE_HEADERS.items():
        p = os.path.join(d, name)
        os.makedirs(os.path.dirname(p), exist_ok=True)
        with open(p, 'w') as fh:
            fh.write(text)
    _DIR = d
    return d


def _c_int(text):
    """A C integer literal → int (suffixes dropped; 0x hex, 0b binary, a leading 0 = octal)."""
    import re
    v = re.sub(r'[uUlL]+$', '', text)
    if v[:2].lower() in ('0x', '0b'):
        return int(v, 0)
    return int(v, 8) if len(v) > 1 and v[0] == '0' else int(v)


def _preprocessor_class():
    import copy
    import re
    from pycparser.ply import cpp

    class _PP(cpp.Preprocessor):
        """PLY's preprocessor (pycparser.ply.cpp, BSD — David Beazley) with three fixes: (1) every token is tagged with
        the file it came from (for #line markers); (2) evalexpr keeps `!=` intact (PLY rewrites every `!` to ` not `,
        which makes `A != B` a syntax error) and divides as C does (integer `/`) — the body follows PLY's own evalexpr;
        (3) a function-like macro with NO parameters (`#define hal_wdt_init() wdt_enable(4)`) consumes its `()` at the
        use site (PLY treats it as object-like and leaves `wdt_enable(4)()` behind)."""

        def define(self, tokens):
            super().define(tokens)
            toks = self.tokenize(tokens) if isinstance(tokens, str) else tokens
            if len(toks) > 2 and toks[1].value == '(' and toks[2].value == ')' and toks[0].value in self.macros:
                self.macros[toks[0].value].empty_fn = True

        def expand_macros(self, tokens, expanded=None):
            out, i = [], 0
            while i < len(tokens):
                t = tokens[i]
                out.append(t)
                m = self.macros.get(t.value) if t.type == self.t_ID else None
                if m is not None and getattr(m, 'empty_fn', False) and not (expanded and t.value in expanded):
                    j = i + 1
                    while j < len(tokens) and tokens[j].type in self.t_WS:
                        j += 1
                    if j < len(tokens) and tokens[j].value == '(':
                        k = j + 1
                        while k < len(tokens) and tokens[k].type in self.t_WS:
                            k += 1
                        if k < len(tokens) and tokens[k].value == ')':
                            i = k + 1
                            continue
                i += 1
            return super().expand_macros(out, expanded)

        def parsegen(self, input, source=None):
            for t in super().parsegen(input, source):
                if not hasattr(t, 'src'):
                    t.src = source
                yield t

        def evalexpr(self, tokens):
            i = 0
            while i < len(tokens):   # defined X / defined(X) → 1 / 0, before expansion (as PLY does)
                if tokens[i].type == self.t_ID and tokens[i].value == 'defined':
                    j, paren, result = i + 1, False, '0'
                    while j < len(tokens):
                        if tokens[j].type in self.t_WS:
                            j += 1
                            continue
                        if tokens[j].type == self.t_ID:
                            result = '1' if tokens[j].value in self.macros else '0'
                            if not paren:
                                break
                        elif tokens[j].value == '(':
                            paren = True
                        elif tokens[j].value == ')':
                            break
                        j += 1
                    tokens[i] = copy.copy(tokens[i])
                    tokens[i].type, tokens[i].value = self.t_INTEGER, result
                    del tokens[i + 1:j + 1]
                i += 1
            tokens = self.expand_macros(tokens)
            parts = []
            for t in tokens:
                if t.type == self.t_ID:
                    parts.append('0')          # an undefined identifier is 0 in #if (C99 6.10.1)
                elif t.type == self.t_INTEGER:
                    parts.append(str(_c_int(str(t.value))))
                else:
                    parts.append(str(t.value))
            expr = ''.join(parts).replace('&&', ' and ').replace('||', ' or ')
            expr = re.sub(r'!(?!=)', ' not ', expr)
            expr = re.sub(r'(?<![/])/(?![/])', '//', expr)
            try:
                return eval(expr, {'__builtins__': {}}, {})
            except Exception:
                self.error(self.source, tokens[0].lineno if tokens else 0, "could not evaluate #if %r" % expr)
                return 0

        def error(self, file, line, msg):
            self.problems.append('%s:%s %s' % (file, line, msg))

    return _PP


def preprocess(path, include_dirs=(), defines=()):
    """→ (text with #line markers, problems). include_dirs: the project's own dirs (searched for "x.h" and <x.h>)."""
    from pycparser.ply import lex, cpp
    pp = _preprocessor_class()(lex.lex(module=cpp))
    pp.problems = []
    for d in [fake_dir()] + [os.path.abspath(x) for x in include_dirs]:
        pp.add_path(d)
    for d in EXTENSION_DEFINES + tuple(defines):
        pp.define(d)
    with open(path) as fh:
        src = fh.read()
    pp.parse(src, os.path.basename(path))
    out, cur_src, cur_line = [], None, None
    while True:
        t = pp.token()
        if not t:
            break
        if t.type == 'CPP_WS':
            out.append('\n' * t.value.count('\n') if '\n' in t.value else ' ')
            if '\n' in t.value and cur_line is not None:
                cur_line += t.value.count('\n')
            continue
        s = getattr(t, 'src', None)
        if s != cur_src or t.lineno != cur_line:
            out.append('\n#line %d "%s"\n' % (t.lineno, s))
            cur_src, cur_line = s, t.lineno
        out.append(str(t.value))
    return ''.join(out), pp.problems
