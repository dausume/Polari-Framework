"""
@cross-cutting
@module topology.topology_self

tpl-0 (AI-Notes/plans/TOPOLOGY_LAYERS_PLAN.md): a backend DESCRIBES ITSELF in the Polari topology, with no isle and no
`pol` CLI. Every fresh backend used to carry the 2026-07-09 dev snapshot (topology_seed) as reality and called itself
'local'; now it knows its own name and writes its own rows at boot, idempotently:

    TopologyDefinition   the active one if any, else one named after this instance (status applied, active)
    InstanceDefinition   this instance (created if absent; an existing row is left as its owner wrote it)
    ModuleAssignment     one per module ACTUALLY live here (placement_truth.sync_assignment_row, the dyn-2b authority path)

Knobs (labelled; every value derived or said in words):
    POLARI_INSTANCE_NAME   this instance's name. Absent -> derived from the first https://<name>.isle CORS origin (the isle
                           instance generator writes that origin first), else 'local'.
    POLARI_MACHINE_NAME    the device this instance runs on. Absent -> ISLE_HOSTNAME, else '' (unknown, never a container id).
    POLARI_TOPOLOGY_SEED   'example' seeds the 2026-07-09 dev snapshot (topology_seed); 'none' does not. Absent -> 'example'
                           only when this instance is one the snapshot itself describes (the compose suite's prf-a), else
                           'none'. So a compose stack spun up from its own files keeps its page; an isle backend shows itself.

    instance_name() / machine_name() / seed_mode()
    describe_self(manager, live_modules, source) -> {ok, instance, topology, machine, assignments, created, words}
"""
import os
from urllib.parse import urlsplit

SEED_MODES = ('example', 'none')
_DEPLOY_TIERS = {'development': 'dev', 'dev': 'dev', 'staging': 'staging', 'production': 'prod', 'prod': 'prod', 'test': 'test'}


def instance_name():
    explicit = (os.environ.get('POLARI_INSTANCE_NAME') or os.environ.get('POLARI_INSTANCE_ID') or '').strip()
    if explicit:
        return explicit
    for origin in (os.environ.get('CORS_ORIGINS') or '').split(','):
        host = (urlsplit(origin.strip()).hostname or '')
        if host.endswith('.isle') and host.count('.') == 1:
            return host[:-len('.isle')]
    return 'local'


def machine_name():
    return (os.environ.get('POLARI_MACHINE_NAME') or os.environ.get('ISLE_HOSTNAME') or '').strip()


def _example_instances():
    try:
        from topology.topology_seed import SEED_INSTANCE_DEFINITIONS
        return {s.get('name') for s in SEED_INSTANCE_DEFINITIONS}
    except Exception:  # noqa: BLE001 - no seed module = nothing to describe
        return set()


def seed_mode():
    knob = (os.environ.get('POLARI_TOPOLOGY_SEED') or '').strip().lower()
    if knob in SEED_MODES:
        return knob
    return 'example' if instance_name() in _example_instances() else 'none'


def _rows(manager, cls):
    return list((getattr(manager, 'objectTables', None) or {}).get(cls, {}).values())


def _save(manager, row):
    db = getattr(manager, 'db', None)
    if db is not None:
        db.saveInstanceInDB(row)


def describe_self(manager, live_modules, source='boot'):
    me = instance_name()
    machine = machine_name()
    created = []
    topologies = _rows(manager, 'TopologyDefinition')
    topo = next((t for t in topologies if getattr(t, 'is_active', False)), None) or (topologies[0] if topologies else None)
    if topo is None:
        from topology.topology_state import TopologyDefinition
        topo = TopologyDefinition(name=me, description='This backend as it describes itself (tpl-0): its own instance and the '
                                  'modules live on it. Peers and the isle add their rows beside it.',
                                  status='applied', is_active=True, notes='self-described at %s (tpl-0)' % source, manager=manager)
        _save(manager, topo)
        created.append('TopologyDefinition:%s' % topo.name)
    inst = next((i for i in _rows(manager, 'InstanceDefinition') if getattr(i, 'name', '') == me), None)
    if inst is None:
        from topology.topology_basis import InstanceDefinition
        tier = _DEPLOY_TIERS.get((os.environ.get('DEPLOY_ENV') or '').strip().lower(), 'dev')
        inst = InstanceDefinition(name=me, kind='prf', service_kinds_json='["prf-backend"]', env_tier=tier, machine_name=machine,
                                  topology_name=topo.name, notes='self-described at %s (tpl-0)' % source, manager=manager)
        _save(manager, inst)
        created.append('InstanceDefinition:%s' % me)
    from topology.placement_truth import sync_assignment_row
    synced = [m for m in sorted(live_modules)
              if sync_assignment_row(manager, m, 'enabled', 'self-described at %s (tpl-0)' % source).get('synced')]
    return {'ok': True, 'instance': me, 'topology': topo.name, 'machine': machine, 'assignments': synced, 'created': created,
            'words': '%s describes itself in topology %s: %d live module%s%s%s'
                     % (me, topo.name, len(synced), '' if len(synced) == 1 else 's',
                        ' on %s' % machine if machine else ' (its device unknown: set POLARI_MACHINE_NAME)',
                        '; created ' + ', '.join(created) if created else '')}


def after_boot(manager, source='boot'):
    """The end-of-boot hook (lazy boot and the monolithic seed pass): describe this backend, then let a module that ships
    boot-time data finish it (cmod: the Bench topology specs, manual fix 13). Best-effort: each part reports in words and a
    failure never stops the boot. -> {self, benches}"""
    out = {}
    try:
        from topology.placement_truth import live_module_set
        out['self'] = describe_self(manager, live_module_set(manager.polServer), source)
    except Exception as exc:  # noqa: BLE001 - a standalone/host-tool manager may have no topology classes
        out['self'] = {'ok': False, 'words': 'self-description skipped: %s: %s' % (type(exc).__name__, exc)}
    try:
        from cmod.custom.bench_topology_spec import apply_shipped
        out['benches'] = apply_shipped(manager)
    except ImportError:
        out['benches'] = []
    except Exception as exc:  # noqa: BLE001
        out['benches'] = [{'applied': False, 'words': 'bench specs skipped: %s: %s' % (type(exc).__name__, exc)}]
    return out
