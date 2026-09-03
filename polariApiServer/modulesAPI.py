"""
Module Management API

Provides endpoints for viewing, toggling, creating, and seeding optional modules.

GET  /modules        — list all discovered modules with status
PUT  /modules        — enable or disable a module
POST /modules/seed   — load seed data for an enabled module
POST /modules/export — write a module's user-authored rows to its
                       initialData/ (json_seeds.export_rows + the
                       module's export_hook privacy strip)
POST /modules/create — create a new module from a definition
"""

from objectTreeDecorators import treeObject, treeObjectInit
import falcon
import json
import importlib
import os
import re


class ModulesAPI(treeObject):
    """
    Falcon resource for /modules endpoint.
    """

    @treeObjectInit
    def __init__(self, polServer):
        self.polServer = polServer
        self.apiName = '/modules'
        if polServer is not None:
            polServer.falconServer.add_route(self.apiName, self)
            polServer.falconServer.add_route(self.apiName + '/seed', self, suffix='seed')
            polServer.falconServer.add_route(self.apiName + '/create', self, suffix='create')
            polServer.falconServer.add_route(self.apiName + '/registry', self, suffix='registry')
            polServer.falconServer.add_route(self.apiName + '/{module_id}', self, suffix='detail')
            # module data convention: the module's initialData/*.json served
            # so another instance can install it by API (json_seeds)
            polServer.falconServer.add_route(self.apiName + '/{module_id}/initial-data', self, suffix='initial_data')
            # mo-3: the reverse path — live user-authored rows written back
            # to the module's initialData/ through its privacy hook
            polServer.falconServer.add_route(self.apiName + '/export', self, suffix='export')

    # ------------------------------------------------------------------
    # GET /modules
    # ------------------------------------------------------------------
    def on_get(self, request, response):
        """Return the list of discovered modules with their status."""
        try:
            modules = self._build_module_list()
            response.media = {"success": True, "modules": modules}
            response.status = falcon.HTTP_200
        except Exception as err:
            response.status = falcon.HTTP_500
            response.media = {"success": False, "error": str(err)}
            print(f"[ModulesAPI] Error in GET: {err}")
            import traceback
            traceback.print_exc()

        response.set_header('Powered-By', 'Polari')

    # ------------------------------------------------------------------
    # GET /modules/{module_id}
    # ------------------------------------------------------------------
    def on_get_detail(self, request, response, module_id):
        """Return detailed info for a single module including classes and dependencies."""
        try:
            from moduleService.moduleDiscovery import (
                discover_available_modules, scan_python_imports,
                detect_cross_module_dependencies
            )

            discovered = discover_available_modules()
            if module_id not in discovered:
                # tt-10: FRAMEWORK BOUNDARY modules (aquaponics,
                # topology, waxprint, ...) aren't in the optional-
                # module registry but are exactly what the graph
                # drill-ins link to — serve them from their source
                # directory + the registered class list.
                return self._boundary_detail(
                    response, module_id)

            info = discovered[module_id]
            module_classes = self.polServer._module_classes.get(module_id, [])
            is_enabled = len(module_classes) > 0
            # Debug: log class names and their types
            for i, cn in enumerate(module_classes):
                print(f"[ModulesAPI] {module_id} class[{i}]: {cn!r} (type={type(cn).__name__})", flush=True)

            # Count instances
            instance_count = 0
            if is_enabled:
                for cn in module_classes:
                    if cn in self.manager.objectTables:
                        instance_count += len(self.manager.objectTables[cn])

            # Build class details
            classes_detail = []
            if is_enabled:
                classes_detail = self._get_classes_from_typing(module_classes)
            else:
                # For disabled user-created modules, read from metadata
                classes_detail = self._get_classes_from_metadata(info['dir_path'])

            # Scan Python imports
            python_deps = scan_python_imports(info['dir_path'])

            # Detect cross-module Polari dependencies
            polari_deps = []
            if is_enabled:
                polari_deps = detect_cross_module_dependencies(
                    module_id, module_classes,
                    self.polServer._module_classes, self.manager
                )

            # tt-10 drill-in map: everything the module DEFINES with
            # a place to navigate to — per-class row counts (data),
            # display pages (pages), text-scanned add_route strings
            # (functionality), and the selftest suites.
            storage = self._storage_descriptor()
            for entry in classes_detail:
                cn = entry.get('className', '')
                entry['instanceCount'] = len(
                    self.manager.objectTables.get(cn, {}) or {})
                # tt-14: where this class's rows live ON THIS
                # backend (class↔database clarity).
                entry['database'] = storage['name']
            response.media = {
                "success": True,
                "module": {
                    "id": module_id,
                    "name": info['display_name'],
                    "description": info['description'],
                    "enabled": is_enabled,
                    "available": info['available'],
                    "userCreated": info['user_created'],
                    "classCount": len(module_classes) if is_enabled else len(classes_detail),
                    "seedInstanceCount": instance_count,
                    "classes": classes_detail,
                    "storage": storage,
                    "pythonDependencies": python_deps,
                    "polariDependencies": polari_deps,
                    "pages": self._module_pages(
                        module_id, module_classes),
                    "apiRoutes": self._scan_api_routes(
                        info['dir_path']),
                    "selftests": self._module_selftests(
                        module_id, info['dir_path']),
                }
            }
            response.status = falcon.HTTP_200

        except Exception as err:
            response.status = falcon.HTTP_500
            response.media = {"success": False, "error": str(err)}
            print(f"[ModulesAPI] Error in GET detail: {err}")
            import traceback
            traceback.print_exc()

        response.set_header('Powered-By', 'Polari')

    # ------------------------------------------------------------------
    # PUT /modules
    # ------------------------------------------------------------------
    def on_put(self, request, response):
        """Toggle a module on or off.

        Request body: { "moduleId": "<module_id>", "enabled": true/false }
        """
        try:
            body = request.media
            module_id = body.get('moduleId')
            enabled = body.get('enabled')

            if not module_id:
                response.status = falcon.HTTP_400
                response.media = {"success": False, "error": "moduleId is required"}
                return

            if enabled is None:
                response.status = falcon.HTTP_400
                response.media = {"success": False, "error": "enabled is required"}
                return

            # Verify the module exists
            from moduleService.moduleDiscovery import discover_available_modules
            discovered = discover_available_modules()
            if module_id not in discovered:
                response.status = falcon.HTTP_404
                response.media = {"success": False, "error": f"Unknown module: {module_id}"}
                return

            if not discovered[module_id]['available']:
                response.status = falcon.HTTP_400
                response.media = {"success": False, "error": f"Module {module_id} is not available (import failed)"}
                return

            self._last_purge_summary = None
            self._toggle_module(module_id, bool(enabled), discovered[module_id])

            display_name = discovered[module_id]['display_name']
            resp_body = {
                "success": True,
                "message": f"{display_name} module {'enabled' if enabled else 'disabled'}",
                "modules": self._build_module_list()
            }
            if self._last_purge_summary is not None:
                resp_body["purgeSummary"] = self._last_purge_summary
            response.media = resp_body
            response.status = falcon.HTTP_200

        except Exception as err:
            response.status = falcon.HTTP_500
            response.media = {"success": False, "error": str(err)}
            print(f"[ModulesAPI] Error in PUT: {err}")
            import traceback
            traceback.print_exc()

        response.set_header('Powered-By', 'Polari')

    # ------------------------------------------------------------------
    # POST /modules/seed
    # ------------------------------------------------------------------
    def on_get_initial_data(self, request, response, module_id):
        """GET /modules/{module_id}/initial-data — the module's committed
        initialData/*.json payloads (module data convention), for another
        instance's POST /modules/seed {"moduleId", "source": <this api>}."""
        from moduleService import json_seeds
        pkg = json_seeds.resolve_package(module_id)
        if json_seeds.data_dir(pkg) is None or not json_seeds.list_files(pkg):
            response.status = falcon.HTTP_404
            response.media = {"success": False, "error": f"module {module_id} carries no initialData"}
            return
        body = json_seeds.serve(pkg)
        body['success'] = True
        body['moduleId'] = module_id
        response.media = body
        response.set_header('Powered-By', 'Polari')

    def on_post_seed(self, request, response):
        """Load seed data for an enabled module.

        Request body: { "moduleId": "<module_id>", "source"?: "<api base of
        another instance to pull initial-data from instead of the local
        files> }
        """
        try:
            body = request.media
            module_id = body.get('moduleId')
            source = body.get('source')

            if not module_id:
                response.status = falcon.HTTP_400
                response.media = {"success": False, "error": "moduleId is required"}
                return

            from moduleService import json_seeds
            pkg = json_seeds.resolve_package(module_id)
            module_classes = self.polServer._module_classes.get(module_id, [])
            if not module_classes and not json_seeds.list_files(pkg) and not source:
                response.status = falcon.HTTP_400
                response.media = {"success": False, "error": f"Module {module_id} must be enabled before loading seed data"}
                return

            if source:
                payloads = json_seeds.fetch(source, module_id)
                res = json_seeds.apply(pkg, self.manager, payloads=payloads,
                                       tag=f'{module_id}.initialData@{source}')
                seed_result = {
                    "totalCount": sum(len(v) for v in res['created'].values()),
                    "classCount": len(res['created']),
                    "classes": {k: len(v) for k, v in res['created'].items()},
                    "source": source, "reports": res['reports'],
                    "skipped": res['skipped']}
            else:
                seed_result = self._seed_module(module_id)
            response.media = {
                "success": True,
                "message": f"Loaded {seed_result['totalCount']} seed records across {seed_result['classCount']} classes",
                "seedResult": seed_result,
                "modules": self._build_module_list()
            }
            response.status = falcon.HTTP_200

        except Exception as err:
            response.status = falcon.HTTP_500
            response.media = {"success": False, "error": str(err)}
            print(f"[ModulesAPI] Error in POST /seed: {err}")
            import traceback
            traceback.print_exc()

        response.set_header('Powered-By', 'Polari')

    # ------------------------------------------------------------------
    # POST /modules/export
    # ------------------------------------------------------------------
    def on_post_export(self, request, response):
        """Write a module's live rows to modules/<pkg>/initialData/
        (mo-3, the reverse of /modules/seed).

        Request body: { "moduleId": "<module_id>", "classes"?: [names],
        "onlyNonPrior"?: true }. Only is_prior=False (user-authored)
        rows leave the tables by default — seeds stay in code (D5) —
        and every field the module's export_hook.strip_fields() names
        is removed. Refuses when the module carries no export_hook AND
        no class list can be found. The files then travel with
        `pol modules publish <module>` / push-all-dev.
        """
        try:
            body = request.media or {}
            module_id = body.get('moduleId')
            if not module_id:
                response.status = falcon.HTTP_400
                response.media = {"success": False, "error": "moduleId is required"}
                return
            from moduleService import json_seeds
            pkg = json_seeds.resolve_package(module_id)
            if json_seeds.package_dir(pkg) is None:
                response.status = falcon.HTTP_404
                response.media = {"success": False,
                                  "error": f"module {module_id}: no package dir (modules/{pkg})"}
                return
            hook = json_seeds.load_export_hook(pkg)
            classes = body.get('classes') or None
            if classes and not isinstance(classes, list):
                classes = [c.strip() for c in str(classes).split(',') if c.strip()]
            if not classes and not hook:
                classes = (json_seeds.package_class_names(pkg)
                           or list(self.polServer._module_classes.get(module_id, []) or []))
                if not classes:
                    response.status = falcon.HTTP_400
                    response.media = {
                        "success": False,
                        "error": (f"module {module_id} has no modules/{pkg}/export_hook.py "
                                  f"(include_classes / strip_fields / filter_row) and no "
                                  f"class list ({pkg.upper()}_CLASSES absent, module not "
                                  f"booted, no \"classes\" in the body) — nothing to export")}
                    return
            res = json_seeds.export_rows(
                self.manager, pkg, class_names=classes,
                only_non_prior=bool(body.get('onlyNonPrior', True)),
                hook=hook, source=f'{module_id} live tables')
            response.media = {
                "success": True, "moduleId": module_id, "package": pkg,
                "hook": bool(hook),
                "message": (f"exported {res['total']} row(s) across "
                            f"{len(res['files'])} file(s); stripped fields: "
                            f"{', '.join(res['stripped_fields']) or '-'}"),
                "files": res['files'], "removed": res['removed'],
                "classes": res['classes'], "stripped": res['stripped_fields'],
                "dropped": res['dropped'], "skipped": res['skipped'],
            }
            response.status = falcon.HTTP_200
        except ValueError as err:
            response.status = falcon.HTTP_400
            response.media = {"success": False, "error": str(err)}
        except Exception as err:
            response.status = falcon.HTTP_500
            response.media = {"success": False, "error": str(err)}
            print(f"[ModulesAPI] Error in POST /export: {err}")
            import traceback
            traceback.print_exc()
        response.set_header('Powered-By', 'Polari')

    # ------------------------------------------------------------------
    # POST /modules/create
    # ------------------------------------------------------------------
    def on_get_registry(self, request, response):
        """mp-1: the module register — official/vendor/self entries
        with filesystem-synced downloaded flags (never stale)."""
        from moduleService.module_registry import load_registry
        response.media = {'success': True,
                          'registry': load_registry()}
        response.set_header('Powered-By', 'Polari')

    def on_post_create(self, request, response):
        """Create a new module from a definition.

        Request body: {
            "name": "My Module",
            "description": "...",
            "classes": [
                {
                    "className": "MyClass",
                    "fields": [
                        {"name": "title", "type": "str"},
                        {"name": "count", "type": "int"}
                    ]
                }
            ]
        }
        """
        try:
            body = request.media
            if not body:
                response.status = falcon.HTTP_400
                response.media = {"success": False, "error": "Request body is required"}
                return

            from moduleService.moduleScaffoldGenerator import scaffold_module

            result = scaffold_module(body)

            # Persist new module as disabled by default
            from moduleService.moduleState import save_module_state
            save_module_state(result['module_id'], False)

            # mp-1: user-created modules register as kind 'self' in
            # the inspectable register — your own module has the
            # same shape as an official one.
            from moduleService.module_registry import register_module
            register_module(
                result['module_id'], 'self',
                description=body.get('description', ''),
                path=f"modules/{result['package_name']}")

            response.media = {
                "success": True,
                "message": f"Module '{body.get('name', '')}' created successfully",
                "moduleId": result['module_id'],
                "packageName": result['package_name'],
                "classesCreated": result['classes_created'],
                "modules": self._build_module_list()
            }
            response.status = falcon.HTTP_201

        except ValueError as ve:
            response.status = falcon.HTTP_400
            response.media = {"success": False, "error": str(ve)}
        except Exception as err:
            response.status = falcon.HTTP_500
            response.media = {"success": False, "error": str(err)}
            print(f"[ModulesAPI] Error in POST /create: {err}")
            import traceback
            traceback.print_exc()

        response.set_header('Powered-By', 'Polari')

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    # ------------------------------------------------------------------
    # tt-10 drill-in helpers — where a module's pages/functionality/
    # data live, so a person can navigate straight to them.
    # ------------------------------------------------------------------

    def _boundary_detail(self, response, module_id):
        """Detail for a framework directory module: classes derived
        from the registered class list (a class belongs to the
        boundary whose package defines it), plus the same drill-in
        map as registry modules. Honest 404 when no such directory
        exists."""
        import os as _os
        root = _os.path.dirname(_os.path.dirname(
            _os.path.abspath(__file__)))
        # mp-1: feature modules may live in either import root.
        dir_path = _os.path.join(root, module_id)
        if not _os.path.isdir(dir_path):
            dir_path = _os.path.join(root, 'modules', module_id)
        if not _os.path.isdir(dir_path):
            # mp-3: a registered module whose code is absent gets the
            # honest get-command, not a generic 404.
            from moduleService.module_registry import load_registry
            from moduleService.module_loading import missing_message
            if module_id in load_registry().get('modules', {}):
                response.status = falcon.HTTP_404
                response.media = {
                    "success": False,
                    "notDownloaded": True,
                    "error": missing_message(module_id)}
                return
            response.status = falcon.HTTP_404
            response.media = {
                "success": False,
                "error": f"Module '{module_id}' not found — neither "
                         "a registry module nor a framework "
                         "directory"}
            return
        from moduleService.moduleDiscovery import scan_python_imports
        from moduleService.module_dependency_tracker import (
            FRAMEWORK_BOUNDARIES, _sanitize_import_names,
            scan_boundary_imports,
        )
        module_classes = sorted(
            cls.__name__ for cls in (getattr(
                self.polServer, 'defClassList', None) or [])
            if getattr(cls, '__module__', '').split('.')[0]
            == module_id)
        classes_detail = self._get_classes_from_typing(
            module_classes)
        storage = self._storage_descriptor()
        for entry in classes_detail:
            entry['instanceCount'] = len(
                self.manager.objectTables.get(
                    entry.get('className', ''), {}) or {})
            entry['database'] = storage['name']
        instance_count = sum(
            entry['instanceCount'] for entry in classes_detail)
        response.media = {
            "success": True,
            "module": {
                "id": module_id,
                "name": module_id,
                "description": FRAMEWORK_BOUNDARIES.get(
                    module_id,
                    f'framework module directory {module_id}/'),
                "enabled": True,
                "available": True,
                "userCreated": False,
                "classCount": len(module_classes),
                "seedInstanceCount": instance_count,
                "classes": classes_detail,
                "storage": storage,
                "pythonDependencies": _sanitize_import_names(
                    scan_python_imports(dir_path)),
                "polariDependencies": [
                    {"moduleId": dep, "moduleName": dep,
                     "reasons": ["imports the boundary"]}
                    for dep in scan_boundary_imports(
                        module_id, root)],
                "pages": self._module_pages(
                    module_id, module_classes),
                "apiRoutes": self._scan_api_routes(dir_path),
                "selftests": self._module_selftests(
                    module_id, dir_path),
            }
        }
        response.status = falcon.HTTP_200
        response.set_header('Powered-By', 'Polari')

    def _storage_descriptor(self):
        """tt-14: WHERE this backend's object rows live — so 'which
        database does this class live on' has a concrete answer.
        Honest scope: this descriptor is THIS instance's storage;
        instances with their own local sqlite answer for their own
        rows (sqlite ownership is per-instance by design)."""
        db = getattr(self.manager, 'db', None)
        adapter = getattr(db, 'adapter', None)
        kind = type(adapter).__name__ if adapter is not None else ''
        scope = str(getattr(db, 'instanceScope', '') or '')
        if 'Maria' in kind:
            return {
                'kind': 'mariadb',
                'name': f"mariadb:{getattr(adapter, 'database', '?')}"
                        f"@{getattr(adapter, 'host', '?')}",
                'shared': True,
                'note': 'shared MariaDB — visible to every sharing '
                        'instance'
                        + (f' (shared-object scope "{scope}")'
                           if scope else '')}
        if 'Sqlite' in kind:
            local_name = (getattr(adapter, 'dbName', '')
                          or getattr(db, 'name', '') or '?')
            return {
                'kind': 'sqlite',
                'name': f'sqlite:{local_name}',
                'shared': False,
                'note': 'local sqlite file — THIS instance owns '
                        'these objects; other instances own their '
                        'own sqlite files'}
        return {'kind': kind or 'unknown', 'name': '',
                'shared': False,
                'note': 'no db adapter visible on this manager'}

    def _module_pages(self, module_id, module_classes):
        """DisplayDefinition rows this module defines: attributed by
        source_class membership, or by the page/route carrying the
        module's own name. Each entry carries the frontend route."""
        pages = []
        class_set = set(module_classes or [])
        needle = module_id.lower()
        for row in (self.manager.objectTables.get(
                'DisplayDefinition', {}) or {}).values():
            name = getattr(row, 'name', '')
            source_class = getattr(row, 'source_class', '')
            page_route = getattr(row, 'pageRoute', '') or ''
            mine = (source_class in class_set
                    or needle in name.lower()
                    or (page_route and needle in page_route.lower()))
            if not mine:
                continue
            pages.append({
                'name': name,
                'sourceClass': source_class,
                'route': page_route or f'/display/{name}',
            })
        return sorted(pages, key=lambda p: p['name'])

    #: Catches both spellings in the codebase: direct
    #: `falconServer.add_route('/x', ...)` and the aliased
    #: `add = polServer.falconServer.add_route; add('/x', ...)` —
    #: the leading '/' keeps unrelated add() calls out.
    _ROUTE_RE = re.compile(
        r"(?:add_route|\badd)\(\s*['\"](/[^'\"]*)['\"]")

    def _scan_api_routes(self, dir_path):
        """The module's registered API routes, text-scanned from its
        own source (same idiom as scan_boundary_imports — catches
        the real strings, no server introspection)."""
        routes = set()
        if not dir_path or not os.path.isdir(dir_path):
            return []
        for dirpath, _dirnames, filenames in os.walk(dir_path):
            if '__pycache__' in dirpath:
                continue
            for filename in filenames:
                if not filename.endswith('.py'):
                    continue
                try:
                    with open(os.path.join(dirpath, filename),
                              encoding='utf-8',
                              errors='ignore') as f:
                        source = f.read()
                except OSError:
                    continue
                routes.update(self._ROUTE_RE.findall(source))
        return sorted(routes)

    def _module_selftests(self, module_id, dir_path):
        """Selftest suites in the module dir + the exact command
        that runs them (the pol CLI's discovery rule)."""
        suites = []
        if dir_path and os.path.isdir(dir_path):
            for filename in sorted(os.listdir(dir_path)):
                if (filename.startswith('selftest_')
                        and filename.endswith('.py')):
                    suites.append(
                        f'{module_id}.{filename[:-3]}')
        return {
            'suites': suites,
            'command': (f'pol modules selftest {module_id}'
                        if suites else ''),
        }

    def _build_module_list(self):
        """Build the list of module descriptors from dynamic discovery."""
        from moduleService.moduleDiscovery import discover_available_modules

        discovered = discover_available_modules()
        modules = []

        for module_id, info in discovered.items():
            module_classes = self.polServer._module_classes.get(module_id, [])
            is_enabled = len(module_classes) > 0

            # Count instances in objectTables
            instance_count = 0
            if is_enabled:
                for cls_name in module_classes:
                    if cls_name in self.manager.objectTables:
                        instance_count += len(self.manager.objectTables[cls_name])

            modules.append({
                "id": module_id,
                "name": info['display_name'],
                "description": info['description'],
                "enabled": is_enabled,
                "available": info['available'],
                "classCount": len(module_classes),
                "seedInstanceCount": instance_count,
                "userCreated": info['user_created'],
            })

        # tt-11 (Dustin: 'only two modules are configurable'): the
        # registry only knows the legacy optional modules — list the
        # FRAMEWORK BOUNDARY modules too, so every module is visible
        # and drillable. Their enable/disable knob is honest: it
        # lives on the TOPOLOGY (ModuleAssignment rows), not here —
        # the flag lets the UI say so instead of a dead toggle.
        from moduleService.module_dependency_tracker import (
            FRAMEWORK_BOUNDARIES,
        )
        by_module = {}
        for cls in (getattr(self.polServer, 'defClassList', None)
                    or []):
            top = getattr(cls, '__module__', '').split('.')[0]
            by_module.setdefault(top, []).append(cls.__name__)
        known = {m['id'] for m in modules}
        root = os.path.dirname(os.path.dirname(
            os.path.abspath(__file__)))
        for module_id in sorted(set(by_module) | set(
                FRAMEWORK_BOUNDARIES)):
            present = (os.path.isdir(os.path.join(root, module_id))
                       or os.path.isdir(os.path.join(
                           root, 'modules', module_id)))
            if module_id in known or not present:
                continue
            class_names = by_module.get(module_id, [])
            modules.append({
                "id": module_id,
                "name": module_id,
                "description": FRAMEWORK_BOUNDARIES.get(
                    module_id,
                    f'framework module directory {module_id}/'),
                "enabled": True,
                "available": True,
                "classCount": len(class_names),
                "seedInstanceCount": sum(
                    len(self.manager.objectTables.get(cn, {}) or {})
                    for cn in class_names),
                "userCreated": False,
                # In-process framework module: toggling lives on the
                # topology (ModuleAssignment), not this registry.
                "boundary": True,
            })
        # mp-3: registry modules whose CODE is absent from this
        # checkout appear honestly — not a dead entry, a get-command.
        from moduleService.module_loading import (
            MISSING_FEATURE_MODULES, missing_message,
        )
        from moduleService.module_registry import load_registry
        listed = {m['id'] for m in modules}
        registry_modules = load_registry().get('modules', {})
        for module_id, entry in sorted(registry_modules.items()):
            if entry.get('downloaded') or module_id in listed:
                continue
            modules.append({
                "id": module_id,
                "name": module_id,
                "description": entry.get('description', ''),
                "enabled": False,
                "available": False,
                "classCount": 0,
                "seedInstanceCount": 0,
                "userCreated": entry.get('kind') == 'self',
                "downloaded": False,
                "notDownloaded": missing_message(module_id),
                "repo": entry.get('repo', ''),
            })
        # Import-time absences polariServer recorded (covers modules
        # the registry does not know yet).
        for module_id, msg in sorted(MISSING_FEATURE_MODULES.items()):
            if module_id in listed or module_id in registry_modules:
                continue
            modules.append({
                "id": module_id, "name": module_id, "description": '',
                "enabled": False, "available": False, "classCount": 0,
                "seedInstanceCount": 0, "userCreated": False,
                "downloaded": False, "notDownloaded": msg, "repo": '',
            })
        return modules

    def _toggle_module(self, module_id, enabled, module_info):
        """Enable or disable a module at runtime."""
        from config_loader import config
        from moduleService.moduleDiscovery import module_id_to_package

        if enabled:
            # Already enabled?
            if self.polServer._module_classes.get(module_id, []):
                print(f"[ModulesAPI] {module_id} already enabled, skipping")
                return

            package_name = module_info['package_name']
            try:
                mod = importlib.import_module(package_name)
            except ImportError:
                raise RuntimeError(f"Module package '{package_name}' could not be imported")

            print(f"[ModulesAPI] Enabling {module_id} ({package_name})")

            # Only register classes — seed data is loaded separately via POST /modules/seed
            result = mod.initialize(manager=self.manager, include_seed_data=False)

            class_names = list(result['registered_classes'].keys())
            self.polServer._module_classes[module_id] = class_names

            # Ensure moduleBinding is set on all classes (even pre-existing ones)
            for cn in class_names:
                typing = self.manager.objectTypingDict.get(cn)
                if typing:
                    typing.moduleBinding = module_id

            # Apply semantic type overrides from metadata (safety net)
            from moduleService.moduleDiscovery import apply_metadata_type_overrides
            apply_metadata_type_overrides(module_info['dir_path'], self.manager)

            # Backwards compat for materials_science
            if module_id == 'materials_science':
                self.polServer._materials_science_classes = class_names

            crude_ok = 0
            crude_fail = 0
            for class_name in result['registered_classes']:
                try:
                    self.polServer.registerCRUDEforObjectType(class_name)
                    crude_ok += 1
                except Exception as ce:
                    crude_fail += 1
                    print(f"[ModulesAPI] CRUDE failed for {class_name}: {ce}")

            print(f"[ModulesAPI] Enabled {module_id}: {len(class_names)} classes, {crude_ok} CRUDE ok, {crude_fail} CRUDE fail")
        else:
            # Disable: purge all data, typing, CRUDE endpoints
            module_classes = self.polServer._module_classes.get(module_id, [])
            purge_summaries = {}
            total_instances = 0
            for class_name in module_classes:
                try:
                    result = self.manager.purgeObjectType(class_name)
                    purge_summaries[class_name] = result
                    total_instances += result.get('instancesPurged', 0)
                except Exception as pe:
                    print(f"[ModulesAPI] Purge failed for {class_name}: {pe}")
                    purge_summaries[class_name] = {'error': str(pe)}

            self.polServer._module_classes[module_id] = []

            # Backwards compat for materials_science
            if module_id == 'materials_science':
                self.polServer._materials_science_classes = []

            self._last_purge_summary = {
                'classesPurged': len(module_classes),
                'instancesPurged': total_instances,
                'details': purge_summaries
            }
            print(f"[ModulesAPI] Disabled {module_id}: purged {len(module_classes)} classes, {total_instances} instances")

        # Persist to runtime config (volatile) and state file (survives restarts)
        config.set_runtime(f'modules.{module_id}.enabled', enabled)
        from moduleService.moduleState import save_module_state
        save_module_state(module_id, enabled)

    def _seed_module(self, module_id):
        """Load seed data for a module."""
        from moduleService.json_seeds import resolve_package

        package_name = resolve_package(module_id)
        seed_module = importlib.import_module(f'{package_name}.seedData')

        print(f"[ModulesAPI] Loading seed data for {module_id}...")
        created = seed_module.seed_initial_data(manager=self.manager)

        class_details = {}
        total_count = 0
        for cls_name, instances in created.items():
            class_details[cls_name] = len(instances)
            total_count += len(instances)

        print(f"[ModulesAPI] Seed complete for {module_id}: {total_count} total instances")

        return {
            "totalCount": total_count,
            "classCount": len(created),
            "classes": class_details
        }

    def _get_classes_from_typing(self, class_names):
        """Extract class detail info from the manager's objectTypingDict."""
        classes_detail = []
        for class_name in sorted(class_names):
            # Ensure class_name is a string (guard against corrupted _module_classes)
            if not isinstance(class_name, str):
                print(f"[ModulesAPI] WARNING: non-string class name in module class list: {class_name!r} (type={type(class_name).__name__})")
                continue
            typing_obj = self.manager.objectTypingDict.get(class_name)
            if typing_obj is None:
                classes_detail.append({
                    "className": str(class_name),
                    "fields": [],
                    "referencedBy": [],
                    "inheritsFrom": [],
                    "detailsAvailable": False,
                })
                continue

            # Extract fields
            fields = []
            # Internal vars to exclude from field listing
            _INTERNAL_VARS = {
                'manager', 'branch', 'id', 'objectTree', 'objectReferencesDict',
                'sourceFiles', 'identifiers', 'variableNameList', 'polyTypedVars',
                'polyTypedVarsDict', 'typingDicts', 'baseAccessDictionary',
                'basePermissionDictionary', 'eventsList', 'analyzeValuesMode',
            }
            vars_dict = getattr(typing_obj, 'polyTypedVarsDict', {})
            for var_name, var_typing in vars_dict.items():
                if var_name in _INTERNAL_VARS:
                    continue
                type_name = 'any'
                default_val = ''
                if hasattr(var_typing, 'pythonTypeDefault'):
                    raw_type = var_typing.pythonTypeDefault
                    type_name = str(raw_type) if raw_type is not None else 'any'
                # polyTypedVariable doesn't have a defaultValue attribute;
                # pull from the constructor signature instead
                if hasattr(var_typing, 'defaultValue'):
                    dv = var_typing.defaultValue
                    default_val = str(dv) if dv is not None else ''
                fields.append({
                    "name": str(var_name),
                    "type": type_name,
                    "defaultValue": default_val,
                })

            # Extract referenced-by classes
            obj_refs = getattr(typing_obj, 'objectReferencesDict', {})
            referenced_by = sorted(obj_refs.keys()) if isinstance(obj_refs, dict) else []

            # Extract inheritsFrom - ensure all values are plain strings
            inherits = getattr(typing_obj, 'inheritsFrom', None)
            inherits_list = []
            if inherits and isinstance(inherits, dict):
                for _var, parent in inherits.items():
                    if isinstance(parent, str):
                        inherits_list.append(parent)
                    elif hasattr(parent, '__name__'):
                        inherits_list.append(parent.__name__)
                    else:
                        inherits_list.append(str(parent))

            # Use typing_obj.className as the authoritative name (always a string)
            resolved_name = getattr(typing_obj, 'className', None) or class_name
            classes_detail.append({
                "className": str(resolved_name),
                "fields": fields,
                "referencedBy": referenced_by,
                "inheritsFrom": inherits_list,
                "detailsAvailable": True,
            })

        return classes_detail

    def _get_classes_from_metadata(self, dir_path):
        """Read class definitions from _module_metadata.json for disabled modules."""
        import os
        metadata_path = os.path.join(dir_path, '_module_metadata.json')
        if not os.path.isfile(metadata_path):
            return []

        try:
            with open(metadata_path, 'r') as f:
                metadata = json.load(f)
            classes = metadata.get('classes', [])
            return [
                {
                    "className": cls.get('className', ''),
                    "fields": [
                        {"name": fl.get('name', ''), "type": fl.get('type', 'str'), "defaultValue": ''}
                        for fl in cls.get('fields', [])
                    ],
                    "referencedBy": [],
                    "inheritsFrom": [],
                    "detailsAvailable": False,
                }
                for cls in classes
            ]
        except Exception:
            return []
