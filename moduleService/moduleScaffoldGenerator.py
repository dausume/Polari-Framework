"""
Module Scaffold Generator

Generates a complete Polari module package on disk from a definition dict.
Produces files following the exact patterns used by polariMaterialsScienceModule.
"""

import os
import re
import json
import keyword
from datetime import datetime, timezone

from moduleService.moduleDiscovery import _snake_to_pascal, _pascal_to_snake, _get_framework_root, _get_modules_dir


# ── Validation ────────────────────────────────────────────────────────────────

ALLOWED_FIELD_TYPES = {
    'str', 'int', 'float', 'bool', 'list', 'dict',
    'map_coordinate', 'map_line_segment', 'map_polygon',
    'reference', 'date_duration', 'datetime_duration',
    'time', 'time_duration', 'precision_time', 'schedule',
}

TYPE_DEFAULTS = {
    'str': "''",
    'int': '0',
    'float': '0.0',
    'bool': 'False',
    'list': '[]',
    'dict': '{}',
    'map_coordinate': "'[]'",
    'map_line_segment': "'{}'",
    'map_polygon': "'{}'",
    'reference': 'None',
    'date_duration': 'None',
    'datetime_duration': 'None',
    'time': 'None',
    'time_duration': 'None',
    'precision_time': 'None',
    'schedule': 'None',
}

# Semantic types whose Python default is a string but should NOT be typed as 'str'.
# Used by initializeVarsFromSignature override in register files.
SEMANTIC_TYPES = {
    'map_coordinate', 'map_line_segment', 'map_polygon',
    'reference', 'date_duration', 'datetime_duration',
    'time', 'time_duration', 'precision_time', 'schedule',
}


def _validate_identifier(name, label='name'):
    """Validate that a string is a valid Python identifier."""
    if not name or not isinstance(name, str):
        raise ValueError(f'{label} must be a non-empty string')
    if not name.isidentifier():
        raise ValueError(f'{label} "{name}" is not a valid Python identifier')
    if keyword.iskeyword(name):
        raise ValueError(f'{label} "{name}" is a Python keyword')


def _validate_pascal_case(name, label='class name'):
    """Validate that a string is PascalCase."""
    _validate_identifier(name, label)
    if not name[0].isupper():
        raise ValueError(f'{label} "{name}" must start with an uppercase letter (PascalCase)')


def validate_module_definition(definition):
    """Validate a module definition dict before scaffolding.

    definition: {
        name: str,           # Human-readable module name
        description: str,    # Optional description
        classes: [
            {
                className: str,   # PascalCase class name
                fields: [
                    { name: str, type: str, defaultValue: any }
                ]
            }
        ]
    }

    Raises ValueError on validation failure.
    """
    name = definition.get('name', '').strip()
    if not name:
        raise ValueError('Module name is required')

    # Derive the pascal and snake versions
    # Allow spaces, hyphens, underscores in the human name
    words = re.split(r'[\s_-]+', name)
    pascal_name = ''.join(w.capitalize() for w in words if w)
    if not pascal_name.isidentifier():
        raise ValueError(f'Module name "{name}" cannot be converted to a valid identifier')

    # Check for directory collision
    framework_root = _get_modules_dir()
    dir_name = 'polari' + pascal_name + 'Module'
    if os.path.exists(os.path.join(framework_root, dir_name)):
        raise ValueError(f'Module directory "{dir_name}" already exists')

    classes = definition.get('classes', [])
    if not classes:
        raise ValueError('At least one class is required')

    seen_class_names = set()
    for cls in classes:
        class_name = cls.get('className', '').strip()
        _validate_pascal_case(class_name, 'Class name')

        if class_name in seen_class_names:
            raise ValueError(f'Duplicate class name: "{class_name}"')
        seen_class_names.add(class_name)

        fields = cls.get('fields', [])
        if not fields:
            raise ValueError(f'Class "{class_name}" must have at least one field')

        seen_field_names = set()
        for field in fields:
            field_name = field.get('name', '').strip()
            _validate_identifier(field_name, f'Field name in {class_name}')

            if field_name in seen_field_names:
                raise ValueError(f'Duplicate field "{field_name}" in class "{class_name}"')
            seen_field_names.add(field_name)

            field_type = field.get('type', 'str')
            if field_type not in ALLOWED_FIELD_TYPES:
                raise ValueError(
                    f'Field "{field_name}" has invalid type "{field_type}". '
                    f'Allowed: {", ".join(sorted(ALLOWED_FIELD_TYPES))}'
                )


# ── File Generators ───────────────────────────────────────────────────────────

def _class_name_to_filename(class_name):
    """Convert PascalCase class name to a camelCase filename (without .py).

    E.g. 'ExperimentRun' -> 'experimentRun'
    """
    return class_name[0].lower() + class_name[1:]


def _generate_class_file(class_name, fields):
    """Generate the contents of a treeObject class file."""
    filename_base = _class_name_to_filename(class_name)

    # Build constructor params
    param_lines = []
    assign_lines = []
    for field in fields:
        fname = field['name']
        ftype = field.get('type', 'str')
        default = TYPE_DEFAULTS.get(ftype, "''")
        param_lines.append(f"                 {fname}={default}")
        assign_lines.append(f"        self.{fname} = {fname}")

    params_str = ',\n'.join(param_lines)
    assigns_str = '\n'.join(assign_lines)

    # Build field docstring entries
    field_docs = '\n'.join(
        f"        {f['name']}: {f.get('type', 'str')}"
        for f in fields
    )

    return f'''from objectTreeDecorators import treeObject, treeObjectInit


class {class_name}(treeObject):
    """
    {class_name} model class.

    Attributes:
{field_docs}
    """

    @treeObjectInit
    def __init__(self,
                 manager=None,
                 branch=None,
                 id=None,
{params_str}):
        treeObject.__init__(self, manager=manager, branch=branch, id=id)
{assigns_str}

    def __repr__(self):
        return f"{class_name}(id='{{self.id}}')"
'''


def _generate_register_file(pascal_name, snake_name, classes):
    """Generate the register<Name>Module.py file."""
    package_name = 'polari' + pascal_name + 'Module'

    # Build import statements
    imports = []
    for cls in classes:
        cn = cls['className']
        fn = _class_name_to_filename(cn)
        imports.append(f"    from {package_name}.{fn} import {cn}")

    imports_str = '\n'.join(imports)

    # Build registered_classes dict entries
    dict_entries = []
    for cls in classes:
        cn = cls['className']
        dict_entries.append(f"        '{cn}': {cn},")
    dict_str = '\n'.join(dict_entries)

    # Build field type overrides for semantic types (map_coordinate, etc.)
    # These must be applied after initializeVarsFromSignature since it can't infer them.
    type_override_entries = []
    for cls in classes:
        cn = cls['className']
        fields = cls.get('fields', [])
        for field in fields:
            ft = field.get('type', 'str')
            if ft in SEMANTIC_TYPES:
                type_override_entries.append(
                    f"        ('{cn}', '{field['name']}', '{ft}'),"
                )

    if type_override_entries:
        overrides_block = "    # Semantic type overrides (types that can't be inferred from defaults)\n"
        overrides_block += "    _FIELD_TYPE_OVERRIDES = [\n"
        overrides_block += '\n'.join(type_override_entries)
        overrides_block += "\n    ]\n"
        overrides_block += "    for _cls_name, _field_name, _field_type in _FIELD_TYPE_OVERRIDES:\n"
        overrides_block += "        _typing = manager.objectTypingDict.get(_cls_name)\n"
        overrides_block += "        if _typing and hasattr(_typing, 'polyTypedVarsDict'):\n"
        overrides_block += "            _var = _typing.polyTypedVarsDict.get(_field_name)\n"
        overrides_block += "            if _var:\n"
        overrides_block += "                _var.pythonTypeDefault = _field_type\n"
    else:
        overrides_block = ""

    return f'''"""
Registration for {pascal_name} module.

Registers all module classes with the Polari object tree manager.
"""


def register_{snake_name}_defaults(manager=None):
    """Register {pascal_name} module classes with the given manager.

    Args:
        manager: The object tree manager to register with.

    Returns:
        dict: Mapping of class name to class object.
    """
{imports_str}

    registered_classes = {{
{dict_str}
    }}

    if manager is not None:
        for class_name, class_obj in registered_classes.items():
            existing = manager.objectTypingDict.get(class_name)
            if existing is not None:
                # Class already registered — ensure moduleBinding is set
                existing.moduleBinding = '{snake_name}'
                continue
            typing_obj = manager.makeDefaultObjectTyping(classObj=class_obj)
            if typing_obj is not None:
                typing_obj.excludeFromCRUDE = False
                typing_obj.moduleBinding = '{snake_name}'
                typing_obj.initializeVarsFromSignature()

{overrides_block}
    return registered_classes
'''


def _generate_init_file(pascal_name, snake_name, classes):
    """Generate the __init__.py file."""
    package_name = 'polari' + pascal_name + 'Module'

    # Build imports
    import_lines = []
    all_names = []
    for cls in classes:
        cn = cls['className']
        fn = _class_name_to_filename(cn)
        import_lines.append(f"from {package_name}.{fn} import {cn}")
        all_names.append(f"    '{cn}',")

    imports_str = '\n'.join(import_lines)
    all_str = '\n'.join(all_names)

    return f'''"""
{pascal_name} Module

Auto-generated Polari module.
"""

{imports_str}

from {package_name}.register{pascal_name}Module import register_{snake_name}_defaults
from {package_name}.seedData import seed_initial_data


def initialize(manager=None, include_seed_data=False):
    """Initialize the {pascal_name} module.

    Args:
        manager: The object tree manager to register with.
        include_seed_data: If True, load initial data.

    Returns:
        dict: {{'registered_classes': dict, 'seed_data': dict}}
    """
    registered_classes = register_{snake_name}_defaults(manager)

    result = {{
        'registered_classes': registered_classes,
        'seed_data': {{}}
    }}

    if include_seed_data:
        result['seed_data'] = seed_initial_data(manager)

    return result


__all__ = [
{all_str}
    'initialize',
    'register_{snake_name}_defaults',
    'seed_initial_data',
]
'''


def _generate_seed_stub():
    """Generate an empty seedData.py stub."""
    return '''"""
Seed Data

Load initial data for this module from JSON files in initialData/.
"""


def seed_initial_data(manager=None):
    """Load seed data into the object tree.

    Returns:
        dict: Mapping of class name to list of created instances.
    """
    return {}
'''


# ── Orchestrator ──────────────────────────────────────────────────────────────

def scaffold_module(definition, framework_root=None):
    """Generate a complete module package on disk.

    Args:
        definition: Module definition dict (name, description, classes).
        framework_root: Root directory of the framework. Auto-detected if None.

    Returns:
        dict: {module_id, package_name, dir_path, classes_created}

    Raises:
        ValueError: If validation fails.
    """
    validate_module_definition(definition)

    if framework_root is None:
        framework_root = _get_modules_dir()

    name = definition['name'].strip()
    description = definition.get('description', '').strip()
    classes = definition['classes']

    # Derive names
    words = re.split(r'[\s_-]+', name)
    pascal_name = ''.join(w.capitalize() for w in words if w)
    snake_name = _pascal_to_snake(pascal_name)
    package_name = 'polari' + pascal_name + 'Module'
    dir_path = os.path.join(framework_root, package_name)

    # Create directory structure
    os.makedirs(dir_path, exist_ok=False)
    os.makedirs(os.path.join(dir_path, 'initialData'), exist_ok=True)

    # Generate class files
    classes_created = []
    for cls in classes:
        class_name = cls['className'].strip()
        fields = cls.get('fields', [])
        # Normalize fields
        normalized_fields = []
        for f in fields:
            normalized_fields.append({
                'name': f['name'].strip(),
                'type': f.get('type', 'str'),
                'defaultValue': f.get('defaultValue', TYPE_DEFAULTS.get(f.get('type', 'str'), "''")),
            })

        filename = _class_name_to_filename(class_name) + '.py'
        filepath = os.path.join(dir_path, filename)
        content = _generate_class_file(class_name, normalized_fields)
        with open(filepath, 'w') as f:
            f.write(content)
        classes_created.append(class_name)

    # Generate register file
    register_filename = f'register{pascal_name}Module.py'
    with open(os.path.join(dir_path, register_filename), 'w') as f:
        f.write(_generate_register_file(pascal_name, snake_name, classes))

    # Generate __init__.py
    with open(os.path.join(dir_path, '__init__.py'), 'w') as f:
        f.write(_generate_init_file(pascal_name, snake_name, classes))

    # Generate seedData.py stub
    with open(os.path.join(dir_path, 'seedData.py'), 'w') as f:
        f.write(_generate_seed_stub())

    # Write module metadata
    metadata = {
        'id': snake_name,
        'name': name,
        'description': description,
        'user_created': True,
        'created_at': datetime.now(timezone.utc).isoformat(),
        'classes': [
            {
                'className': cls['className'].strip(),
                'fields': [
                    {'name': fl['name'].strip(), 'type': fl.get('type', 'str')}
                    for fl in cls.get('fields', [])
                ]
            }
            for cls in classes
        ]
    }
    with open(os.path.join(dir_path, '_module_metadata.json'), 'w') as f:
        json.dump(metadata, f, indent=2)

    return {
        'module_id': snake_name,
        'package_name': package_name,
        'dir_path': dir_path,
        'classes_created': classes_created,
    }


# ── Bind Existing Class to Module ─────────────────────────────────────────────

def _extract_fields_from_typing(typing_obj):
    """Extract field definitions from a polyTypedObject.

    Returns a list of {'name': str, 'type': str} dicts suitable for
    _generate_class_file().
    """
    skip_vars = {
        'manager', 'branch', 'id', 'objectTree', 'objectReferencesDict',
        'sourceFiles', 'identifiers', 'variableNameList', 'polyTypedVars',
        'polyTypedVarsDict', 'typingDicts', 'baseAccessDictionary',
        'basePermissionDictionary', 'eventsList', 'analyzeValuesMode',
    }
    fields = []
    vars_dict = getattr(typing_obj, 'polyTypedVarsDict', {})
    for var_name, var_typing in vars_dict.items():
        if var_name in skip_vars:
            continue
        type_name = getattr(var_typing, 'pythonTypeDefault', 'str') or 'str'
        # Preserve semantic types (map_coordinate, etc.); normalize complex compound types
        if type_name in ALLOWED_FIELD_TYPES:
            resolved_type = type_name
        else:
            base_type = type_name.split('(')[0] if '(' in type_name else type_name
            resolved_type = base_type if base_type in ALLOWED_FIELD_TYPES else 'str'
        fields.append({'name': var_name, 'type': resolved_type})
    return fields


def _read_existing_classes_from_register(register_path, package_name):
    """Parse an existing register file to find currently registered class names.

    Returns a list of class name strings.
    """
    existing = []
    if not os.path.isfile(register_path):
        return existing
    try:
        with open(register_path, 'r') as f:
            content = f.read()
        # Match lines like:  'ClassName': ClassName,
        for match in re.finditer(r"'(\w+)':\s*\w+,", content):
            existing.append(match.group(1))
    except Exception:
        pass
    return existing


def bind_class_to_module(class_name, typing_obj, module_id, framework_root=None):
    """Write a class's source file into an existing module and update register/init files.

    Args:
        class_name: The class name (PascalCase string).
        typing_obj: The polyTypedObject for this class.
        module_id: The module ID (snake_case) to bind to.
        framework_root: Framework root directory. Auto-detected if None.

    Returns:
        dict: {class_name, module_id, file_written, files_updated}

    Raises:
        ValueError: If the module directory doesn't exist.
    """
    if framework_root is None:
        framework_root = _get_modules_dir()

    pascal_module = _snake_to_pascal(module_id)
    package_name = 'polari' + pascal_module + 'Module'
    dir_path = os.path.join(framework_root, package_name)

    if not os.path.isdir(dir_path):
        raise ValueError(f"Module directory '{package_name}' does not exist")

    # Extract fields from the typing object
    fields = _extract_fields_from_typing(typing_obj)
    if not fields:
        # If no fields found in typing, try _variableDefinitions on the class
        class_def = getattr(typing_obj, 'classDefinition', None)
        if class_def and hasattr(class_def, '_variableDefinitions'):
            for vdef in class_def._variableDefinitions:
                fields.append({
                    'name': vdef.get('name', ''),
                    'type': vdef.get('type', 'str'),
                })
        if not fields:
            fields = [{'name': 'name', 'type': 'str'}]

    # 1. Write the class .py file
    filename = _class_name_to_filename(class_name) + '.py'
    filepath = os.path.join(dir_path, filename)
    content = _generate_class_file(class_name, fields)
    with open(filepath, 'w') as f:
        f.write(content)
    print(f"[ModuleBind] Wrote {filepath}")

    # 2. Get list of all classes that should be in the module
    register_filename = f'register{pascal_module}Module.py'
    register_path = os.path.join(dir_path, register_filename)
    existing_classes = _read_existing_classes_from_register(register_path, package_name)

    # Add the new class if not already present
    if class_name not in existing_classes:
        existing_classes.append(class_name)

    # Build class defs for file generation
    all_class_defs = [{'className': cn, 'fields': []} for cn in existing_classes]
    # The fields don't matter for register/init generation — only class names do

    # 3. Regenerate the register file
    with open(register_path, 'w') as f:
        f.write(_generate_register_file(pascal_module, module_id, all_class_defs))
    print(f"[ModuleBind] Updated {register_path}")

    # 4. Regenerate __init__.py
    init_path = os.path.join(dir_path, '__init__.py')
    with open(init_path, 'w') as f:
        f.write(_generate_init_file(pascal_module, module_id, all_class_defs))
    print(f"[ModuleBind] Updated {init_path}")

    # 5. Update _module_metadata.json if it exists
    metadata_path = os.path.join(dir_path, '_module_metadata.json')
    if os.path.isfile(metadata_path):
        try:
            with open(metadata_path, 'r') as f:
                metadata = json.load(f)
            # Add class to metadata if not present
            meta_classes = metadata.get('classes', [])
            if not any(c.get('className') == class_name for c in meta_classes):
                meta_classes.append({
                    'className': class_name,
                    'fields': [{'name': fl['name'], 'type': fl['type']} for fl in fields],
                })
                metadata['classes'] = meta_classes
                with open(metadata_path, 'w') as f:
                    json.dump(metadata, f, indent=2)
                print(f"[ModuleBind] Updated {metadata_path}")
        except Exception as e:
            print(f"[ModuleBind] Warning: Could not update metadata: {e}")

    return {
        'class_name': class_name,
        'module_id': module_id,
        'file_written': filename,
        'files_updated': [register_filename, '__init__.py'],
    }
