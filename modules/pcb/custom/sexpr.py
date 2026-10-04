"""
@module pcb.custom.sexpr

brd-bo's S-EXPRESSION reader/writer (board.custom.sexpr — parse, write, Q, q, find, value, check_netlist) EXTENDED for the two
KiCad design files pcb-0 reads and writes (D-pcb-1 "write directly"):

  find_all(tree, head)   every sub-expression with that head, at any depth (pads inside footprints, pins inside symbols)
  num / xy / prop        a number atom; an (at x y [rot]) / (start x y) pair; a symbol's / footprint's (property "K" "V")
  check_kicad(tree, kind) the shape KiCad 9 writes for a `.kicad_sch` (kicad_sch) or `.kicad_pcb` (kicad_pcb): the top-level head,
                         (version N) at or past KiCad 6's, a generator, the required sections, unique uuids — the stand-in for
                         KiCad's own reader on a device with no kicad-cli; the engine's ERC/DRC is the real reader

Nothing here imports KiCad; the file formats are KiCad's (documented at https://dev-docs.kicad.org/en/file-formats/).
"""
from board.custom.sexpr import Q, SexprError, find, parse, q, value, write  # noqa: F401 — re-exported: one reader for both modules

#: the oldest s-expression schematic / board formats (KiCad 6.0's) — older files are the legacy formats we do not read
MIN_VERSION = {'kicad_sch': 20211123, 'kicad_pcb': 20211014}
REQUIRED = {'kicad_sch': ('version', 'generator', 'lib_symbols'), 'kicad_pcb': ('version', 'generator', 'general', 'layers', 'setup')}


def find_all(tree, head):
    out = []
    if isinstance(tree, list):
        if tree and tree[0] == head:
            out.append(tree)
        for x in tree[1:] if tree else ():
            out.extend(find_all(x, head))
    return out


def num(x, default=0.0):
    try:
        return float(x)
    except (TypeError, ValueError):
        return default


def xy(tree, head='at'):
    """(x, y, rot) of the first (head x y [rot]) child — (0, 0, 0) when absent."""
    f = find(tree, head)
    if not f:
        return 0.0, 0.0, 0.0
    a = f[0]
    return num(a[1] if len(a) > 1 else 0), num(a[2] if len(a) > 2 else 0), num(a[3] if len(a) > 3 and not isinstance(a[3], list) else 0)


def prop(tree, key, default=''):
    for p in find(tree, 'property'):
        if len(p) > 2 and str(p[1]) == key:
            return str(p[2])
    return default


def check_kicad(tree, kind):
    """Problems with a parsed KiCad design file (empty = the shape KiCad 6+ writes)."""
    if kind not in MIN_VERSION:
        return ['unknown kind %r (kicad_sch | kicad_pcb)' % kind]
    if not (isinstance(tree, list) and tree and tree[0] == kind):
        return ['not a %s file: the top-level expression is (%s …)' % (kind, tree[0] if isinstance(tree, list) and tree else '?')]
    why = ['(%s …) missing' % s for s in REQUIRED[kind] if not find(tree, s)]
    v = int(num(value(tree, 'version'), 0))
    if v < MIN_VERSION[kind]:
        why.append('(version %s) predates KiCad 6 (%d) — a legacy file this reader does not take' % (v, MIN_VERSION[kind]))
    uuids = [str(u[1]) for u in find_all(tree, 'uuid') if len(u) > 1]
    dup = sorted({u for u in uuids if uuids.count(u) > 1})
    if dup:
        why.append('%d duplicate uuid(s), e.g. %s' % (len(dup), dup[0]))
    if kind == 'kicad_sch':
        for s in find(tree, 'symbol'):
            if not value(s, 'lib_id'):
                why.append('a placed symbol without lib_id')
            elif not prop(s, 'Reference'):
                why.append('symbol %s without a Reference property' % value(s, 'lib_id'))
        libs = {str(s[1]) for s in find(find(tree, 'lib_symbols')[0], 'symbol')} if find(tree, 'lib_symbols') else set()
        missing = sorted({value(s, 'lib_id') for s in find(tree, 'symbol')} - libs)
        if missing:
            why.append('placed symbols not embedded in lib_symbols: %s' % ', '.join(missing))
    else:
        codes = [str(n[1]) for n in find(tree, 'net') if len(n) > 2]
        if len(codes) != len(set(codes)):
            why.append('duplicate net codes')
        for fp in find(tree, 'footprint'):
            if not prop(fp, 'Reference'):
                why.append('footprint %s without a Reference property' % (fp[1] if len(fp) > 1 else '?'))
    return why
