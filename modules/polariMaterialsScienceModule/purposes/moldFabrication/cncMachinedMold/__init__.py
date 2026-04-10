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
CNC Machined Mold Materials Module

Defines composite material suitability for CNC machining fine-resolution molds.
"""

from polariMaterialsScienceModule.purposes.moldFabrication.cncMachinedMold.cncMachinedMoldMaterial import CNCMachinedMoldMaterial
from polariMaterialsScienceModule.purposes.moldFabrication.cncMachinedMold.milledMoldMaterial import MilledMoldMaterial
from polariMaterialsScienceModule.purposes.moldFabrication.cncMachinedMold.turnedMoldMaterial import TurnedMoldMaterial

__all__ = [
    'CNCMachinedMoldMaterial',
    'MilledMoldMaterial',
    'TurnedMoldMaterial'
]
