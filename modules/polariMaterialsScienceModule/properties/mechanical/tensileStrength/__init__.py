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
Tensile Strength Module

Provides tensile strength-related models with a clear abstraction hierarchy:

Abstraction Levels (0 = most abstract, higher = more specific):
- Level 0: MaterialProperty (core reference)
  - MechanicalProperty (strength/resistance category)
    - Level 1: TensileStrength (abstract tensile strength concept)
    - Level 2: UltimateTensileStrength (derived/computed UTS in MPa)
    - Level 3: TensileMeasurement (raw UTM measurement datapoints)
"""

from polariMaterialsScienceModule.properties.mechanical.tensileStrength.tensileStrength import TensileStrength
from polariMaterialsScienceModule.properties.mechanical.tensileStrength.ultimateTensileStrength import UltimateTensileStrength
from polariMaterialsScienceModule.properties.mechanical.tensileStrength.tensileMeasurement import TensileMeasurement

__all__ = [
    'TensileStrength',
    'UltimateTensileStrength',
    'TensileMeasurement'
]
