"""
@module cmod.custom.c_types

C types (pycparser AST) → a plain description, the AVR width, and the POLARI type a port carries (C_MODULARIZATION_PLAN
§2). The Polari side is the proto vocabulary the class rows and c_twin already use (grpcbridge.custom.c_twin.C_TYPES:
int64, double, bool, string, bytes) plus `ref:<Type>` for a struct (a C struct is not a Polari scalar — it maps to a
class by NAME when one exists; cmod-1's graph decides that, cmod-0 only records it).

Widths are avr-gcc's (ATmega328P): char 1, short 2, int 2, long 4, long long 8, float 4, double 4 (= float), pointer 2.
A width that cannot be known (an unresolved typedef) is 0, never guessed.
"""
from pycparser import c_ast

AVR_WIDTHS = {'char': 1, 'short': 2, 'int': 2, 'long': 4, 'long long': 8, 'float': 4, 'double': 4, 'long double': 4, '_Bool': 1,
              'void': 0}
POINTER_BYTES = 2
_FLOAT = ('float', 'double', 'long double')


def const_int(e):
    """A constant integer expression (a Constant, + - * / % << >> | & ^, unary -, a cast) → int, else None."""
    import operator as op
    if isinstance(e, c_ast.Constant) and e.type in ('int', 'unsigned int', 'long int', 'unsigned long int'):
        v = e.value.rstrip('uUlL')
        try:
            return int(v, 16) if v[:2].lower() == '0x' else int(v, 8) if len(v) > 1 and v[0] == '0' else int(v)
        except ValueError:
            return None
    if isinstance(e, c_ast.Cast):
        return const_int(e.expr)
    if isinstance(e, c_ast.UnaryOp) and e.op in ('-', '+'):
        v = const_int(e.expr)
        return None if v is None else (-v if e.op == '-' else v)
    if isinstance(e, c_ast.BinaryOp):
        ops = {'+': op.add, '-': op.sub, '*': op.mul, '/': op.floordiv, '%': op.mod, '<<': op.lshift, '>>': op.rshift,
               '|': op.or_, '&': op.and_, '^': op.xor}
        a, b = const_int(e.left), const_int(e.right)
        if a is None or b is None or e.op not in ops or (e.op in ('/', '%') and b == 0):
            return None
        return ops[e.op](a, b)
    return None


def _base_name(names):
    n = [x for x in names if x not in ('signed', 'unsigned', 'const', 'volatile')]
    s = ' '.join(n) or 'int'
    if s in ('short int', 'long int', 'long long int'):
        s = s[:-4]
    return s


class TypeTable(object):
    """The typedefs and structs of one translation unit (file scope)."""

    def __init__(self, ast):
        self.typedefs, self.structs = {}, {}
        for ext in ast.ext:
            if isinstance(ext, c_ast.Typedef):
                self.typedefs[ext.name] = ext.type
            if isinstance(ext, c_ast.Decl) and isinstance(ext.type, c_ast.Struct) and ext.type.name and ext.type.decls:
                self.structs[ext.type.name] = ext.type

    def describe(self, t, depth=0):
        """→ {'c': text, 'kind': int|float|bool|void|pointer|array|struct|unknown, 'width': bytes, 'signed', 'volatile',
        'const', 'target': (for pointer/array) the pointee description, 'name': typedef/struct name}."""
        if depth > 12:
            return {'c': '?', 'kind': 'unknown', 'width': 0}
        quals = list(getattr(t, 'quals', []) or [])
        if isinstance(t, c_ast.TypeDecl):
            d = self._inner(t.type, depth)
            d['volatile'] = d.get('volatile') or 'volatile' in quals
            d['const'] = d.get('const') or 'const' in quals
            if 'volatile' in quals:
                d['c'] = 'volatile ' + d['c']
            if 'const' in quals:
                d['c'] = 'const ' + d['c']
            return d
        if isinstance(t, c_ast.PtrDecl):
            tgt = self.describe(t.type, depth + 1)
            return {'c': tgt['c'] + ' *', 'kind': 'pointer', 'width': POINTER_BYTES, 'target': tgt, 'volatile': 'volatile' in quals,
                    'const': 'const' in quals}
        if isinstance(t, c_ast.ArrayDecl):
            tgt = self.describe(t.type, depth + 1)
            n = const_int(t.dim) or 0
            return {'c': tgt['c'] + '[%s]' % (n or ''), 'kind': 'array', 'width': tgt.get('width', 0) * n, 'target': tgt, 'length': n,
                    'volatile': tgt.get('volatile', False), 'const': tgt.get('const', False)}
        if isinstance(t, c_ast.FuncDecl):
            return {'c': 'function', 'kind': 'function', 'width': POINTER_BYTES}
        return {'c': '?', 'kind': 'unknown', 'width': 0}

    def _inner(self, t, depth):
        if isinstance(t, c_ast.IdentifierType):
            names = list(t.names)
            if len(names) == 1 and names[0] in self.typedefs:
                d = dict(self.describe(self.typedefs[names[0]], depth + 1))
                d['name'] = names[0]
                d['c'] = names[0]
                return d
            base = _base_name(names)
            kind = 'void' if base == 'void' else 'bool' if base == '_Bool' else 'float' if base in _FLOAT else 'int' if base in AVR_WIDTHS else 'unknown'
            return {'c': ' '.join(names), 'kind': kind, 'width': AVR_WIDTHS.get(base, 0), 'signed': 'unsigned' not in names and kind == 'int'}
        if isinstance(t, (c_ast.Struct, c_ast.Union)):
            s = self.structs.get(t.name, t)
            width = 0   # the AVR aligns everything to 1 byte: a struct is the sum of its members, no padding
            for decl in (getattr(s, 'decls', None) or []):
                w = self.describe(decl.type, depth + 1).get('width', 0)
                if not w:
                    width = 0
                    break
                width += w
            return {'c': '%s %s' % ('struct' if isinstance(t, c_ast.Struct) else 'union', t.name or ''), 'kind': 'struct', 'width': width,
                    'name': t.name or ''}
        if isinstance(t, c_ast.Enum):
            return {'c': 'enum %s' % (t.name or ''), 'kind': 'int', 'width': 2, 'signed': True}
        return {'c': '?', 'kind': 'unknown', 'width': 0}


def polari_type(d):
    """A described C type → the Polari (proto) type of the port, or '' for void."""
    k = d.get('kind')
    if k == 'void':
        return ''
    if k == 'int':
        return 'int64'
    if k == 'float':
        return 'double'
    if k == 'bool':
        return 'bool'
    if k == 'struct':
        return 'ref:%s' % (d.get('name') or 'struct')
    if k in ('pointer', 'array'):
        tgt = d.get('target') or {}
        if tgt.get('kind') == 'int' and tgt.get('width') == 1 and (tgt.get('name') in (None, '') and 'char' in tgt.get('c', '')
                                                                   and 'unsigned' not in tgt.get('c', '')):
            return 'string'
        if tgt.get('kind') == 'int' and tgt.get('width') == 1 or tgt.get('kind') == 'void':
            return 'bytes'
        if tgt.get('kind') == 'struct':
            return 'ref:%s' % (tgt.get('name') or 'struct')
        return polari_type(tgt)
    return 'unknown'
