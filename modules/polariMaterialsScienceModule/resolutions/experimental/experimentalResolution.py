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
ExperimentalResolution Model

Level 0 resolution category for real-world experimental measurements.
This is the foundational level where material data comes from physical
experiments performed at human scale.

This resolution includes:
- RawExperimentalMaterial: Direct measurement data from lab tests
- RulesOfMixturesExperimentalMaterial: Predicted composite behavior

Experimental data at this level can be translated to higher resolution
simulation formats (FEM, CGMD, MD, DFT) for computational modeling.
"""

from objectTreeDecorators import treeObjectInit
from polariMaterialsScienceModule.resolutions.resolutionCategory import ResolutionCategory


class ExperimentalResolution(ResolutionCategory):
    """
    Experimental resolution category (Level 0).

    Represents real-world experimental measurements at human scale.
    This is the coarsest resolution level, directly measurable in a lab.

    Resolution level: 0

    Attributes:
        materialId: ID reference to the parent Material
    """

    RESOLUTION_LEVEL = 0
    RESOLUTION_CATEGORY = 'experimental'

    @treeObjectInit
    def __init__(self,
                 manager=None,
                 branch=None,
                 id=None,
                 materialId='',
                 name='Experimental Resolution',
                 description='Real-world experimental measurement data',
                 categoryDescription='Human-scale experimental measurements from laboratory tests'):
        ResolutionCategory.__init__(self, manager=manager, branch=branch, id=id,
                                    materialId=materialId,
                                    name=name, description=description,
                                    categoryDescription=categoryDescription,
                                    scaleRange='mm-m',
                                    typicalMethods='Physical testing, ASTM/ISO standards')
        self.resolutionLevel = self.RESOLUTION_LEVEL
        self.resolutionCategory = self.RESOLUTION_CATEGORY

    def __repr__(self):
        return f"ExperimentalResolution(id='{self.id}', materialId='{self.materialId}')"
