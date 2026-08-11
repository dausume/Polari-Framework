#!/usr/bin/env python3
"""dyn-1 boot-parity dump: construct the full monolithic server
against a throwaway sqlite and print a canonical JSON of everything
dyn-1 must not change: route templates, defClassList, missing
modules, per-table row counts."""
import json
import os
import sys

os.environ.setdefault('POLARI_LAZY_BOOT', 'off')

repo = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, repo)
mods = os.path.join(repo, 'modules')
if os.path.isdir(mods):
    sys.path.insert(0, mods)

from objectTreeManagerDecorators import managerObject  # noqa: E402

mgr = managerObject(hasServer=True, hasDB=True)
pol = mgr.polServer


def routes(app):
    found = []

    def walk(node, prefix):
        uri = getattr(node, 'uri_template', None)
        if uri:
            found.append(uri)
        for child in getattr(node, 'children', []) or []:
            walk(child, prefix)

    for root in app._router._roots:
        walk(root, '')
    return sorted(set(found))


dump = {
    'routes': routes(pol.falconServer),
    'defClassList': sorted(c.__name__ for c in pol.defClassList),
    'allDefClassList': sorted(
        c.__name__ for c in getattr(pol, 'allDefClassList', [])),
    'missingModules': sorted(
        __import__('moduleService.module_loading',
                   fromlist=['MISSING_FEATURE_MODULES'])
        .MISSING_FEATURE_MODULES),
    'uriList': sorted(set(pol.uriList)),
    'tables': {name: len(rows)
               for name, rows in sorted(mgr.objectTables.items())},
}
out = os.environ.get('PARITY_OUT', '/tmp/parity.json')
with open(out, 'w') as fh:
    json.dump(dump, fh, indent=1, sort_keys=True)
print(f'PARITY DUMP -> {out}: {len(dump["routes"])} routes, '
      f'{len(dump["defClassList"])} classes, '
      f'{len(dump["tables"])} tables')
