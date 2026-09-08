"""
AgroForestry Module

Auto-generated Polari module.
"""

from agro_forestry.plant_basis import Plant
from agro_forestry.gardenBoundaryPost_basis import GardenBoundaryPost
from agro_forestry.gardenBoundary_basis import GardenBoundary

from agro_forestry.custom.registerAgroForestryModule import register_agro_forestry_defaults
from agro_forestry.agro_forestry_data_seed import seed_initial_data


def initialize(manager=None, include_seed_data=False):
    """Initialize the AgroForestry module.

    Args:
        manager: The object tree manager to register with.
        include_seed_data: If True, load initial data.

    Returns:
        dict: {'registered_classes': dict, 'seed_data': dict}
    """
    registered_classes = register_agro_forestry_defaults(manager)

    result = {
        'registered_classes': registered_classes,
        'seed_data': {}
    }

    if include_seed_data:
        result['seed_data'] = seed_initial_data(manager)

    return result


__all__ = [
    'Plant',
    'GardenBoundaryPost',
    'GardenBoundary',
    'initialize',
    'register_agro_forestry_defaults',
    'seed_initial_data',
]
