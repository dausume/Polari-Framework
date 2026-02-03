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
Polari No-Code System

This module provides the core functionality for the Polari no-code visual programming system.

Components:
- stateSpaceDecorators: Decorators for marking methods as state-space events
- stateDefinition: StateDefinition model for defining how classes appear as states

API Endpoints (located in polariApiServer/stateSpaceAPI.py):
- GET /stateSpaceClasses - List all state-space enabled classes
- GET /stateSpaceConfig/{className} - Get state-space config for a class
- PUT /stateSpaceConfig/{className} - Update state-space config for a class
- GET /stateDefinitions - List all state definitions
- POST /stateDefinitions - Create a new state definition

Usage:
    from polariNoCode import stateSpaceEvent, StateDefinition
    from polariNoCode import SlotDefinition, FieldDisplay

    # Mark a method as a state-space event
    @stateSpaceEvent(
        display_name="Process Order",
        description="Validates and processes an incoming order"
    )
    def process_order(self, order_data: dict) -> dict:
        ...

    # Create a state definition
    state_def = StateDefinition(
        name="ProcessOrder",
        source_class_name="OrderProcessor",
        event_method_name="process_order"
    )
"""

# State-space decorators
from polariNoCode.stateSpaceDecorators import (
    stateSpaceEvent,
    get_state_space_events,
    register_state_space_class,
    get_all_state_space_classes,
    is_state_space_event,
    get_event_metadata,
    STATE_SPACE_EVENT_REGISTRY
)

# State definition models
from polariNoCode.StateDefinition import (
    StateDefinition,
    SlotDefinition,
    FieldDisplay,
    create_state_definition_from_event
)

__all__ = [
    # Decorators
    'stateSpaceEvent',
    'get_state_space_events',
    'register_state_space_class',
    'get_all_state_space_classes',
    'is_state_space_event',
    'get_event_metadata',
    'STATE_SPACE_EVENT_REGISTRY',
    # Models
    'StateDefinition',
    'SlotDefinition',
    'FieldDisplay',
    'create_state_definition_from_event',
]
