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
FieldDisplay for Polari No-Code System

Defines how fields are displayed in the state UI of the no-code visual programming interface.
"""


class FieldDisplay:
    """
    Defines how a field is displayed in the state UI.

    Attributes:
        field_name: The name of the field on the source class
        display_name: Human-readable name shown in the UI
        visible: Whether the field is visible in the state
        row: Row position in the state display
        editable: Whether the field can be edited in the UI
        field_type: Type of input control ('text', 'number', 'boolean', 'select', etc.)
    """
    def __init__(
        self,
        field_name: str,
        display_name: str = '',
        visible: bool = True,
        row: int = 0,
        editable: bool = False,
        field_type: str = 'text'
    ):
        self.field_name = field_name
        self.display_name = display_name or field_name
        self.visible = visible
        self.row = row
        self.editable = editable
        self.field_type = field_type

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            'fieldName': self.field_name,
            'displayName': self.display_name,
            'visible': self.visible,
            'row': self.row,
            'editable': self.editable,
            'fieldType': self.field_type
        }

    @classmethod
    def from_dict(cls, data: dict) -> 'FieldDisplay':
        """Create a FieldDisplay from a dictionary."""
        return cls(
            field_name=data.get('fieldName', ''),
            display_name=data.get('displayName', ''),
            visible=data.get('visible', True),
            row=data.get('row', 0),
            editable=data.get('editable', False),
            field_type=data.get('fieldType', 'text')
        )
