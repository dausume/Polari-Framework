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
StateBuildingBlock Module for Polari No-Code System

Components:
- CodeTemplate: Code template for a specific runtime
- StateBuildingBlock: Defines a building block with code templates
- StateBuildingBlockRegistry: Singleton registry for all building blocks
"""

from polariNoCode.StateBuildingBlock.StateBuildingBlock import (
    CodeTemplate,
    StateBuildingBlock,
    StateBuildingBlockRegistry,
)

__all__ = [
    'CodeTemplate',
    'StateBuildingBlock',
    'StateBuildingBlockRegistry',
]
