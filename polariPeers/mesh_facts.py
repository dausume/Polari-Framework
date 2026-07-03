"""
@cross-cutting
@module polariPeers.mesh_facts
@tags @xc:bindings

Mesh facts — Polari's READ-ONLY view of the Isle-Mesh seam
(/MESH_CONVERGENCE_PLAN.md §4): am-i-meshed, my .isle name, known
devices, service-name claims. The isle CLI owns the answers; Polari only
consumes them.

Graceful absence is the contract: no isle CLI on the host (the normal
unmeshed case, e.g. inside the twin containers) → {'meshed': False},
never an exception. Isle-Mesh hasn't shipped `isle facts --json` yet, so
the command is OVERRIDABLE (env POLARI_MESH_FACTS_CMD /
POLARI_MESH_CLAIM_CMD) — role auto-config develops and tests against a
mock long before the real subcommand lands.

@consumers
  - polariPeers.role_autoconfig (detect/claim/discover evidence)
  - polariPeers.agreements_api (the same-isle auto-approve knob)
@see /MESH_CONVERGENCE_PLAN.md §4, §7
"""

import json
import os
import shlex
import subprocess
from typing import Any, Dict

FACTS_CMD_DEFAULT = 'isle facts --json'
CLAIM_CMD_DEFAULT = 'isle claim {name} --json'
CMD_TIMEOUT_S = 10

UNMESHED: Dict[str, Any] = {
    'meshed': False, 'isleName': '', 'devices': [], 'claims': {},
}


def _run_json(cmd: str) -> Dict[str, Any]:
    """Run a CLI command, parse stdout as JSON. {'_error': ...} on any
    failure (missing binary, non-zero exit, bad JSON, timeout)."""
    try:
        proc = subprocess.run(
            shlex.split(cmd), capture_output=True, text=True,
            timeout=CMD_TIMEOUT_S)
    except (OSError, ValueError, subprocess.TimeoutExpired) as exc:
        return {'_error': f'{type(exc).__name__}: {exc}'}
    if proc.returncode != 0:
        return {'_error': f'exit {proc.returncode}: '
                          f'{(proc.stderr or "").strip()[:200]}'}
    try:
        parsed = json.loads(proc.stdout or '')
    except ValueError as exc:
        return {'_error': f'bad JSON: {exc}'}
    return parsed if isinstance(parsed, dict) else {'_error': 'non-object JSON'}


def get_mesh_facts() -> Dict[str, Any]:
    """The mesh-facts snapshot. Always returns the full shape; `source`
    says where it came from ('cli' | 'absent:<why>')."""
    cmd = (os.environ.get('POLARI_MESH_FACTS_CMD') or FACTS_CMD_DEFAULT).strip()
    result = _run_json(cmd)
    if '_error' in result:
        out = dict(UNMESHED)
        out['source'] = f'absent:{result["_error"]}'
        return out
    return {
        'meshed': bool(result.get('meshed')),
        'isleName': result.get('isleName') or result.get('isle_name') or '',
        'devices': result.get('devices') or [],
        'claims': result.get('claims') or {},
        'source': 'cli',
    }


def claim_name(name: str) -> Dict[str, Any]:
    """Atomic first-claim-wins name claim via the mesh registry.
    Returns {'claimed': bool, 'owner': ..., 'source': ...}; when the CLI
    is absent the claim is simply UNAVAILABLE ({'claimed': False,
    'available': False}) — callers proceed without a mesh claim."""
    template = (os.environ.get('POLARI_MESH_CLAIM_CMD')
                or CLAIM_CMD_DEFAULT).strip()
    cmd = template.replace('{name}', shlex.quote(name))
    result = _run_json(cmd)
    if '_error' in result:
        return {'claimed': False, 'available': False,
                'source': f'absent:{result["_error"]}'}
    return {
        'claimed': bool(result.get('claimed')),
        'available': True,
        'owner': result.get('owner') or '',
        'source': 'cli',
    }
