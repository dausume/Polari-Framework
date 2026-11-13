"""
@module board.custom.rdl_import

hal-4 (econ, HAL_CATOM_CATALOGUE_PLAN.md §4; pol's decision 2026-11-13): OUR OWN silicon is read from its SystemRDL directly, because
CMSIS-SVD cannot carry what our HAL needs (SystemRDL `singlepulse` has no SVD form, so a strobe would be unknowable). This is A READER
FOR THE SYSTEMRDL SUBSET OUR RTL USES - not a SystemRDL compiler. Anything outside the subset is REFUSED in words; the full language
(parameters, dynamic property assignment, user-defined properties, enums, regfiles, component definitions reused by name ...) is what
PeakRDL's compiler is for, once installing it is allowed.

The subset:
  addrmap NAME { ... };                      one top-level address map (a nested addrmap is refused)
  default PROP = VALUE;  PROP = VALUE;       regwidth / accesswidth / name / desc / sw / hw / reset (defaults apply to what follows)
  reg { ... } INST [ '[' N ']' ] @ OFF [ += STRIDE ] ;     an anonymous reg, one instance, optionally an array (OFF required)
  field { ... } NAME '[' HI ':' LO ']' | '[' WIDTH ']' [ = RESET ] ;     a WIDTH-only field is packed at the next free bit (lsb0)
  field props: sw = rw|r|w ; hw = rw|r|w|na ; onwrite = woclr|woset|wot|wclr|wset ; onread = rclr|rset ; singlepulse ; hwset ;
               hwclr ; counter ; name = "..." ; desc = "..."      (a bare boolean `singlepulse;` or `singlepulse = true;`)
  numbers: 12, 0x1F, 8'h1f, 4'b0101, 'd3.   comments: // and /* */.

Rows: the generator's shape (svd_import.rows'), with access_word / access_source 'rdl' / access_cite = the RDL file, line and the
properties that decided it. The access words (plan §4b): sw=rw -> rw; sw=r -> r; sw=w -> w; sw=w + singlepulse -> w-strobe;
sw=rw + onwrite=woclr -> r-w1c. Any other combination (onread side effects, woset / wot, singlepulse on a readable field ...) gets no
word and says why, so choose() fails closed.
"""
import re


class RdlRefused(Exception):
    pass


_TOK = re.compile(r'\s+|//[^\n]*|/\*.*?\*/|(?P<str>"(?:[^"\\]|\\.)*")|(?P<num>\d*\'[hHbBdD][0-9a-fA-F_]+|0[xX][0-9a-fA-F_]+|\d+)'
                  r'|(?P<op>\+=|->|[{}\[\]:;=@,#().])|(?P<id>[A-Za-z_]\w*)', re.S)

FIELD_PROPS = {'sw', 'hw', 'onwrite', 'onread', 'singlepulse', 'hwset', 'hwclr', 'counter', 'name', 'desc', 'reset'}
REG_PROPS = {'regwidth', 'accesswidth', 'name', 'desc'}
MAP_PROPS = {'name', 'desc'}
DEFAULTABLE = {'regwidth', 'accesswidth', 'sw', 'hw'}
ENUMS = {'sw': {'rw', 'r', 'w'}, 'hw': {'rw', 'r', 'w', 'na'}, 'onwrite': {'woclr', 'woset', 'wot', 'wclr', 'wset'}, 'onread': {'rclr', 'rset'}}
BOOLS = {'singlepulse', 'hwset', 'hwclr', 'counter'}
OUTSIDE = {'regfile': 'regfile', 'mem': 'mem', 'signal': 'signal', 'enum': 'enum', 'property': 'a user-defined property', 'external': 'external',
           'alias': 'alias', 'internal': 'internal', 'constraint': 'constraint', 'struct': 'struct'}


def _number(text, line):
    t = text.replace('_', '')
    if "'" in t:
        base = {'h': 16, 'b': 2, 'd': 10}[t.split("'")[1][0].lower()]
        return int(t.split("'")[1][1:], base)
    return int(t, 0)


def tokens(src):
    out, pos, line = [], 0, 1
    while pos < len(src):
        m = _TOK.match(src, pos)
        if not m:
            raise RdlRefused('line %d: cannot read %r' % (line, src[pos:pos + 20]))
        kind = m.lastgroup
        if kind:
            out.append((kind, m.group(kind), line))
        line += m.group(0).count('\n')
        pos = m.end()
    out.append(('eof', '', line))
    return out


class _P:
    def __init__(self, toks, path):
        self.t, self.i, self.path = toks, 0, path

    def peek(self, k=0):
        return self.t[self.i + k]

    def take(self, want=None):
        tok = self.t[self.i]
        if want is not None and tok[1] != want:
            raise RdlRefused('%s line %d: expected %r, found %r' % (self.path, tok[2], want, tok[1] or 'end of file'))
        self.i += 1
        return tok

    def refuse_outside(self, tok):
        if tok[1] in OUTSIDE:
            raise RdlRefused('%s line %d: %s is outside the SystemRDL subset this reader covers (PeakRDL\'s compiler reads it)' % (self.path, tok[2], OUTSIDE[tok[1]]))

    def prop(self, allowed, scope):
        """PROP ; | PROP = VALUE ;  -> (name, value, line)"""
        name = self.take()
        if self.peek()[1] == '->':
            raise RdlRefused('%s line %d: a dynamic property assignment (->) is outside the subset' % (self.path, name[2]))
        if name[0] != 'id' or name[1] not in allowed:
            raise RdlRefused('%s line %d: property %r is not in the subset for a %s (allowed: %s)' % (self.path, name[2], name[1], scope, ', '.join(sorted(allowed))))
        if self.peek()[1] == ';':
            self.take(';')
            if name[1] not in BOOLS:
                raise RdlRefused('%s line %d: %s needs a value' % (self.path, name[2], name[1]))
            return name[1], True, name[2]
        self.take('=')
        v = self.take()
        self.take(';')
        if v[0] == 'str':
            val = v[1][1:-1]
        elif v[0] == 'num':
            val = _number(v[1], v[2])
        elif v[1] in ('true', 'false'):
            val = v[1] == 'true'
        else:
            val = v[1]
        if name[1] in ENUMS and val not in ENUMS[name[1]]:
            raise RdlRefused('%s line %d: %s = %s is outside the subset (%s)' % (self.path, name[2], name[1], val, ' | '.join(sorted(ENUMS[name[1]]))))
        if name[1] in BOOLS and val is not True and val is not False:
            raise RdlRefused('%s line %d: %s takes true / false' % (self.path, name[2], name[1]))
        return name[1], val, name[2]


def _word(f):
    sw, ow, orr, sp = f['sw'], f.get('onwrite'), f.get('onread'), f.get('singlepulse')
    if orr:
        return None, 'onread = %s: no HAL access word agreed for a read side effect yet' % orr
    if sp and sw != 'w':
        return None, 'singlepulse on a sw = %s field: only a write-only singlepulse is a strobe (w-strobe)' % sw
    if sp:
        return 'w-strobe', 'sw = w; singlepulse'
    if ow == 'woclr' and sw == 'rw':
        return 'r-w1c', 'sw = rw; onwrite = woclr'
    if ow:
        return None, 'onwrite = %s with sw = %s: no HAL access word agreed' % (ow, sw)
    return {'rw': 'rw', 'r': 'r', 'w': 'w'}[sw], 'sw = %s' % sw


def load(path):
    """-> {'name', 'desc', 'path', 'registers': [{register, offset, regwidth, reset, line, desc, fields: [...]}]}"""
    src = open(path).read()
    p = _P(tokens(src), path.rsplit('/', 1)[-1])
    tok = p.take()
    p.refuse_outside(tok)
    if tok[1] != 'addrmap':
        raise RdlRefused('%s line %d: the file must be one addrmap (found %r)' % (p.path, tok[2], tok[1]))
    name = p.take()
    if name[0] != 'id':
        raise RdlRefused('%s line %d: the addrmap needs a name' % (p.path, name[2]))
    p.take('{')
    amap = {'name': name[1], 'desc': '', 'path': p.path, 'registers': []}
    dflt = {'regwidth': 32, 'accesswidth': 32, 'sw': 'rw', 'hw': 'rw'}
    while p.peek()[1] != '}':
        tok = p.peek()
        p.refuse_outside(tok)
        if tok[1] == 'default':
            p.take()
            k, v, _ = p.prop(DEFAULTABLE, 'default')
            dflt[k] = v
        elif tok[1] == 'reg':
            amap['registers'].extend(_reg(p, dflt))
        elif tok[1] == 'addrmap':
            raise RdlRefused('%s line %d: a nested addrmap is outside the subset' % (p.path, tok[2]))
        elif tok[1] == 'field':
            raise RdlRefused('%s line %d: a field directly in the addrmap (outside a reg) is outside the subset' % (p.path, tok[2]))
        elif tok[0] == 'id' and p.peek(1)[1] in ('.', '->'):
            raise RdlRefused('%s line %d: a dynamic property assignment (%s...->prop) is outside the subset' % (p.path, tok[2], tok[1]))
        elif tok[0] == 'id' and p.peek(1)[1] == '=':
            k, v, _ = p.prop(MAP_PROPS, 'addrmap')
            amap[k] = v
        elif tok[0] == 'id' and p.peek(1)[1] == '{':
            raise RdlRefused('%s line %d: a named component definition (%s ... { }) is outside the subset: use an anonymous reg { } inst @ off;' % (p.path, tok[2], tok[1]))
        else:
            raise RdlRefused('%s line %d: %r is outside the subset' % (p.path, tok[2], tok[1]))
    p.take('}')
    p.take(';')
    if p.peek()[0] != 'eof':
        raise RdlRefused('%s line %d: one addrmap per file' % (p.path, p.peek()[2]))
    seen = {}
    for r in amap['registers']:
        for b in range(r['offset'], r['offset'] + r['regwidth'] // 8):
            if b in seen:
                raise RdlRefused('%s line %d: %s overlaps %s at byte 0x%X' % (p.path, r['line'], r['register'], seen[b], b))
            seen[b] = r['register']
    return amap


def _reg(p, dflt):
    start = p.take('reg')
    if p.peek()[1] == '#' or (p.peek(1)[1] == '#'):
        raise RdlRefused('%s line %d: parameters (#(...)) are outside the subset' % (p.path, start[2]))
    if p.peek()[1] != '{':
        raise RdlRefused('%s line %d: a named reg definition is outside the subset: use an anonymous reg { } inst @ off;' % (p.path, start[2]))
    p.take('{')
    reg = {'regwidth': dflt['regwidth'], 'accesswidth': dflt['accesswidth'], 'name': '', 'desc': ''}
    rdflt = dict(dflt)
    fields, nextbit = [], 0
    while p.peek()[1] != '}':
        tok = p.peek()
        p.refuse_outside(tok)
        if tok[1] == 'default':
            p.take()
            k, v, _ = p.prop(DEFAULTABLE, 'default')
            rdflt[k] = v
            if k in reg:
                reg[k] = v
        elif tok[1] == 'field':
            f = _field(p, rdflt, nextbit)
            nextbit = f['bit_hi'] + 1
            fields.append(f)
        elif tok[0] == 'id' and p.peek(1)[1] == '=':
            k, v, _ = p.prop(REG_PROPS, 'reg')
            reg[k] = v
        else:
            raise RdlRefused('%s line %d: %r is outside the subset inside a reg' % (p.path, tok[2], tok[1]))
    p.take('}')
    inst = p.take()
    if inst[0] != 'id':
        raise RdlRefused('%s line %d: the reg needs an instance name' % (p.path, inst[2]))
    count = None
    if p.peek()[1] == '[':
        p.take('[')
        n = p.take()
        if n[0] != 'num':
            raise RdlRefused('%s line %d: an array size must be a number' % (p.path, n[2]))
        count = _number(n[1], n[2])
        p.take(']')
    if p.peek()[1] != '@':
        raise RdlRefused('%s line %d: %s has no @ offset (automatic addressing is outside the subset)' % (p.path, inst[2], inst[1]))
    p.take('@')
    off = p.take()
    offset = _number(off[1], off[2])
    stride = reg['regwidth'] // 8
    if p.peek()[1] == '+=':
        p.take('+=')
        s = p.take()
        stride = _number(s[1], s[2])
    p.take(';')
    for f in fields:
        if f['bit_hi'] >= reg['regwidth']:
            raise RdlRefused('%s line %d: field %s [%d:%d] does not fit a %d-bit reg' % (p.path, f['line'], f['field'], f['bit_hi'], f['bit_lo'], reg['regwidth']))
    used = {}
    for f in fields:
        for b in range(f['bit_lo'], f['bit_hi'] + 1):
            if b in used:
                raise RdlRefused('%s line %d: field %s overlaps %s at bit %d' % (p.path, f['line'], f['field'], used[b], b))
            used[b] = f['field']
    reset = sum(int(f['reset_value']) << f['bit_lo'] for f in fields if f['reset_value'].isdigit())
    out = []
    for k in range(count or 1):
        nm = (inst[1] + (str(k) if count else '')).upper()
        out.append({'register': nm, 'offset': offset + k * stride, 'regwidth': reg['regwidth'], 'reset': reset, 'line': start[2],
                    'desc': reg['desc'] or reg['name'], 'fields': [dict(f) for f in fields]})
    return out


def _field(p, rdflt, nextbit):
    start = p.take('field')
    if p.peek()[1] != '{':
        raise RdlRefused('%s line %d: a named field definition is outside the subset' % (p.path, start[2]))
    p.take('{')
    f = {'sw': rdflt['sw'], 'hw': rdflt['hw'], 'desc': '', 'name': '', 'props': []}
    while p.peek()[1] != '}':
        p.refuse_outside(p.peek())
        k, v, ln = p.prop(FIELD_PROPS, 'field')
        f[k] = v
        if k not in ('desc', 'name'):
            f['props'].append('%s = %s' % (k, v) if v is not True else k)
    p.take('}')
    name = p.take()
    if name[0] != 'id':
        raise RdlRefused('%s line %d: the field needs an instance name' % (p.path, name[2]))
    p.take('[')
    a = p.take()
    if p.peek()[1] == ':':
        p.take(':')
        b = p.take()
        hi, lo = _number(a[1], a[2]), _number(b[1], b[2])
        if hi < lo:
            raise RdlRefused('%s line %d: [%d:%d] is msb0 / reversed, outside the subset (lsb0 only)' % (p.path, name[2], hi, lo))
    else:
        lo = nextbit
        hi = lo + _number(a[1], a[2]) - 1
    p.take(']')
    reset = f.get('reset', '')
    if p.peek()[1] == '=':
        p.take('=')
        r = p.take()
        reset = _number(r[1], r[2])
    p.take(';')
    w = hi - lo + 1
    if reset != '' and reset >= (1 << w):
        raise RdlRefused('%s line %d: reset %d does not fit %s[%d:%d]' % (p.path, name[2], reset, name[1], hi, lo))
    out = {'field': name[1].upper(), 'bit_lo': lo, 'bit_hi': hi, 'width': w, 'reset_value': str(reset) if reset != '' else 'undefined (no reset in the RDL)',
           'sw': f['sw'], 'hw': f['hw'], 'onwrite': f.get('onwrite'), 'onread': f.get('onread'), 'singlepulse': f.get('singlepulse', False),
           'hwset': f.get('hwset', False), 'hwclr': f.get('hwclr', False), 'counter': f.get('counter', False), 'desc': f['desc'] or f['name'],
           'line': start[2], 'props': ['sw = %s' % f['sw']] + [x for x in f['props'] if not x.startswith('sw =')]}
    return out


def rows(amap, block=None, prefix=None, base=0):
    """the generator's row shape, every field with its access word decided from the RDL (or none, said) -> (REGISTERS, FIELDS, left)"""
    block = block or amap['name'].upper()
    pre = (prefix if prefix is not None else amap['name'].upper()) + '_'
    R, F, left = [], [], []
    for r in amap['registers']:
        rn = pre + r['register'] + '_REG'
        R.append({'register': rn, 'block': block, 'offset': r['offset'], 'reset': '0x%08X' % r['reset'], 'title': r['desc'],
                  'where': '%s line %d' % (amap['path'], r['line']), 'undetermined': '', 'part': 'rdl'})
        for f in r['fields']:
            word, why = _word(f)
            cite = '%s line %d: %s' % (amap['path'], f['line'], '; '.join(f['props']))
            F.append({'register': rn, 'field': f['field'], 'bit_hi': f['bit_hi'], 'bit_lo': f['bit_lo'], 'width': f['width'], 'reset_value': f['reset_value'],
                      'description': f['desc'], 'values': {'any': f['desc']} if f['desc'] else {'any': 'no description in the RDL'},
                      'page_table': '%s line %d' % (amap['path'], f['line']), 'trm_access': '', 'access': '', 'access_word': word or '',
                      'access_source': 'rdl' if word else '', 'access_cite': cite if word else '', 'affects_pin': '', 'affects_signal': '',
                      'notes': ('access %s (%s)' % (word, why)) if word else ('NO access word: %s' % why), 'part': 'rdl',
                      'rdl': {k: f[k] for k in ('sw', 'hw', 'onwrite', 'onread', 'singlepulse', 'hwset', 'hwclr', 'counter')}})
            if not word:
                left.append({'register': rn, 'field': f['field'], 'why': why})
    return R, F, left
