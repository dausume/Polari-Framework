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
    from polariAgroForestryModule.plant import Plant
    from polariAgroForestryModule.gardenBoundaryPost import GardenBoundaryPost

    registered_classes = {
        'Plant': Plant,
        'GardenBoundaryPost': GardenBoundaryPost,
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

    return registered_classes
