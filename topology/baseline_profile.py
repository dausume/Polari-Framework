"""
@module topology.baseline_profile

dyn-5 (DYNAMIC_MODULES_PLAN): the BASELINE instance — lightweight but
functional, so a polari-rf comes up fast on modest hardware and every
other module arrives afterward, one at a time, on demand
(dyn-2 admit / dyn-4 fetch+admit).

Dustin's shape (2026-08-10): "quickly put up baseline polari-rf
instances and then follow through on the gradual bring up of modules
one at a time... so we can put away modules when we do not need them
and develop with the limited resources we have."

What the floor contains, and WHY each one is floor rather than
convenience:

  polariapps  — an instance must be able to DESCRIBE what it offers
                (PolariAppDefinition rows, the app nav) before it can
                sensibly offer anything;
  appstore    — and be able to hand a client the shell/registration
                that reaches it;
  islemesh    — and be locatable on the mesh it belongs to.

Everything else is demand-driven. Core packages are NOT listed: they
register everywhere by construction (module_gating.CORE_PACKAGES) and
naming them would imply they were optional.

The baseline is EXPLICIT ROWS, never an empty env: an empty
POLARI_MODULES means the monolithic ALL-modules default, which is the
opposite of a baseline. `plan_baseline` produces the rows to write;
`pol topology baseline` (CLI) writes them and applies.
"""

from polariApiServer.module_gating import CORE_PACKAGES

#: The floor. Three modules — describe, deliver, locate.
BASELINE_MODULES = ('polariapps', 'appstore', 'islemesh')

#: Modules a baseline deliberately EXCLUDES even though a monolithic
#: boot would load them — named so the exclusion reads as a decision
#: rather than an oversight.
BASELINE_NOTES = {
    'scoring': 'heavy seed set; admit when the scorecard work needs '
               'it',
    'materialsScience': 'engine-backed; wants a worker host anyway',
    'testing': 'opt-in package — test builds only',
}


def baseline_rows(instance, topology_name=''):
    """The ModuleAssignment rows a baseline instance needs, as plain
    dicts (pure — writing them is the caller's job)."""
    return [{'name': f'{module}@{instance}',
             'module_name': module,
             'instance_name': instance,
             'state': 'enabled',
             'topology_name': topology_name,
             'notes': 'dyn-5 baseline floor'}
            for module in BASELINE_MODULES]


def plan_baseline(manager, instance, topology_name=''):
    """Preview: what a baseline for `instance` would declare, what it
    would REMOVE from any current declaration, and the honest cost
    statement. Executes nothing (knobs-and-suggestions: the mover
    previews, the human applies)."""
    from topology.topology_analysis import active_topology_name
    topology_name = topology_name or active_topology_name(manager)
    current = {}
    for row in manager.objectTables.get('ModuleAssignment',
                                        {}).values():
        if getattr(row, 'instance_name', '') == instance:
            current[getattr(row, 'module_name', '')] = \
                getattr(row, 'state', '')
    enabled_now = {m.split('.')[0] for m, s in current.items()
                   if s == 'enabled'}
    floor = set(BASELINE_MODULES)
    return {
        'ok': True,
        'instance': instance,
        'topology': topology_name,
        'baselineModules': sorted(floor),
        'rows': baseline_rows(instance, topology_name),
        'alreadyEnabled': sorted(enabled_now & floor),
        'toEnable': sorted(floor - enabled_now),
        'toStandDown': sorted(enabled_now - floor),
        'coreAlwaysPresent': sorted(CORE_PACKAGES),
        'excludedOnPurpose': BASELINE_NOTES,
        'note': 'a baseline is explicit ROWS — an empty '
                'POLARI_MODULES would boot the monolithic '
                'ALL-modules default instead',
        'afterwards': 'bring modules up one at a time: POST '
                      '/modules/{m}/admit (on disk) or '
                      '/modules/{m}/fetch-admit (pull the '
                      'definition in); put them away with '
                      '/modules/{m}/put-away',
    }


def apply_baseline(manager, instance, topology_name='',
                   stand_down=False):
    """Write the baseline rows. `stand_down` additionally marks
    non-floor enabled rows 'transient' — the reversibility contract
    (visible, inert, one click back), never deleted. Live modules are
    NOT torn down here: rows are the declaration, and
    /modules/{m}/put-away is the live act (dyn-3), so an operator can
    declare a baseline and stand modules down deliberately."""
    plan = plan_baseline(manager, instance, topology_name)
    topology_name = plan['topology']
    written, stood_down = [], []
    try:
        from topology.topology_modules import ModuleAssignment
    except Exception as exc:
        return {'ok': False, 'refusal': f'topology rows unavailable: '
                                        f'{exc}'}
    existing = {}
    for row in manager.objectTables.get('ModuleAssignment',
                                        {}).values():
        if getattr(row, 'instance_name', '') == instance:
            existing[getattr(row, 'module_name', '')] = row
    for module in BASELINE_MODULES:
        row = existing.get(module)
        if row is None:
            row = ModuleAssignment(
                name=f'{module}@{instance}', module_name=module,
                instance_name=instance, state='enabled',
                topology_name=topology_name,
                notes='dyn-5 baseline floor', manager=manager)
        else:
            row.state = 'enabled'
            row.notes = 'dyn-5 baseline floor'
        if manager.db is not None:
            manager.db.saveInstanceInDB(row)
        written.append(row.name)
    if stand_down:
        for module, row in existing.items():
            if (module.split('.')[0] not in BASELINE_MODULES
                    and getattr(row, 'state', '') == 'enabled'):
                row.state = 'transient'
                row.notes = ('stood down by dyn-5 baseline — '
                             'visible, inert, one click back')
                if manager.db is not None:
                    manager.db.saveInstanceInDB(row)
                stood_down.append(row.name)
    return {'ok': True, 'instance': instance,
            'topology': topology_name,
            'rowsWritten': written,
            'stoodDownToTransient': stood_down,
            'plan': plan,
            'next': 'pol topology apply --plan (deploy-time env '
                    'derives from these rows); modules arrive live '
                    'via /modules/{m}/admit afterwards'}
