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
Melting Point Module

Provides melting point-related models with a clear abstraction hierarchy:

Abstraction Levels (0 = most abstract, higher = more specific):
- Level 0: MaterialProperty (core reference)
  - ThermalProperty (temperature-dependent category)
    - Level 1: MeltingPoint (abstract melting point concept)
    - Level 2: MeltingPointValue (derived/computed value in Celsius)
    - Level 3: DSCMeltingMeasurement (raw DSC measurement datapoints)
"""

from polariMaterialsScienceModule.properties.thermal.meltingPoint.meltingPoint import MeltingPoint
from polariMaterialsScienceModule.properties.thermal.meltingPoint.meltingPointValue import MeltingPointValue
from polariMaterialsScienceModule.properties.thermal.meltingPoint.dscMeltingMeasurement import DSCMeltingMeasurement

__all__ = [
    'MeltingPoint',
    'MeltingPointValue',
    'DSCMeltingMeasurement'
]
