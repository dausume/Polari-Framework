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
Hardness Module

Provides hardness-related models with a clear abstraction hierarchy:

Abstraction Levels (0 = most abstract, higher = more specific):
- Level 0: MaterialProperty (core reference)
  - MechanicalProperty (strength/resistance category)
    - Level 1: Hardness (abstract hardness concept)
    - Level 2: HardnessScale (derived/standard value on specific scale)
    - Level 3: ShoreMeasurement (raw durometer measurement datapoints)
"""

from polariMaterialsScienceModule.properties.mechanical.hardness.hardness import Hardness
from polariMaterialsScienceModule.properties.mechanical.hardness.hardnessScale import HardnessScale
from polariMaterialsScienceModule.properties.mechanical.hardness.shoreMeasurement import ShoreMeasurement

__all__ = [
    'Hardness',
    'HardnessScale',
    'ShoreMeasurement'
]
