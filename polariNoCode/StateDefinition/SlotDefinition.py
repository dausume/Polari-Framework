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
SlotDefinition for Polari No-Code System

Defines input/output slots for states in the no-code visual programming interface.
Slots are connection points that allow data flow between states.
"""

from typing import Any


class SlotDefinition:
    """
    Defines an input or output slot for a state in the no-code interface.

    Slots are connection points on states that allow data flow between states.

    Attributes:
        name: Internal name for the slot
        display_name: Human-readable name shown in the UI
        slot_type: Either 'input' or 'output'
        data_type: Type hint string (e.g., 'str', 'int', 'dict', 'any')
        is_required: Whether this slot must be connected
        default_value: Default value if not connected
        description: Description of the slot's purpose
    """
    def __init__(
        self,
        name: str,
        display_name: str,
        slot_type: str,  # 'input' or 'output'
        data_type: str = 'any',
        is_required: bool = True,
        default_value: Any = None,
        description: str = ''
    ):
        self.name = name
        self.display_name = display_name
        self.slot_type = slot_type
        self.data_type = data_type
        self.is_required = is_required
        self.default_value = default_value
        self.description = description

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            'name': self.name,
            'displayName': self.display_name,
            'slotType': self.slot_type,
            'dataType': self.data_type,
            'isRequired': self.is_required,
            'defaultValue': self.default_value,
            'description': self.description
        }

    @classmethod
    def from_dict(cls, data: dict) -> 'SlotDefinition':
        """Create a SlotDefinition from a dictionary."""
        return cls(
            name=data.get('name', ''),
            display_name=data.get('displayName', ''),
            slot_type=data.get('slotType', 'input'),
            data_type=data.get('dataType', 'any'),
            is_required=data.get('isRequired', True),
            default_value=data.get('defaultValue'),
            description=data.get('description', '')
        )
