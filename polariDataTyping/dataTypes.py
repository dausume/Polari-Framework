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