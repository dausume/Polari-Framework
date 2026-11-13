"""selftest_sweep.derive - the sweep list, derived; a selftest no list runs becomes a finding instead of a silent omission.

The sweep runs every module named in an app's polari-app.json top-level "selftests". Every *selftest*.py file under an app
directory (upstream/ and __pycache__/ excluded) is then classed:
  listed          in "selftests" (swept)
  covered         not listed, but REACHED from a listed selftest of the same app: imported (`from app.mod import ...`,
                  `import app.mod`, `from app.parent import mod`, importlib.import_module('app.mod')) or named by a quoted string that is an
                  ELEMENT - a list / tuple / dict item or a call argument ('app.mod' / 'mod'); reaching is transitive through
                  covered files. A comment, a docstring or a name quoted inside prose never counts.
  PACKAGED-UNRUN  shipped in files.selftests, but neither listed nor reached
  UNLISTED        in no list and reached by nothing
  MISSING-FILE    listed, but no such file

    python3 tools/selftest_sweep/derive.py [ROOT]      # ROOT = polari-framework/ (default: this checkout)
stdout: '<app> <module> <class>' for every row the sweep should run (listed + PACKAGED-UNRUN + UNLISTED);
stderr: one line per finding and a summary; exit 1 when there is any finding.
"""
import glob
import json
import os
import re
import sys

SWEPT = ('listed', 'PACKAGED-UNRUN', 'UNLISTED')


def _strip_comments(src):
    """-> (code, elements): the source without comments and docstrings (tokenize, so a '#' inside a string stays), and the
    string literals that sit as an ELEMENT - a list / tuple / set / dict item or a call argument. A quoted name inside a
    message or any other prose string is never an element, so it never covers."""
    import io
    import tokenize
    try:
        toks = list(tokenize.generate_tokens(io.StringIO(src).readline))
    except (tokenize.TokenError, IndentationError, SyntaxError):
        return re.sub(r'(?m)^\s*#.*$', '', src), []
    STMT = (tokenize.NEWLINE, tokenize.INDENT, tokenize.DEDENT, tokenize.ENCODING)
    sig = [t for t in toks if t.type not in (tokenize.NL, tokenize.COMMENT)]
    lines = src.splitlines(True)
    drop = [t for t in toks if t.type == tokenize.COMMENT]
    elements = []
    for i, t in enumerate(sig):
        prev = sig[i - 1] if i else None
        nxt = sig[i + 1] if i + 1 < len(sig) else None
        if t.type == tokenize.STRING:
            if (prev is None or prev.type in STMT) and (nxt is None or nxt.type in (tokenize.NEWLINE, tokenize.ENDMARKER)):
                drop.append(t)   # a whole statement that is only a string: a docstring
                continue
            if prev is not None and prev.type == tokenize.OP and prev.string in ('[', '(', '{', ',') and \
                    nxt is not None and nxt.type == tokenize.OP and nxt.string in (',', ']', ')', '}', ':'):
                elements.append(re.sub(r'^[rRbBuUfF]*([\'"]{1,3})(.*)\1$', r'\2', t.string, flags=re.S))
    for t in sorted(drop, key=lambda t: t.start, reverse=True):   # blank the span in the ORIGINAL text, so dotted names stay intact
        (r0, c0), (r1, c1) = t.start, t.end
        if r0 == r1:
            lines[r0 - 1] = lines[r0 - 1][:c0] + ' ' * (c1 - c0) + lines[r0 - 1][c1:]
        else:
            lines[r0 - 1] = lines[r0 - 1][:c0] + '\n'
            for r in range(r0, r1 - 1):
                lines[r] = '\n'
            lines[r1 - 1] = ' ' * c1 + lines[r1 - 1][c1:]
    return ''.join(lines), elements


def _mod(entry, pkg):
    e = entry[:-3] if entry.endswith('.py') else entry
    e = e.replace('/', '.')
    return e.split('.', 1)[1] if e.startswith(pkg + '.') else e


def reaches(stripped, pkg, mod):
    """does this source (as _strip_comments returns it) import or table-name <pkg>.<mod>?"""
    src, elements = stripped
    if pkg + '.' + mod in elements or mod in elements:
        return True
    full = re.escape(pkg + '.' + mod)
    parent, _, base = (pkg + '.' + mod).rpartition('.')
    pats = [r'\bfrom\s+%s\s+import\b' % full,
            r'\bimport\s+%s\b' % full,
            r'\bfrom\s+%s\s+import\s+(?:\(\s*)?(?:[\w\s,]*,\s*)?%s\b' % (re.escape(parent), re.escape(base)),
            r'import_module\(\s*[\'"]%s[\'"]' % full]
    return any(re.search(p, src) for p in pats)


def classify(root):
    apps = sorted(glob.glob(os.path.join(root, 'modules/*/polari-app.json')) + glob.glob(os.path.join(root, '*/polari-app.json')))
    rows = []
    for mf in apps:
        d = os.path.dirname(mf)
        pkg = os.path.basename(d)
        m = json.load(open(mf))
        listed = [_mod(s, pkg) for s in (m.get('selftests') or [])]
        packaged = {_mod(s, pkg) for s in ((m.get('files') or {}).get('selftests') or [])}
        files = {}
        for f in glob.glob(os.path.join(d, '**', '*selftest*.py'), recursive=True):
            if '/upstream/' in f or '__pycache__' in f:
                continue
            files[os.path.relpath(f, d)[:-3].replace(os.sep, '.')] = f
        src = {x: _strip_comments(open(f, errors='replace').read()) for x, f in files.items()}
        for x in listed:
            rows.append((pkg, pkg + '.' + x, 'listed' if x in files else 'MISSING-FILE'))
        reached, frontier = set(), [x for x in listed if x in files]
        while frontier:   # transitive: a covered aggregator's own imports count too
            cur = frontier.pop()
            for x in files:
                if x not in reached and x not in listed and reaches(src[cur], pkg, x):
                    reached.add(x)
                    frontier.append(x)
        for x in sorted(set(files) - set(listed)):
            rows.append((pkg, pkg + '.' + x, 'covered' if x in reached else 'PACKAGED-UNRUN' if x in packaged else 'UNLISTED'))
    return len(apps), rows


def main(argv):
    root = argv[1] if len(argv) > 1 else os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..')
    n, rows = classify(root)
    counts = {}
    for pkg, mod, cls in rows:
        counts[cls] = counts.get(cls, 0) + 1
        if cls in SWEPT:
            print(pkg, mod, cls)
        if cls not in ('listed', 'covered'):
            print('%s %s' % (cls, mod), file=sys.stderr)
    print('apps %d; %s' % (n, ', '.join('%s %d' % kv for kv in sorted(counts.items()))), file=sys.stderr)
    return 1 if any(c not in ('listed', 'covered') for c in counts) else 0


if __name__ == '__main__':
    sys.exit(main(sys.argv))
