standardTypesPython = ['str','int','float','complex','list','tuple','range','dict',
'set','frozenset','bool','bytes','bytearray','memoryview', 'type', 'NoneType', 'TextIOWrapper']
ignoredObjectsPython = ['struct_time', 'API', 'App', 'polariList']
ignoredObjectImports = {'falcon':['API', 'App'], 'time':['struct_time']}
dataTypesPython = standardTypesPython + ignoredObjectsPython
dataTypesJS = ['undefined','Boolean','Number','String','BigInt','Symbol','null','Object','Function']
dataTypesJSON = ['String','Number','Object','Array','Boolean','null']
dataAffinitiesSqlite = ['NONE','INTEGER','REAL','TEXT','NUMERIC']