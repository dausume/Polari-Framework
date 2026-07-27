"""
Self-test for mlb-5a: the [DB-Save] verbosity knob.

POLARI_DB_LOG=quiet (the default) silences the per-field [DB-Save]
stream that was a measurable chunk of the 15-25 min cold seed;
POLARI_DB_LOG=verbose restores it byte-for-byte. Warnings and errors
print unconditionally in both modes (asserted structurally: no
warning/error print site sits behind the gate).

Run from polari-framework/:
    python3 -m polariDBmanagement.selftest_db_log_quiet
"""

import ast
import os
import sys

from polariDBmanagement.managedDB import _db_log_verbose

PASS = 0
FAIL = 0


def check(label, condition):
    global PASS, FAIL
    if condition:
        PASS += 1
        print(f'  ok: {label}')
    else:
        FAIL += 1
        print(f'  FAIL: {label}')


def test_knob():
    print('[knob semantics]')
    old = os.environ.pop('POLARI_DB_LOG', None)
    try:
        check('unset -> quiet (default)', _db_log_verbose() is False)
        os.environ['POLARI_DB_LOG'] = 'verbose'
        check('verbose -> verbose', _db_log_verbose() is True)
        os.environ['POLARI_DB_LOG'] = 'VERBOSE '
        check('case/space tolerant', _db_log_verbose() is True)
        os.environ['POLARI_DB_LOG'] = 'quiet'
        check('quiet -> quiet', _db_log_verbose() is False)
        os.environ['POLARI_DB_LOG'] = 'garbage'
        check('unknown value -> quiet (safe default)',
              _db_log_verbose() is False)
    finally:
        if old is None:
            os.environ.pop('POLARI_DB_LOG', None)
        else:
            os.environ['POLARI_DB_LOG'] = old


def _print_sites(tree):
    """Every print(...) call in saveInstanceInDB + its save-mismatch
    helpers, tagged with whether it sits under an
    `if _db_log_verbose():` guard."""
    sites = []

    class Visitor(ast.NodeVisitor):
        def __init__(self):
            self.guard_stack = []

        def visit_If(self, node):
            is_guard = (isinstance(node.test, ast.Call)
                        and isinstance(node.test.func, ast.Name)
                        and node.test.func.id == '_db_log_verbose')
            self.guard_stack.append(is_guard)
            for child in node.body:
                self.visit(child)
            self.guard_stack.pop()
            for child in node.orelse:
                self.visit(child)

        def visit_Call(self, node):
            if isinstance(node.func, ast.Name) \
                    and node.func.id == 'print' and node.args:
                first = node.args[0]
                text = ''
                if isinstance(first, ast.JoinedStr):
                    text = ''.join(
                        part.value for part in first.values
                        if isinstance(part, ast.Constant))
                elif isinstance(first, ast.Constant):
                    text = str(first.value)
                if '[DB-Save]' in text:
                    sites.append(
                        (text, any(self.guard_stack)))
            self.generic_visit(node)

    Visitor().visit(tree)
    return sites


def test_gating_structure():
    print('[structural: chatty gated, warnings/errors loud]')
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                        'managedDB.py')
    tree = ast.parse(open(path).read())
    sites = _print_sites(tree)
    check('found the [DB-Save] print sites', len(sites) >= 15)
    loud = [t for t, guarded in sites if not guarded]
    gated = [t for t, guarded in sites if guarded]
    check('the per-field/SQL/SUCCESS stream is gated (>= 10 sites)',
          len(gated) >= 10)
    for needle in ('WARNING', 'INSERT failed',
                   'schema-stability outcome',
                   'schema-stability handler failed',
                   'meta-class', 'widened'):
        check(f'"{needle}" print stays UNCONDITIONAL',
              any(needle in t for t in loud)
              and not any(needle in t for t in gated))
    for needle in ('SUCCESS', 'Table columns', 'SQL:'):
        check(f'"{needle}" print is gated',
              any(needle in t for t in gated)
              and not any(needle in t for t in loud))


def main():
    test_knob()
    test_gating_structure()
    print(f'\n{PASS} passed, {FAIL} failed')
    return 1 if FAIL else 0


if __name__ == '__main__':
    sys.exit(main())
