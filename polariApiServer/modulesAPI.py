"""
Module Management API

Provides endpoints for viewing and toggling optional modules
(e.g., Materials Science) at runtime.

GET  /modules       — list all known modules with status
PUT  /modules       — enable or disable a module
POST /modules/seed  — load seed data for an enabled module
"""

from objectTreeDecorators import treeObject, treeObjectInit
import falcon
import json


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

    # ------------------------------------------------------------------
    # GET /modules
    # ------------------------------------------------------------------
    def on_get(self, request, response):
        """Return the list of known optional modules with their status."""
        try:
            modules = self._build_module_list()
            response.media = {"success": True, "modules": modules}
            response.status = falcon.HTTP_200
        except Exception as err:
            response.status = falcon.HTTP_500
            response.media = {"success": False, "error": str(err)}
            print(f"[MS-Module-Load] [ModulesAPI] Error in GET: {err}")
            import traceback
            traceback.print_exc()

        response.set_header('Powered-By', 'Polari')

    # ------------------------------------------------------------------
    # PUT /modules
    # ------------------------------------------------------------------
    def on_put(self, request, response):
        """
        Toggle a module on or off.

        Request body:
            { "moduleId": "materials_science", "enabled": true }
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

            if module_id == 'materials_science':
                self._toggle_materials_science(bool(enabled))
                response.media = {
                    "success": True,
                    "message": f"Materials Science module {'enabled' if enabled else 'disabled'}",
                    "modules": self._build_module_list()
                }
                response.status = falcon.HTTP_200
            else:
                response.status = falcon.HTTP_404
                response.media = {"success": False, "error": f"Unknown module: {module_id}"}

        except Exception as err:
            response.status = falcon.HTTP_500
            response.media = {"success": False, "error": str(err)}
            print(f"[MS-Module-Load] [ModulesAPI] Error in PUT: {err}")
            import traceback
            traceback.print_exc()

        response.set_header('Powered-By', 'Polari')

    # ------------------------------------------------------------------
    # POST /modules/seed
    # ------------------------------------------------------------------
    def on_post_seed(self, request, response):
        """
        Load seed data for an enabled module.

        Request body:
            { "moduleId": "materials_science" }
        """
        try:
            body = request.media
            module_id = body.get('moduleId')

            if not module_id:
                response.status = falcon.HTTP_400
                response.media = {"success": False, "error": "moduleId is required"}
                return

            if module_id == 'materials_science':
                ms_classes = getattr(self.polServer, '_materials_science_classes', [])
                if not ms_classes:
                    response.status = falcon.HTTP_400
                    response.media = {"success": False, "error": "Materials Science module must be enabled before loading seed data"}
                    return

                seed_result = self._seed_materials_science()
                response.media = {
                    "success": True,
                    "message": f"Loaded {seed_result['totalCount']} seed records across {seed_result['classCount']} classes",
                    "seedResult": seed_result,
                    "modules": self._build_module_list()
                }
                response.status = falcon.HTTP_200
            else:
                response.status = falcon.HTTP_404
                response.media = {"success": False, "error": f"Unknown module: {module_id}"}

        except Exception as err:
            response.status = falcon.HTTP_500
            response.media = {"success": False, "error": str(err)}
            print(f"[MS-Module-Load] [ModulesAPI] Error in POST /seed: {err}")
            import traceback
            traceback.print_exc()

        response.set_header('Powered-By', 'Polari')

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    def _build_module_list(self):
        """Build the list of module descriptors."""
        # Check availability
        try:
            from polariMaterialsScienceModule import initialize as _init_ms
            ms_available = True
        except ImportError:
            ms_available = False

        ms_classes = getattr(self.polServer, '_materials_science_classes', [])
        ms_enabled = len(ms_classes) > 0

        # Count seed data instances in objectTables
        seed_instance_count = 0
        if ms_enabled:
            for cls_name in ms_classes:
                if cls_name in self.manager.objectTables:
                    seed_instance_count += len(self.manager.objectTables[cls_name])

        return [
            {
                "id": "materials_science",
                "name": "Materials Science",
                "description": "Material properties, devices, resolutions, and formulations",
                "enabled": ms_enabled,
                "available": ms_available,
                "classCount": len(ms_classes),
                "seedInstanceCount": seed_instance_count
            }
        ]

    def _toggle_materials_science(self, enabled: bool):
        """Enable or disable the Materials Science module at runtime (classes only, no seed data)."""
        from config_loader import config

        if enabled:
            # Already enabled?
            if getattr(self.polServer, '_materials_science_classes', []):
                print("[MS-Module-Load] [ModulesAPI] Already enabled, skipping")
                return

            try:
                from polariMaterialsScienceModule import initialize as initialize_materials_science
            except ImportError:
                raise RuntimeError("Materials Science Python package is not installed")

            print(f"[MS-Module-Load] [ModulesAPI] Enabling Materials Science module via runtime toggle")
            print(f"[MS-Module-Load] [ModulesAPI] manager.objectTypingDict BEFORE: {len(self.manager.objectTypingDict)} entries")

            # Only register classes — seed data is loaded separately via POST /modules/seed
            result = initialize_materials_science(
                manager=self.manager,
                include_seed_data=False
            )

            print(f"[MS-Module-Load] [ModulesAPI] manager.objectTypingDict AFTER: {len(self.manager.objectTypingDict)} entries")
            self.polServer._materials_science_classes = list(result['registered_classes'].keys())

            crude_ok = 0
            crude_fail = 0
            for class_name in result['registered_classes']:
                try:
                    self.polServer.registerCRUDEforObjectType(class_name)
                    crude_ok += 1
                except Exception as ce:
                    crude_fail += 1
                    print(f"[MS-Module-Load] [ModulesAPI] CRUDE failed for {class_name}: {ce}")

            print(f"[MS-Module-Load] [ModulesAPI] Enabled: {len(result['registered_classes'])} classes, {crude_ok} CRUDE ok, {crude_fail} CRUDE fail")
        else:
            # Disable: clear class list so api-config stops reporting them
            prev_count = len(getattr(self.polServer, '_materials_science_classes', []))
            self.polServer._materials_science_classes = []
            print(f"[MS-Module-Load] [ModulesAPI] Disabled: cleared {prev_count} class entries (CRUDE routes still registered until restart)")

        # Persist to runtime config so subsequent config.get() calls reflect the change
        config.set_runtime('modules.materials_science.enabled', enabled)

    def _seed_materials_science(self):
        """Load seed data for the Materials Science module."""
        from polariMaterialsScienceModule.seedData import seed_initial_data

        print(f"[MS-Module-Load] [ModulesAPI] Loading seed data...")
        print(f"[MS-Module-Load] [ModulesAPI] objectTables BEFORE seed: {len(self.manager.objectTables)} class keys")

        created = seed_initial_data(manager=self.manager)

        print(f"[MS-Module-Load] [ModulesAPI] objectTables AFTER seed: {len(self.manager.objectTables)} class keys")

        # Build result summary
        class_details = {}
        total_count = 0
        for cls_name, instances in created.items():
            class_details[cls_name] = len(instances)
            total_count += len(instances)
            # Verify they landed in objectTables
            in_tables = len(self.manager.objectTables.get(cls_name, {}))
            print(f"[MS-Module-Load] [ModulesAPI]   {cls_name}: {len(instances)} created, {in_tables} in objectTables")

        print(f"[MS-Module-Load] [ModulesAPI] Seed complete: {total_count} total instances")

        return {
            "totalCount": total_count,
            "classCount": len(created),
            "classes": class_details
        }
