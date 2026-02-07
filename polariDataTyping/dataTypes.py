#Standard types inherent to python
standardTypesPython = ['str','int','float','complex','list','tuple','range','dict',
'set','frozenset','bool','bytes','bytearray','memoryview', 'type', 'NoneType',
'method-wrapper', 'TextIOWrapper']
#Potential Object names that should never be used despite no object existing for them.
reservedObjectNames = ['method-wrapper']
#Objects that are defined but should not be assessed as a treeObject or managerObject
ignoredObjectsPython = ['struct_time', 'API', 'App', 'polariList']
#An alternative format defining what modules certain ignored objects should be originating from.
ignoredObjectImports = {'falcon':['API', 'App'], 'time':['struct_time']}
#A list of all existing types in python, including both object types and standard types.
dataTypesPython = standardTypesPython + ignoredObjectsPython
#A list of all standard data types in Javascript for use in converting types.
dataTypesJS = ['undefined','Boolean','Number','String','BigInt','Symbol','null','Object','Function']
#A list of all standard data types in JSON for use when sending data.
dataTypesJSON = ['String','Number','Object','Array','Boolean','null']
#A list of all SQLite standard data types for use when storing data.
dataAffinitiesSqlite = ['NONE','INTEGER','REAL','TEXT','NUMERIC']

# Mapping from Python type names to SQLite affinity types.
# Compound types (list, dict, tuple, object references) map to TEXT
# since they are serialized as JSON strings in the database.
_pythonToSqliteMap = {
    'str': 'TEXT',
    'int': 'INTEGER',
    'float': 'REAL',
    'complex': 'TEXT',
    'bool': 'NUMERIC',
    'bytes': 'BLOB',
    'bytearray': 'BLOB',
    'NoneType': 'NONE',
    'list': 'TEXT',
    'tuple': 'TEXT',
    'dict': 'TEXT',
    'set': 'TEXT',
    'frozenset': 'TEXT',
    'range': 'TEXT',
    'memoryview': 'BLOB',
    'dateTime': 'TEXT',
    'TextIOWrapper': 'TEXT',
}

def pythonTypeToSqliteAffinity(pythonTypeName):
    """Map a Python type name string to its SQLite affinity.

    For simple types (str, int, float, etc.) returns the direct mapping.
    For compound types like 'list(str,int)', 'object(User)',
    'classreference(...)' etc., returns TEXT since they are serialized.

    Args:
        pythonTypeName: String name of the Python type (e.g. 'str', 'int',
                       'list(str,int)', 'object(User)')

    Returns:
        SQLite affinity string: 'TEXT', 'INTEGER', 'REAL', 'NUMERIC', 'BLOB', or 'NONE'
    """
    if pythonTypeName is None:
        return 'NONE'
    # Direct match for simple types
    if pythonTypeName in _pythonToSqliteMap:
        return _pythonToSqliteMap[pythonTypeName]
    # Compound types: list(...), dict(...), tuple(...), object(...), classreference(...), etc.
    if '(' in pythonTypeName:
        return 'TEXT'
    # Unknown types default to TEXT for safety
    return 'TEXT'