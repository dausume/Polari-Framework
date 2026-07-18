"""
Module Management API

Provides endpoints for viewing, toggling, creating, and seeding optional modules.

GET  /modules        — list all discovered modules with status
PUT  /modules        — enable or disable a module
POST /modules/seed   — load seed data for an enabled module
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
            polServer.falconServer.add_route(self.apiName + '/{module_id}', self, suffix='detail')

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
            for entry in classes_detail:
                cn = entry.get('className', '')
                entry['instanceCount'] = len(
                    self.manager.objectTables.get(cn, {}) or {})
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
    def on_post_seed(self, request, response):
        """Load seed data for an enabled module.

        Request body: { "moduleId": "<module_id>" }
        """
        try:
            body = request.media
            module_id = body.get('moduleId')

            if not module_id:
                response.status = falcon.HTTP_400
                response.media = {"success": False, "error": "moduleId is required"}
                return

            module_classes = self.polServer._module_classes.get(module_id, [])
            if not module_classes:
                response.status = falcon.HTTP_400
                response.media = {"success": False, "error": f"Module {module_id} must be enabled before loading seed data"}
                return

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
    # POST /modules/create
    # ------------------------------------------------------------------
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
        dir_path = _os.path.join(root, module_id)
        if not _os.path.isdir(dir_path):
            response.status = falcon.HTTP_404
            response.media = {
                "success": False,
                "error": f"Module '{module_id}' not found — neither "
                         "a registry module nor a framework "
                         "directory"}
            return
        from moduleService.moduleDiscovery import scan_python_imports
        from moduleService.module_dependency_tracker import (
            FRAMEWORK_BOUNDARIES, scan_boundary_imports,
        )
        module_classes = sorted(
            cls.__name__ for cls in (getattr(
                self.polServer, 'defClassList', None) or [])
            if getattr(cls, '__module__', '').split('.')[0]
            == module_id)
        classes_detail = self._get_classes_from_typing(
            module_classes)
        for entry in classes_detail:
            entry['instanceCount'] = len(
                self.manager.objectTables.get(
                    entry.get('className', ''), {}) or {})
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
                "pythonDependencies": scan_python_imports(dir_path),
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
        from moduleService.moduleDiscovery import module_id_to_package

        package_name = module_id_to_package(module_id)
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
