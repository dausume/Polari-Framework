"""
@module polariApiServer.live_admission

dyn-2 (DYNAMIC_MODULES_PLAN): admit a module into a RUNNING server —
no container recreate. The exact same steps boot runs, per module,
replayed post-listen:

    typing pass -> defClassList extend -> ownership registry ->
    tables/restore/seeds (AdmissionWorker._admit, reused verbatim) ->
    CRUDE routes -> custom endpoints (module_endpoints constructor) ->
    lifecycle rows + boot record + STOMP.

Honesty during the window: bootRegistry.reopen() re-arms the 503
middleware for the admitting module only; every other module keeps
answering. finish() recomputes all_online afterward.

Boundaries (the plan's, enforced here):
  - core packages refuse (they register everywhere by construction);
  - code absent on disk refuses with the fetch suggestion — the
    fetch+admit loop is dyn-4, and code that was absent at BOOT
    additionally needs its defClassList contribution rebuilt, which
    only dyn-4's un-stub path provides;
  - the POLARI_MODULES env var is a DERIVED CACHE (dyn-2b): admission
    appends to the process-local copy so gating agrees, and reports
    that it did — ModuleAssignment rows stay the durable authority;
  - falcon has no route removal, so endpoint constructors run at most
    once per process (polServer.endpointConstructed).

Thread-safety: one admission at a time (module-level lock); route
mutations happen inside it (the falcon router recompiles on
add_route — serializing admissions keeps that window minimal).
"""

import os
import threading
import time

from moduleService.module_loading import (
    MISSING_FEATURE_MODULES, feature_downloaded, missing_message,
)
from polariApiServer.module_gating import (
    CORE_PACKAGES, module_enabled,
)
from polariApiServer.lazy_boot import AdmissionWorker, top_module

_ADMISSION_LOCK = threading.Lock()


def admit_module_live(manager, module, with_deps=False):
    """Admit one on-disk module into the running server. Returns a
    result dict — {'ok': True, ...} on success or no-op, {'ok': False,
    'refusal': ..., 'suggestion': ...} on an honest refusal.

    with_deps=True admits the module's REQUIRES CLOSURE first, in
    dependency order — the gradual bring-up dyn-5 promises: one call,
    modules arriving one at a time, each admitted only after what it
    needs. Without it a module whose deps are offline refuses and
    names them (the safe default: nothing implicit)."""
    with _ADMISSION_LOCK:
        if not with_deps:
            return _admit_locked(manager, module)
        return _admit_with_deps(manager, module)


def _requires_closure(module):
    """The module's dependency closure, in admission order (deps
    before dependents), from the registry's `requires` — the same
    source boot's dependency_order uses."""
    try:
        from moduleService.module_boot_records import (
            dependency_order, load_module_requires,
        )
    except Exception:
        return [module], {}
    requires = load_module_requires()
    seen, stack, wanted = set(), [module], []
    while stack:
        current = stack.pop()
        if current in seen:
            continue
        seen.add(current)
        wanted.append(current)
        stack.extend(requires.get(current, ()))
    ordered = dependency_order(sorted(wanted), requires)
    if ordered.get('ok'):
        return ordered['order'], requires
    return wanted[::-1], requires


def _admit_with_deps(manager, module):
    order, _ = _requires_closure(module)
    steps, failed = [], None
    for name in order:
        result = _admit_locked(manager, name)
        steps.append({'module': name,
                      'ok': bool(result.get('ok')),
                      'noop': bool(result.get('noop')),
                      'classes': len(result.get('classes') or []),
                      'rows': result.get('seededOrRestoredRows'),
                      'refusal': result.get('refusal')})
        if not result.get('ok'):
            failed = result
            break
    admitted = [s['module'] for s in steps
                if s['ok'] and not s['noop']]
    if failed is not None:
        why = failed.get('refusal') or 'admission failed'
        return {'ok': False, 'module': module,
                'refusal': f"stopped at '{steps[-1]['module']}': "
                           f'{why}',
                'plannedOrder': order, 'steps': steps,
                'admittedBeforeStop': admitted,
                'suggestion': failed.get('suggestion')}
    return {'ok': True, 'module': module, 'withDeps': True,
            'plannedOrder': order, 'steps': steps,
            'admitted': admitted,
            'note': 'dependency closure admitted in order — each '
                    'module came up only after what it needs'}


def put_away_module_live(manager, module):
    """dyn-3: NON-destructive deactivation of a module in the running
    server. Frees in-memory rows/typing/CRUDE and shrinks
    defClassList; DB TABLES STAY INTACT so re-admission is a
    restoreTables away (never purgeObjectType — that drops tables).
    Requests resolving to the module answer 410 Gone with the
    bring-back hint (middleware). Honest limit, stated in the result:
    imported CODE stays resident — only a recreate reclaims it."""
    with _ADMISSION_LOCK:
        return _put_away_locked(manager, module)


def _table_classes(polServer, module):
    """A module's definition-class contribution, rebuilt from the
    dyn-1 import table: the symbols it declares that are treeObject
    subclasses defined BY that module. Verified 2026-08-11 against a
    live boot — exact for every module except pspp, whose 4 classes
    are a pre-existing registration bug (in seed_pairs, absent from
    defClassList => silent no-table), NOT a rule failure."""
    import polariApiServer.polariServer as server_mod
    from objectTreeDecorators import treeObject
    from polariApiServer.feature_imports import FEATURE_IMPORT_BLOCKS
    found = []
    for entry_module, imports in FEATURE_IMPORT_BLOCKS:
        if entry_module != module:
            continue
        for _, symbols in imports:
            for symbol in symbols:
                value = getattr(server_mod, symbol, None)
                if (isinstance(value, type)
                        and issubclass(value, treeObject)
                        and top_module(value) == module
                        and value not in found):
                    found.append(value)
    return found


def _unstub_and_extend(polServer, module):
    """dyn-4: rebind a fetched module's real symbols over its stubs
    and put its classes back into the pre-gate list, so the ordinary
    dyn-2 path can admit it. Broken code raises LOUDLY (never a
    silent skip) — the caller reports the refusal."""
    import polariApiServer.polariServer as server_mod
    from moduleService.module_loading import unstub_feature_module
    from polariApiServer.feature_imports import FEATURE_IMPORT_BLOCKS
    try:
        unstub_feature_module(server_mod.__dict__, module,
                              FEATURE_IMPORT_BLOCKS)
    except ImportError as exc:
        return {'ok': False, 'module': module,
                'refusal': f"'{module}' code is present but does "
                           f'not import: {exc}',
                'suggestion': {
                    'action': 'fix the module or re-fetch it — a '
                              'downloaded module that cannot import '
                              'is a real breakage, never a silent '
                              'skip'}}
    except KeyError:
        return {'ok': False, 'module': module,
                'refusal': f"'{module}' is not declared in the "
                           'feature-import table — nothing to '
                           'un-stub.',
                'suggestion': {
                    'action': 'add its entry to '
                              'polariApiServer/feature_imports.py '
                              '(dyn-1 declaration), then admit'}}
    classes = _table_classes(polServer, module)
    known = set(getattr(polServer, 'allDefClassList', []))
    added = [c for c in classes if c not in known]
    polServer.allDefClassList.extend(added)
    return {'ok': True, 'unstubbed': True,
            'classesRecovered': sorted(c.__name__ for c in added)}


def fetch_and_admit_module(manager, module, source_ref=None,
                           source_kind=None, install_deps=False):
    """dyn-4: pull a module's DEFINITION into this instance and bring
    it online — fetch code (module_fetcher, which clones into
    modules/<name>, already an import root) -> optional per-module
    pip deps -> un-stub from the dyn-1 table -> ordinary live
    admission. Fetching is code execution, so this stays an explicit
    act: peer sources remain refused (no signing story yet), and the
    caller supplies the source or a ModuleSourceConfig row does."""
    with _ADMISSION_LOCK:
        if feature_downloaded(module):
            fetched = {'fetched': False,
                       'note': 'code already present — nothing to '
                               'fetch'}
        else:
            try:
                from polariPeers.module_fetcher import (
                    fetch_module_project,
                )
            except Exception as exc:
                return {'ok': False, 'module': module,
                        'refusal': f'module fetcher unavailable: '
                                   f'{exc}'}
            if (source_kind or '').strip() == 'peer':
                return {'ok': False, 'module': module,
                        'refusal': 'peer-sourced CODE is refused — '
                                   'bundles (rows) from peers are '
                                   'fine; code needs a signing '
                                   'story first.'}
            if source_ref:
                # The fetcher reads a ModuleSourceConfig row — an
                # inline source becomes one (the durable record of
                # WHERE this instance's copy came from).
                configured = _upsert_source_config(
                    manager, module, source_kind or 'git', source_ref)
                if not configured.get('ok'):
                    return {'ok': False, 'module': module,
                            'refusal': 'could not record the module '
                                       'source',
                            'sourceConfig': configured}
            try:
                fetched = fetch_module_project(manager, module)
            except Exception as exc:
                return {'ok': False, 'module': module,
                        'refusal': f'fetch failed: '
                                   f'{type(exc).__name__}: {exc}'}
            if isinstance(fetched, dict) and fetched.get('ok') is False:
                return {'ok': False, 'module': module,
                        'refusal': 'fetch refused',
                        'fetch': fetched}
        if not feature_downloaded(module):
            return {'ok': False, 'module': module,
                    'refusal': f"'{module}' code is still not "
                               'present after the fetch step.',
                    'fetch': fetched}

        deps = {'installed': False,
                'note': 'not requested (install_deps=False) — a pip '
                        'install into a running container is lost on '
                        'recreate; persist accepted packages in '
                        'requirements.txt'}
        if install_deps:
            deps = _install_module_deps(module)
            if not deps.get('ok', True):
                return {'ok': False, 'module': module,
                        'refusal': 'dependency install failed',
                        'fetch': fetched, 'deps': deps}

        result = _admit_locked(manager, module)
        result['fetch'] = fetched
        result['deps'] = deps
        return result


def _upsert_source_config(manager, module, kind, locator, ref=''):
    """Record WHERE this instance's copy of a module comes from —
    the fetcher's input and the durable provenance of fetched code.
    auto_fetch stays OFF: fetching is an explicit act."""
    try:
        from polariPeers.module_source_config import (
            ModuleSourceConfig,
        )
        found = None
        for row in manager.objectTables.get('ModuleSourceConfig',
                                            {}).values():
            if getattr(row, 'name', '') == module:
                found = row
                break
        if found is None:
            found = ModuleSourceConfig(
                name=module, source_kind=kind, locator=locator,
                ref=ref, auto_fetch=False,
                notes='recorded by dyn-4 fetch+admit',
                manager=manager)
        else:
            found.source_kind = kind
            found.locator = locator
            if ref:
                found.ref = ref
        if manager.db is not None:
            manager.db.saveInstanceInDB(found)
        return {'ok': True, 'row': module, 'kind': kind,
                'locator': locator}
    except Exception as exc:
        return {'ok': False,
                'reason': f'{type(exc).__name__}: {exc}'}


def _install_module_deps(module):
    """Per-module pip deps: derived by AST scan, installed with the
    existing confirmed installer. Honest about impermanence."""
    try:
        from moduleService.module_dependency_tracker import (
            install_packages, plan_install,
        )
        from moduleService.module_loading import module_code_dir
        plan = plan_install([module]) if plan_install.__code__ \
            .co_argcount == 1 else plan_install(module_code_dir(module))
        report = install_packages(plan) if plan else {'installed': []}
        return {'ok': True, 'plan': plan, 'report': report,
                'note': 'installed into the RUNNING container only '
                        '— persist accepted packages in '
                        'requirements.txt'}
    except Exception as exc:
        return {'ok': False,
                'reason': f'{type(exc).__name__}: {exc}',
                'note': 'dependency install is best-effort; the '
                        'module may still admit if its imports are '
                        'already satisfiable'}


def _put_away_locked(manager, module):
    polServer = manager.polServer
    registry = polServer.bootRegistry

    if module in CORE_PACKAGES:
        return {'ok': False, 'module': module,
                'refusal': f"'{module}' is a core package — every "
                           'instance needs it; it cannot be put '
                           'away.'}
    classes = [c for c in polServer.defClassList
               if top_module(c) == module]
    ctor_done = module in getattr(polServer, 'endpointConstructed',
                                  set())
    if not classes and not ctor_done:
        return {'ok': True, 'module': module, 'noop': True,
                'note': f"'{module}' is not online here — nothing "
                        'to put away.'}
    # Reverse-requires: putting away a module an ACTIVE module needs
    # would break the dependent silently. Refuse, naming them.
    try:
        from moduleService.module_boot_records import (
            load_module_requires,
        )
        active = {top_module(c) for c in polServer.defClassList} \
            | getattr(polServer, 'endpointConstructed', set())
        active.discard(module)
        dependents = sorted(
            m for m, reqs in load_module_requires().items()
            if module in reqs and m in active)
    except Exception:
        dependents = []
    if dependents:
        return {'ok': False, 'module': module,
                'refusal': f"active modules depend on '{module}': "
                           f'{dependents}.',
                'suggestion': {
                    'action': 'put the dependents away first: '
                              + ', '.join(
                                  f'POST /modules/{d}/put-away'
                                  for d in dependents)}}

    started = time.time()
    freed_rows = 0
    names = [c.__name__ for c in classes]
    for name in names:
        # purgeObjectType minus every destructive step: rows out of
        # RAM (DB rows untouched), typing out of the registries,
        # CRUDE out of the lists (the falcon route stays — the
        # middleware 410s it), tree entries out of the tree.
        table = manager.objectTables.pop(name, None)
        freed_rows += len(table) if table else 0
        typing = manager.objectTypingDict.pop(name, None)
        if typing is not None and typing in manager.objectTyping:
            manager.objectTyping.remove(typing)
        for crude in list(polServer.crudeObjectsList):
            if crude.apiObject == name:
                polServer.crudeObjectsList.remove(crude)
                if crude.apiName in polServer.uriList:
                    polServer.uriList.remove(crude.apiName)
        if manager.objectTree is not None:
            try:
                manager._removeClassFromTree(manager.objectTree, name)
            except Exception:
                pass
    polServer.defClassList = [c for c in polServer.defClassList
                              if top_module(c) != module]

    # Gate cache (dyn-2b): make module_enabled() agree. An unset
    # POLARI_MODULES means ALL — putting one module away turns the
    # knob into the explicit active list minus this module.
    raw = (os.environ.get('POLARI_MODULES') or '').strip()
    if raw:
        names_env = [e.strip() for e in raw.split(',')
                     if e.strip()
                     and e.strip().split('.')[0] != module]
        os.environ['POLARI_MODULES'] = ','.join(names_env)
    else:
        active = sorted(
            ({top_module(c) for c in polServer.defClassList}
             | getattr(polServer, 'endpointConstructed', set()))
            - set(CORE_PACKAGES) - {module})
        os.environ['POLARI_MODULES'] = ','.join(active)

    registry.put_away(module)
    worker = AdmissionWorker(manager)
    registry.mark(module, 'disabled',
                  error=f'put away — POST /modules/{module}/admit '
                        'brings it back',
                  finished_at=time.time())
    row = registry.status_of(module)
    worker._upsert_polari_module(module, row)
    from polariApiServer.lazy_boot import _stomp_publish
    _stomp_publish(module, row)
    # dyn-2b: the change LANDS in the authority + the observation.
    from topology.placement_truth import (
        record_placement_observation, sync_assignment_row,
    )
    row_sync = sync_assignment_row(manager, module, 'disabled',
                                   'live put-away')
    observation = record_placement_observation(manager,
                                               'live put-away')
    return {'ok': True, 'module': module,
            'assignmentRow': row_sync,
            'observation': observation,
            'classesDeactivated': sorted(names),
            'inMemoryRowsFreed': freed_rows,
            'dbTablesKept': True,
            'answers': '410 Gone with the bring-back hint',
            'tookSeconds': round(time.time() - started, 3),
            'note': 'imported code stays resident until the next '
                    'recreate — put-away frees data memory and '
                    'quiets the API, honestly.'}


def _admit_locked(manager, module):
    polServer = manager.polServer
    registry = polServer.bootRegistry

    # ---- refusals, most specific first -------------------------
    if module in CORE_PACKAGES:
        return {'ok': False, 'module': module,
                'refusal': f"'{module}' is a core package — core "
                           'registers everywhere by construction; '
                           'there is nothing to admit.'}
    if not feature_downloaded(module):
        return {'ok': False, 'module': module,
                'refusal': f"'{module}' has no code on this "
                           'instance.',
                'suggestion': {
                    'action': missing_message(module),
                    'note': 'fetch + admit in one step is dyn-4 '
                            '(POST /api/module-projects/fetch, then '
                            'admit after a restart for now)'}}
    unstubbed = None
    if module in MISSING_FEATURE_MODULES:
        # dyn-4: code arrived AFTER boot — its symbols are stubs and
        # allDefClassList never held its classes. Un-stub from the
        # SAME declaration boot used, then rebuild the module's
        # class contribution from the table (see _table_classes).
        unstubbed = _unstub_and_extend(polServer, module)
        if not unstubbed.get('ok'):
            return unstubbed

    # ---- dependency order is mandatory, not cosmetic -----------
    # (cross-module inheritance means a module admits only after its
    # requires; same rule dependency_order enforces at boot.)
    try:
        from moduleService.module_boot_records import (
            load_module_requires,
        )
        needs = [d for d in load_module_requires().get(module, ())
                 if not module_enabled(d)
                 or d in MISSING_FEATURE_MODULES]
    except Exception:
        needs = []
    if needs:
        return {'ok': False, 'module': module,
                'refusal': f"'{module}' requires "
                           f"{sorted(needs)} which are not online "
                           'on this instance.',
                'suggestion': {
                    'action': 'admit the dependencies first, in '
                              'order: '
                              + ', '.join(f'POST /modules/{d}/admit'
                                          for d in sorted(needs))}}

    classes = [c for c in getattr(polServer, 'allDefClassList', [])
               if top_module(c) == module]
    already = [c for c in polServer.defClassList
               if top_module(c) == module]
    ctor_done = module in getattr(polServer, 'endpointConstructed',
                                  set())
    new_classes = [c for c in classes if c not in already]
    from polariApiServer.module_endpoints import (
        MODULE_ENDPOINT_CONSTRUCTORS,
    )
    ctor_pending = (module in MODULE_ENDPOINT_CONSTRUCTORS
                    and not ctor_done)
    # A no-op means genuinely NOTHING left to do: every declared
    # class registered AND the endpoints constructed. A partially
    # present module (e.g. one class registered by another path)
    # must still admit the rest.
    if module_enabled(module) and not new_classes and not ctor_pending:
        return {'ok': True, 'module': module, 'noop': True,
                'note': f"'{module}' is already online here "
                        f'({len(already)} classes registered).'}

    started = time.time()
    worker = AdmissionWorker(manager)
    registry.readmit(module)  # clear any dyn-3 put-away marker
    registry.reopen(module)
    worker._transition(module, 'loading', started_at=started,
                       deps_ready_at=started)
    try:
        # ---- gate cache: process-local POLARI_MODULES ----------
        env_updated = False
        raw = (os.environ.get('POLARI_MODULES') or '').strip()
        if raw:
            names = {e.strip().split('.')[0]
                     for e in raw.split(',') if e.strip()}
            if module not in names:
                os.environ['POLARI_MODULES'] = f'{raw},{module}'
                env_updated = True

        # ---- typing pass (the boot block, per class) -----------
        for cls in new_classes:
            typing = manager.getObjectTyping(classObj=cls)
            if typing is not None:
                typing.excludeFromCRUDE = False
                typing.isDefinitionClass = True
                typing.initializeVarsFromSignature()
        polServer.defClassList.extend(new_classes)
        registry.register_classes(new_classes)

        # ---- tables + restore + seeds (boot's own step) --------
        seeded = worker._admit(module)

        # ---- routes: CRUDE + custom endpoints ------------------
        routes_added = []
        for cls in new_classes:
            crude = polServer.registerCRUDEforObjectType(cls.__name__)
            if crude is not None:
                routes_added.append(crude.apiName)
        constructed = False
        if not ctor_done:
            from polariApiServer.module_endpoints import (
                MODULE_ENDPOINT_CONSTRUCTORS,
            )
            ctor = MODULE_ENDPOINT_CONSTRUCTORS.get(module)
            if ctor is not None:
                ctor(polServer)
                constructed = True
            polServer.endpointConstructed.add(module)

        worker._transition(module, 'online', finished_at=time.time(),
                           seeded_rows=seeded)
        registry.finish()
        # dyn-2b: the change LANDS in the authority + the observation.
        from topology.placement_truth import (
            record_placement_observation, sync_assignment_row,
        )
        row_sync = sync_assignment_row(manager, module, 'enabled',
                                       'live admission')
        observation = record_placement_observation(manager,
                                                   'live admission')
        return {'ok': True, 'module': module,
                'assignmentRow': row_sync,
                'observation': observation,
                'classes': sorted(c.__name__ for c in new_classes),
                'seededOrRestoredRows': seeded,
                'crudeRoutes': routes_added,
                'customEndpointsConstructed': constructed,
                'envUpdatedProcessLocal': env_updated,
                'tookSeconds': round(time.time() - started, 3),
                'note': 'POLARI_MODULES is a derived cache — the '
                        'durable truth is the ModuleAssignment row '
                        '(pol topology assign).'}
    except BaseException as exc:
        worker._transition(module, 'failed',
                           error=f'{type(exc).__name__}: {exc}',
                           finished_at=time.time())
        registry.finish()
        raise
