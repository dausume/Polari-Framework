"""
@cross-cutting
@module topology.topology_io

Portable topology packages (top-1 groundwork for top-3):
export_topology() emits the SELF-CONTAINED, CREDENTIAL-FREE document
that becomes `topologies/<name>.topology.yml`, and merge_topology_doc()
plans an idempotent-by-name import of such a document.

Credential-free BY CONSTRUCTION: no topology class carries a secret —
connections reference artifact PATHS, and the credential substrate
regenerates content on every target. Packages are safe to
commit/share.

Round-trip contract (top-3 gate): export(merge(export(X))) ==
export(X). merge is PURE (returns a plan, creates nothing) so the
contract is testable stdlib-only; the API/CLI applies plans.

@consumers
  - topology.topology_api (/api/topology/export|import)
  - polari-cli scripts/topology.sh (top-2/3 pull/push/export/deploy)
"""

import json

from topology.topology_analysis import _loads, _rows, _scoped
from topology.topology_constants import SCHEMA_VERSION

#: Classes a package carries, in dependency order (referenced rows
#: before referencing rows), with the fields that travel. Machines are
#: NOT topology-scoped (shared substrate) so they export as
#: requirements the deploy target must satisfy or map.
PACKAGE_FIELDS = {
    'PolariNodeMachine': (
        'name', 'ssh_alias', 'arch', 'mem_gb', 'roles_json',
        'swarm_role', 'repo_dir', 'source', 'notes'),
    'TopologyDefinition': (
        'name', 'description', 'default_target', 'status',
        'schema_version', 'notes'),
    'InstanceDefinition': (
        'name', 'kind', 'service_kinds_json', 'replicas', 'env_tier',
        'machine_name', 'placement_constraint', 'db_backend',
        'image_tag', 'orchestration_target', 'topology_name', 'notes'),
    'ModuleAssignment': (
        'name', 'module_name', 'instance_name', 'state',
        'topology_name', 'notes'),
    'ModuleDependencyEdge': (
        'name', 'module_name', 'consumer_instance_name',
        'depends_on_module', 'provider_instance_name', 'status',
        'topology_name', 'notes'),
    'ServiceConnection': (
        'name', 'interconnect_key', 'from_kind', 'to_kind',
        'from_instance_name', 'to_instance_name', 'artifact',
        'topology_name', 'notes'),
}

#: Fields that are LIVE state, not desired state — excluded so a
#: package equals itself regardless of when it was exported.
_VOLATILE = {'is_active', 'validation_findings_json', 'validated_at',
             'evidence_json'}


def _row_dict(row, fields):
    return {f: getattr(row, f, '') for f in fields
            if f not in _VOLATILE}


def export_topology(manager, topology_name):
    """One topology as a portable, credential-free document."""
    defs = [r for r in _rows(manager, 'TopologyDefinition')
            if getattr(r, 'name', '') == topology_name]
    if not defs:
        return {'ok': False,
                'error': f'no TopologyDefinition named "{topology_name}"'}
    inst = _scoped(manager, 'InstanceDefinition', topology_name)
    machine_names = {getattr(i, 'machine_name', '') for i in inst}
    doc = {
        'schema_version': SCHEMA_VERSION,
        'kind': 'polari-topology-package',
        'topology': _row_dict(defs[0],
                              PACKAGE_FIELDS['TopologyDefinition']),
        # Only the machines this topology actually places onto —
        # exported as REQUIREMENTS the deploy target satisfies/maps.
        'machines': sorted(
            (_row_dict(m, PACKAGE_FIELDS['PolariNodeMachine'])
             for m in _rows(manager, 'PolariNodeMachine')
             if getattr(m, 'name', '') in machine_names),
            key=lambda d: d['name']),
        'instances': sorted(
            (_row_dict(i, PACKAGE_FIELDS['InstanceDefinition'])
             for i in inst), key=lambda d: d['name']),
        'assignments': sorted(
            (_row_dict(a, PACKAGE_FIELDS['ModuleAssignment'])
             for a in _scoped(manager, 'ModuleAssignment',
                              topology_name)),
            key=lambda d: d['name']),
        'edges': sorted(
            (_row_dict(e, PACKAGE_FIELDS['ModuleDependencyEdge'])
             for e in _scoped(manager, 'ModuleDependencyEdge',
                              topology_name)),
            key=lambda d: d['name']),
        'connections': sorted(
            (_row_dict(c, PACKAGE_FIELDS['ServiceConnection'])
             for c in _scoped(manager, 'ServiceConnection',
                              topology_name)),
            key=lambda d: d['name']),
    }
    return {'ok': True, 'document': doc}


_DOC_SECTIONS = (
    ('machines', 'PolariNodeMachine'),
    ('topology', 'TopologyDefinition'),
    ('instances', 'InstanceDefinition'),
    ('assignments', 'ModuleAssignment'),
    ('edges', 'ModuleDependencyEdge'),
    ('connections', 'ServiceConnection'),
)


def merge_topology_doc(manager, doc):
    """Plan an idempotent-by-name import of a package document.

    PURE — returns {'creates': [(class_name, row_dict)], 'skips':
    [...]} without touching anything. Existing names are skipped
    (seed contract); the CLI's diff view (top-2) is where field-level
    updates get surfaced as suggestions.
    """
    if not isinstance(doc, dict) or doc.get(
            'kind') != 'polari-topology-package':
        return {'ok': False,
                'error': 'not a polari-topology-package document'}
    if str(doc.get('schema_version', '')) != SCHEMA_VERSION:
        return {'ok': False,
                'error': f'schema_version {doc.get("schema_version")!r}'
                         f' != supported {SCHEMA_VERSION!r}'}
    creates, skips = [], []
    for section, class_name in _DOC_SECTIONS:
        entries = doc.get(section, [])
        if isinstance(entries, dict):
            entries = [entries]
        existing = {getattr(r, 'name', '')
                    for r in _rows(manager, class_name)}
        allowed = set(PACKAGE_FIELDS[class_name]) - _VOLATILE
        for entry in entries:
            name = entry.get('name', '')
            row = {k: v for k, v in entry.items() if k in allowed}
            if not name:
                skips.append({'class': class_name, 'name': '',
                              'reason': 'entry without a name'})
            elif name in existing:
                skips.append({'class': class_name, 'name': name,
                              'reason': 'exists (idempotent-by-name)'})
            else:
                creates.append((class_name, row))
    return {'ok': True, 'creates': creates, 'skips': skips}


def package_equal(doc_a, doc_b):
    """Round-trip comparator: semantic equality of two packages."""
    return json.dumps(doc_a, sort_keys=True) == json.dumps(
        doc_b, sort_keys=True)
