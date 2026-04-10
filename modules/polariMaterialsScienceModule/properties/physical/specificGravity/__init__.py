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
Specific Gravity Module

Provides specific gravity-related models with a clear abstraction hierarchy:

Abstraction Levels:
- Level 1: SpecificGravity (abstract specific gravity concept, inherits MaterialProperty)
- Level 2: ReferentialSpecificGravity (derived value normalized against reference material)
- Level 3: Raw measurements:
  - PycnometerMeasurement (weighing known volume flask)
  - HydrometerMeasurement (floating instrument direct reading)
  - DensityMeterMeasurement (oscillating tube digital measurement)

Specific gravity is the ratio of a substance's density to a reference substance
(typically water at 4°C for liquids/solids, or air for gases).
"""

from polariMaterialsScienceModule.properties.physical.specificGravity.specificGravity import SpecificGravity
from polariMaterialsScienceModule.properties.physical.specificGravity.referentialSpecificGravity import ReferentialSpecificGravity
from polariMaterialsScienceModule.properties.physical.specificGravity.pycnometerMeasurement import PycnometerMeasurement
from polariMaterialsScienceModule.properties.physical.specificGravity.hydrometerMeasurement import HydrometerMeasurement
from polariMaterialsScienceModule.properties.physical.specificGravity.densityMeterMeasurement import DensityMeterMeasurement

__all__ = [
    'SpecificGravity',
    'ReferentialSpecificGravity',
    'PycnometerMeasurement',
    'HydrometerMeasurement',
    'DensityMeterMeasurement'
]
