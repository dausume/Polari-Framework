"""
@module cmod.custom.projects

WHAT A C PROJECT IS to cmod (C_MODULARIZATION_PLAN.md §2, D-cmod-3: both kinds must work):

  template   a firmware template inside a Polari module whose buildable projects are RENDERED per configuration — the UNO
             (`board/custom/firmware/uno`: hal.c/hal.h + apps/*.c, rendered by board.custom.gen per FirmwareVariant into a
             plain project: main.c (the app) + hal.c/hal.h + board_config.h + the generated <class>_packets.h + Makefile)
  plain      any directory a person wrote by hand: *.c / *.h and a Makefile that builds it — "people make hardware C
             normally". Its one configuration is the directory as it is.

A CONFIGURATION is one buildable rendering. An atom compiled only under some knobs (hal_presses under HAL_INT0) is found
in the configuration that turns the knob on; the atom records which configurations compile it. The UNO's list is the four
single-instance seeded variants + two COVERAGE configurations that turn every sc-1 knob on (written below with their
flags — the scenario_rig app, which only the firmware-fault scenarios use), so every function of the template is seen.
"""
import os
import shutil

HERE = os.path.dirname(os.path.abspath(__file__))
MODULES = os.path.dirname(os.path.dirname(HERE))
UNO_ROOT = os.path.join(MODULES, 'board', 'custom', 'firmware', 'uno')
MANIFEST_NAME = 'polari-firmware.json'

#: the coverage configurations (scenario_rig + every sc-1 knob) — dict variants board.custom.variants.resolve validates
_SC = {'app': 'scenario_rig', 'board_definition': 'arduino-uno-r3', 'classes_json': '["SimRigState"]',
       'features_json': '{"led": true, "commands": true}', 'knobs_json': '{"rig_name": "uno-cmod"}', 'twin_stimulus_json': '{}'}
COVERAGE = [
    dict(_SC, name='cmod-cover-commit', title='coverage: every sc-1 knob on, EEPROM write-then-commit, ack with timeout',
         build_flags_json='["HAL_UART_ERRCOUNT=1", "HAL_INT0=1", "HAL_INT0_DEBOUNCE_MS=20", "HAL_WDT=1", "SC_EEPROM_RECORD=2", "SC_ACK_WAIT=1", "SC_ACK_TIMEOUT_MS=200"]'),
    dict(_SC, name='cmod-cover-record', title='coverage: EEPROM record in place, ack without timeout, INT0 without debounce',
         build_flags_json='["HAL_INT0=1", "SC_EEPROM_RECORD=1", "SC_ACK_WAIT=1"]'),
]
TEMPLATES = {
    'uno': {'root': UNO_ROOT, 'root_rel': 'board/custom/firmware/uno', 'board': 'arduino-uno-r3', 'mcu': 'atmega328p',
            'title': 'UNO firmware template (board module)',
            'variants': ['uno-sim-rig', 'uno-blink-only', 'uno-adc-sweep', 'uno-echo'], 'coverage': COVERAGE,
            'modules': [('hal', ['hal.c', 'hal.h'], 'hal'), ('board_config', ['board_config.h'], 'config')]
            + [('apps/%s' % a, ['apps/%s.c' % a], 'app') for a in ('sim_rig', 'blink', 'analog', 'echo', 'scenario_rig')]},
}


class ProjectRefused(ValueError):
    pass


def resolve(project):
    """'uno' (a template) or a directory path (a plain project) → the project spec."""
    if project in TEMPLATES:
        spec = dict(TEMPLATES[project], name=project, kind='template')
        return spec
    path = os.path.abspath(os.path.expanduser(project))
    if not os.path.isdir(path):
        raise ProjectRefused('no project %r — a template (%s) or a directory with *.c and a Makefile' % (project, ', '.join(TEMPLATES)))
    if not os.path.isfile(os.path.join(path, 'Makefile')):
        raise ProjectRefused('%s has no Makefile — a plain project must build with make alone' % path)
    mods = []
    for rel in sorted(_sources(path)):
        stem, ext = os.path.splitext(rel)
        if ext == '.c':
            files = [rel] + ([stem + '.h'] if os.path.isfile(os.path.join(path, stem + '.h')) else [])
            mods.append((stem, files, 'source'))
    paired = {f for _, fs, _ in mods for f in fs}
    mods += [(os.path.splitext(rel)[0], [rel], 'header') for rel in sorted(_sources(path)) if rel.endswith('.h') and rel not in paired]
    # a plain project inside the framework's modules (a rendered graph, cmod-1) is named relative to modules/, so its committed
    # manifest carries no absolute path of the machine that conformed it
    rel = os.path.relpath(path, MODULES) if path.startswith(MODULES + os.sep) else path
    return {'name': os.path.basename(path.rstrip('/')), 'kind': 'plain', 'root': path, 'root_rel': rel, 'board': '', 'mcu': 'atmega328p',
            'title': os.path.basename(path.rstrip('/')), 'modules': mods}


def _sources(root):
    out = []
    for d, dirs, files in os.walk(root):
        dirs[:] = [x for x in dirs if not x.startswith('.') and x not in ('build', 'out', 'obj')]
        for f in files:
            if f.endswith(('.c', '.h')):
                out.append(os.path.relpath(os.path.join(d, f), root))
    return out


def configurations(spec):
    if spec['kind'] == 'plain':
        return [{'name': 'default', 'kind': 'as-is', 'flags': []}]
    from board.custom import variants as V
    out = []
    for name in spec['variants']:
        v = V.find(name)
        out.append({'name': name, 'kind': 'board-variant', 'variant': v, 'app': v['app'], 'flags': []})
    for v in spec['coverage']:
        r = V.resolve(v)
        out.append({'name': v['name'], 'kind': 'coverage', 'variant': v, 'app': v['app'], 'flags': ['%s=%d' % f for f in r['flags']]})
    return out


def render(spec, cfg, work):
    """One configuration → {'dir', 'map': {file in dir: module file rel to the root}, 'generated': [...], 'sources': [...]}."""
    if spec['kind'] == 'plain':
        srcs = sorted(f for f in _sources(spec['root']) if f.endswith('.c'))
        return {'dir': spec['root'], 'map': {f: f for f in srcs}, 'generated': [], 'sources': srcs,
                'include_dirs': [spec['root']] + [os.path.join(spec['root'], d) for d in ('include', 'src') if os.path.isdir(os.path.join(spec['root'], d))]}
    from board.custom import gen
    shutil.rmtree(work, ignore_errors=True)
    row = gen.gen('uno', work=work, variant=cfg['name'], variant_rows=[cfg['variant']])
    d = row['project_dir']
    srcs = sorted(f for f in os.listdir(d) if f.endswith('.c'))
    mp = {'main.c': 'apps/%s.c' % cfg['app']}
    mp.update({f: f for f in srcs if f != 'main.c'})
    gen_files = sorted(f for f in os.listdir(d) if f.endswith('_packets.h')) + ['board_config.h']
    return {'dir': d, 'map': mp, 'generated': gen_files, 'sources': srcs, 'include_dirs': [d], 'source_sha': row.get('source_sha', '')}


def manifest_path(spec):
    return os.path.join(spec['root'], MANIFEST_NAME)
