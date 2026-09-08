"""
Registration for AgroForestry module.

Registers all module classes with the Polari object tree manager.
"""


def register_agro_forestry_defaults(manager=None):
    """Register AgroForestry module classes with the given manager.

    Args:
        manager: The object tree manager to register with.

    Returns:
        dict: Mapping of class name to class object.
    """
    from agro_forestry.plant_basis import Plant
    from agro_forestry.gardenBoundaryPost_basis import GardenBoundaryPost
    from agro_forestry.gardenBoundary_basis import GardenBoundary

    registered_classes = {
        'Plant': Plant,
        'GardenBoundaryPost': GardenBoundaryPost,
        'GardenBoundary': GardenBoundary,
    }

    if manager is not None:
        for class_name, class_obj in registered_classes.items():
            existing = manager.objectTypingDict.get(class_name)
            if existing is not None:
                # Class already registered — ensure moduleBinding is set
                existing.moduleBinding = 'agro_forestry'
                continue
            typing_obj = manager.makeDefaultObjectTyping(classObj=class_obj)
            if typing_obj is not None:
                typing_obj.excludeFromCRUDE = False
                typing_obj.moduleBinding = 'agro_forestry'
                typing_obj.initializeVarsFromSignature()

    # Semantic type overrides (types that can't be inferred from defaults)
    # initializeVarsFromSignature infers 'str' from string defaults like '[]' and '{}'.
    # These overrides restore the correct semantic types.
    _FIELD_TYPE_OVERRIDES = [
        ('GardenBoundaryPost', 'boundaryPost', 'map_coordinate'),
        ('GardenBoundary', 'bounds', 'map_polygon'),
    ]
    for _cls_name, _field_name, _field_type in _FIELD_TYPE_OVERRIDES:
        _typing = manager.objectTypingDict.get(_cls_name)
        if _typing and hasattr(_typing, 'polyTypedVarsDict'):
            _var = _typing.polyTypedVarsDict.get(_field_name)
            if _var:
                _var.pythonTypeDefault = _field_type

    return registered_classes
