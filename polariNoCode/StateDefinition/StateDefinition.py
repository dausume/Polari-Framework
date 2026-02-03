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
StateDefinition Model for Polari No-Code System

A StateDefinition is a template that defines how a polyTypedObject class
can be used as a state in the no-code visual programming interface.

A single class may have multiple StateDefinitions, each representing a different
way the class can be used as a state (e.g., different events, different field displays).

Related modules:
- polariNoCode.stateSpaceDecorators: Decorators for marking methods as state-space events
- polariApiServer.stateSpaceAPI: REST API endpoints for state-space functionality

Example:
    An "Order" class might have StateDefinitions for:
    - "Process Order" (using the process_order event)
    - "Cancel Order" (using the cancel_order event)
    - "View Order Details" (display-only, no event)
"""

from objectTreeDecorators import treeObject, treeObjectInit
from typing import List
from polariNoCode.StateDefinition.SlotDefinition import SlotDefinition
from polariNoCode.StateDefinition.FieldDisplay import FieldDisplay


class StateDefinition(treeObject):
    """
    A StateDefinition defines how a class can be used as a state in the no-code interface.

    Attributes:
        name: Unique name for this state definition
        display_name: Human-readable name shown in the UI
        source_class_name: The polyTypedObject class this definition is for
        event_method_name: The @stateSpaceEvent method to use (optional)
        input_slots: List of SlotDefinition for inputs
        output_slots: List of SlotDefinition for outputs
        display_fields: List of FieldDisplay for field configuration
        fields_per_row: Number of fields per row (1 or 2)
        description: Description of what this state does
        category: Category for grouping in the UI
        icon: Icon name or path for the state
        color: Color for the state in the UI
    """

    @treeObjectInit
    def __init__(
        self,
        name: str = '',
        display_name: str = '',
        source_class_name: str = '',
        event_method_name: str = '',
        input_slots: List[dict] = None,
        output_slots: List[dict] = None,
        display_fields: List[dict] = None,
        fields_per_row: int = 1,
        description: str = '',
        category: str = 'General',
        icon: str = '',
        color: str = '#3f51b5',
        manager=None,
        **kwargs
    ):
        self.name = name
        self.display_name = display_name or name
        self.source_class_name = source_class_name
        self.event_method_name = event_method_name
        self.description = description
        self.category = category
        self.icon = icon
        self.color = color
        self.fields_per_row = max(1, min(2, fields_per_row))

        # Convert slot dictionaries to SlotDefinition objects
        self.input_slots = [
            SlotDefinition.from_dict(s) if isinstance(s, dict) else s
            for s in (input_slots or [])
        ]
        self.output_slots = [
            SlotDefinition.from_dict(s) if isinstance(s, dict) else s
            for s in (output_slots or [])
        ]

        # Convert field display dictionaries to FieldDisplay objects
        self.display_fields = [
            FieldDisplay.from_dict(f) if isinstance(f, dict) else f
            for f in (display_fields or [])
        ]

    def add_input_slot(self, slot: SlotDefinition) -> None:
        """Add an input slot to this state definition."""
        self.input_slots.append(slot)

    def add_output_slot(self, slot: SlotDefinition) -> None:
        """Add an output slot to this state definition."""
        self.output_slots.append(slot)

    def add_display_field(self, field: FieldDisplay) -> None:
        """Add a display field to this state definition."""
        self.display_fields.append(field)

    def set_fields_per_row(self, count: int) -> None:
        """Set the number of fields per row (1 or 2)."""
        self.fields_per_row = max(1, min(2, count))

    def generate_slots_from_event(self, poly_typed_object) -> None:
        """
        Auto-generate input/output slots from the specified event method.

        Args:
            poly_typed_object: The polyTypedObject to get event metadata from
        """
        if not self.event_method_name or not poly_typed_object:
            return

        # Find the event method metadata
        for event in poly_typed_object.stateSpaceEventMethods:
            if event.get('method_name') == self.event_method_name:
                # Generate input slots from parameters
                for param in event.get('input_params', []):
                    slot = SlotDefinition(
                        name=param['name'],
                        display_name=param.get('display_name', param['name']),
                        slot_type='input',
                        data_type=param.get('type', 'any'),
                        is_required=param.get('is_required', True),
                        default_value=param.get('default_value')
                    )
                    self.input_slots.append(slot)

                # Generate output slot from return type
                output_info = event.get('output', {})
                output_slot = SlotDefinition(
                    name='output',
                    display_name=output_info.get('display_name', 'Output'),
                    slot_type='output',
                    data_type=output_info.get('type', 'any'),
                    is_required=False
                )
                self.output_slots.append(output_slot)
                break

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            'id': self.id if hasattr(self, 'id') else None,
            'name': self.name,
            'displayName': self.display_name,
            'sourceClassName': self.source_class_name,
            'eventMethodName': self.event_method_name,
            'inputSlots': [s.to_dict() for s in self.input_slots],
            'outputSlots': [s.to_dict() for s in self.output_slots],
            'displayFields': [f.to_dict() for f in self.display_fields],
            'fieldsPerRow': self.fields_per_row,
            'description': self.description,
            'category': self.category,
            'icon': self.icon,
            'color': self.color
        }

    @classmethod
    def from_dict(cls, data: dict, manager=None) -> 'StateDefinition':
        """Create a StateDefinition from a dictionary."""
        return cls(
            name=data.get('name', ''),
            display_name=data.get('displayName', ''),
            source_class_name=data.get('sourceClassName', ''),
            event_method_name=data.get('eventMethodName', ''),
            input_slots=data.get('inputSlots', []),
            output_slots=data.get('outputSlots', []),
            display_fields=data.get('displayFields', []),
            fields_per_row=data.get('fieldsPerRow', 1),
            description=data.get('description', ''),
            category=data.get('category', 'General'),
            icon=data.get('icon', ''),
            color=data.get('color', '#3f51b5'),
            manager=manager
        )

    def validate(self) -> tuple:
        """
        Validate this state definition.

        Returns:
            Tuple of (is_valid: bool, errors: list)
        """
        errors = []

        if not self.name:
            errors.append("State definition name is required")

        if not self.source_class_name:
            errors.append("Source class name is required")

        # Validate slot names are unique
        input_names = [s.name for s in self.input_slots]
        output_names = [s.name for s in self.output_slots]

        if len(input_names) != len(set(input_names)):
            errors.append("Input slot names must be unique")

        if len(output_names) != len(set(output_names)):
            errors.append("Output slot names must be unique")

        return (len(errors) == 0, errors)


def create_state_definition_from_event(
    poly_typed_object,
    event_method_name: str,
    name: str = '',
    display_name: str = '',
    manager=None
) -> StateDefinition:
    """
    Helper function to create a StateDefinition from a @stateSpaceEvent method.

    Args:
        poly_typed_object: The polyTypedObject containing the event
        event_method_name: Name of the @stateSpaceEvent method
        name: Name for the state definition (defaults to event display name)
        display_name: Display name (defaults to event display name)
        manager: Manager object for tree registration

    Returns:
        A new StateDefinition configured for the event
    """
    # Find the event metadata
    event_metadata = None
    for event in poly_typed_object.stateSpaceEventMethods:
        if event.get('method_name') == event_method_name:
            event_metadata = event
            break

    if not event_metadata:
        raise ValueError(f"Event method '{event_method_name}' not found on {poly_typed_object.className}")

    # Create the state definition
    state_def = StateDefinition(
        name=name or event_metadata.get('display_name', event_method_name),
        display_name=display_name or event_metadata.get('display_name', event_method_name),
        source_class_name=poly_typed_object.className,
        event_method_name=event_method_name,
        description=event_metadata.get('description', ''),
        category=event_metadata.get('category', 'General'),
        manager=manager
    )

    # Generate slots from event
    state_def.generate_slots_from_event(poly_typed_object)

    return state_def
