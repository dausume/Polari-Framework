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


def admit_module_live(manager, module):
    """Admit one on-disk module into the running server. Returns a
    result dict — {'ok': True, ...} on success or no-op, {'ok': False,
    'refusal': ..., 'suggestion': ...} on an honest refusal."""
    with _ADMISSION_LOCK:
        return _admit_locked(manager, module)


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
    if module in MISSING_FEATURE_MODULES:
        # Code arrived AFTER boot: symbols are stubbed and the
        # boot-time defClassList never held its classes, so the
        # pre-gate list cannot supply them. dyn-4 owns this path.
        return {'ok': False, 'module': module,
                'refusal': f"'{module}' was absent at boot — its "
                           'class list is not recoverable in this '
                           'process yet.',
                'suggestion': {
                    'action': 'restart the backend (the code is now '
                              'present, boot admits it), or wait for '
                              'dyn-4 fetch+admit',
                }}

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
    if module_enabled(module) and (already or ctor_done):
        return {'ok': True, 'module': module, 'noop': True,
                'note': f"'{module}' is already online here "
                        f'({len(already)} classes registered).'}

    started = time.time()
    worker = AdmissionWorker(manager)
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
        new_classes = [c for c in classes if c not in already]
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
        return {'ok': True, 'module': module,
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
