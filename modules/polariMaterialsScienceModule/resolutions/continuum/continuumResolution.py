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
ContinuumResolution Model

Level 1 resolution category for Finite Element Methods (FEM).
This level represents materials as continuous media suitable for
structural and thermal simulations.

FEM materials are derived from experimental data and can be:
- Consistent: Same properties across all elements
- Stochastic: Spatially varying properties
- Chosen: Selected from available options
- Range: Bounded by upper/lower limits

FEM is finer than experimental because it requires more detailed
characterization of material behavior under various conditions.
"""

from objectTreeDecorators import treeObjectInit
from polariMaterialsScienceModule.resolutions.resolutionCategory import ResolutionCategory


class ContinuumResolution(ResolutionCategory):
    """
    Continuum resolution category (Level 1).

    Represents materials suitable for Finite Element Method simulations.
    The material is treated as a continuous medium with bulk properties.

    Resolution level: 1

    Attributes:
        materialId: ID reference to the parent Material
    """

    RESOLUTION_LEVEL = 1
    RESOLUTION_CATEGORY = 'continuum'

    @treeObjectInit
    def __init__(self,
                 manager=None,
                 branch=None,
                 id=None,
                 materialId='',
                 name='Continuum Resolution',
                 description='Finite Element Method material definition',
                 categoryDescription='Continuum mechanics representation for FEM simulations'):
        ResolutionCategory.__init__(self, manager=manager, branch=branch, id=id,
                                    materialId=materialId,
                                    name=name, description=description,
                                    categoryDescription=categoryDescription,
                                    scaleRange='µm-mm',
                                    typicalMethods='FEM, FEA, structural analysis')
        self.resolutionLevel = self.RESOLUTION_LEVEL
        self.resolutionCategory = self.RESOLUTION_CATEGORY

    def __repr__(self):
        return f"ContinuumResolution(id='{self.id}', materialId='{self.materialId}')"
