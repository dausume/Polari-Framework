"""
Seed data for SolutionDefinition instances.

Contains the 3 sample no-code solutions that are pre-loaded on first startup
when the SolutionDefinition table is empty. Each entry is a dict with the
fields expected by SolutionDefinition.__init__ (name, function_name,
target_runtime, definition).  The 'definition' value is a JSON string
containing the full solution structure consumed by the frontend.
"""

import json

# ---------------------------------------------------------------------------
# Solution 1: AdditionTester.test_addition
# ---------------------------------------------------------------------------
_ADDITION_TEST_DEFINITION = {
    "id": 1,
    "solutionName": "AdditionTester.test_addition",
    "functionName": "test_addition",
    "targetRuntime": "python_backend",
    "xBounds": 1000,
    "yBounds": 600,
    "boundClass": {
        "className": "AdditionTester",
        "displayName": "Addition Tester",
        "description": "A simple test that adds two numbers and checks if the result matches an expected value",
        "pythonImports": [],
        "fields": [
            {"name": "num_a", "displayName": "Number A", "type": "int", "defaultValue": 0, "description": "First number to add"},
            {"name": "num_b", "displayName": "Number B", "type": "int", "defaultValue": 0, "description": "Second number to add"},
            {"name": "expected_result", "displayName": "Expected Result", "type": "int", "defaultValue": 0, "description": "Expected sum for comparison"},
            {"name": "sum_result", "displayName": "Sum Result", "type": "int", "defaultValue": 0, "description": "Calculated sum of num_a + num_b"},
            {"name": "test_passed", "displayName": "Test Passed", "type": "bool", "defaultValue": False, "description": "Whether the sum matches expected"}
        ],
        "methods": [
            {
                "name": "test_addition",
                "displayName": "Test Addition",
                "parameters": [
                    {"name": "num_a", "type": "int"},
                    {"name": "num_b", "type": "int"},
                    {"name": "expected_result", "type": "int"}
                ],
                "returnType": "bool",
                "description": "Add two numbers and check if result matches expected value"
            }
        ]
    },
    "stateInstances": [
        {
            "stateName": "Start",
            "id": "start-state",
            "index": 0,
            "shapeType": "circle",
            "solutionName": "AdditionTester.test_addition",
            "stateClass": "InitialState",
            "boundObjectClass": "InitialState",
            "boundObjectFieldValues": {
                "displayName": "Start",
                "description": "Begin addition test with input parameters",
                "inputParams": [
                    {"name": "num_a", "type": "int", "description": "First number"},
                    {"name": "num_b", "type": "int", "description": "Second number"},
                    {"name": "expected_result", "type": "int", "description": "Expected sum"}
                ]
            },
            "stateSvgSizeX": None, "stateSvgSizeY": None, "stateSvgRadius": 60,
            "layerName": "start-layer",
            "stateLocationX": 80, "stateLocationY": 280,
            "stateSvgName": "circle",
            "slots": [
                {
                    "index": 0, "stateName": "Start", "slotAngularPosition": 180,
                    "connectors": [{"id": 1, "sourceSlot": 0, "sinkSlot": 0, "targetStateName": "Compute Sum"}],
                    "isInput": False, "allowOneToMany": True, "allowManyToOne": False,
                    "label": "Out", "passthroughVariableName": "num_a,num_b,expected_result"
                }
            ],
            "slotRadius": 5, "backgroundColor": "#4CAF50"
        },
        {
            "stateName": "Compute Sum",
            "id": "compute-sum",
            "index": 1,
            "shapeType": "circle",
            "solutionName": "AdditionTester.test_addition",
            "stateClass": "MathOperation",
            "boundObjectClass": "MathOperation",
            "boundObjectFieldValues": {
                "displayName": "Compute Sum",
                "description": "Calculate the sum of the two input numbers",
                "operationType": "add",
                "leftOperand": {"sourceType": "from_input", "inputSlotIndex": 0, "inputVariableName": "num_a"},
                "rightOperand": {"sourceType": "from_input", "inputSlotIndex": 0, "inputVariableName": "num_b"},
                "resultTarget": "solution_field",
                "resultFieldPath": "self.sum_result",
                "resultVariableName": "sum_result"
            },
            "stateSvgSizeX": None, "stateSvgSizeY": None, "stateSvgRadius": 65,
            "layerName": "math-layer",
            "stateLocationX": 280, "stateLocationY": 280,
            "stateSvgName": "circle",
            "slots": [
                {"index": 0, "stateName": "Compute Sum", "slotAngularPosition": 0, "connectors": [], "isInput": True, "allowOneToMany": False, "allowManyToOne": True, "label": "num_a, num_b"},
                {
                    "index": 1, "stateName": "Compute Sum", "slotAngularPosition": 180,
                    "connectors": [{"id": 3, "sourceSlot": 1, "sinkSlot": 0, "targetStateName": "Check Result"}],
                    "isInput": False, "allowOneToMany": True, "allowManyToOne": False,
                    "label": "sum_result", "passthroughVariableName": "sum_result"
                }
            ],
            "slotRadius": 5, "backgroundColor": "#FF9800"
        },
        {
            "stateName": "Check Result",
            "id": "check-result",
            "index": 2,
            "shapeType": "diamond",
            "solutionName": "AdditionTester.test_addition",
            "stateClass": "ConditionalChain",
            "boundObjectClass": "ConditionalChain",
            "boundObjectFieldValues": {
                "displayName": "Check Result",
                "description": "Check if the calculated sum matches the expected result",
                "defaultLogicalOperator": "AND",
                "links": [
                    {
                        "id": "link_check_equality",
                        "displayName": "sum_result == expected_result",
                        "conditionType": "equals",
                        "logicalOperator": "AND",
                        "isStateSpaceObject": True,
                        "leftSource": {"sourceType": "from_source_object", "sourceObjectPath": "self.sum_result"},
                        "rightSource": {"sourceType": "from_source_object", "sourceObjectPath": "self.expected_result"},
                        "fieldName": "sum_result",
                        "conditionValue": "expected_result"
                    }
                ]
            },
            "stateSvgSizeX": None, "stateSvgSizeY": None, "stateSvgRadius": 70,
            "layerName": "conditional-layer",
            "stateLocationX": 520, "stateLocationY": 280,
            "stateSvgName": "diamond",
            "slots": [
                {
                    "index": 0, 
                    "stateName": "Check Result", 
                    "slotAngularPosition": 270, 
                    "connectors": [], "isInput": True, "allowOneToMany": False, "allowManyToOne": True, "label": "In"},
                {
                    "index": 1, "stateName": "Check Result", "slotAngularPosition": 45,
                    "connectors": [{"id": 5, "sourceSlot": 1, "sinkSlot": 0, "targetStateName": "Return True"}],
                    "isInput": False, "allowOneToMany": True, "allowManyToOne": False,
                    "label": "True", "color": "#4CAF50"
                },
                {
                    "index": 2, "stateName": "Check Result", "slotAngularPosition": 135,
                    "connectors": [{"id": 6, "sourceSlot": 2, "sinkSlot": 0, "targetStateName": "Return False"}],
                    "isInput": False, "allowOneToMany": True, "allowManyToOne": False,
                    "label": "False", "color": "#F44336"
                }
            ],
            "slotRadius": 5, "backgroundColor": "#4CAF50"
        },
        {
            "stateName": "Return True",
            "id": "return-true",
            "index": 3,
            "shapeType": "rectangle",
            "solutionName": "AdditionTester.test_addition",
            "stateClass": "ReturnStatement",
            "boundObjectClass": "ReturnStatement",
            "boundObjectFieldValues": {"displayName": "Return True", "description": "Test passed - sum matches expected", "returnValue": "True"},
            "stateSvgSizeX": None, "stateSvgSizeY": None, "stateSvgRadius": None,
            "stateSvgWidth": 120, "stateSvgHeight": 80, "cornerRadius": 8,
            "layerName": "end-layer",
            "stateLocationX": 740, "stateLocationY": 180,
            "stateSvgName": "rectangle",
            "slots": [
                {
                    "index": 0, 
                    "stateName": "Return True", 
                    "slotAngularPosition": 320, 
                    "connectors": [], 
                    "isInput": True, 
                    "allowOneToMany": False, 
                    "allowManyToOne": True
                    }
            ],
            "slotRadius": 5, "backgroundColor": "#4CAF50"
        },
        {
            "stateName": "Return False",
            "id": "return-false",
            "index": 4,
            "shapeType": "rectangle",
            "solutionName": "AdditionTester.test_addition",
            "stateClass": "ReturnStatement",
            "boundObjectClass": "ReturnStatement",
            "boundObjectFieldValues": {"displayName": "Return False", "description": "Test failed - sum does not match expected", "returnValue": "False"},
            "stateSvgSizeX": None, "stateSvgSizeY": None, "stateSvgRadius": None,
            "stateSvgWidth": 120, "stateSvgHeight": 80, "cornerRadius": 8,
            "layerName": "end-layer",
            "stateLocationX": 740, "stateLocationY": 380,
            "stateSvgName": "rectangle",
            "slots": [
                {
                    "index": 0, 
                    "stateName": "Return False", 
                    "slotAngularPosition": 320, 
                    "connectors": [], 
                    "isInput": True, 
                    "allowOneToMany": False, 
                    "allowManyToOne": True
                    }
            ],
            "slotRadius": 5, "backgroundColor": "#F44336"
        }
    ]
}

# ---------------------------------------------------------------------------
# Solution 2: User.detectChanges
# ---------------------------------------------------------------------------
_USER_FORM_DETECT_DEFINITION = {
    "id": 2,
    "solutionName": "User.detectChanges",
    "functionName": "detectChanges",
    "targetRuntime": "typescript_frontend",
    "xBounds": 1200,
    "yBounds": 700,
    "boundClass": {
        "className": "User",
        "displayName": "User",
        "description": "Represents an authenticated user in the system — the owner of the profile being edited",
        "pythonImports": ["from typing import Optional", "from datetime import datetime"],
        "typescriptImports": [
            "import { Observable, Subscription } from 'rxjs';",
            "import { distinctUntilChanged, debounceTime, filter } from 'rxjs/operators';",
            "import { PolariService } from '@services/polari.service';"
        ],
        "fields": [
            {"name": "user_id", "displayName": "User ID", "type": "str", "description": "Unique user identifier"},
            {"name": "username", "displayName": "Username", "type": "str", "defaultValue": "", "description": "Login name"},
            {"name": "email", "displayName": "Email", "type": "str", "defaultValue": "", "description": "Primary email address"},
            {"name": "display_name", "displayName": "Display Name", "type": "str", "defaultValue": "", "description": "Name shown in the UI"},
            {"name": "bio", "displayName": "Bio", "type": "str", "defaultValue": "", "description": "Short user biography"},
            {"name": "avatar_url", "displayName": "Avatar URL", "type": "Optional[str]", "description": "URL to the profile picture"},
            {"name": "updated_at", "displayName": "Updated At", "type": "Optional[datetime]", "description": "Timestamp of the last profile update"}
        ],
        "methods": [
            {"name": "backend_update", "displayName": "Backend Update", "parameters": [{"name": "update_data", "type": "dict"}], "returnType": "bool", "description": "Validate and persist user profile changes"},
            {
                "name": "detectChanges",
                "displayName": "Detect Changes",
                "parameters": [],
                "returnType": "None",
                "description": "Subscribe to user form changes and push updates to the backend when the form is dirty"
            }
        ]
    },
    "stateInstances": [
        {
            "stateName": "Watch User Form", "id": "form-subscription", "index": 0,
            "shapeType": "circle", "solutionName": "User.detectChanges",
            "stateClass": "FormSubscription", "boundObjectClass": "FormSubscription",
            "boundObjectFieldValues": {
                "displayName": "Watch User Form",
                "description": "Subscribe to the reactive user-profile form value stream (debounced & deduplicated)",
                "sourceName": "userForm$",
                "triggerType": "form_subscription",
                "formFields": [
                    {"fieldName": "username", "displayName": "Username", "fieldType": "str", "required": True},
                    {"fieldName": "email", "displayName": "Email", "fieldType": "str", "required": True},
                    {"fieldName": "display_name", "displayName": "Display Name", "fieldType": "str", "required": True},
                    {"fieldName": "bio", "displayName": "Bio", "fieldType": "str", "required": False}
                ]
            },
            "stateSvgSizeX": None, "stateSvgSizeY": None, "stateSvgRadius": 100,
            "layerName": "start-layer", "stateLocationX": 140, "stateLocationY": 320,
            "stateSvgName": "circle",
            "slots": [
                {
                    "index": 0,
                    "stateName": "Watch User Form",
                    "slotAngularPosition": 180, 
                    "connectors": [
                        {
                            "id": 201, 
                            "sourceSlot": 0, 
                            "sinkSlot": 0, 
                            "targetStateName": "Validate Fields"
                            }
                    ], 
                    "isInput": False, 
                    "allowOneToMany": True, 
                    "allowManyToOne": False, 
                    "label": "formData", 
                    "passthroughVariableName": "formData"
                }
            ],
            "slotRadius": 5, "backgroundColor": "#E91E63"
        },
        {
            "stateName": "Validate Fields", "id": "validate-fields", "index": 1,
            "shapeType": "circle", "solutionName": "User.detectChanges",
            "stateClass": "FormValidation", "boundObjectClass": "FormValidation",
            "boundObjectFieldValues": {
                "displayName": "Validate Fields",
                "description": "Route each form field to individual validation with debounce and per-field validity tracking",
                "fields": [
                    {"fieldName": "username", "displayName": "Username", "fieldType": "str", "outputSlotIndex": 2, "enabled": True, "required": True, "debounceMs": 300},
                    {"fieldName": "email", "displayName": "Email", "fieldType": "str", "outputSlotIndex": 3, "enabled": True, "required": True, "debounceMs": 300},
                    {"fieldName": "display_name", "displayName": "Display Name", "fieldType": "str", "outputSlotIndex": 4, "enabled": True, "required": True, "debounceMs": 300},
                    {"fieldName": "bio", "displayName": "Bio", "fieldType": "str", "outputSlotIndex": 5, "enabled": True, "required": False, "debounceMs": 300}
                ]
            },
            "stateSvgSizeX": None, "stateSvgSizeY": None, "stateSvgRadius": 100,
            "layerName": "validation-layer", "stateLocationX": 400, "stateLocationY": 320,
            "stateSvgName": "circle",
            "slots": [
                {"index": 0, "stateName": "Validate Fields", "slotAngularPosition": 0, "connectors": [], "isInput": True, "allowOneToMany": False, "allowManyToOne": True, "label": "formData"},
                {"index": 1, "stateName": "Validate Fields", "slotAngularPosition": 180, "connectors": [{"id": 208, "sourceSlot": 1, "sinkSlot": 0, "targetStateName": "Call Backend Update"}], "isInput": False, "allowOneToMany": True, "allowManyToOne": False, "label": "All Valid", "passthroughVariableName": "formData"},
                {"index": 2, "stateName": "Validate Fields", "slotAngularPosition": 100, "connectors": [], "isInput": False, "allowOneToMany": True, "allowManyToOne": False, "label": "Username", "passthroughVariableName": "username"},
                {"index": 3, "stateName": "Validate Fields", "slotAngularPosition": 130, "connectors": [], "isInput": False, "allowOneToMany": True, "allowManyToOne": False, "label": "Email", "passthroughVariableName": "email"},
                {"index": 4, "stateName": "Validate Fields", "slotAngularPosition": 160, "connectors": [], "isInput": False, "allowOneToMany": True, "allowManyToOne": False, "label": "Display Name", "passthroughVariableName": "display_name"},
                {"index": 5, "stateName": "Validate Fields", "slotAngularPosition": 190, "connectors": [], "isInput": False, "allowOneToMany": True, "allowManyToOne": False, "label": "Bio", "passthroughVariableName": "bio"}
            ],
            "slotRadius": 5, "backgroundColor": "#00BCD4"
        },
        {
            "stateName": "Call Backend Update", "id": "call-backend-update", "index": 2,
            "shapeType": "circle", "solutionName": "User.detectChanges",
            "stateClass": "AwaitBackendCall", "boundObjectClass": "AwaitBackendCall",
            "boundObjectFieldValues": {"displayName": "Save to Backend", "targetSolutionName": "User.backend_update", "resultVariable": "saveResult", "description": "Call User.backend_update with the changed form data and await success/failure"},
            "stateSvgSizeX": None, "stateSvgSizeY": None, "stateSvgRadius": 100,
            "layerName": "cross-runtime-layer", "stateLocationX": 660, "stateLocationY": 320,
            "stateSvgName": "circle",
            "slots": [
                {"index": 0, "stateName": "Call Backend Update", "slotAngularPosition": 180, "connectors": [], "isInput": True, "allowOneToMany": False, "allowManyToOne": True, "label": "formData"},
                {"index": 1, "stateName": "Call Backend Update", "slotAngularPosition": 0, "connectors": [{"id": 205, "sourceSlot": 1, "sinkSlot": 0, "targetStateName": "Done"}], "isInput": False, "allowOneToMany": True, "allowManyToOne": False, "label": "saveResult", "passthroughVariableName": "saveResult"}
            ],
            "slotRadius": 5, "backgroundColor": "#FF5722"
        },
        {
            "stateName": "Done", "id": "done-state", "index": 3,
            "shapeType": "rectangle", "solutionName": "User.detectChanges",
            "stateClass": "ReturnStatement", "boundObjectClass": "ReturnStatement",
            "boundObjectFieldValues": {"displayName": "Done", "description": "Change-detection cycle complete", "returnValue": "void"},
            "stateSvgSizeX": None, "stateSvgSizeY": None, "stateSvgRadius": None,
            "stateSvgWidth": 120, "stateSvgHeight": 80, "cornerRadius": 8,
            "layerName": "end-layer", "stateLocationX": 900, "stateLocationY": 320,
            "stateSvgName": "rectangle",
            "slots": [{"index": 0, "stateName": "Done", "slotAngularPosition": 180, "connectors": [], "isInput": True, "allowOneToMany": False, "allowManyToOne": True}],
            "slotRadius": 5, "backgroundColor": "#F44336"
        }
    ]
}

# ---------------------------------------------------------------------------
# Solution 3: User.backend_update
# ---------------------------------------------------------------------------
_USER_BACKEND_UPDATE_DEFINITION = {
    "id": 3,
    "solutionName": "User.backend_update",
    "functionName": "backend_update",
    "targetRuntime": "python_backend",
    "xBounds": 1200,
    "yBounds": 700,
    "boundClass": {
        "className": "User",
        "displayName": "User",
        "description": "Represents an authenticated user in the system — the owner of the profile being edited",
        "pythonImports": ["from typing import Optional", "from datetime import datetime"],
        "fields": [
            {"name": "user_id", "displayName": "User ID", "type": "str", "description": "Unique user identifier"},
            {"name": "username", "displayName": "Username", "type": "str", "defaultValue": "", "description": "Login name"},
            {"name": "email", "displayName": "Email", "type": "str", "defaultValue": "", "description": "Primary email address"},
            {"name": "display_name", "displayName": "Display Name", "type": "str", "defaultValue": "", "description": "Name shown in the UI"},
            {"name": "bio", "displayName": "Bio", "type": "str", "defaultValue": "", "description": "Short user biography"},
            {"name": "avatar_url", "displayName": "Avatar URL", "type": "Optional[str]", "description": "URL to the profile picture"},
            {"name": "updated_at", "displayName": "Updated At", "type": "Optional[datetime]", "description": "Timestamp of the last profile update"}
        ],
        "methods": [
            {"name": "backend_update", "displayName": "Backend Update", "parameters": [{"name": "update_data", "type": "dict"}], "returnType": "bool", "description": "Validate and persist user profile changes — only the owning user may call this"},
            {"name": "get_profile", "displayName": "Get Profile", "parameters": [], "returnType": "dict", "description": "Return a sanitised dict of the user profile for the frontend"}
        ]
    },
    "stateInstances": [
        {
            "stateName": "Start", "id": "start-state", "index": 0,
            "shapeType": "circle", "solutionName": "User.backend_update",
            "stateClass": "LogicFlowEntry", "boundObjectClass": "LogicFlowEntry",
            "boundObjectFieldValues": {"displayName": "Start", "triggerType": "logic_flow_entry", "description": "Receive update_data dict from the frontend"},
            "stateSvgSizeX": None, "stateSvgSizeY": None, "stateSvgRadius": 60,
            "layerName": "start-layer", "stateLocationX": 80, "stateLocationY": 320,
            "stateSvgName": "circle",
            "slots": [
                {"index": 0, "stateName": "Start", "slotAngularPosition": 0, "connectors": [{"id": 301, "sourceSlot": 0, "sinkSlot": 0, "targetStateName": "Validate Data"}], "isInput": False, "allowOneToMany": True, "allowManyToOne": False, "label": "To Validate", "passthroughVariableName": "update_data"}
            ],
            "slotRadius": 5, "backgroundColor": "#673AB7"
        },
        {
            "stateName": "Validate Data", "id": "validate-data", "index": 1,
            "shapeType": "diamond", "solutionName": "User.backend_update",
            "stateClass": "ConditionalChain", "boundObjectClass": "ConditionalChain",
            "boundObjectFieldValues": {
                "displayName": "Validate Data", "description": "Ensure the update payload is non-empty and contains only allowed fields",
                "condition": "update_data and all(k in allowed_fields for k in update_data)", "defaultLogicalOperator": "AND",
                "links": [{"id": "link_validate", "displayName": "update_data is valid", "conditionType": "custom", "logicalOperator": "AND", "isStateSpaceObject": True, "leftSource": {"sourceType": "from_input", "inputSlotIndex": 0, "inputVariableName": "update_data"}, "rightSource": {"sourceType": "literal", "literalValue": "True"}, "fieldName": "update_data", "conditionValue": "True"}]
            },
            "stateSvgSizeX": None, "stateSvgSizeY": None, "stateSvgRadius": 70,
            "layerName": "conditional-layer", "stateLocationX": 300, "stateLocationY": 320,
            "stateSvgName": "diamond",
            "slots": [
                {"index": 0, "stateName": "Validate Data", "slotAngularPosition": 180, "connectors": [], "isInput": True, "allowOneToMany": False, "allowManyToOne": True, "label": "update_data", "parameterName": "update_data", "parameterType": "dict"},
                {"index": 1, "stateName": "Validate Data", "slotAngularPosition": 30, "connectors": [{"id": 302, "sourceSlot": 1, "sinkSlot": 0, "targetStateName": "Update Fields"}], "isInput": False, "allowOneToMany": True, "allowManyToOne": False, "label": "Valid", "color": "#4CAF50", "passthroughVariableName": "update_data"},
                {"index": 2, "stateName": "Validate Data", "slotAngularPosition": 330, "connectors": [{"id": 303, "sourceSlot": 2, "sinkSlot": 0, "targetStateName": "Log Failure"}], "isInput": False, "allowOneToMany": True, "allowManyToOne": False, "label": "Invalid", "color": "#F44336"}
            ],
            "slotRadius": 5, "backgroundColor": "#4CAF50"
        },
        {
            "stateName": "Update Fields", "id": "update-fields", "index": 2,
            "shapeType": "circle", "solutionName": "User.backend_update",
            "stateClass": "ForEachLoop", "boundObjectClass": "ForEachLoop",
            "boundObjectFieldValues": {"displayName": "Apply Updates", "itemVariable": "field_name", "indexVariable": "idx", "collectionVariable": "update_data.keys()", "description": "Iterate over each changed field and set it on the User object"},
            "stateSvgSizeX": None, "stateSvgSizeY": None, "stateSvgRadius": 65,
            "layerName": "loop-layer", "stateLocationX": 540, "stateLocationY": 220,
            "stateSvgName": "circle",
            "slots": [
                {"index": 0, "stateName": "Update Fields", "slotAngularPosition": 180, "connectors": [], "isInput": True, "allowOneToMany": False, "allowManyToOne": True, "label": "update_data"},
                {"index": 1, "stateName": "Update Fields", "slotAngularPosition": 0, "connectors": [{"id": 304, "sourceSlot": 1, "sinkSlot": 0, "targetStateName": "Set Timestamp"}], "isInput": False, "allowOneToMany": True, "allowManyToOne": False, "label": "Loop Done"}
            ],
            "slotRadius": 5, "backgroundColor": "#2196F3"
        },
        {
            "stateName": "Set Timestamp", "id": "set-timestamp", "index": 3,
            "shapeType": "circle", "solutionName": "User.backend_update",
            "stateClass": "VariableAssignment", "boundObjectClass": "VariableAssignment",
            "boundObjectFieldValues": {"displayName": "Set Timestamp", "variableName": "self.updated_at", "value": "datetime.utcnow()", "dataType": "datetime", "description": "Record the timestamp of this profile update"},
            "stateSvgSizeX": None, "stateSvgSizeY": None, "stateSvgRadius": 60,
            "layerName": "assignment-layer", "stateLocationX": 740, "stateLocationY": 220,
            "stateSvgName": "circle",
            "slots": [
                {"index": 0, "stateName": "Set Timestamp", "slotAngularPosition": 180, "connectors": [], "isInput": True, "allowOneToMany": False, "allowManyToOne": True, "label": "Input"},
                {"index": 1, "stateName": "Set Timestamp", "slotAngularPosition": 0, "connectors": [{"id": 305, "sourceSlot": 1, "sinkSlot": 0, "targetStateName": "Log Success"}], "isInput": False, "allowOneToMany": True, "allowManyToOne": False, "label": "Output"}
            ],
            "slotRadius": 5, "backgroundColor": "#9C27B0"
        },
        {
            "stateName": "Log Success", "id": "log-success", "index": 4,
            "shapeType": "circle", "solutionName": "User.backend_update",
            "stateClass": "LogOutput", "boundObjectClass": "LogOutput",
            "boundObjectFieldValues": {"displayName": "Log Success", "messageTemplate": "User {self.user_id} profile updated successfully", "logLevel": "info"},
            "stateSvgSizeX": None, "stateSvgSizeY": None, "stateSvgRadius": 55,
            "layerName": "debug-layer", "stateLocationX": 940, "stateLocationY": 220,
            "stateSvgName": "circle",
            "slots": [
                {"index": 0, "stateName": "Log Success", "slotAngularPosition": 180, "connectors": [], "isInput": True, "allowOneToMany": False, "allowManyToOne": True, "label": "Input"},
                {"index": 1, "stateName": "Log Success", "slotAngularPosition": 0, "connectors": [{"id": 306, "sourceSlot": 1, "sinkSlot": 0, "targetStateName": "Commit Changes"}], "isInput": False, "allowOneToMany": True, "allowManyToOne": False, "label": "Output"}
            ],
            "slotRadius": 5, "backgroundColor": "#607D8B"
        },
        {
            "stateName": "Commit Changes", "id": "commit-changes", "index": 5,
            "shapeType": "rectangle", "solutionName": "User.backend_update",
            "stateClass": "StateChangeCommit", "boundObjectClass": "StateChangeCommit",
            "boundObjectFieldValues": {"displayName": "Commit Changes", "description": "Profile update succeeded — commit to backend", "targetFieldName": "user_profile", "changeType": "update"},
            "stateSvgSizeX": None, "stateSvgSizeY": None, "stateSvgRadius": None,
            "stateSvgWidth": 120, "stateSvgHeight": 80, "cornerRadius": 8,
            "layerName": "end-layer", "stateLocationX": 1100, "stateLocationY": 220,
            "stateSvgName": "rectangle",
            "slots": [{"index": 0, "stateName": "Commit Changes", "slotAngularPosition": 180, "connectors": [], "isInput": True, "allowOneToMany": False, "allowManyToOne": True}],
            "slotRadius": 5, "backgroundColor": "#4CAF50"
        },
        {
            "stateName": "Log Failure", "id": "log-failure", "index": 6,
            "shapeType": "circle", "solutionName": "User.backend_update",
            "stateClass": "LogOutput", "boundObjectClass": "LogOutput",
            "boundObjectFieldValues": {"displayName": "Log Failure", "messageTemplate": "User {self.user_id} update rejected — invalid payload", "logLevel": "warning"},
            "stateSvgSizeX": None, "stateSvgSizeY": None, "stateSvgRadius": 55,
            "layerName": "debug-layer", "stateLocationX": 540, "stateLocationY": 440,
            "stateSvgName": "circle",
            "slots": [
                {"index": 0, "stateName": "Log Failure", "slotAngularPosition": 180, "connectors": [], "isInput": True, "allowOneToMany": False, "allowManyToOne": True, "label": "Input"},
                {"index": 1, "stateName": "Log Failure", "slotAngularPosition": 0, "connectors": [{"id": 307, "sourceSlot": 1, "sinkSlot": 0, "targetStateName": "Return False"}], "isInput": False, "allowOneToMany": True, "allowManyToOne": False, "label": "Output"}
            ],
            "slotRadius": 5, "backgroundColor": "#607D8B"
        },
        {
            "stateName": "Return False", "id": "return-false", "index": 7,
            "shapeType": "rectangle", "solutionName": "User.backend_update",
            "stateClass": "ReturnStatement", "boundObjectClass": "ReturnStatement",
            "boundObjectFieldValues": {"displayName": "Return False", "description": "Profile update failed — invalid data", "returnValue": "False"},
            "stateSvgSizeX": None, "stateSvgSizeY": None, "stateSvgRadius": None,
            "stateSvgWidth": 120, "stateSvgHeight": 80, "cornerRadius": 8,
            "layerName": "end-layer", "stateLocationX": 780, "stateLocationY": 440,
            "stateSvgName": "rectangle",
            "slots": [{"index": 0, "stateName": "Return False", "slotAngularPosition": 180, "connectors": [], "isInput": True, "allowOneToMany": False, "allowManyToOne": True}],
            "slotRadius": 5, "backgroundColor": "#F44336"
        }
    ]
}


# ---------------------------------------------------------------------------
# Solution 4: CalculusTester.derivative_test
# ---------------------------------------------------------------------------
# Demonstrates the equation field type + RunEquation state wired together.
# A user supplies a LaTeX expression as `input_expression`; the RunEquation
# state references the `CalcTester.DerivativeOfExpr` equation (which has a
# single declared `f` potential), binds `f` to `self.input_expression`, and
# stores the derivative LaTeX into `self.result_expression`.
#
# Phase E will add a second solution (`splice_and_integrate`) demonstrating
# multi-potential equations.

_CALCULUS_TESTER_BOUND_CLASS = {
    "className": "CalculusTester",
    "displayName": "Calculus Tester",
    "description": "Tester object whose fields hold LaTeX equations. Demonstrates the equation field type + RunEquation state.",
    "pythonImports": [],
    "fields": [
        {"name": "input_expression",   "displayName": "Input Expression",   "type": "equation", "defaultValue": "",  "description": "LaTeX expression to operate on (e.g. 2*x or \\sin(x))"},
        {"name": "input_expression_2", "displayName": "Input Expression 2", "type": "equation", "defaultValue": "",  "description": "Second LaTeX expression (used by multi-potential solutions)"},
        {"name": "operation_type",     "displayName": "Operation",          "type": "str",      "defaultValue": "derivative", "description": "Which operation to apply (derivative, integral_indefinite, etc.)"},
        {"name": "variable",           "displayName": "Variable",           "type": "str",      "defaultValue": "x", "description": "Variable to operate on"},
        {"name": "result_expression",  "displayName": "Result Expression",  "type": "equation", "defaultValue": "",  "description": "Result LaTeX produced by the equation executor"},
        {"name": "expected_result",    "displayName": "Expected Result",    "type": "equation", "defaultValue": "",  "description": "Optional expected LaTeX, for tester comparison"},
        {"name": "test_passed",        "displayName": "Test Passed",        "type": "bool",     "defaultValue": False, "description": "Whether the result matched expected_result"}
    ],
    "methods": [
        {
            "name": "derivative_test",
            "displayName": "Derivative Test",
            "parameters": [
                {"name": "input_expression", "type": "equation", "description": "Formula to differentiate"},
                {"name": "variable",         "type": "str",      "description": "Variable to differentiate with respect to"}
            ],
            "returnType": "equation",
            "description": "Differentiate the input expression and store the result"
        },
        {
            "name": "splice_and_integrate",
            "displayName": "Splice & Integrate",
            "parameters": [
                {"name": "input_expression",   "type": "equation"},
                {"name": "input_expression_2", "type": "equation"}
            ],
            "returnType": "equation",
            "description": "Integrate the product of two LaTeX fragments with respect to x"
        }
    ]
}

_CALCULUS_DERIVATIVE_TEST_DEFINITION = {
    "id": 4,
    "solutionName": "CalculusTester.derivative_test",
    "functionName": "derivative_test",
    "targetRuntime": "python_backend",
    "xBounds": 1100,
    "yBounds": 500,
    "boundClass": _CALCULUS_TESTER_BOUND_CLASS,
    "stateInstances": [
        {
            "stateName": "Start", "id": "start-state", "index": 0,
            "shapeType": "circle",
            "solutionName": "CalculusTester.derivative_test",
            "stateClass": "InitialState", "boundObjectClass": "InitialState",
            "boundObjectFieldValues": {
                "displayName": "Start",
                "description": "Begin derivative test with input parameters",
                "inputParams": [
                    {"name": "input_expression", "type": "equation", "description": "Formula to differentiate"},
                    {"name": "variable",         "type": "str",      "description": "Variable to differentiate with respect to"}
                ]
            },
            "stateSvgSizeX": None, "stateSvgSizeY": None, "stateSvgRadius": 60,
            "layerName": "start-layer",
            "stateLocationX": 100, "stateLocationY": 250,
            "stateSvgName": "circle",
            "slots": [
                {
                    "index": 0, "stateName": "Start", "slotAngularPosition": 0,
                    "connectors": [{"id": 1, "sourceSlot": 0, "sinkSlot": 0, "targetStateName": "Differentiate"}],
                    "isInput": False, "allowOneToMany": True, "allowManyToOne": False,
                    "label": "Out", "passthroughVariableName": "input_expression,variable"
                }
            ],
            "slotRadius": 5, "backgroundColor": "#4CAF50"
        },
        {
            "stateName": "Differentiate", "id": "run-equation", "index": 1,
            "shapeType": "circle",
            "solutionName": "CalculusTester.derivative_test",
            "stateClass": "CalculusOperation", "boundObjectClass": "CalculusOperation",
            "boundObjectFieldValues": {
                "displayName": "Differentiate",
                # Reference the seeded `CalcTester.DerivativeOfExpr` equation
                # (added in equationSeedData.py). Single potential `f` is
                # bound to self.input_expression at runtime.
                "equationId": "",
                "equationName": "CalcTester.DerivativeOfExpr",
                "bindings": [
                    {
                        "symbol": "f",
                        "source": {
                            "sourceType": "from_source_object",
                            "sourceObjectPath": "self.input_expression"
                        }
                    }
                ],
                "resultTarget": "solution_field",
                "resultFieldPath": "result_expression",
                "resultVariableName": "result_expression"
            },
            "stateSvgSizeX": None, "stateSvgSizeY": None, "stateSvgRadius": 75,
            "layerName": "math-layer",
            "stateLocationX": 360, "stateLocationY": 250,
            "stateSvgName": "circle",
            "slots": [
                {"index": 0, "stateName": "Differentiate", "slotAngularPosition": 180, "connectors": [], "isInput": True, "allowOneToMany": False, "allowManyToOne": True, "label": "In"},
                {
                    "index": 1, "stateName": "Differentiate", "slotAngularPosition": 0,
                    "connectors": [{"id": 2, "sourceSlot": 1, "sinkSlot": 0, "targetStateName": "Return"}],
                    "isInput": False, "allowOneToMany": True, "allowManyToOne": False,
                    "label": "result_expression", "passthroughVariableName": "result_expression"
                }
            ],
            "slotRadius": 5, "backgroundColor": "#FFB74D"
        },
        {
            "stateName": "Return", "id": "return-result", "index": 2,
            "shapeType": "rectangle",
            "solutionName": "CalculusTester.derivative_test",
            "stateClass": "ReturnValue", "boundObjectClass": "ReturnValue",
            "boundObjectFieldValues": {
                "displayName": "Return Result",
                "description": "Return the derivative LaTeX",
                "returnValueSource": {
                    "sourceType": "from_source_object",
                    "sourceObjectPath": "self.result_expression"
                }
            },
            "stateSvgSizeX": None, "stateSvgSizeY": None, "stateSvgRadius": None,
            "stateSvgWidth": 140, "stateSvgHeight": 80, "cornerRadius": 8,
            "layerName": "end-layer",
            "stateLocationX": 640, "stateLocationY": 250,
            "stateSvgName": "rectangle",
            "slots": [
                {"index": 0, "stateName": "Return", "slotAngularPosition": 180, "connectors": [], "isInput": True, "allowOneToMany": False, "allowManyToOne": True}
            ],
            "slotRadius": 5, "backgroundColor": "#4CAF50"
        }
    ]
}


# ---------------------------------------------------------------------------
# Solution 5: CalculusTester.splice_and_integrate
# ---------------------------------------------------------------------------
# Demonstrates a MULTI-POTENTIAL equation. References
# `CalcTester.IntegrateProduct` whose LaTeX is `f \cdot g` and which declares
# two literal-string potentials `f` and `g`. The CalculusOperation overlay
# auto-renders TWO source-selector slots — the user binds `f` to
# `self.input_expression` and `g` to `self.input_expression_2`, and the
# executor's symbol substitution composes the product LaTeX implicitly
# before integrating. No explicit "splice" state is needed.

_CALCULUS_SPLICE_AND_INTEGRATE_DEFINITION = {
    "id": 5,
    "solutionName": "CalculusTester.splice_and_integrate",
    "functionName": "splice_and_integrate",
    "targetRuntime": "python_backend",
    "xBounds": 1100,
    "yBounds": 500,
    "boundClass": _CALCULUS_TESTER_BOUND_CLASS,
    "stateInstances": [
        {
            "stateName": "Start", "id": "start-state", "index": 0,
            "shapeType": "circle",
            "solutionName": "CalculusTester.splice_and_integrate",
            "stateClass": "InitialState", "boundObjectClass": "InitialState",
            "boundObjectFieldValues": {
                "displayName": "Start",
                "description": "Begin splice-and-integrate test with two LaTeX fragments",
                "inputParams": [
                    {"name": "input_expression",   "type": "equation", "description": "First LaTeX fragment (will be substituted as `f`)"},
                    {"name": "input_expression_2", "type": "equation", "description": "Second LaTeX fragment (will be substituted as `g`)"}
                ]
            },
            "stateSvgSizeX": None, "stateSvgSizeY": None, "stateSvgRadius": 60,
            "layerName": "start-layer",
            "stateLocationX": 100, "stateLocationY": 250,
            "stateSvgName": "circle",
            "slots": [
                {
                    "index": 0, "stateName": "Start", "slotAngularPosition": 0,
                    "connectors": [{"id": 1, "sourceSlot": 0, "sinkSlot": 0, "targetStateName": "Integrate Product"}],
                    "isInput": False, "allowOneToMany": True, "allowManyToOne": False,
                    "label": "Out", "passthroughVariableName": "input_expression,input_expression_2"
                }
            ],
            "slotRadius": 5, "backgroundColor": "#4CAF50"
        },
        {
            "stateName": "Integrate Product", "id": "run-equation", "index": 1,
            "shapeType": "circle",
            "solutionName": "CalculusTester.splice_and_integrate",
            "stateClass": "CalculusOperation", "boundObjectClass": "CalculusOperation",
            "boundObjectFieldValues": {
                "displayName": "Integrate Product",
                # `CalcTester.IntegrateProduct` declares two potentials (`f`,
                # `g`) — the overlay renders two source-selector slots, each
                # of which we wire to a different equation field.
                "equationId": "",
                "equationName": "CalcTester.IntegrateProduct",
                "bindings": [
                    {
                        "symbol": "f",
                        "source": {
                            "sourceType": "from_source_object",
                            "sourceObjectPath": "self.input_expression"
                        }
                    },
                    {
                        "symbol": "g",
                        "source": {
                            "sourceType": "from_source_object",
                            "sourceObjectPath": "self.input_expression_2"
                        }
                    }
                ],
                "resultTarget": "solution_field",
                "resultFieldPath": "result_expression",
                "resultVariableName": "result_expression"
            },
            "stateSvgSizeX": None, "stateSvgSizeY": None, "stateSvgRadius": 80,
            "layerName": "math-layer",
            "stateLocationX": 380, "stateLocationY": 250,
            "stateSvgName": "circle",
            "slots": [
                {"index": 0, "stateName": "Integrate Product", "slotAngularPosition": 180, "connectors": [], "isInput": True, "allowOneToMany": False, "allowManyToOne": True, "label": "In"},
                {
                    "index": 1, "stateName": "Integrate Product", "slotAngularPosition": 0,
                    "connectors": [{"id": 2, "sourceSlot": 1, "sinkSlot": 0, "targetStateName": "Return"}],
                    "isInput": False, "allowOneToMany": True, "allowManyToOne": False,
                    "label": "result_expression", "passthroughVariableName": "result_expression"
                }
            ],
            "slotRadius": 5, "backgroundColor": "#FFB74D"
        },
        {
            "stateName": "Return", "id": "return-result", "index": 2,
            "shapeType": "rectangle",
            "solutionName": "CalculusTester.splice_and_integrate",
            "stateClass": "ReturnValue", "boundObjectClass": "ReturnValue",
            "boundObjectFieldValues": {
                "displayName": "Return Result",
                "description": "Return the integrated product as LaTeX",
                "returnValueSource": {
                    "sourceType": "from_source_object",
                    "sourceObjectPath": "self.result_expression"
                }
            },
            "stateSvgSizeX": None, "stateSvgSizeY": None, "stateSvgRadius": None,
            "stateSvgWidth": 140, "stateSvgHeight": 80, "cornerRadius": 8,
            "layerName": "end-layer",
            "stateLocationX": 660, "stateLocationY": 250,
            "stateSvgName": "rectangle",
            "slots": [
                {"index": 0, "stateName": "Return", "slotAngularPosition": 180, "connectors": [], "isInput": True, "allowOneToMany": False, "allowManyToOne": True}
            ],
            "slotRadius": 5, "backgroundColor": "#4CAF50"
        }
    ]
}


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

SEED_SOLUTIONS = [
    {
        "name": "AdditionTester.test_addition",
        "function_name": "test_addition",
        "target_runtime": "python_backend",
        "definition": json.dumps(_ADDITION_TEST_DEFINITION),
    },
    {
        "name": "User.detectChanges",
        "function_name": "detectChanges",
        "target_runtime": "typescript_frontend",
        "definition": json.dumps(_USER_FORM_DETECT_DEFINITION),
    },
    {
        "name": "User.backend_update",
        "function_name": "backend_update",
        "target_runtime": "python_backend",
        "definition": json.dumps(_USER_BACKEND_UPDATE_DEFINITION),
    },
    {
        "name": "CalculusTester.derivative_test",
        "function_name": "derivative_test",
        "target_runtime": "python_backend",
        "definition": json.dumps(_CALCULUS_DERIVATIVE_TEST_DEFINITION),
    },
    {
        "name": "CalculusTester.splice_and_integrate",
        "function_name": "splice_and_integrate",
        "target_runtime": "python_backend",
        "definition": json.dumps(_CALCULUS_SPLICE_AND_INTEGRATE_DEFINITION),
    },
]
