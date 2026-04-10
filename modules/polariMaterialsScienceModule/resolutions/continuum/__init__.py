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
Continuum Resolution Module

Level 1 - Finite Element Methods scale.

Resolution Types:
- ConsistentFiniteElementMaterial: Consistent properties per unit/conditions
- StochasticFiniteElementMaterial: Partially randomized property distributions
- ChosenMaterial: Selected from known properties/conditions
- RangeMaterial: Lower, average, upper bound representations
"""

from polariMaterialsScienceModule.resolutions.continuum.continuumResolution import ContinuumResolution
from polariMaterialsScienceModule.resolutions.continuum.consistentFiniteElementMaterial import ConsistentFiniteElementMaterial
from polariMaterialsScienceModule.resolutions.continuum.stochasticFiniteElementMaterial import StochasticFiniteElementMaterial
from polariMaterialsScienceModule.resolutions.continuum.chosenMaterial import ChosenMaterial
from polariMaterialsScienceModule.resolutions.continuum.rangeMaterial import RangeMaterial

__all__ = [
    'ContinuumResolution',
    'ConsistentFiniteElementMaterial',
    'StochasticFiniteElementMaterial',
    'ChosenMaterial',
    'RangeMaterial'
]
