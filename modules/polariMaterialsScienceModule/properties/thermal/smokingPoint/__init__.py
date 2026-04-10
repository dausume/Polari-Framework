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
Smoking Point Module

Provides smoking point-related models with a clear abstraction hierarchy:

Abstraction Levels (0 = most abstract, higher = more specific):
- Level 0: MaterialProperty (core reference)
  - ThermalProperty (temperature-dependent category)
    - Level 1: SmokingPoint (abstract smoking point concept)
    - Level 2: SmokingPointValue (derived/computed value in Celsius)
    - Level 3: SmokingPointMeasurement (raw visual/automated datapoints)
"""

from polariMaterialsScienceModule.properties.thermal.smokingPoint.smokingPoint import SmokingPoint
from polariMaterialsScienceModule.properties.thermal.smokingPoint.smokingPointValue import SmokingPointValue
from polariMaterialsScienceModule.properties.thermal.smokingPoint.smokingPointMeasurement import SmokingPointMeasurement

__all__ = [
    'SmokingPoint',
    'SmokingPointValue',
    'SmokingPointMeasurement'
]
