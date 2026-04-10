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
QuantumResolution Model

Level 4 resolution category for Density Functional Theory (DFT).
This is the finest resolution level, treating electrons explicitly
using quantum mechanics.

DFT provides:
- Electronic structure
- Accurate energetics
- Chemical bonding
- Spectroscopic properties
"""

from objectTreeDecorators import treeObjectInit
from polariMaterialsScienceModule.resolutions.resolutionCategory import ResolutionCategory


class QuantumResolution(ResolutionCategory):
    """
    Quantum resolution category (Level 4).

    Represents materials using density functional theory with
    explicit treatment of electrons.

    Resolution level: 4

    Attributes:
        materialId: ID reference to the parent Material
    """

    RESOLUTION_LEVEL = 4
    RESOLUTION_CATEGORY = 'quantum'

    @treeObjectInit
    def __init__(self,
                 manager=None,
                 branch=None,
                 id=None,
                 materialId='',
                 name='Quantum Resolution',
                 description='Density functional theory representation',
                 categoryDescription='DFT simulation with explicit electrons'):
        ResolutionCategory.__init__(self, manager=manager, branch=branch, id=id,
                                    materialId=materialId,
                                    name=name, description=description,
                                    categoryDescription=categoryDescription,
                                    scaleRange='Å',
                                    typicalMethods='DFT, VASP, Gaussian, QE')
        self.resolutionLevel = self.RESOLUTION_LEVEL
        self.resolutionCategory = self.RESOLUTION_CATEGORY

    def __repr__(self):
        return f"QuantumResolution(id='{self.id}', materialId='{self.materialId}')"
