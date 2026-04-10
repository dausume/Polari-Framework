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
Solid Surface Energy Module

Provides surface energy-related models with a clear abstraction hierarchy:

Abstraction Levels (0 = most abstract, higher = more specific):
- Level 0: MaterialProperty (core reference)
  - SurfaceProperty (interfacial phenomena category)
    - Level 1: SolidSurfaceEnergy (abstract surface energy concept)
    - Level 2: CriticalSurfaceTension (derived/computed value in mN/m)
    - Level 3: ContactAngleMeasurement (raw goniometer measurement datapoints)
"""

from polariMaterialsScienceModule.properties.surface.solidSurfaceEnergy.solidSurfaceEnergy import SolidSurfaceEnergy
from polariMaterialsScienceModule.properties.surface.solidSurfaceEnergy.criticalSurfaceTension import CriticalSurfaceTension
from polariMaterialsScienceModule.properties.surface.solidSurfaceEnergy.contactAngleMeasurement import ContactAngleMeasurement

__all__ = [
    'SolidSurfaceEnergy',
    'CriticalSurfaceTension',
    'ContactAngleMeasurement'
]
