"""
Self-test for modules-as-projects (msci-6, Track 2): ModuleSourceConfig
+ module_fetcher against a REAL local git repo fixture.

Run from polari-framework/:
    python3 -m polariPeers.selftest_module_projects
"""

import os
import subprocess
import sys
import tempfile
from types import SimpleNamespace

from polariPeers.module_fetcher import (
    auto_fetch_configured, fetch_module_project, fetch_suggestions,
    project_statuses,
)

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


def _git(args, cwd):
    subprocess.run(['git'] + args, cwd=cwd, check=True,
                   capture_output=True, text=True,
                   env={**os.environ,
                        'GIT_AUTHOR_NAME': 't', 'GIT_AUTHOR_EMAIL': 't@t',
                        'GIT_COMMITTER_NAME': 't',
                        'GIT_COMMITTER_EMAIL': 't@t'})


def _make_fixture_repo(root):
    repo = os.path.join(root, 'polariDemoFixtureModule-src')
    os.makedirs(repo)
    _git(['init', '-q', '-b', 'main'], repo)
    with open(os.path.join(repo, '__init__.py'), 'w') as f:
        f.write('"""fixture module"""\n')
    _git(['add', '.'], repo)
    _git(['commit', '-q', '-m', 'v1'], repo)
    return repo


def _manager(configRows):
    rows = {r.name: r for r in configRows}
    fakeDB = SimpleNamespace(saveInstanceInDB=lambda row: True)
    return SimpleNamespace(
        objectTables={'ModuleSourceConfig': rows}, db=fakeDB)


def main():
    with tempfile.TemporaryDirectory() as tmp:
        modulesDir = os.path.join(tmp, 'modules')
        repo = _make_fixture_repo(tmp)

        gitConfig = SimpleNamespace(
            name='polariDemoFixtureModule', source_kind='git',
            locator=repo, ref='', auto_fetch=False, status='absent',
            fetched_version='', last_error='', notes='')
        fileConfig = SimpleNamespace(
            name='polariCopiedFixtureModule', source_kind='file',
            locator=repo, ref='', auto_fetch=True, status='absent',
            fetched_version='', last_error='', notes='')
        manager = _manager([gitConfig, fileConfig])

        print('[statuses + suggestions before fetch]')
        statuses = project_statuses(manager, modulesDir)
        check('both configs listed, folders absent',
              len(statuses) == 2
              and not any(s['folderPresent'] for s in statuses))
        suggestions = fetch_suggestions(manager, modulesDir)
        check('two evidence-bearing suggestions', len(suggestions) == 2
              and all(s['evidence'] and s['action'] for s in suggestions))
        check('suggestion names the fetch knob',
              suggestions[0]['knob'] == 'POST /api/module-projects/fetch')

        print('[git fetch]')
        result = fetch_module_project(
            manager, 'polariDemoFixtureModule', modulesDir)
        check('clone succeeds', result['ok'] and result['action'] == 'cloned')
        check('folder materialized', os.path.isdir(
            os.path.join(modulesDir, 'polariDemoFixtureModule')))
        check('commit SHA recorded',
              len(result['fetchedVersion']) == 40
              and gitConfig.fetched_version == result['fetchedVersion'])
        check('row status fetched', gitConfig.status == 'fetched')

        # New upstream commit → re-fetch updates and tracks the SHA.
        with open(os.path.join(repo, 'extra.py'), 'w') as f:
            f.write('x = 2\n')
        _git(['add', '.'], repo)
        _git(['commit', '-q', '-m', 'v2'], repo)
        v1 = result['fetchedVersion']
        result = fetch_module_project(
            manager, 'polariDemoFixtureModule', modulesDir)
        check('re-fetch updates', result['ok']
              and result['action'] == 'updated'
              and result['fetchedVersion'] != v1)

        print('[auto-fetch knob]')
        results = auto_fetch_configured(manager, modulesDir)
        check('only the auto_fetch row fetched', len(results) == 1
              and results[0]['name'] == 'polariCopiedFixtureModule'
              and results[0]['action'] == 'copied')
        check('no suggestions once materialized',
              fetch_suggestions(manager, modulesDir) == [])

        print('[refusals]')
        check('unknown config refuses', fetch_module_project(
            manager, 'nope', modulesDir)['ok'] is False)
        peerConfig = SimpleNamespace(
            name='polariPeerThingModule', source_kind='peer',
            locator='peer-a:thing', ref='', auto_fetch=False,
            status='absent', fetched_version='', last_error='', notes='')
        manager.objectTables['ModuleSourceConfig'][peerConfig.name] = \
            peerConfig
        verdict = fetch_module_project(
            manager, 'polariPeerThingModule', modulesDir)
        check('peer kind points at the bundle flow',
              verdict['ok'] is False
              and '/api/modules/install' in verdict['error'])
        badConfig = SimpleNamespace(
            name='polariBadModule', source_kind='git',
            locator=os.path.join(tmp, 'missing-repo'), ref='',
            auto_fetch=False, status='absent', fetched_version='',
            last_error='', notes='')
        manager.objectTables['ModuleSourceConfig'][badConfig.name] = \
            badConfig
        verdict = fetch_module_project(manager, 'polariBadModule',
                                       modulesDir)
        check('bad locator errors + row records it',
              verdict['ok'] is False and badConfig.status == 'error'
              and badConfig.last_error)

    print(f'\n{PASS} passed, {FAIL} failed')
    return 1 if FAIL else 0


if __name__ == '__main__':
    sys.exit(main())
