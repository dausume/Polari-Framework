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

"""
State-Space Decorators for Polari No-Code System

This module provides decorators for marking class methods as state-space events
that can be used in the no-code visual programming interface.

A state-space event is a method that:
- Takes defined input parameters (which become input slots)
- Returns a defined output (which becomes output slots)
- Can be visually connected in the no-code editor

Related modules:
- polariNoCode.stateDefinition: StateDefinition model for defining how classes appear as states
- polariApiServer.stateSpaceAPI: REST API endpoints for state-space functionality

Usage:
    from polariNoCode.stateSpaceDecorators import stateSpaceEvent

    class OrderProcessor:
        @stateSpaceEvent(
            display_name="Process Order",
            description="Validates and processes an incoming order",
            input_slot_names={"order_data": "Order Input", "user_id": "User ID"},
            output_slot_name="Processed Order"
        )
        def process_order(self, order_data: dict, user_id: str) -> dict:
            # Process the order
            return {"status": "processed", "order_id": "123"}
"""

from functools import wraps
import inspect
from typing import Any, Dict, Optional, Callable, get_type_hints


# Registry to track all state-space events by class
STATE_SPACE_EVENT_REGISTRY: Dict[str, list] = {}


def stateSpaceEvent(
    display_name: Optional[str] = None,
    description: Optional[str] = None,
    input_slot_names: Optional[Dict[str, str]] = None,
    output_slot_name: Optional[str] = None,
    category: Optional[str] = None
):
    """
    Decorator to mark a method as a state-space event.

    State-space events can be used in the no-code visual programming interface.
    The decorator extracts input/output information from the method signature
    and type hints.

    Args:
        display_name: Human-readable name for the event (defaults to method name)
        description: Description of what the event does
        input_slot_names: Dict mapping parameter names to display names for input slots
        output_slot_name: Display name for the output slot
        category: Category for grouping events in the UI

    Returns:
        Decorated function with state-space metadata attached

    Example:
        @stateSpaceEvent(
            display_name="Calculate Total",
            description="Calculates the total price including tax",
            input_slot_names={"items": "Item List", "tax_rate": "Tax Rate"},
            output_slot_name="Total Price"
        )
        def calculate_total(self, items: list, tax_rate: float = 0.08) -> float:
            subtotal = sum(item['price'] for item in items)
            return subtotal * (1 + tax_rate)
    """
    def decorator(func: Callable) -> Callable:
        # Mark the function as a state-space event
        func._is_state_space_event = True

        # Get method signature for parameter analysis
        sig = inspect.signature(func)
        params = sig.parameters

        # Try to get type hints (may fail for some methods)
        try:
            hints = get_type_hints(func)
        except Exception:
            hints = {}

        # Extract input parameters (excluding 'self')
        input_params = []
        for param_name, param in params.items():
            if param_name == 'self':
                continue

            param_info = {
                'name': param_name,
                'display_name': (input_slot_names or {}).get(param_name, param_name),
                'type': hints.get(param_name, Any).__name__ if hasattr(hints.get(param_name, Any), '__name__') else str(hints.get(param_name, 'Any')),
                'has_default': param.default is not inspect.Parameter.empty,
                'default_value': param.default if param.default is not inspect.Parameter.empty else None,
                'is_required': param.default is inspect.Parameter.empty
            }
            input_params.append(param_info)

        # Extract return type
        return_type = hints.get('return', Any)
        return_type_name = return_type.__name__ if hasattr(return_type, '__name__') else str(return_type)

        # Store metadata on the function
        func._state_space_metadata = {
            'method_name': func.__name__,
            'display_name': display_name or func.__name__.replace('_', ' ').title(),
            'description': description or func.__doc__ or '',
            'category': category or 'General',
            'input_params': input_params,
            'output': {
                'type': return_type_name,
                'display_name': output_slot_name or 'Output'
            }
        }

        @wraps(func)
        def wrapper(*args, **kwargs):
            return func(*args, **kwargs)

        # Copy metadata to wrapper
        wrapper._is_state_space_event = True
        wrapper._state_space_metadata = func._state_space_metadata

        return wrapper

    return decorator


def get_state_space_events(cls) -> list:
    """
    Get all state-space events defined on a class.

    Args:
        cls: The class to inspect

    Returns:
        List of state-space event metadata dictionaries
    """
    events = []

    for name in dir(cls):
        try:
            attr = getattr(cls, name)
            if callable(attr) and hasattr(attr, '_is_state_space_event') and attr._is_state_space_event:
                metadata = getattr(attr, '_state_space_metadata', {})
                metadata['method_name'] = name
                events.append(metadata)
        except Exception:
            continue

    return events


def register_state_space_class(cls):
    """
    Class decorator to register a class as having state-space events.

    This decorator scans the class for @stateSpaceEvent decorated methods
    and registers them in the global registry.

    Usage:
        @register_state_space_class
        class OrderProcessor:
            @stateSpaceEvent(...)
            def process_order(self, ...):
                ...
    """
    class_name = cls.__name__
    events = get_state_space_events(cls)

    if events:
        STATE_SPACE_EVENT_REGISTRY[class_name] = events
        cls._state_space_events = events

    return cls


def get_all_state_space_classes() -> Dict[str, list]:
    """
    Get all registered state-space classes and their events.

    Returns:
        Dictionary mapping class names to their state-space events
    """
    return STATE_SPACE_EVENT_REGISTRY.copy()


def is_state_space_event(method) -> bool:
    """
    Check if a method is marked as a state-space event.

    Args:
        method: The method to check

    Returns:
        True if the method is a state-space event
    """
    return getattr(method, '_is_state_space_event', False)


def get_event_metadata(method) -> Optional[dict]:
    """
    Get the state-space metadata for a method.

    Args:
        method: The method to get metadata for

    Returns:
        Metadata dictionary or None if not a state-space event
    """
    if not is_state_space_event(method):
        return None
    return getattr(method, '_state_space_metadata', None)
