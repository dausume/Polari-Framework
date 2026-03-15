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

from concurrent.futures import ThreadPoolExecutor, as_completed

MAX_INHERITANCE_DEPTH = 10


class InheritanceCreationError(Exception):
    """Raised when one or more parent instance creations fail during orchestrated creation."""
    def __init__(self, errors):
        self.errors = errors  # dict of {parentClassName: exception}
        failed = ', '.join(f'{cls}: {err}' for cls, err in errors.items())
        super().__init__(f"Failed to create parent instances: {failed}")


class InheritanceDepthError(Exception):
    """Raised when inheritance chain exceeds MAX_INHERITANCE_DEPTH."""
    pass


def validateParentData(manager, className, parentData):
    """Pre-flight validation that all required parent data is present and params are valid.

    Args:
        manager: The managerObject hosting the type system.
        className: The multi-inheritance child class name.
        parentData: Dict of {parentClassName: {initParams}} for parents to create.

    Raises:
        ValueError: If parent data is missing or has invalid params.
    """
    typing = manager.objectTypingDict.get(className)
    if typing is None:
        raise ValueError(f"No typing found for class '{className}'")
    if not typing.isMultiInheritanceClass:
        return  # Nothing to validate

    for varName, parentClassName in typing.inheritsFrom.items():
        # Check if the parent data is provided OR if the child params include the var directly
        # (meaning the caller is passing an existing parent instance reference)
        if parentClassName not in parentData:
            raise ValueError(
                f"Missing parent data for '{parentClassName}' (variable '{varName}') "
                f"required by multi-inheritance class '{className}'. "
                f"Provide it in '_parentData' or pass an existing instance ID."
            )

        parentTyping = manager.objectTypingDict.get(parentClassName)
        if parentTyping is None:
            raise ValueError(
                f"Parent class '{parentClassName}' referenced by '{className}' "
                f"has no registered typing on the manager."
            )

        # Validate parent init params
        parentParams = parentData[parentClassName]
        if isinstance(parentParams, dict):
            for paramName in parentParams:
                if paramName == '_parentData':
                    continue  # Nested parent data for grandparent creation
                allParams = parentTyping.kwRequiredParams + parentTyping.kwDefaultParams
                if paramName not in allParams:
                    raise ValueError(
                        f"Invalid parameter '{paramName}' for parent class '{parentClassName}'. "
                        f"Valid params: {allParams}"
                    )


def _createSingleInstance(manager, className, params):
    """Create a single instance of a class using its registered create method.

    Args:
        manager: The managerObject.
        className: Class to instantiate.
        params: Dict of init keyword arguments.

    Returns:
        The created instance.
    """
    typing = manager.objectTypingDict[className]
    createMethod = typing.getCreateMethod(returnTupWithParams=True)
    instance = createMethod(**params, manager=manager)
    return instance


def _createParentsInParallel(manager, parentSpecs, depth):
    """Create parent instances in parallel threads.

    Args:
        manager: The managerObject.
        parentSpecs: Dict of {parentClassName: initParams}.
        depth: Current inheritance depth (for recursion limiting).

    Returns:
        Dict of {parentClassName: createdInstance}.

    Raises:
        InheritanceCreationError: If any parent creation fails (after rollback).
    """
    results = {}
    errors = {}

    maxWorkers = min(len(parentSpecs), 4)
    with ThreadPoolExecutor(max_workers=maxWorkers) as executor:
        futureToClass = {}
        for parentClassName, params in parentSpecs.items():
            future = executor.submit(
                createWithInheritance, manager, parentClassName, dict(params), depth=depth + 1
            )
            futureToClass[future] = parentClassName

        for future in as_completed(futureToClass):
            parentClassName = futureToClass[future]
            try:
                results[parentClassName] = future.result()
            except Exception as e:
                errors[parentClassName] = e

    if errors:
        # Rollback successfully created parents
        _rollbackCreatedInstances(manager, list(results.values()))
        raise InheritanceCreationError(errors)

    return results


def _rollbackCreatedInstances(manager, instances):
    """Remove instances from objectTables and DB on creation failure.

    Args:
        manager: The managerObject.
        instances: List of instances to roll back.
    """
    for inst in instances:
        className = inst.__class__.__name__
        instId = getattr(inst, 'id', None)
        # Remove from objectTables
        if className in manager.objectTables and instId is not None:
            manager.objectTables[className].pop(instId, None)
        # Remove from DB
        if hasattr(manager, 'db') and manager.db is not None and instId is not None:
            try:
                manager.db.deleteInstanceFromDB(inst)
            except Exception:
                pass  # Best-effort rollback


def createWithInheritance(manager, className, params, depth=0):
    """Orchestrated instance creation that handles multi-inheritance parent chains.

    If the class has _polariInheritsFrom, this function:
    1. Extracts _parentData from params
    2. Recursively creates all parent instances (in parallel)
    3. Assigns parent instances to the child's reference variables
    4. Creates the child instance

    For classes without inheritance, falls through to simple creation.

    Args:
        manager: The managerObject hosting the type system.
        className: The class name to instantiate.
        params: Dict of init keyword arguments. For multi-inheritance classes,
                should include '_parentData': {parentClassName: {initParams}}.
        depth: Current recursion depth (internal, for cycle protection).

    Returns:
        The created instance (with parent references set).

    Raises:
        InheritanceDepthError: If depth exceeds MAX_INHERITANCE_DEPTH.
        InheritanceCreationError: If parent creation fails.
        ValueError: If parent data is missing or invalid.
    """
    if depth > MAX_INHERITANCE_DEPTH:
        raise InheritanceDepthError(
            f"Exceeded max inheritance depth ({MAX_INHERITANCE_DEPTH}) "
            f"while creating '{className}'. Check for deep or circular inheritance."
        )

    typing = manager.objectTypingDict.get(className)
    if typing is None:
        raise ValueError(f"No typing found for class '{className}'")

    # Simple case: no inheritance, just create directly
    if not typing.isMultiInheritanceClass:
        return _createSingleInstance(manager, className, params)

    # Extract parent data from params
    parentData = params.pop('_parentData', {})

    # Check if any parent references are passed directly as existing instance IDs
    # in the main params (e.g. params = {'vehicle': 'existingVehicleId', ...})
    existingParentRefs = {}
    for varName, parentClassName in typing.inheritsFrom.items():
        if varName in params:
            refValue = params.pop(varName)
            # Look up existing instance by ID
            if isinstance(refValue, str):
                parentInstances = manager.objectTables.get(parentClassName, {})
                existingInst = parentInstances.get(refValue)
                if existingInst is not None:
                    existingParentRefs[varName] = existingInst
                else:
                    raise ValueError(
                        f"Existing parent instance '{refValue}' not found in "
                        f"{parentClassName} objectTables for variable '{varName}'"
                    )
            else:
                # Assume it's already an object reference
                existingParentRefs[varName] = refValue

    # Determine which parents still need to be created
    parentsToCreate = {}
    for varName, parentClassName in typing.inheritsFrom.items():
        if varName not in existingParentRefs:
            if parentClassName in parentData:
                parentsToCreate[parentClassName] = parentData[parentClassName]

    # Validate that all parents are accounted for
    for varName, parentClassName in typing.inheritsFrom.items():
        if varName not in existingParentRefs and parentClassName not in parentsToCreate:
            raise ValueError(
                f"No data provided for parent '{parentClassName}' (variable '{varName}') "
                f"of class '{className}'. Pass in '_parentData' or provide an existing instance ID."
            )

    # Create parents that need creating (in parallel if multiple)
    createdParents = {}  # parentClassName -> instance
    if parentsToCreate:
        createdParents = _createParentsInParallel(manager, parentsToCreate, depth)

    # Persist created parents to DB
    if createdParents and hasattr(manager, 'db') and manager.db is not None:
        for parentInst in createdParents.values():
            try:
                manager.db.saveInstanceInDB(parentInst)
            except Exception as e:
                print(f'[inheritanceOrchestrator] DB persist for parent {parentInst.__class__.__name__} failed: {e}')

    # Create the child instance with its own params (parent vars start as None)
    childInstance = _createSingleInstance(manager, className, params)

    # Assign parent instances to the child's reference variables.
    # Setting these attributes triggers __setattr__ on the treeObject,
    # which handles nesting the parent into the tree automatically.
    for varName, parentClassName in typing.inheritsFrom.items():
        if varName in existingParentRefs:
            setattr(childInstance, varName, existingParentRefs[varName])
        elif parentClassName in createdParents:
            setattr(childInstance, varName, createdParents[parentClassName])

    return childInstance
