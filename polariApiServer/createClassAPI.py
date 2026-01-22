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
        try:
            # Parse request body
            raw_data = request.bounded_stream.read()
            class_def = json.loads(raw_data.decode('utf-8'))

            # Validate required fields
            if 'className' not in class_def or not class_def['className']:
                response.status = falcon.HTTP_400
                response.media = {'success': False, 'error': 'className is required'}
                return

            className = class_def['className']
            displayName = class_def.get('classDisplayName', className)
            variables = class_def.get('variables', [])
            registerCRUDE = class_def.get('registerCRUDE', True)

            # Validate className format (PascalCase, alphanumeric)
            if not className[0].isupper():
                response.status = falcon.HTTP_400
                response.media = {'success': False, 'error': 'className must start with uppercase letter'}
                return

            if not className.replace('_', '').isalnum():
                response.status = falcon.HTTP_400
                response.media = {'success': False, 'error': 'className must be alphanumeric (underscores allowed)'}
                return

            # Check if class already exists
            if className in self.manager.objectTypingDict:
                response.status = falcon.HTTP_409
                response.media = {'success': False, 'error': f'Class {className} already exists'}
                return

            # Create the dynamic class and register it
            result = self._createDynamicClass(
                className=className,
                displayName=displayName,
                variables=variables,
                registerCRUDE=registerCRUDE
            )

            response.status = falcon.HTTP_201
            response.media = {
                'success': True,
                'className': className,
                'displayName': displayName,
                'apiEndpoint': f'/{className}',
                'crudeRegistered': registerCRUDE,
                'variableCount': len(variables)
            }

        except json.JSONDecodeError:
            response.status = falcon.HTTP_400
            response.media = {'success': False, 'error': 'Invalid JSON in request body'}
        except Exception as e:
            response.status = falcon.HTTP_500
            response.media = {'success': False, 'error': str(e)}
            import traceback
            traceback.print_exc()

        response.set_header('Powered-By', 'Polari')

    def _createDynamicClass(self, className, displayName, variables, registerCRUDE):
        """
        Dynamically creates a new Python class and registers it with the Polari framework.
        """
        # Build variable names and defaults
        var_defaults = {}
        for var in variables:
            var_name = var.get('varName', '')
            if var_name:
                var_defaults[var_name] = self._getDefaultValue(var.get('varType', 'str'))

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

        # Create class attributes
        class_attrs = {
            '__init__': treeObjectInit(dynamic_init),
            'displayName': displayName,
            '_dynamicClass': True,
            '_variableDefinitions': variables
        }

        # Dynamically create the class inheriting from treeObject
        DynamicClass = type(className, (treeObject,), class_attrs)

        # Determine identifier variables
        identifiers = ['id']
        for var in variables:
            if var.get('isIdentifier', False) and var.get('varName') not in identifiers:
                identifiers.append(var['varName'])

        # Create polyTypedObject for the new class
        # Dynamically created classes have different defaults than core framework objects:
        # - allowClassEdit=True: Users can modify the class definition via API
        # - isStateSpaceObject=True: Available in No-Code State-Space by default
        # - excludeFromCRUDE=False: Should have public CRUDE endpoints
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
            isStateSpaceObject=True,
            excludeFromCRUDE=False
        )

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

        print(f"[createClassAPI] Created {len(newTyping.polyTypedVars)} polyTypedVars for {className}")

        # Also add to objectTyping list (polyTypedObject only adds to dict)
        if newTyping not in self.manager.objectTyping:
            self.manager.objectTyping.append(newTyping)

        # Store the dynamic class reference for instantiation
        if not hasattr(self.manager, 'dynamicClasses'):
            self.manager.dynamicClasses = {}
        self.manager.dynamicClasses[className] = DynamicClass

        # Register CRUDE endpoint if requested
        if registerCRUDE and self.polServer:
            self.polServer.registerCRUDEforObjectType(className)
            print(f"[createClassAPI] Registered CRUDE endpoint for dynamic class: {className}")

        print(f"[createClassAPI] Created dynamic class: {className} with {len(variables)} variables")
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
