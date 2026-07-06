#    Copyright (C) 2020  Dustin Etts
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.

#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.

#    You should have received a copy of the GNU General Public License
#    along with this program.  If not, see <https://www.gnu.org/licenses/>.

from objectTreeDecorators import treeObject, treeObjectInit
from polariDataTyping.polyTyping import polyTypedObject
from polariDataTyping.polyTypedVars import polyTypedVariable
import falcon
import json
import sqlite3
import os

# Registry schema in sqlite-affinity form — each DB adapter translates
# these for its own dialect (see polariDBmanagement/db_adapter.py).
_DYNAMIC_REGISTRY_COLUMNS = [
    'className TEXT PRIMARY KEY',
    'displayName TEXT',
    'variables TEXT',
    'registerCRUDE INTEGER',
    'isStateSpaceObject INTEGER',
    'stateSpaceDisplayFields TEXT',
    'stateSpaceFieldsPerRow INTEGER',
    'inheritsFrom TEXT',
]


class createClassAPI(treeObject):
    """
    API endpoint for dynamically creating new classes at runtime.
    Created classes are automatically wrapped as polari objects with
    CRUDE endpoints and optional database tables.
    """

    @treeObjectInit
    def __init__(self, polServer):
        self.polServer = polServer
        self.apiName = '/createClass'
        if polServer is not None:
            polServer.falconServer.add_route(self.apiName, self)

    def on_post(self, request, response):
        """Handle class creation requests"""
        import sys
        print(f'[DEBUG-CC] === on_post ENTERED === method={request.method} path={request.path}', flush=True)
        print(f'[DEBUG-CC] content_length={request.content_length} content_type={request.content_type}', flush=True)
        try:
            # Parse request body using get_media() (Falcon's built-in JSON parsing)
            # Note: request.stream.read() hangs with wsgiref in Falcon 4.x
            print('[DEBUG-CC] calling request.get_media()...', flush=True)
            class_def = request.get_media()
            print(f'[DEBUG-CC] get_media() complete, keys={list(class_def.keys())}', flush=True)

            # Validate required fields
            if 'className' not in class_def or not class_def['className']:
                print('[DEBUG-CC] FAIL: className missing', flush=True)
                response.status = falcon.HTTP_400
                response.media = {'success': False, 'error': 'className is required'}
                return

            className = class_def['className']
            displayName = class_def.get('classDisplayName', className)
            variables = class_def.get('variables', [])
            registerCRUDE = class_def.get('registerCRUDE', True)
            # State-space configuration
            isStateSpaceObject = class_def.get('isStateSpaceObject', True)  # Default to True for dynamic classes
            stateSpaceDisplayFields = class_def.get('stateSpaceDisplayFields', [])
            stateSpaceFieldsPerRow = class_def.get('stateSpaceFieldsPerRow', 1)
            # Multiple-inheritance configuration: {varName: parentClassName}
            inheritsFrom = class_def.get('inheritsFrom', {})
            print(f'[DEBUG-CC] className={className} vars={len(variables)} registerCRUDE={registerCRUDE} inheritsFrom={inheritsFrom}', flush=True)

            # Validate className format (PascalCase, alphanumeric)
            if not className[0].isupper():
                print('[DEBUG-CC] FAIL: className not uppercase', flush=True)
                response.status = falcon.HTTP_400
                response.media = {'success': False, 'error': 'className must start with uppercase letter'}
                return

            if not className.replace('_', '').isalnum():
                print('[DEBUG-CC] FAIL: className not alnum', flush=True)
                response.status = falcon.HTTP_400
                response.media = {'success': False, 'error': 'className must be alphanumeric (underscores allowed)'}
                return

            # Check if class already exists
            if className in self.manager.objectTypingDict:
                print(f'[DEBUG-CC] FAIL: class {className} already exists', flush=True)
                response.status = falcon.HTTP_409
                response.media = {'success': False, 'error': f'Class {className} already exists'}
                return

            # Create the dynamic class and register it
            print(f'[DEBUG-CC] calling _createDynamicClass for {className}...', flush=True)
            result = self._createDynamicClass(
                className=className,
                displayName=displayName,
                variables=variables,
                registerCRUDE=registerCRUDE,
                isStateSpaceObject=isStateSpaceObject,
                stateSpaceDisplayFields=stateSpaceDisplayFields,
                stateSpaceFieldsPerRow=stateSpaceFieldsPerRow,
                inheritsFrom=inheritsFrom
            )
            print(f'[DEBUG-CC] _createDynamicClass returned OK for {className}', flush=True)

            warnings = result.get('warnings', []) if isinstance(result, dict) else []

            response.status = falcon.HTTP_201
            responseBody = {
                'success': True,
                'className': className,
                'displayName': displayName,
                'apiEndpoint': f'/{className}',
                'crudeRegistered': registerCRUDE,
                'variableCount': len(variables),
                'isStateSpaceObject': isStateSpaceObject
            }
            if warnings:
                responseBody['warnings'] = warnings
            response.media = responseBody
            print(f'[DEBUG-CC] === on_post SUCCESS === {className} created, {len(warnings)} warning(s)', flush=True)

        except json.JSONDecodeError as e:
            print(f'[DEBUG-CC] EXCEPTION JSONDecodeError: {e}', flush=True)
            response.status = falcon.HTTP_400
            response.media = {'success': False, 'error': 'Invalid JSON in request body'}
        except Exception as e:
            print(f'[DEBUG-CC] EXCEPTION: {type(e).__name__}: {e}', flush=True)
            response.status = falcon.HTTP_500
            response.media = {'success': False, 'error': str(e)}
            import traceback
            traceback.print_exc()

        response.set_header('Powered-By', 'Polari')

    def _createDynamicClass(self, className, displayName, variables, registerCRUDE,
                            isStateSpaceObject=True, stateSpaceDisplayFields=None, stateSpaceFieldsPerRow=1,
                            inheritsFrom=None):
        """
        Dynamically creates a new Python class and registers it with the Polari framework.

        Args:
            className: Name of the class to create
            displayName: Human-readable display name
            variables: List of variable definitions
            registerCRUDE: Whether to register CRUDE endpoints
            isStateSpaceObject: Whether this class can be used in no-code state-space
            stateSpaceDisplayFields: Which fields to display in state UI
            stateSpaceFieldsPerRow: Number of fields per row in state display (1 or 2)
            inheritsFrom: Dict mapping variable names to parent class names for
                          multi-inheritance, e.g. {'vehicle': 'Vehicle', 'policy': 'InsurancePolicy'}
        """
        if inheritsFrom is None:
            inheritsFrom = {}
        print(f'[DEBUG-CC] _createDynamicClass START: {className}', flush=True)
        # Validate inheritsFrom parent classes exist
        for varName, parentClassName in inheritsFrom.items():
            if parentClassName not in self.manager.objectTypingDict:
                raise ValueError(
                    f"Parent class '{parentClassName}' (for variable '{varName}') "
                    f"is not registered. Create or register it before defining '{className}'."
                )
        # Build variable names and defaults
        var_defaults = {}
        for var in variables:
            var_name = var.get('varName', '')
            if var_name:
                var_defaults[var_name] = self._getDefaultValue(var.get('varType', 'str'))
        # Add inheritance reference variables (initialized to None)
        for varName in inheritsFrom:
            if varName not in var_defaults:
                var_defaults[varName] = None
        print(f'[DEBUG-CC] step 1: var_defaults built ({len(var_defaults)} vars, {len(inheritsFrom)} inheritance refs)', flush=True)

        # Create the dynamic __init__ method with EXPLICIT parameter names
        # This is critical because treeObjectInit filters kwargs based on co_varnames.
        # Using **kwargs would cause all custom variables to be filtered out.
        # We use exec() to generate a function with the actual parameter names.

        # Filter out tree-object base params to avoid duplicates in signature
        base_params = {'id', 'manager', 'branch', 'inTree'}
        custom_defaults = {k: v for k, v in var_defaults.items() if k not in base_params}
        param_names = list(custom_defaults.keys())

        # Build function signature with explicit parameters
        # e.g., "def dynamic_init(self, manager=None, testVar='', otherVar=0):"
        param_str = ', '.join([f"{name}={repr(default)}" for name, default in custom_defaults.items()])
        if param_str:
            param_str = ', ' + param_str

        # Build the body assignments
        body_assignments = '\n'.join([f'    self.{name} = {name}' for name in param_names])

        func_code = f'''
def dynamic_init(self, manager=None, branch=None, id=None{param_str}):
    treeObject.__init__(self, manager=manager, branch=branch, id=id)
{body_assignments}
'''
        # Execute to create the function
        local_ns = {'treeObject': treeObject}
        exec(func_code, local_ns)
        dynamic_init = local_ns['dynamic_init']
        print(f'[DEBUG-CC] step 2: dynamic __init__ created via exec', flush=True)

        # Create class attributes
        class_attrs = {
            '__init__': treeObjectInit(dynamic_init),
            'displayName': displayName,
            '_dynamicClass': True,
            '_variableDefinitions': variables
        }
        # Set multi-inheritance declaration if provided
        if inheritsFrom:
            class_attrs['_polariInheritsFrom'] = dict(inheritsFrom)

        # Dynamically create the class inheriting from treeObject
        DynamicClass = type(className, (treeObject,), class_attrs)
        print(f'[DEBUG-CC] step 3: DynamicClass type() created', flush=True)

        # Determine identifier variables
        identifiers = ['id']
        for var in variables:
            if var.get('isIdentifier', False) and var.get('varName') not in identifiers:
                identifiers.append(var['varName'])

        # Create polyTypedObject for the new class
        # Dynamically created classes have different defaults than core framework objects:
        # - allowClassEdit=True: Users can modify the class definition via API
        # - isStateSpaceObject: User-configurable, defaults to True
        # - excludeFromCRUDE=False: Should have public CRUDE endpoints
        print(f'[DEBUG-CC] step 4: creating polyTypedObject...', flush=True)
        newTyping = polyTypedObject(
            className=className,
            manager=self.manager,
            sourceFiles=[],
            identifierVariables=identifiers,
            objectReferencesDict={},
            classDefinition=DynamicClass,
            kwRequiredParams=[],
            kwDefaultParams=list(var_defaults.keys()),
            allowClassEdit=True,
            isStateSpaceObject=isStateSpaceObject,
            excludeFromCRUDE=False
        )
        print(f'[DEBUG-CC] step 4: polyTypedObject created OK', flush=True)

        # Configure state-space display fields if this is a state-space object
        if isStateSpaceObject and stateSpaceDisplayFields:
            newTyping.setStateSpaceDisplayFields(stateSpaceDisplayFields, stateSpaceFieldsPerRow)
        elif isStateSpaceObject:
            # Default: show all variables
            all_var_names = [v.get('varName') for v in variables if v.get('varName')]
            newTyping.setStateSpaceDisplayFields(all_var_names, stateSpaceFieldsPerRow)
        print(f'[DEBUG-CC] step 5: state-space config set', flush=True)

        # Populate polyTypedVars from the frontend variable definitions
        # This ensures typing metadata is available even before any instances exist
        for var in variables:
            var_name = var.get('varName', '')
            var_type = var.get('varType', 'str')
            if var_name:
                # Create a polyTypedVariable with a default value to establish the type
                default_value = self._getDefaultValue(var_type)
                try:
                    polyVar = polyTypedVariable(
                        polyTypedObj=newTyping,
                        attributeName=var_name,
                        attributeValue=default_value
                    )
                    # Override the pythonTypeDefault with the explicitly defined type
                    # (in case default value inference differs)
                    polyVar.pythonTypeDefault = var_type
                    # Store additional metadata from frontend definition
                    polyVar.displayName = var.get('varDisplayName', var_name)
                    polyVar.isIdentifier = var.get('isIdentifier', False)
                    polyVar.isUnique = var.get('isUnique', False)
                    # Store reference class name for reference/referenceList types
                    ref_class = var.get('refClass', None)
                    if ref_class:
                        polyVar.refClass = ref_class

                    # Add to the polyTypedObject's variable lists
                    newTyping.polyTypedVars.append(polyVar)
                    newTyping.polyTypedVarsDict[var_name] = polyVar
                    newTyping.variableNameList.append(var_name)
                except Exception as e:
                    print(f"[createClassAPI] Warning: Could not create polyTypedVariable for {var_name}: {e}")

        print(f"[DEBUG-CC] step 6: created {len(newTyping.polyTypedVars)} polyTypedVars for {className}", flush=True)

        # Also add to objectTyping list (polyTypedObject only adds to dict)
        if newTyping not in self.manager.objectTyping:
            self.manager.objectTyping.append(newTyping)
        print(f'[DEBUG-CC] step 7: added to objectTyping list', flush=True)

        # Store the dynamic class reference for instantiation
        if not hasattr(self.manager, 'dynamicClasses'):
            self.manager.dynamicClasses = {}
        self.manager.dynamicClasses[className] = DynamicClass

        # Register CRUDE endpoint if requested
        if registerCRUDE and self.polServer:
            print(f'[DEBUG-CC] step 8: registering CRUDE endpoint...', flush=True)
            self.polServer.registerCRUDEforObjectType(className)
            print(f"[DEBUG-CC] step 8: CRUDE endpoint registered for {className}", flush=True)
        else:
            print(f'[DEBUG-CC] step 8: skipping CRUDE (registerCRUDE={registerCRUDE})', flush=True)

        # Build inheritance reverse index for newly created class
        if newTyping.isMultiInheritanceClass:
            for parentClassName in newTyping.getInheritanceParentClassNames():
                parentTyping = self.manager.objectTypingDict.get(parentClassName)
                if parentTyping is not None:
                    if className not in parentTyping.inheritedByClasses:
                        parentTyping.inheritedByClasses.append(className)
            try:
                newTyping.validateInheritanceGraph()
            except ValueError as e:
                print(f'[DEBUG-CC] INHERITANCE ERROR: {e}', flush=True)
            print(f'[DEBUG-CC] step 8b: inheritance reverse index built for {className}', flush=True)

        # Track warnings for non-fatal issues to report back to the frontend
        warnings = []

        # Create database table for the new class if DB is active
        if hasattr(self.manager, 'db') and self.manager.db is not None:
            try:
                print(f'[DEBUG-CC] step 9: creating DB table...', flush=True)
                if newTyping.polyTypedVarsDict:
                    newTyping.makeTypedTableFromAnalysis()
                    print(f"[DEBUG-CC] step 9: DB table created for {className}", flush=True)
            except Exception as e:
                msg = f'Database table creation failed for {className}: {e}'
                print(f"[DEBUG-CC] step 9: ERROR {msg}", flush=True)
                warnings.append(msg)
        else:
            print(f'[DEBUG-CC] step 9: no DB active, skipping table creation', flush=True)

        # Persist dynamic class definition to registry table for restore on restart
        if hasattr(self.manager, 'db') and self.manager.db is not None:
            try:
                print(f'[DEBUG-CC] step 10: persisting class definition...', flush=True)
                self._persistClassDefinition(className, displayName, variables,
                                              registerCRUDE, isStateSpaceObject,
                                              stateSpaceDisplayFields, stateSpaceFieldsPerRow,
                                              inheritsFrom=inheritsFrom)
                print(f'[DEBUG-CC] step 10: class definition persisted', flush=True)
            except Exception as e:
                msg = f'Class created but failed to save to registry — data will not survive restart: {e}'
                print(f"[DEBUG-CC] step 10: ERROR {msg}", flush=True)
                warnings.append(msg)
        else:
            print(f'[DEBUG-CC] step 10: no DB active, skipping persist', flush=True)

        print(f"[DEBUG-CC] _createDynamicClass COMPLETE: {className} with {len(variables)} variables, {len(warnings)} warning(s)", flush=True)
        return {'typing': newTyping, 'warnings': warnings}

    def _getDefaultValue(self, var_type):
        """Get default value for a variable type"""
        type_defaults = {
            'str': '',
            'int': 0,
            'float': 0.0,
            'list': [],
            'dict': {},
            'bool': False,
            'reference': None,
            'map_coordinate': '[]',
            'map_line_segment': '{}',
            'map_polygon': '{}',
            'date_duration': None,
            'datetime_duration': None,
            'time': None,
            'time_duration': None,
            'precision_time': None,
            'schedule': None,
            # `equation` is a string carrying LaTeX source; rendered + soft-validated
            # on the frontend via KaTeX. Persisted as plain TEXT.
            'equation': ''
        }
        return type_defaults.get(var_type, '')

    def _persistClassDefinition(self, className, displayName, variables,
                                 registerCRUDE, isStateSpaceObject,
                                 stateSpaceDisplayFields, stateSpaceFieldsPerRow,
                                 inheritsFrom=None):
        """Save dynamic class definition to _dynamic_class_registry table."""
        db = self.manager.db
        adapter = db.adapter
        conn = adapter.connect()
        cursor = conn.cursor()
        # Ensure registry table exists with the correct schema.
        # If it exists with a stale column count, rebuild it preserving existing rows.
        expectedCols = 8
        registryDDL = ('CREATE TABLE _dynamic_class_registry ('
                       + ', '.join(adapter.translateColumnDefs(
                           _DYNAMIC_REGISTRY_COLUMNS)) + ')')
        ph8 = ', '.join([adapter.placeholder] * expectedCols)
        if adapter.tableExists(conn, '_dynamic_class_registry'):
            colCount = len(adapter.tableColumns(conn, '_dynamic_class_registry'))
            if colCount < expectedCols:
                cursor.execute('SELECT * FROM _dynamic_class_registry')
                existing = cursor.fetchall()
                cursor.execute('DROP TABLE _dynamic_class_registry')
                cursor.execute(registryDDL)
                for row in existing:
                    padded = tuple(row) + (None,) * (expectedCols - len(row))
                    cursor.execute(
                        f'INSERT INTO _dynamic_class_registry VALUES ({ph8})',
                        padded)
                conn.commit()
                print(f'[createClassAPI] Rebuilt _dynamic_class_registry: {colCount} -> {expectedCols} columns, {len(existing)} entries preserved')
        else:
            cursor.execute(registryDDL)
        cursor.execute(
            adapter.replaceSQL('_dynamic_class_registry',
                               [c.split()[0] for c in _DYNAMIC_REGISTRY_COLUMNS]),
            (
                className,
                displayName,
                json.dumps(variables),
                1 if registerCRUDE else 0,
                1 if isStateSpaceObject else 0,
                json.dumps(stateSpaceDisplayFields) if stateSpaceDisplayFields else None,
                stateSpaceFieldsPerRow,
                json.dumps(inheritsFrom) if inheritsFrom else None
            )
        )
        conn.commit()
        conn.close()
        db.cache.invalidateTable(db.name, '_dynamic_class_registry')
        print(f"[createClassAPI] Persisted class definition for {className} to registry")

    @staticmethod
    def restoreDynamicClasses(manager, dbFilePath):
        """Restore all dynamic class definitions from the registry table.

        Called during restoreFromDatabase() BEFORE the instance restore loop,
        so that dynamic class tables are recognized as known classes.

        Args:
            manager: The managerObject
            dbFilePath: Legacy .db path (unused — the manager's DB adapter
                decides the actual backend)
        """
        adapter = manager.db.adapter
        conn = adapter.connect()
        cursor = conn.cursor()
        # Check if registry table exists
        if not adapter.tableExists(conn, '_dynamic_class_registry'):
            conn.close()
            return
        cursor.execute('SELECT * FROM _dynamic_class_registry')
        rows = cursor.fetchall()
        conn.close()

        if not rows:
            return

        print(f'[DB] Restoring {len(rows)} dynamic class definitions...')

        for row in rows:
            # Handle both old 7-column and new 8-column registry formats
            if len(row) >= 8:
                className, displayName, variablesJson, registerCRUDE, isStateSpaceObject, displayFieldsJson, fieldsPerRow, inheritsFromJson = row
            else:
                className, displayName, variablesJson, registerCRUDE, isStateSpaceObject, displayFieldsJson, fieldsPerRow = row
                inheritsFromJson = None
            # Skip if already registered (shouldn't happen, but safety check)
            if className in manager.objectTypingDict:
                print(f'[DB] Dynamic class {className} already registered, skipping')
                continue

            variables = json.loads(variablesJson) if variablesJson else []
            stateSpaceDisplayFields = json.loads(displayFieldsJson) if displayFieldsJson else None
            inheritsFrom = json.loads(inheritsFromJson) if inheritsFromJson else {}

            # Re-create the dynamic class using the same logic as _createDynamicClass
            var_defaults = {}
            type_defaults = {
                'str': '', 'int': 0, 'float': 0.0, 'list': [], 'dict': {}, 'bool': False,
                'reference': None, 'map_coordinate': '[]', 'map_line_segment': '{}', 'map_polygon': '{}',
                'date_duration': None, 'datetime_duration': None, 'time': None, 'time_duration': None, 'precision_time': None, 'schedule': None
            }
            for var in variables:
                var_name = var.get('varName', '')
                if var_name:
                    var_defaults[var_name] = type_defaults.get(var.get('varType', 'str'), '')
            # Add inheritance reference variables
            for varName in inheritsFrom:
                if varName not in var_defaults:
                    var_defaults[varName] = None

            base_params = {'id', 'manager', 'branch', 'inTree'}
            custom_defaults = {k: v for k, v in var_defaults.items() if k not in base_params}
            param_names = list(custom_defaults.keys())

            param_str = ', '.join([f"{name}={repr(default)}" for name, default in custom_defaults.items()])
            if param_str:
                param_str = ', ' + param_str

            body_assignments = '\n'.join([f'    self.{name} = {name}' for name in param_names])

            func_code = f'''
def dynamic_init(self, manager=None, branch=None, id=None{param_str}):
    treeObject.__init__(self, manager=manager, branch=branch, id=id)
{body_assignments}
'''
            local_ns = {'treeObject': treeObject}
            exec(func_code, local_ns)
            dynamic_init = local_ns['dynamic_init']

            class_attrs = {
                '__init__': treeObjectInit(dynamic_init),
                'displayName': displayName,
                '_dynamicClass': True,
                '_variableDefinitions': variables
            }
            if inheritsFrom:
                class_attrs['_polariInheritsFrom'] = dict(inheritsFrom)

            DynamicClass = type(className, (treeObject,), class_attrs)

            identifiers = ['id']
            for var in variables:
                if var.get('isIdentifier', False) and var.get('varName') not in identifiers:
                    identifiers.append(var['varName'])

            newTyping = polyTypedObject(
                className=className,
                manager=manager,
                sourceFiles=[],
                identifierVariables=identifiers,
                objectReferencesDict={},
                classDefinition=DynamicClass,
                kwRequiredParams=[],
                kwDefaultParams=list(var_defaults.keys()),
                allowClassEdit=True,
                isStateSpaceObject=bool(isStateSpaceObject),
                excludeFromCRUDE=False
            )

            if bool(isStateSpaceObject) and stateSpaceDisplayFields:
                newTyping.setStateSpaceDisplayFields(stateSpaceDisplayFields, fieldsPerRow or 1)
            elif bool(isStateSpaceObject):
                all_var_names = [v.get('varName') for v in variables if v.get('varName')]
                newTyping.setStateSpaceDisplayFields(all_var_names, fieldsPerRow or 1)

            for var in variables:
                var_name = var.get('varName', '')
                var_type = var.get('varType', 'str')
                if var_name:
                    default_value = type_defaults.get(var_type, '')
                    try:
                        polyVar = polyTypedVariable(
                            polyTypedObj=newTyping,
                            attributeName=var_name,
                            attributeValue=default_value
                        )
                        polyVar.pythonTypeDefault = var_type
                        polyVar.displayName = var.get('varDisplayName', var_name)
                        polyVar.isIdentifier = var.get('isIdentifier', False)
                        polyVar.isUnique = var.get('isUnique', False)
                        ref_class = var.get('refClass', None)
                        if ref_class:
                            polyVar.refClass = ref_class
                        newTyping.polyTypedVars.append(polyVar)
                        newTyping.polyTypedVarsDict[var_name] = polyVar
                        newTyping.variableNameList.append(var_name)
                    except Exception as e:
                        print(f"[DB] Warning: Could not create polyTypedVariable for {var_name}: {e}")

            if newTyping not in manager.objectTyping:
                manager.objectTyping.append(newTyping)

            if not hasattr(manager, 'dynamicClasses'):
                manager.dynamicClasses = {}
            manager.dynamicClasses[className] = DynamicClass

            # Build inheritance reverse index for restored class
            if newTyping.isMultiInheritanceClass:
                for parentClassName in newTyping.getInheritanceParentClassNames():
                    parentTyping = manager.objectTypingDict.get(parentClassName)
                    if parentTyping is not None:
                        if className not in parentTyping.inheritedByClasses:
                            parentTyping.inheritedByClasses.append(className)
                    else:
                        print(f'[DB] WARNING: Restored class {className} inherits from {parentClassName} but parent typing not found yet')

            print(f'[DB] Restored dynamic class: {className} ({len(variables)} variables, inheritsFrom={inheritsFrom})')

        # Detect orphaned dynamic class tables — tables with data that aren't
        # in the registry or objectTypingDict. This handles classes created before
        # the registry was introduced, or whose registry entries were lost.
        createClassAPI._repairOrphanedDynamicClasses(manager, dbFilePath)

    @staticmethod
    def _repairOrphanedDynamicClasses(manager, dbFilePath):
        """Detect DB tables that have data but no registry entry or objectTypingDict entry.

        For each orphan, reconstruct a minimal class definition from the DB schema
        columns and register it so its data can be restored.
        """
        # Known framework/internal table prefixes and names to skip
        knownFrameworkTables = {
            '_dynamic_class_registry', 'sqlite_sequence',
            # Tables that correspond to built-in framework classes
            # (they'll be in objectTypingDict or are side tables)
        }

        adapter = manager.db.adapter
        conn = adapter.connect()
        cursor = conn.cursor()

        # Get all table names from DB
        allTables = adapter.listTables(conn)

        # Get registered class names from registry
        registeredNames = set()
        if adapter.tableExists(conn, '_dynamic_class_registry'):
            cursor.execute('SELECT className FROM _dynamic_class_registry')
            registeredNames = {row[0] for row in cursor.fetchall()}

        orphans = []
        for tableName in allTables:
            if tableName in knownFrameworkTables:
                continue
            if tableName.startswith('_') or '_variant' in tableName:
                continue
            if tableName in manager.objectTypingDict:
                continue
            if tableName in registeredNames:
                continue
            # Check if the table has actual data
            try:
                cursor.execute(
                    f'SELECT count(*) FROM {adapter.quoteIdent(tableName)}')
                rowCount = cursor.fetchone()[0]
            except Exception:
                continue
            if rowCount == 0:
                continue
            # Get column schema
            columns = adapter.tableColumnDefs(conn, tableName)
            orphans.append((tableName, columns, rowCount))

        conn.close()

        if not orphans:
            return

        print(f'[DB] Found {len(orphans)} orphaned dynamic class tables with data, repairing...')

        type_defaults = {
            'str': '', 'int': 0, 'float': 0.0, 'list': [], 'dict': {}, 'bool': False,
            'reference': None, 'map_coordinate': '[]', 'map_line_segment': '{}', 'map_polygon': '{}',
            'date_duration': None, 'datetime_duration': None, 'time': None, 'time_duration': None, 'precision_time': None, 'schedule': None
        }
        skip_cols = {'_branch_path', 'id'}

        for tableName, columns, rowCount in orphans:
            # Build variable definitions from DB schema columns
            variables = []
            for colName, colType in columns:
                if colName in skip_cols:
                    continue
                # Map SQLite types back to variable types
                varType = 'str'
                if colType in ('INTEGER',):
                    varType = 'int'
                elif colType in ('REAL',):
                    varType = 'float'
                variables.append({
                    'varName': colName,
                    'varDisplayName': colName,
                    'varType': varType,
                    'isIdentifier': False,
                    'isUnique': False
                })

            # Build the dynamic class the same way as the registry restore above
            var_defaults = {}
            for var in variables:
                var_name = var.get('varName', '')
                if var_name:
                    var_defaults[var_name] = type_defaults.get(var.get('varType', 'str'), '')

            base_params = {'id', 'manager', 'branch', 'inTree'}
            custom_defaults = {k: v for k, v in var_defaults.items() if k not in base_params}
            param_names = list(custom_defaults.keys())

            param_str = ', '.join([f"{name}={repr(default)}" for name, default in custom_defaults.items()])
            if param_str:
                param_str = ', ' + param_str

            body_assignments = '\n'.join([f'    self.{name} = {name}' for name in param_names])

            func_code = f'''
def dynamic_init(self, manager=None, branch=None, id=None{param_str}):
    treeObject.__init__(self, manager=manager, branch=branch, id=id)
{body_assignments}
'''
            local_ns = {'treeObject': treeObject}
            try:
                exec(func_code, local_ns)
            except Exception as e:
                print(f'[DB] Failed to reconstruct class {tableName}: {e}')
                continue
            dynamic_init = local_ns['dynamic_init']

            class_attrs = {
                '__init__': treeObjectInit(dynamic_init),
                'displayName': tableName,
                '_dynamicClass': True,
                '_variableDefinitions': variables
            }
            DynamicClass = type(tableName, (treeObject,), class_attrs)

            newTyping = polyTypedObject(
                className=tableName,
                manager=manager,
                sourceFiles=[],
                identifierVariables=['id'],
                objectReferencesDict={},
                classDefinition=DynamicClass,
                kwRequiredParams=[],
                kwDefaultParams=list(var_defaults.keys()),
                allowClassEdit=True,
                isStateSpaceObject=False,
                excludeFromCRUDE=False
            )

            for var in variables:
                var_name = var.get('varName', '')
                var_type = var.get('varType', 'str')
                if var_name:
                    default_value = type_defaults.get(var_type, '')
                    try:
                        polyVar = polyTypedVariable(
                            polyTypedObj=newTyping,
                            attributeName=var_name,
                            attributeValue=default_value
                        )
                        polyVar.pythonTypeDefault = var_type
                        polyVar.displayName = var.get('varDisplayName', var_name)
                        newTyping.polyTypedVars.append(polyVar)
                        newTyping.polyTypedVarsDict[var_name] = polyVar
                        newTyping.variableNameList.append(var_name)
                    except Exception as e:
                        print(f'[DB] Warning: Could not create polyTypedVariable for {var_name}: {e}')

            if newTyping not in manager.objectTyping:
                manager.objectTyping.append(newTyping)

            if not hasattr(manager, 'dynamicClasses'):
                manager.dynamicClasses = {}
            manager.dynamicClasses[tableName] = DynamicClass

            # Backfill the registry entry so this doesn't need repair next boot
            try:
                conn = adapter.connect()
                cursor = conn.cursor()
                cursor.execute(
                    'CREATE TABLE IF NOT EXISTS _dynamic_class_registry ('
                    + ', '.join(adapter.translateColumnDefs(
                        _DYNAMIC_REGISTRY_COLUMNS)) + ')')
                cursor.execute(
                    adapter.replaceSQL(
                        '_dynamic_class_registry',
                        [c.split()[0] for c in _DYNAMIC_REGISTRY_COLUMNS]),
                    (tableName, tableName, json.dumps(variables), 1, 0, None, None, None)
                )
                conn.commit()
                conn.close()
                manager.db.cache.invalidateTable(
                    manager.db.name, '_dynamic_class_registry')
            except Exception as e:
                print(f'[DB] Warning: Could not backfill registry for {tableName}: {e}')

            print(f'[DB] Repaired orphaned class: {tableName} ({len(variables)} variables, {rowCount} data rows, registry backfilled)')

    def on_put(self, request, response):
        """Handle class edit requests — modify variables of an existing dynamic class"""
        try:
            class_def = request.get_media()
            className = class_def.get('className')
            if not className:
                response.status = falcon.HTTP_400
                response.media = {'success': False, 'error': 'className is required'}
                return

            # Must exist
            if className not in self.manager.objectTypingDict:
                response.status = falcon.HTTP_404
                response.media = {'success': False, 'error': f'Class {className} not found'}
                return

            existingTyping = self.manager.objectTypingDict[className]

            # Must be editable
            if not getattr(existingTyping, 'allowClassEdit', False):
                response.status = falcon.HTTP_403
                response.media = {'success': False, 'error': f'Class {className} is not editable'}
                return

            variables = class_def.get('variables', [])
            displayName = class_def.get('classDisplayName', getattr(existingTyping.classDefinition, 'displayName', className))
            isStateSpaceObject = class_def.get('isStateSpaceObject', existingTyping.isStateSpaceObject)
            stateSpaceDisplayFields = class_def.get('stateSpaceDisplayFields', None)
            stateSpaceFieldsPerRow = class_def.get('stateSpaceFieldsPerRow', 1)
            inheritsFrom = class_def.get('inheritsFrom', existingTyping.inheritsFrom)

            # Rebuild class + typing using _editDynamicClass
            self._editDynamicClass(
                className=className,
                displayName=displayName,
                variables=variables,
                existingTyping=existingTyping,
                isStateSpaceObject=isStateSpaceObject,
                stateSpaceDisplayFields=stateSpaceDisplayFields,
                stateSpaceFieldsPerRow=stateSpaceFieldsPerRow,
                inheritsFrom=inheritsFrom
            )

            response.status = falcon.HTTP_200
            response.media = {
                'success': True,
                'className': className,
                'displayName': displayName,
                'variableCount': len(variables)
            }
        except Exception as e:
            response.status = falcon.HTTP_500
            response.media = {'success': False, 'error': str(e)}
        response.set_header('Powered-By', 'Polari')

    def _editDynamicClass(self, className, displayName, variables, existingTyping,
                          isStateSpaceObject=True, stateSpaceDisplayFields=None, stateSpaceFieldsPerRow=1,
                          inheritsFrom=None):
        """
        Edits an existing dynamic class by rebuilding it with new variable definitions.
        Updates the class definition, typing metadata, and database schema.
        """
        if inheritsFrom is None:
            inheritsFrom = {}
        print(f'[DEBUG-CC] _editDynamicClass START: {className}', flush=True)

        # Build variable names and defaults
        var_defaults = {}
        for var in variables:
            var_name = var.get('varName', '')
            if var_name:
                var_defaults[var_name] = self._getDefaultValue(var.get('varType', 'str'))
        # Add inheritance reference variables
        for varName in inheritsFrom:
            if varName not in var_defaults:
                var_defaults[varName] = None

        # Create the dynamic __init__ method with EXPLICIT parameter names
        base_params = {'id', 'manager', 'branch', 'inTree'}
        custom_defaults = {k: v for k, v in var_defaults.items() if k not in base_params}
        param_names = list(custom_defaults.keys())

        param_str = ', '.join([f"{name}={repr(default)}" for name, default in custom_defaults.items()])
        if param_str:
            param_str = ', ' + param_str

        body_assignments = '\n'.join([f'    self.{name} = {name}' for name in param_names])

        func_code = f'''
def dynamic_init(self, manager=None, branch=None, id=None{param_str}):
    treeObject.__init__(self, manager=manager, branch=branch, id=id)
{body_assignments}
'''
        local_ns = {'treeObject': treeObject}
        exec(func_code, local_ns)
        dynamic_init = local_ns['dynamic_init']

        # Create new class via type()
        class_attrs = {
            '__init__': treeObjectInit(dynamic_init),
            'displayName': displayName,
            '_dynamicClass': True,
            '_variableDefinitions': variables
        }
        if inheritsFrom:
            class_attrs['_polariInheritsFrom'] = dict(inheritsFrom)
        DynamicClass = type(className, (treeObject,), class_attrs)
        print(f'[DEBUG-CC] _editDynamicClass: rebuilt DynamicClass for {className}', flush=True)

        # Update existingTyping: classDefinition, polyTypedVars, variableNameList, kwDefaultParams
        existingTyping.classDefinition = DynamicClass
        # Update inheritance metadata
        oldParentClasses = set(existingTyping.getInheritanceParentClassNames())
        existingTyping.inheritsFrom = dict(inheritsFrom)
        # Remove this class from old parents' inheritedByClasses
        for oldParentClassName in oldParentClasses:
            oldParentTyping = self.manager.objectTypingDict.get(oldParentClassName)
            if oldParentTyping and className in oldParentTyping.inheritedByClasses:
                oldParentTyping.inheritedByClasses.remove(className)
        # Add to new parents' inheritedByClasses
        for parentClassName in existingTyping.getInheritanceParentClassNames():
            parentTyping = self.manager.objectTypingDict.get(parentClassName)
            if parentTyping and className not in parentTyping.inheritedByClasses:
                parentTyping.inheritedByClasses.append(className)
        existingTyping.polyTypedVars = []
        existingTyping.polyTypedVarsDict = {}
        existingTyping.variableNameList = []
        existingTyping.kwDefaultParams = list(var_defaults.keys())

        # Determine identifier variables
        identifiers = ['id']
        for var in variables:
            if var.get('isIdentifier', False) and var.get('varName') not in identifiers:
                identifiers.append(var['varName'])
        existingTyping.identifierVariables = identifiers

        # Rebuild polyTypedVars from the updated variable definitions
        for var in variables:
            var_name = var.get('varName', '')
            var_type = var.get('varType', 'str')
            if var_name:
                default_value = self._getDefaultValue(var_type)
                try:
                    polyVar = polyTypedVariable(
                        polyTypedObj=existingTyping,
                        attributeName=var_name,
                        attributeValue=default_value
                    )
                    polyVar.pythonTypeDefault = var_type
                    polyVar.displayName = var.get('varDisplayName', var_name)
                    polyVar.isIdentifier = var.get('isIdentifier', False)
                    polyVar.isUnique = var.get('isUnique', False)
                    ref_class = var.get('refClass', None)
                    if ref_class:
                        polyVar.refClass = ref_class
                    existingTyping.polyTypedVars.append(polyVar)
                    existingTyping.polyTypedVarsDict[var_name] = polyVar
                    existingTyping.variableNameList.append(var_name)
                except Exception as e:
                    print(f"[createClassAPI] Warning: Could not create polyTypedVariable for {var_name}: {e}")

        print(f"[DEBUG-CC] _editDynamicClass: rebuilt {len(existingTyping.polyTypedVars)} polyTypedVars", flush=True)

        # Update state-space configuration
        existingTyping.isStateSpaceObject = isStateSpaceObject
        if isStateSpaceObject and stateSpaceDisplayFields:
            existingTyping.setStateSpaceDisplayFields(stateSpaceDisplayFields, stateSpaceFieldsPerRow)
        elif isStateSpaceObject:
            all_var_names = [v.get('varName') for v in variables if v.get('varName')]
            existingTyping.setStateSpaceDisplayFields(all_var_names, stateSpaceFieldsPerRow)

        # Update dynamic class reference
        if not hasattr(self.manager, 'dynamicClasses'):
            self.manager.dynamicClasses = {}
        self.manager.dynamicClasses[className] = DynamicClass

        # Update DB table schema — add new columns for any new variables
        if hasattr(self.manager, 'db') and self.manager.db is not None:
            try:
                db = self.manager.db
                adapter = db.adapter
                conn = adapter.connect()
                cursor = conn.cursor()
                existing_cols = set(adapter.tableColumns(conn, className))
                # Add new columns that don't exist yet (sqlite affinities;
                # the adapter translates for other dialects)
                type_map = {'str': 'TEXT', 'int': 'INTEGER', 'float': 'REAL', 'bool': 'INTEGER',
                            'list': 'TEXT', 'dict': 'TEXT', 'reference': 'TEXT'}
                for var in variables:
                    col_name = var.get('varName', '')
                    if col_name and col_name not in existing_cols:
                        col_type = adapter.translateColumnDefs(
                            [f'{col_name} '
                             f'{type_map.get(var.get("varType", "str"), "TEXT")}']
                        )[0].split(None, 1)[1]
                        cursor.execute(
                            f'ALTER TABLE {adapter.quoteIdent(className)} ADD '
                            f'COLUMN {adapter.quoteIdent(col_name)} {col_type}')
                        print(f'[DEBUG-CC] _editDynamicClass: added column {col_name} ({col_type}) to {className}', flush=True)
                conn.commit()
                conn.close()
                db.cache.invalidateTable(db.name, className)
            except Exception as e:
                print(f"[DEBUG-CC] _editDynamicClass: WARNING DB schema update failed: {e}", flush=True)

        # Re-persist class definition to registry (INSERT OR REPLACE)
        if hasattr(self.manager, 'db') and self.manager.db is not None:
            try:
                self._persistClassDefinition(className, displayName, variables,
                                              True, isStateSpaceObject,
                                              stateSpaceDisplayFields, stateSpaceFieldsPerRow,
                                              inheritsFrom=inheritsFrom)
                print(f'[DEBUG-CC] _editDynamicClass: class definition re-persisted', flush=True)
            except Exception as e:
                print(f"[DEBUG-CC] _editDynamicClass: WARNING persist failed: {e}", flush=True)

        print(f"[DEBUG-CC] _editDynamicClass COMPLETE: {className} with {len(variables)} variables", flush=True)

    def on_delete(self, request, response):
        """Handle class deletion requests — delete a dynamically created class and its collateral definitions"""
        try:
            class_def = request.get_media()
            className = class_def.get('className')
            if not className:
                response.status = falcon.HTTP_400
                response.media = {'success': False, 'error': 'className is required'}
                return

            # Must exist
            if className not in self.manager.objectTypingDict:
                response.status = falcon.HTTP_404
                response.media = {'success': False, 'error': f'Class {className} not found'}
                return

            existingTyping = self.manager.objectTypingDict[className]

            # Must be a dynamic (user-created) class — framework classes cannot be deleted
            classDef = existingTyping.classDefinition
            isDynamic = getattr(classDef, '_dynamicClass', False)
            if not isDynamic:
                response.status = falcon.HTTP_403
                response.media = {
                    'success': False,
                    'error': f'Class {className} is a framework class and cannot be deleted. '
                             f'Only dynamically created classes can be deleted.'
                }
                return

            # Must be editable
            if not getattr(existingTyping, 'allowClassEdit', False):
                response.status = falcon.HTTP_403
                response.media = {'success': False, 'error': f'Class {className} is not editable and cannot be deleted'}
                return

            print(f'[DEBUG-CC] on_delete: deleting class {className}', flush=True)

            # 1. Purge collateral definitions (displays, tables, graphs, geojson, datasets, field profiles, filter chains)
            collateralSummary = self._purgeCollateralDefinitions(className)
            print(f'[DEBUG-CC] on_delete: collateral purge complete: {collateralSummary}', flush=True)

            # 2. Clean up inheritance reverse index before purging
            if existingTyping.isMultiInheritanceClass:
                for parentClassName in existingTyping.getInheritanceParentClassNames():
                    parentTyping = self.manager.objectTypingDict.get(parentClassName)
                    if parentTyping and className in parentTyping.inheritedByClasses:
                        parentTyping.inheritedByClasses.remove(className)

            # 3. Purge the class itself (instances, DB table, typing, CRUDE, tree entries)
            purgeSummary = self.manager.purgeObjectType(className)
            print(f'[DEBUG-CC] on_delete: purgeObjectType complete: {purgeSummary}', flush=True)

            # 4. Remove from dynamicClasses dict
            if hasattr(self.manager, 'dynamicClasses') and className in self.manager.dynamicClasses:
                del self.manager.dynamicClasses[className]

            # 5. Remove from _dynamic_class_registry DB table
            registryRemoved = False
            if hasattr(self.manager, 'db') and self.manager.db is not None:
                try:
                    db = self.manager.db
                    db.deleteRowsWhere(
                        '_dynamic_class_registry', 'className', className)
                    registryRemoved = True
                    print(f'[DEBUG-CC] on_delete: removed {className} from _dynamic_class_registry', flush=True)
                except Exception as e:
                    print(f'[DEBUG-CC] on_delete: WARNING failed to remove from registry: {e}', flush=True)

            response.status = falcon.HTTP_200
            response.media = {
                'success': True,
                'className': className,
                'purgeSummary': purgeSummary,
                'collateralPurged': collateralSummary,
                'registryRemoved': registryRemoved
            }
            print(f'[DEBUG-CC] on_delete: SUCCESS — class {className} fully deleted', flush=True)

        except Exception as e:
            print(f'[DEBUG-CC] on_delete EXCEPTION: {type(e).__name__}: {e}', flush=True)
            response.status = falcon.HTTP_500
            response.media = {'success': False, 'error': str(e)}
            import traceback
            traceback.print_exc()

        response.set_header('Powered-By', 'Polari')

    def _purgeCollateralDefinitions(self, className):
        """Remove all collateral definition objects (displays, tables, graphs, etc.) tied to this class via source_class."""
        collateralTypes = [
            'DisplayDefinition',
            'TableDefinition',
            'GraphDefinition',
            'GeoJsonDefinition',
            'DataSetDefinition',
            'FieldProfileDefinition',
            'FilterChainDefinition',
            'MapPointDefinition',
        ]
        summary = {}
        for defType in collateralTypes:
            removed = 0
            if defType in self.manager.objectTables:
                instances = list(self.manager.objectTables[defType])
                for inst in instances:
                    if getattr(inst, 'source_class', None) == className:
                        self.manager.objectTables[defType].remove(inst)
                        removed += 1
                # Also remove from DB if available
                if removed > 0 and hasattr(self.manager, 'db') and self.manager.db is not None:
                    try:
                        db = self.manager.db
                        if defType in db.tables:
                            db.deleteRowsWhere(defType, 'source_class', className)
                    except Exception as e:
                        print(f'[DEBUG-CC] _purgeCollateralDefinitions: WARNING DB cleanup for {defType} failed: {e}', flush=True)
            if removed > 0:
                summary[defType] = removed
        return summary

    def on_get(self, request, response):
        """Return list of dynamically created classes"""
        try:
            dynamic_classes = {}
            if hasattr(self.manager, 'dynamicClasses'):
                for className, classDef in self.manager.dynamicClasses.items():
                    dynamic_classes[className] = {
                        'displayName': getattr(classDef, 'displayName', className),
                        'variables': getattr(classDef, '_variableDefinitions', [])
                    }

            response.status = falcon.HTTP_200
            response.media = {
                'success': True,
                'dynamicClasses': dynamic_classes,
                'count': len(dynamic_classes)
            }
        except Exception as e:
            response.status = falcon.HTTP_500
            response.media = {'success': False, 'error': str(e)}

        response.set_header('Powered-By', 'Polari')
