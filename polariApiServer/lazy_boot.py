"""
@module polariApiServer.lazy_boot

mlb-1/2/3 (MODULE_LAZY_BOOT_PLAN): TWO-PHASE BOOT.

Knob: POLARI_LAZY_BOOT=on|off (default off = today's monolithic boot,
the safe fallback; the knob is read once at process start).

Phase 0 (synchronous, seconds): typing + route registration only —
no DB, no seeds, no restore. The entrypoint starts LISTENING, then
launches the admission worker (daemon thread, same idiom as the mesh
autoconfig thread).

Admission worker:
  1. CORE DATA: jumpstartDatabase restoring core-owned (and orphan)
     tables + ensureDefinitionTables for core classes -> core-ready.
     /api/health flips 200 here; ModuleBootRecord history is restored
     here, so per-module ETAs are available before modules trickle.
  2. Each gated-in feature module, dependency-ordered
     (module_boot_records.dependency_order over the json register):
     tables -> restore -> seeds -> dynamic init, then online + a
     ModuleBootRecord (duration measured from deps-ready, per
     Dustin). Transitions broadcast over the existing STOMP topics.
  3. persistTree + the auto-fetch hook, exactly once, at the end.

Honesty: while a module is pending/loading, requests that resolve to
its resources return 503 with {moduleLoading, status, etaSeconds} —
never a 404, never empty data. A module that FAILS admission stays
failed and LOUD (error text on the row + traceback in the log);
dependents of a failed module are marked blocked, not skipped
silently.

@consumers
  - initLocalhostPolariServer (worker launch + phase-0 skip)
  - polariApiServer.polariServer (registry + middleware + endpoints)
  - objectTreeManagerDecorators (phase-0 DB skip)
  - moduleService.selftest_lazy_boot
"""

import os
import threading
import time
import traceback

import falcon

from polariApiServer.module_gating import CORE_PACKAGES


def lazy_boot_enabled():
    """POLARI_LAZY_BOOT=on|true|1|yes turns the two-phase boot on;
    anything else is the monolithic default."""
    raw = (os.environ.get('POLARI_LAZY_BOOT') or 'off').strip().lower()
    return raw in ('1', 'true', 'yes', 'on')


def top_module(cls):
    return (getattr(cls, '__module__', '') or '').split('.')[0]


def is_core_module(name):
    return name in CORE_PACKAGES


#: Lifecycle states a module moves through during admission.
LIFECYCLE = ('pending', 'loading', 'online', 'failed', 'blocked',
             'disabled')


class ModuleBootRegistry:
    """In-memory truth for the current boot. Thread-safe. The durable
    mirrors (PolariModule lifecycle fields + ModuleBootRecord rows)
    are written by the worker once the DB exists."""

    def __init__(self):
        self._lock = threading.Lock()
        self.lazy = lazy_boot_enabled()
        self.boot_started_at = time.time()
        self.boot_id = str(int(self.boot_started_at))
        self.core_data_ready_at = None
        self.finished_at = None
        # {module: {status, started_at, finished_at, error,
        #           seeded_rows, deps, deps_ready_at, eta_s}}
        self.modules = {}
        # {className: module} for middleware resolution.
        self.class_owner = {}
        # In monolithic boots everything is online by construction.
        self.all_online = not self.lazy

    def register_classes(self, classes):
        with self._lock:
            for cls in classes:
                self.class_owner[cls.__name__] = top_module(cls)

    def plan(self, module_names, requires):
        with self._lock:
            for m in module_names:
                self.modules[m] = {
                    'status': 'pending', 'started_at': None,
                    'finished_at': None, 'error': '',
                    'seeded_rows': 0,
                    'deps': sorted(requires.get(m, ())),
                    'deps_ready_at': None, 'eta_s': None,
                }

    def mark(self, module, status, **extra):
        with self._lock:
            row = self.modules.setdefault(module, {
                'status': 'pending', 'started_at': None,
                'finished_at': None, 'error': '', 'seeded_rows': 0,
                'deps': [], 'deps_ready_at': None, 'eta_s': None})
            row['status'] = status
            row.update(extra)

    def core_ready(self):
        with self._lock:
            self.core_data_ready_at = time.time()

    def finish(self):
        with self._lock:
            self.finished_at = time.time()
            self.all_online = all(
                r['status'] in ('online', 'disabled')
                for r in self.modules.values())

    def status_of(self, module):
        with self._lock:
            row = self.modules.get(module)
            return dict(row) if row else None

    def is_data_pending(self, module):
        """True while requests touching `module` should 503: feature
        modules until online; core-owned data until core-ready."""
        if self.all_online:
            return False
        with self._lock:
            if is_core_module(module) or module == '__dynamic__':
                return self.core_data_ready_at is None
            row = self.modules.get(module)
            if row is None:
                return self.core_data_ready_at is None
            return row['status'] not in ('online', 'disabled')

    def owner_of_class(self, class_name):
        with self._lock:
            return self.class_owner.get(class_name)

    def snapshot(self):
        with self._lock:
            # Disabled modules are tracked (visible) but not counted
            # toward bring-up progress.
            total = sum(1 for r in self.modules.values()
                        if r['status'] != 'disabled')
            online = sum(1 for r in self.modules.values()
                         if r['status'] == 'online')
            return {
                'lazyBoot': self.lazy,
                'bootId': self.boot_id,
                'bootStartedAt': self.boot_started_at,
                'coreReadyAt': self.core_data_ready_at,
                'finishedAt': self.finished_at,
                'secondsToCore': (
                    round(self.core_data_ready_at
                          - self.boot_started_at, 3)
                    if self.core_data_ready_at else None),
                'secondsToFull': (
                    round(self.finished_at - self.boot_started_at, 3)
                    if self.finished_at else None),
                'moduleCount': total,
                'onlineCount': online,
                'percentOnline': (round(100.0 * online / total, 1)
                                  if total else 100.0),
                'modules': {m: dict(r)
                            for m, r in self.modules.items()},
            }


class ModuleLoadingMiddleware:
    """503-not-404 while a resource's owning module is still loading.
    Resolution: polariCRUDE resources own one CLASS (apiObject) ->
    the class's module; custom API resources belong to their defining
    package. Core custom APIs (health/status/system-info) never
    block."""

    #: Custom-API classes that must answer during boot.
    ALWAYS_OPEN = ('HealthEndpoint', 'ModulesStatusEndpoint')

    def __init__(self, polServer):
        self._polServer = polServer

    def process_resource(self, req, resp, resource, params):
        registry = getattr(self._polServer, 'bootRegistry', None)
        if registry is None or registry.all_online:
            return
        if type(resource).__name__ in self.ALWAYS_OPEN:
            return
        class_name = getattr(resource, 'apiObject', None)
        if isinstance(class_name, str) and class_name:
            module = registry.owner_of_class(class_name) \
                or '__dynamic__'
        else:
            module = top_module(type(resource))
            if is_core_module(module):
                # Core custom APIs stay open — they carry no
                # module-owned table data of their own.
                return
        if not registry.is_data_pending(module):
            return
        status = registry.status_of(module) or {}
        raise falcon.HTTPServiceUnavailable(
            title='module loading',
            description=(
                f"module '{module}' is "
                f"{status.get('status', 'booting')} — data is not "
                'online yet'),
            headers={'Retry-After': '5'},
        ) from None


class HealthEndpoint:
    """GET /api/health — 200 once CORE DATA is ready (the plan's
    'healthcheck flips healthy at core-ready'); 503 with the boot
    snapshot before that. Monolithic boots are core-ready by
    construction (requests can't arrive pre-listen)."""

    def __init__(self, polServer):
        self._polServer = polServer
        polServer.falconServer.add_route('/api/health', self)

    def on_get(self, request, response):
        registry = getattr(self._polServer, 'bootRegistry', None)
        snap = registry.snapshot() if registry else {}
        core_ready = (not registry) or (not registry.lazy) \
            or registry.core_data_ready_at is not None
        response.media = {
            'ok': core_ready,
            'phase': ('online' if not registry or registry.all_online
                      else 'admitting-modules' if core_ready
                      else 'core-boot'),
            **snap,
        }
        if not core_ready:
            response.status = '503 Service Unavailable'


class ModulesStatusEndpoint:
    """GET /api/modules/status — the mlb-3 summary doc: core-ready
    time, per-module lifecycle rows (+ deps + ETA from history),
    counts, overall percent."""

    def __init__(self, polServer):
        self._polServer = polServer
        polServer.falconServer.add_route('/api/modules/status', self)

    def on_get(self, request, response):
        registry = getattr(self._polServer, 'bootRegistry', None)
        if registry is None:
            response.media = {'ok': True, 'lazyBoot': False,
                              'note': 'registry absent — monolithic '
                                      'boot, everything online'}
            return
        response.media = {'ok': True, **registry.snapshot()}


def _stomp_publish(module, row):
    """Broadcast a lifecycle transition over the existing STOMP
    machinery (topic per class, like every other row change)."""
    try:
        from polariApiServer.stompWebSocketServer import (
            get_stomp_server,
        )
        server = get_stomp_server()
        if server is not None:
            server.publish('/topic/PolariModule', {
                'operation': 'module-boot-status',
                'module': module, **row})
    except Exception:
        pass  # push is best-effort; poll fallback always works


def _instance_name():
    return (os.environ.get('POLARI_INSTANCE_NAME')
            or os.environ.get('POLARI_INSTANCE_ID') or 'local')


class AdmissionWorker:
    """The post-listen bring-up. One instance per process; `run()`
    is the daemon-thread body (initLocalhostPolariServer starts it
    just before the blocking listen)."""

    def __init__(self, manager):
        self.manager = manager
        self.polServer = manager.polServer
        self.registry = self.polServer.bootRegistry

    # -- planning ------------------------------------------------

    def feature_modules_present(self):
        """Feature (non-core) modules this boot should admit — the
        modules owning gated-in defClassList classes, plus the
        dynamic-loader modules."""
        mods = set()
        for cls in self.polServer.defClassList:
            m = top_module(cls)
            if not is_core_module(m):
                mods.add(m)
        return mods

    def class_names_for(self, modules):
        return {cls.__name__ for cls in self.polServer.defClassList
                if top_module(cls) in modules}

    def core_class_names(self):
        return {cls.__name__ for cls in self.polServer.defClassList
                if is_core_module(top_module(cls))}

    # -- history / ETA -------------------------------------------

    def _history_rows(self):
        return list(self.manager.objectTables
                    .get('ModuleBootRecord', {}).values())

    def _stamp_etas(self):
        from moduleService.module_boot_records import (
            expected_duration_s,
        )
        rows = self._history_rows()
        instance = _instance_name()
        for module in list(self.registry.modules):
            eta = expected_duration_s(rows, module, instance)
            if eta is not None:
                self.registry.mark(
                    module,
                    self.registry.status_of(module)['status'],
                    eta_s=round(eta, 3))

    # -- durable mirrors -----------------------------------------

    def _upsert_polari_module(self, module, row):
        try:
            from polariPeers.polari_module import PolariModule
            table = self.manager.objectTables.get('PolariModule', {})
            found = None
            for inst in table.values():
                if getattr(inst, 'name', None) == module:
                    found = inst
                    break
            if found is None:
                found = PolariModule(name=module, status='installed',
                                     manager=self.manager)
            found.boot_status = row['status']
            found.boot_started_at = row.get('started_at') or 0.0
            found.boot_finished_at = row.get('finished_at') or 0.0
            found.seeded_rows = row.get('seeded_rows') or 0
            found.boot_error = row.get('error') or ''
            found.expected_online_s = row.get('eta_s') or 0.0
            if self.manager.db is not None:
                self.manager.db.saveInstanceInDB(found)
        except Exception as exc:
            print(f'[LazyBoot] PolariModule mirror failed for '
                  f'{module}: {exc}', flush=True)

    def _write_boot_record(self, module, row):
        try:
            from moduleService.module_boot_records import (
                ModuleBootRecord,
            )
            instance = _instance_name()
            deps_ready = row.get('deps_ready_at') \
                or self.registry.core_data_ready_at \
                or self.registry.boot_started_at
            online_at = row.get('finished_at') or time.time()
            record = ModuleBootRecord(
                name=f'{module}@{instance}@{self.registry.boot_id}',
                module_name=module,
                instance_name=instance,
                boot_id=self.registry.boot_id,
                boot_started_at=self.registry.boot_started_at,
                deps_ready_at=deps_ready,
                online_at=online_at,
                duration_after_deps_s=round(online_at - deps_ready, 3),
                status=('online' if row['status'] == 'online'
                        else 'failed'),
                error=row.get('error') or '',
                seeded_rows=row.get('seeded_rows') or 0,
                lazy_boot=True,
                manager=self.manager)
            if self.manager.db is not None:
                self.manager.db.saveInstanceInDB(record)
        except Exception as exc:
            print(f'[LazyBoot] boot record failed for {module}: '
                  f'{exc}', flush=True)

    def _transition(self, module, status, **extra):
        self.registry.mark(module, status, **extra)
        row = self.registry.status_of(module)
        _stomp_publish(module, row)
        if status in ('online', 'failed'):
            self._upsert_polari_module(module, row)
            self._write_boot_record(module, row)

    # -- the phases ----------------------------------------------

    def run(self):
        try:
            self._run_inner()
        except BaseException as exc:
            print(f'[LazyBoot] ADMISSION WORKER CRASHED: '
                  f'{type(exc).__name__}: {exc}', flush=True)
            traceback.print_exc()

    def _run_inner(self):
        manager, polServer = self.manager, self.polServer
        registry = self.registry
        from moduleService.module_boot_records import (
            dependency_order, load_module_requires,
        )
        feature_mods = self.feature_modules_present()
        requires = load_module_requires()
        registry.plan(sorted(feature_mods), requires)
        # Track what is NOT enabled too — known modules gated off or
        # absent on this instance show as 'disabled', so the topology
        # view can display the full enabled/disabled split honestly.
        try:
            from moduleService.module_loading import FEATURE_MODULES
            known = set(FEATURE_MODULES) | set(requires)
            for m in sorted(known - feature_mods):
                registry.mark(m, 'disabled',
                              error='not enabled on this instance '
                                    '(POLARI_MODULES gate or not '
                                    'downloaded)')
        except Exception:
            pass

        # ---- Phase A: core data --------------------------------
        print('[LazyBoot] Phase A: core data (DB + core tables/'
              'seeds/restore)…', flush=True)
        t0 = time.time()
        core_names = self.core_class_names()
        feature_names = self.class_names_for(feature_mods)
        # Restore: core-owned tables + every table NOT owned by a
        # pending feature module (dynamic classes, legacy tables).
        manager.jumpstartDatabase(
            skip_restore_tables=feature_names)
        polServer.ensureDefinitionTables(only_classes=core_names)
        if getattr(manager, 'hasObjectStore', False):
            pass  # object store connects in managerObject.__init__
        registry.core_ready()
        self._stamp_etas()
        print(f'[LazyBoot] core data ready in '
              f'{time.time() - t0:.1f}s — admitting '
              f'{len(feature_mods)} modules', flush=True)

        # ---- Phase B: modules, dependency-ordered --------------
        ordered = dependency_order(sorted(feature_mods), requires)
        if not ordered.get('ok'):
            print(f"[LazyBoot] {ordered['refusal']}", flush=True)
            for m in feature_mods:
                self._transition(m, 'failed',
                                 error=ordered['refusal'],
                                 finished_at=time.time())
            return
        failed = set()
        online_at = {}
        for module in ordered['order']:
            deps = set(requires.get(module, ())) & feature_mods
            if deps & failed:
                self._transition(
                    module, 'blocked',
                    error='dependency failed: '
                          + ', '.join(sorted(deps & failed)),
                    finished_at=time.time())
                failed.add(module)  # dependents of blocked block too
                continue
            deps_ready_at = max(
                [online_at[d] for d in deps if d in online_at],
                default=registry.core_data_ready_at)
            self._transition(module, 'loading',
                             started_at=time.time(),
                             deps_ready_at=deps_ready_at)
            try:
                seeded = self._admit(module)
                self._transition(module, 'online',
                                 finished_at=time.time(),
                                 seeded_rows=seeded,
                                 deps_ready_at=deps_ready_at)
                online_at[module] = time.time()
                row = registry.status_of(module)
                took = (row['finished_at'] or 0) - deps_ready_at
                print(f'[LazyBoot] {module} ONLINE in {took:.1f}s '
                      f'after deps ({seeded} rows)', flush=True)
            except BaseException as exc:
                traceback.print_exc()
                self._transition(module, 'failed',
                                 error=f'{type(exc).__name__}: {exc}',
                                 finished_at=time.time(),
                                 deps_ready_at=deps_ready_at)
                failed.add(module)
                print(f'[LazyBoot] {module} FAILED: {exc}',
                      flush=True)

        # ---- Phase C: dynamic modules + close-out --------------
        try:
            polServer.initializeDynamicModules()
        except BaseException as exc:
            print(f'[LazyBoot] dynamic module init failed: {exc}',
                  flush=True)
            traceback.print_exc()
        registry.finish()
        try:
            manager.persistTree()
        except BaseException as exc:
            print(f'[LazyBoot] persistTree failed: {exc}', flush=True)
        try:
            from polariPeers.module_fetcher import (
                auto_fetch_configured,
            )
            for result in auto_fetch_configured(manager):
                print(f'[ModuleProjects] auto-fetch: {result}',
                      flush=True)
        except Exception as exc:
            print(f'[ModuleProjects] auto-fetch skipped: {exc}',
                  flush=True)
        snap = registry.snapshot()
        print(f"[LazyBoot] BOOT COMPLETE: {snap['onlineCount']}/"
              f"{snap['moduleCount']} modules online, core in "
              f"{snap['secondsToCore']}s, full in "
              f"{snap['secondsToFull']}s", flush=True)

    def _admit(self, module):
        """Bring ONE module's data online: tables + column sync,
        row restore, seeds. Returns the number of restored+seeded
        rows (best-effort count)."""
        manager, polServer = self.manager, self.polServer
        names = self.class_names_for({module})
        before = sum(
            len(manager.objectTables.get(n, {})) for n in names)
        manager.restoreTables(only_tables=names)
        polServer.ensureDefinitionTables(only_classes=names)
        after = sum(
            len(manager.objectTables.get(n, {})) for n in names)
        return max(0, after - before)


def start_admission_worker(manager):
    worker = AdmissionWorker(manager)
    thread = threading.Thread(target=worker.run, daemon=True,
                              name='module-admission')
    thread.start()
    return worker
