"""
@module testing.custom.nocode_checks

ncg-0 (the acct-4 sliver): the editor-vs-engine variant sweep + the
TypeScript-side parity row.

Truth sources, compared per node class so palette/engine drift is a
LIVE matrix row instead of a periodic audit:

  backend registry   StateBuildingBlockRegistry blocks — the P1
                     execution_status/runtime_capability truth-tags.
  python engine      the classes SolutionExecutionEngine actually
                     dispatches (parsed from its source — the same
                     comparisons that route execution).
  frontend palette   state-space-class-registry.ts className entries
                     + its central EXECUTION_STATUS_BY_CLASS map.
  ts capability      capability.ts BACKEND_ONLY_CLASSES /
                     CLIENT_CAPABLE_CLASSES (the P5 partition).

Per-node rows (`nocode:variant-<Class>`) enumerate the STABLE union
(backend registry ∪ python dispatch) so the row set is identical on
host and in containers; palette-only classes surface through the
summary row (`nocode:variant-sweep`), whose frontend legs skip-honest
when the Angular source tree isn't reachable (POLARI_ANGULAR_ROOT
overrides the sibling-directory default).

Drift rule per class: a block CLAIMED 'real' must actually be
dispatched by the python engine; a claimed-client-capable class must
be in capability.ts's client set (when readable). Truthful 'stub'/
'authoring-only' labels PASS — visible debt is the point, lying about
capability is the failure.
"""

import os
import re
import subprocess
import time

from testing.check_catalog import FRAMEWORK_ROOT

_PALETTE_REL = os.path.join(
    'src', 'app', 'components', 'custom-no-code', 'states', '_shared',
    'state-space-class-registry.ts')
_CAPABILITY_REL = os.path.join(
    'src', 'app', 'services', 'no-code-services', 'solution-engine',
    'capability.ts')

ANGULAR_SUGGESTION = (
    'Angular source not reachable at {root} — set POLARI_ANGULAR_ROOT '
    'to the polari-platform-angular checkout to enable the frontend '
    'legs (host runs); inside containers this skip is expected.')
TS_PARITY_SUGGESTION = (
    'Run on a host with the Angular checkout + node/npm: '
    '`npm run parity` in polari-platform-angular (tsc + node '
    'run-parity.js over polariNoCode/parity_vectors/).')


def angular_root():
    override = (os.environ.get('POLARI_ANGULAR_ROOT') or '').strip()
    if override:
        return override
    return os.path.join(os.path.dirname(FRAMEWORK_ROOT),
                        'polari-platform-angular')


def _read(path):
    try:
        with open(path, encoding='utf-8', errors='replace') as fh:
            return fh.read()
    except OSError:
        return None


def python_dispatch_classes():
    """Classes the python engine's dispatch actually compares on."""
    src = _read(os.path.join(FRAMEWORK_ROOT, 'polariNoCode',
                             'SolutionExecutionEngine.py')) or ''
    found = set(re.findall(r"state_class\s*==\s*'([A-Za-z]+)'", src))
    for group in re.findall(
            r"state_class\s+in\s+[\(\[]([^\)\]]+)[\)\]]", src):
        found.update(re.findall(r"'([A-Za-z]+)'", group))
    return found


def backend_registry_blocks():
    """{className: {'status': ..., 'runtime': ...}} from the P1
    truth-tagged StateBuildingBlockRegistry."""
    from polariNoCode.StateBuildingBlock.StateBuildingBlock import (
        StateBuildingBlockRegistry)
    registry = StateBuildingBlockRegistry()
    registry.register_built_in_blocks()
    return {block.class_name:
            {'status': block.execution_status,
             'runtime': getattr(block, 'runtime_capability', None)}
            for block in registry.get_all()}


def palette_facts():
    """(classes, status_by_class) from the palette registry TS, or
    None when the Angular tree isn't reachable."""
    src = _read(os.path.join(angular_root(), _PALETTE_REL))
    if src is None:
        return None
    classes = set(re.findall(r"className:\s*'([A-Za-z0-9_]+)'", src))
    status_by_class = dict(re.findall(
        r"([A-Za-z0-9_]+):\s*\{\s*status:\s*'([a-z-]+)'", src))
    return classes, status_by_class


def capability_sets():
    """(backend_only, client_capable) from capability.ts, or None."""
    src = _read(os.path.join(angular_root(), _CAPABILITY_REL))
    if src is None:
        return None
    def _set(name):
        match = re.search(
            name + r"\s*=\s*new Set\(\[(.*?)\]\)", src, re.DOTALL)
        return set(re.findall(r"'([A-Za-z0-9_]+)'",
                              match.group(1)) if match else [])
    return _set('BACKEND_ONLY_CLASSES'), _set('CLIENT_CAPABLE_CLASSES')


def variant_class_names():
    """The STABLE per-row enumeration: registry ∪ python dispatch —
    identical on host and in containers by construction."""
    return sorted(set(backend_registry_blocks())
                  | python_dispatch_classes())


def variant_inventory():
    """Merged per-class facts across every reachable source."""
    registry = backend_registry_blocks()
    dispatched = python_dispatch_classes()
    palette = palette_facts()
    capability = capability_sets()
    inventory = {}
    for cls in variant_class_names():
        block = registry.get(cls)
        entry = {
            'registry_status': block['status'] if block else None,
            'registry_runtime': block['runtime'] if block else None,
            'python_dispatched': cls in dispatched,
            'palette': None, 'palette_status': None,
            'ts_client': None, 'ts_backend_only': None,
        }
        if palette is not None:
            classes, status_by_class = palette
            entry['palette'] = cls in classes
            # The palette defaults unlisted classes to 'real' — mirror
            # registerClass()'s `known?.status ?? 'real'` exactly.
            entry['palette_status'] = (
                status_by_class.get(cls, 'real') if cls in classes
                else None)
        if capability is not None:
            backend_only, client_capable = capability
            entry['ts_client'] = cls in client_capable
            entry['ts_backend_only'] = cls in backend_only
        inventory[cls] = entry
    return inventory


def _judge(cls, entry):
    """(ok, evidence) for one class — the drift rules."""
    problems = []
    claimed_real = (entry['registry_status'] == 'real'
                    or entry['palette_status'] == 'real')
    if claimed_real and not entry['python_dispatched']:
        problems.append(
            "claimed 'real' but the python engine never dispatches it")
    if (entry['registry_runtime'] == 'client-and-backend'
            and entry['ts_client'] is False):
        problems.append(
            "registry claims client-and-backend but capability.ts's "
            'client set omits it')
    if (entry['registry_runtime'] == 'backend-only'
            and entry['ts_client'] is True):
        problems.append(
            'registry says backend-only but capability.ts claims '
            'the CLIENT can run it — the TS engine would accept '
            'graphs it cannot execute')
    if (entry['ts_backend_only'] and entry['ts_client']):
        problems.append(
            'capability.ts lists it as BOTH backend-only and '
            'client-capable')
    facts = ('registry={0}/{1}; py-engine={2}; palette={3}({4}); '
             'ts-client={5}'.format(
                 entry['registry_status'] or 'unregistered',
                 entry['registry_runtime'] or '-',
                 'yes' if entry['python_dispatched'] else 'NO',
                 {True: 'yes', False: 'NO', None: 'unread'}[
                     entry['palette']],
                 entry['palette_status'] or '-',
                 {True: 'yes', False: 'no', None: 'unread'}[
                     entry['ts_client']]))
    if problems:
        return False, facts + ' | DRIFT: ' + '; '.join(problems)
    return True, facts


def check_variant(cls):
    entry = variant_inventory().get(cls)
    if entry is None:
        return {'status': 'fail',
                'evidence': f'{cls} vanished from registry AND engine '
                            '— catalog is stale, rerun discovery'}
    ok, evidence = _judge(cls, entry)
    # The honest trigger is "the frontend files were UNREADABLE" —
    # a root directory that exists but lacks the palette file (e.g.
    # after a rename) must say so too, not just a missing checkout.
    if entry['palette'] is None:
        evidence += (' | frontend legs skipped: '
                     + ANGULAR_SUGGESTION.format(root=angular_root()))
    return {'status': 'pass' if ok else 'fail', 'evidence': evidence}


def __getattr__(name):
    """check_variant_<Class> callables for the catalog's per-node
    rows (runner_ref 'module:function' takes no arguments)."""
    prefix = 'check_variant_'
    if name.startswith(prefix):
        cls = name[len(prefix):]
        return lambda: check_variant(cls)
    raise AttributeError(name)


def check_variant_sweep():
    """The blocking summary: any per-class drift or set-level anomaly
    fails; palette-only classes surface here (the per-row set stays
    container-stable on registry ∪ dispatch)."""
    inventory = variant_inventory()
    drifted = [cls for cls, entry in inventory.items()
               if not _judge(cls, entry)[0]]
    anomalies = []
    palette = palette_facts()
    frontend_read = palette is not None
    if frontend_read:
        classes, status_by_class = palette
        stable = set(inventory)
        for cls in sorted(classes - stable):
            status = status_by_class.get(cls, 'real')
            note = f'palette-only class {cls} (status {status})'
            # Authorable, unknown to backend registry AND engine,
            # yet defaulting to a 'real' badge = a silent lie.
            if status == 'real':
                anomalies.append(note + " defaults to a 'real' badge")
        capability = capability_sets()
        if capability is not None:
            backend_only, client_capable = capability
            for cls in sorted((backend_only | client_capable)
                              - classes - stable):
                anomalies.append(
                    f'capability.ts names unknown class {cls}')
    verdict_bits = [f'{len(inventory)} classes swept',
                    f'{len(drifted)} drifted',
                    f'{len(anomalies)} anomalies']
    if not frontend_read:
        verdict_bits.append('frontend legs skipped')
    evidence = '; '.join(verdict_bits)
    if drifted:
        evidence += ' | drift: ' + ', '.join(sorted(drifted))
    if anomalies:
        evidence += ' | ' + '; '.join(anomalies)
    if not frontend_read:
        evidence += (' | '
                     + ANGULAR_SUGGESTION.format(root=angular_root()))
    ok = not drifted and not anomalies
    return {'status': 'pass' if ok else 'fail', 'evidence': evidence,
            'passed': len(inventory) - len(drifted),
            'total': len(inventory)}


def check_ts_parity(timeout_s=600):
    """`npm run parity` — the P5 TS engine over the SAME shared
    vectors selftest_parity runs through the python engine."""
    root = angular_root()
    if not os.path.isfile(os.path.join(root, 'package.json')):
        return {'status': 'skip-honest',
                'evidence': ANGULAR_SUGGESTION.format(root=root)
                            + ' ' + TS_PARITY_SUGGESTION}
    try:
        subprocess.run(['npm', '--version'], capture_output=True,
                       timeout=30, check=True)
    except (OSError, subprocess.SubprocessError):
        return {'status': 'skip-honest',
                'evidence': 'npm not runnable on this host. '
                            + TS_PARITY_SUGGESTION}
    start = time.monotonic()
    try:
        proc = subprocess.run(
            ['npm', 'run', 'parity'], cwd=root, timeout=timeout_s,
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
            text=True, errors='replace')
    except subprocess.TimeoutExpired:
        return {'status': 'fail',
                'evidence': f'npm run parity timed out '
                            f'after {timeout_s}s'}
    output = proc.stdout or ''
    counts = re.findall(r'(\d+)\s*/\s*(\d+)', output)
    passed, total = (map(int, counts[-1]) if counts else (None, None))
    seconds = int(time.monotonic() - start)
    if proc.returncode == 0 and counts:
        return {'status': 'pass', 'passed': passed, 'total': total,
                'evidence': f'TypeScript engine {passed}/{total} '
                            f'parity checks in {seconds}s'}
    tail = output.strip()[-800:]
    return {'status': 'fail', 'passed': passed, 'total': total,
            'evidence': f'exit {proc.returncode}; {tail}'}
