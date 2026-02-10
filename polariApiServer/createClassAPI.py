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
            print(f'[DEBUG-CC] className={className} vars={len(variables)} registerCRUDE={registerCRUDE}', flush=True)

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
                stateSpaceFieldsPerRow=stateSpaceFieldsPerRow
            )
            print(f'[DEBUG-CC] _createDynamicClass returned OK for {className}', flush=True)

            response.status = falcon.HTTP_201
            response.media = {
                'success': True,
                'className': className,
                'displayName': displayName,
                'apiEndpoint': f'/{className}',
                'crudeRegistered': registerCRUDE,
                'variableCount': len(variables),
                'isStateSpaceObject': isStateSpaceObject
            }
            print(f'[DEBUG-CC] === on_post SUCCESS === {className} created', flush=True)

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
                            isStateSpaceObject=True, stateSpaceDisplayFields=None, stateSpaceFieldsPerRow=1):
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
        """
        print(f'[DEBUG-CC] _createDynamicClass START: {className}', flush=True)
        # Build variable names and defaults
        var_defaults = {}
        for var in variables:
            var_name = var.get('varName', '')
            if var_name:
                var_defaults[var_name] = self._getDefaultValue(var.get('varType', 'str'))
        print(f'[DEBUG-CC] step 1: var_defaults built ({len(var_defaults)} vars)', flush=True)

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

        # Create database table for the new class if DB is active
        if hasattr(self.manager, 'db') and self.manager.db is not None:
            try:
                print(f'[DEBUG-CC] step 9: creating DB table...', flush=True)
                if newTyping.polyTypedVarsDict:
                    newTyping.makeTypedTableFromAnalysis()
                    print(f"[DEBUG-CC] step 9: DB table created for {className}", flush=True)
            except Exception as e:
                print(f"[DEBUG-CC] step 9: WARNING DB table failed: {e}", flush=True)
        else:
            print(f'[DEBUG-CC] step 9: no DB active, skipping table creation', flush=True)

        # Persist dynamic class definition to registry table for restore on restart
        if hasattr(self.manager, 'db') and self.manager.db is not None:
            try:
                print(f'[DEBUG-CC] step 10: persisting class definition...', flush=True)
                self._persistClassDefinition(className, displayName, variables,
                                              registerCRUDE, isStateSpaceObject,
                                              stateSpaceDisplayFields, stateSpaceFieldsPerRow)
                print(f'[DEBUG-CC] step 10: class definition persisted', flush=True)
            except Exception as e:
                print(f"[DEBUG-CC] step 10: WARNING persist failed: {e}", flush=True)
        else:
            print(f'[DEBUG-CC] step 10: no DB active, skipping persist', flush=True)

        print(f"[DEBUG-CC] _createDynamicClass COMPLETE: {className} with {len(variables)} variables", flush=True)
        return newTyping

    def _getDefaultValue(self, var_type):
        """Get default value for a variable type"""
        type_defaults = {
            'str': '',
            'int': 0,
            'float': 0.0,
            'list': [],
            'dict': {},
            'bool': False,
            'reference': None
        }
        return type_defaults.get(var_type, '')

    def _persistClassDefinition(self, className, displayName, variables,
                                 registerCRUDE, isStateSpaceObject,
                                 stateSpaceDisplayFields, stateSpaceFieldsPerRow):
        """Save dynamic class definition to _dynamic_class_registry table."""
        db = self.manager.db
        dbFilePath = os.path.join(db.Path, db.name + '.db') if db.Path else db.name + '.db'
        conn = sqlite3.connect(dbFilePath)
        conn.execute('''CREATE TABLE IF NOT EXISTS _dynamic_class_registry (
            className TEXT PRIMARY KEY,
            displayName TEXT,
            variables TEXT,
            registerCRUDE INTEGER,
            isStateSpaceObject INTEGER,
            stateSpaceDisplayFields TEXT,
            stateSpaceFieldsPerRow INTEGER
        )''')
        conn.execute(
            'INSERT OR REPLACE INTO _dynamic_class_registry VALUES (?, ?, ?, ?, ?, ?, ?)',
            (
                className,
                displayName,
                json.dumps(variables),
                1 if registerCRUDE else 0,
                1 if isStateSpaceObject else 0,
                json.dumps(stateSpaceDisplayFields) if stateSpaceDisplayFields else None,
                stateSpaceFieldsPerRow
            )
        )
        conn.commit()
        conn.close()
        print(f"[createClassAPI] Persisted class definition for {className} to registry")

    @staticmethod
    def restoreDynamicClasses(manager, dbFilePath):
        """Restore all dynamic class definitions from the registry table.

        Called during restoreFromDatabase() BEFORE the instance restore loop,
        so that dynamic class tables are recognized as known classes.

        Args:
            manager: The managerObject
            dbFilePath: Path to the .db file
        """
        conn = sqlite3.connect(dbFilePath)
        cursor = conn.cursor()
        # Check if registry table exists
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='_dynamic_class_registry'")
        if not cursor.fetchone():
            conn.close()
            return
        cursor.execute('SELECT * FROM _dynamic_class_registry')
        rows = cursor.fetchall()
        conn.close()

        if not rows:
            return

        print(f'[DB] Restoring {len(rows)} dynamic class definitions...')

        for row in rows:
            className, displayName, variablesJson, registerCRUDE, isStateSpaceObject, displayFieldsJson, fieldsPerRow = row
            # Skip if already registered (shouldn't happen, but safety check)
            if className in manager.objectTypingDict:
                print(f'[DB] Dynamic class {className} already registered, skipping')
                continue

            variables = json.loads(variablesJson) if variablesJson else []
            stateSpaceDisplayFields = json.loads(displayFieldsJson) if displayFieldsJson else None

            # Re-create the dynamic class using the same logic as _createDynamicClass
            var_defaults = {}
            type_defaults = {'str': '', 'int': 0, 'float': 0.0, 'list': [], 'dict': {}, 'bool': False, 'reference': None}
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
            exec(func_code, local_ns)
            dynamic_init = local_ns['dynamic_init']

            class_attrs = {
                '__init__': treeObjectInit(dynamic_init),
                'displayName': displayName,
                '_dynamicClass': True,
                '_variableDefinitions': variables
            }

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

            print(f'[DB] Restored dynamic class: {className} ({len(variables)} variables)')

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
