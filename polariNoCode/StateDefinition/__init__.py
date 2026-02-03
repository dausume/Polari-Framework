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
StateDefinition Module for Polari No-Code System

This module provides the core models for defining how classes appear as states
in the no-code visual programming interface.

Components:
- StateDefinition: Main class defining how a polyTypedObject appears as a state
- SlotDefinition: Defines input/output connection points on states
- FieldDisplay: Defines how fields are displayed in the state UI
"""

from polariNoCode.StateDefinition.SlotDefinition import SlotDefinition
from polariNoCode.StateDefinition.FieldDisplay import FieldDisplay
from polariNoCode.StateDefinition.StateDefinition import (
    StateDefinition,
    create_state_definition_from_event
)

__all__ = [
    'StateDefinition',
    'SlotDefinition',
    'FieldDisplay',
    'create_state_definition_from_event',
]
