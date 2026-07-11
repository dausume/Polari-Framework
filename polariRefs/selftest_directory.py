"""
Selftest — modsplit-1: module gating + the class directory.

Run from polari-framework/:
    python3 -m polariRefs.selftest_directory

Covers: POLARI_MODULES gating (core packages always on; unset = all;
dotted entries match their parent), and /api/refs/directory (classes
route to their module's assigned instance via PeerNode base_url;
unassigned modules stay local; dynamic classes listed as local).
"""

import os
from types import SimpleNamespace

from polariApiServer.module_gating import (
    class_enabled, enabled_module_names, gate_summary, module_enabled,
)
from polariRefs.refs_api import PolariRefsAPI

PASS, FAIL = '\033[0;32mPASS\033[0m', '\033[0;31mFAIL\033[0m'
_results = []


def check(label, cond, extra=''):
    _results.append(bool(cond))
    print(f'  [{PASS if cond else FAIL}] {label}'
          f'{("  " + extra) if extra else ""}')


class _Row:
    def __init__(self, **kw):
        self.__dict__.update(kw)


MsciThing = type('MsciThing', (), {'__module__': 'materialsScience.x'})
AqpThing = type('AqpThing', (), {'__module__': 'aquaponics.pots'})
CoreThing = type('CoreThing', (), {'__module__':
                                   'polariApiServer.displayDefinition'})
LockThing = type('LockThing', (), {'__module__': 'simulationLocks.lease'})


if __name__ == '__main__':
    print('module gating (POLARI_MODULES)')
    os.environ.pop('POLARI_MODULES', None)
    check('knob unset → every module enabled (monolithic default)',
          enabled_module_names() is None and class_enabled(MsciThing)
          and class_enabled(AqpThing))
    os.environ['POLARI_MODULES'] = 'materialsScience'
    check('msci-only instance keeps msci, drops aquaponics',
          class_enabled(MsciThing) and not class_enabled(AqpThing))
    check('core + mesh-substrate classes register EVERYWHERE',
          class_enabled(CoreThing) and class_enabled(LockThing))
    os.environ['POLARI_MODULES'] = 'materialsScience.dft, aquaponics'
    check('dotted entries match their parent package',
          class_enabled(MsciThing) and class_enabled(AqpThing)
          and module_enabled('materialsScience'))
    summary = gate_summary([MsciThing, AqpThing, CoreThing,
                            type('Ghost', (), {'__module__':
                                               'mathshapes.x'})])
    check('gate summary names dropped modules (boot-log evidence)',
          summary['dropped'] == {'mathshapes': 1}
          and summary['kept']['materialsScience'] == 1)
    os.environ.pop('POLARI_MODULES', None)

    print('the class directory (core tells the frontend WHERE)')
    manager = SimpleNamespace(
        objectTables={
            'ModuleAssignment': {
                0: _Row(module_name='materialsScience',
                        instance_name='polari-m', state='enabled'),
                1: _Row(module_name='materialsScience.dft',
                        instance_name='engines', state='enabled'),
                2: _Row(module_name='aquaponics',
                        instance_name='polari-n', state='enabled'),
                3: _Row(module_name='scoring',
                        instance_name='polari-x', state='disabled'),
                # two EXACT assignments for one module: the
                # PeerNode-addressable one must win (deliberate
                # routing act); disable it to fall back local.
                4: _Row(module_name='materialsScience',
                        instance_name='prf-a', state='enabled')},
            'PeerNode': {
                0: _Row(name='polari-m',
                        base_url='https://api.m.example/',
                        identity_json='{"grpcTarget": "m-host:3002"}'),
                1: _Row(name='polari-n',
                        base_url='https://api.n.example',
                        identity_json='{"wsUrl": '
                                      '"wss://custom.n/socket"}')}},
        dynamicClasses={'RuntimeGadget': object},
        idList=[])
    api = PolariRefsAPI(polServer=None, manager=manager)
    api.polServer = SimpleNamespace(
        defClassList=[MsciThing, AqpThing, CoreThing, LockThing])
    response = SimpleNamespace(media=None, status=None)
    api.on_get_directory(SimpleNamespace(get_param=lambda *a: None),
                         response)
    directory = response.media
    check('directory answers with modules + classes',
          directory['ok'] and 'MsciThing' in directory['classes'])
    check('msci class routes to polari-m with its browser base URL '
          '(exact assignment outranks the dotted one)',
          directory['classes']['MsciThing'] ==
          {'module': 'materialsScience', 'instance': 'polari-m',
           'baseUrl': 'https://api.m.example'})
    check('aquaponics class routes to polari-n',
          directory['classes']['AqpThing']['baseUrl']
          == 'https://api.n.example')
    check("core class stays local (baseUrl '' = the serving backend)",
          directory['classes']['CoreThing']['baseUrl'] == ''
          and directory['classes']['LockThing']['baseUrl'] == '')
    check('disabled assignments are ignored',
          'scoring' not in directory['modules'])
    check('dynamic classes listed as local',
          directory['classes']['RuntimeGadget']['module'] == 'dynamic'
          and directory['classes']['RuntimeGadget']['baseUrl'] == '')
    check('wsUrl derives from the browser base URL (vhost upgrades '
          'in place, same path — the api.prf pattern)',
          directory['modules']['materialsScience']['wsUrl']
          == 'wss://api.m.example/')
    check('identity_json overrides win (wsUrl + grpcTarget '
          'advertised)',
          directory['modules']['aquaponics']['wsUrl']
          == 'wss://custom.n/socket'
          and directory['modules']['materialsScience']['grpcTarget']
          == 'm-host:3002')

    total, green = len(_results), sum(_results)
    print(f'\n{green}/{total} checks green')
    raise SystemExit(0 if green == total else 1)
