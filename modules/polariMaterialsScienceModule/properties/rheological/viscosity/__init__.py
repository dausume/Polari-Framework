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
Viscosity Module

Provides viscosity-related models with a clear abstraction hierarchy:

Abstraction Levels (0 = most abstract, higher = more specific):
- Level 0: MaterialProperty (core reference)
  - RheologicalProperty (flow/deformation category)
    - Level 1: Viscosity (abstract viscosity concept)
    - Level 2: KrebsViscosity (derived/computed viscosity in Krebs Units)
    - Level 3: StormerViscosity (raw Stormer viscometer measurement datapoints)
"""

from polariMaterialsScienceModule.properties.rheological.viscosity.viscosity import Viscosity
from polariMaterialsScienceModule.properties.rheological.viscosity.krebsViscosity import KrebsViscosity
from polariMaterialsScienceModule.properties.rheological.viscosity.stormerViscosity import StormerViscosity

__all__ = [
    'Viscosity',
    'KrebsViscosity',
    'StormerViscosity'
]
