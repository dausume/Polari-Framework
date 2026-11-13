"""selftest_sweep.derive - the sweep list, derived; a selftest no list runs becomes a finding instead of a silent omission.

The sweep runs every module named in an app's polari-app.json top-level "selftests". Every *selftest*.py file under an app
directory (upstream/ and __pycache__/ excluded) is then classed:
  listed          in "selftests" (swept)
  covered         not listed, but REACHED from a listed selftest of the same app: imported (`from app.mod import ...`,
                  `import app.mod`, `from app.parent import mod`, importlib.import_module('app.mod')) or named as a quoted
                  runner-table entry ('app.mod' / 'mod'); reaching is transitive through covered files. A comment never counts.
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
    """drop # comments and docstrings, so a mention in prose never reaches a file"""
    src = re.sub(r'(?s)("""|\'\'\').*?\1', '""', src)
    return '\n'.join(re.sub(r'(^|\s)#.*$', '', line) for line in src.splitlines())


def _mod(entry, pkg):
    e = entry[:-3] if entry.endswith('.py') else entry
    e = e.replace('/', '.')
    return e.split('.', 1)[1] if e.startswith(pkg + '.') else e


def reaches(src, pkg, mod):
    """does this (comment-free) source import or table-name <pkg>.<mod>?"""
    full = re.escape(pkg + '.' + mod)
    parent, _, base = (pkg + '.' + mod).rpartition('.')
    pats = [r'\bfrom\s+%s\s+import\b' % full,
            r'\bimport\s+%s\b' % full,
            r'\bfrom\s+%s\s+import\s+(?:\(\s*)?(?:[\w\s,]*,\s*)?%s\b' % (re.escape(parent), re.escape(base)),
            r'import_module\(\s*[\'"]%s[\'"]' % full,
            r'[\'"](?:%s|%s)[\'"]' % (full, re.escape(mod))]
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
