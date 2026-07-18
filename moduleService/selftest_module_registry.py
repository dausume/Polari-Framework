"""
Selftest for the module register (mp-1).

Run from polari-framework/:  python3 -m moduleService.selftest_module_registry

Covers: the real registry file loads with filesystem-synced
downloaded flags (moved modules read TRUE, a fabricated one FALSE),
registration round trip in a temp root (self kind, unknown kinds
refused), and corrupt-file honesty.
"""

import json
import os
import tempfile

from moduleService.module_registry import (
    MODULE_KINDS, load_registry, register_module, registry_path,
    save_registry,
)

_results = []


def check(label, cond, extra=''):
    _results.append((label, bool(cond)))
    print(f'{"PASS" if cond else "FAIL"}: {label}'
          + (f' — {extra}' if extra and not cond else ''))


if __name__ == '__main__':
    print('== suite: the real register ==')
    doc = load_registry()
    check('registry file loads with a modules map',
          isinstance(doc.get('modules'), dict)
          and doc.get('schema_version') == '1')
    check('moved modules read downloaded=True from the filesystem',
          doc['modules'].get('biomining', {}).get('downloaded')
          is True
          and doc['modules'].get('microalgae', {}).get('downloaded')
          is True)
    check('every entry carries kind + path + repo + description',
          all({'kind', 'path', 'repo', 'description'}
              <= set(e) for e in doc['modules'].values()))
    check('kinds stay in vocabulary',
          all(e['kind'] in MODULE_KINDS
              for e in doc['modules'].values()))

    print('== suite: registration round trip (temp root) ==')
    with tempfile.TemporaryDirectory() as root:
        os.makedirs(os.path.join(root, 'modules', 'mymod'))
        result = register_module(
            'mymod', 'self', description='my own objects',
            root=root)
        check('self module registers', result.get('ok')
              and result['entry']['kind'] == 'self')
        check('downloaded synced from the filesystem (dir exists)',
              result['entry']['downloaded'] is True)
        result = register_module('ghostmod', 'vendor',
                                 repo='https://example/repo.git',
                                 root=root)
        check('vendor module without local code reads '
              'downloaded=False',
              result['entry']['downloaded'] is False
              and result['entry']['repo'].startswith('https'))
        check('unknown kind refused honestly',
              not register_module('x', 'vibes', root=root).get('ok'))
        reloaded = load_registry(root)
        check('round trip persists both entries',
              set(reloaded['modules']) == {'mymod', 'ghostmod'})
        # corrupt-file honesty
        with open(registry_path(root), 'w') as f:
            f.write('{nope')
        broken = load_registry(root)
        check('corrupt file => honest empty modules map',
              broken['modules'] == {})

    failed = [label for label, ok in _results if not ok]
    print(f'\n{len(_results) - len(failed)}/{len(_results)} checks '
          f'passed' + (f'; FAILED: {failed}' if failed else ''))
    raise SystemExit(1 if failed else 0)
