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
AtomisticResolution Model

Level 3 resolution category for Classical Molecular Dynamics (MD).
This level represents materials with full atomistic detail using
classical force fields.

MD simulations provide:
- Atomic-level structure
- Dynamic properties
- Transport phenomena
- Thermodynamic properties
"""

from objectTreeDecorators import treeObjectInit
from polariMaterialsScienceModule.resolutions.resolutionCategory import ResolutionCategory


class AtomisticResolution(ResolutionCategory):
    """
    Atomistic resolution category (Level 3).

    Represents materials with full atomistic detail using classical
    molecular dynamics force fields.

    Resolution level: 3

    Attributes:
        materialId: ID reference to the parent Material
    """

    RESOLUTION_LEVEL = 3
    RESOLUTION_CATEGORY = 'atomistic'

    @treeObjectInit
    def __init__(self,
                 manager=None,
                 branch=None,
                 id=None,
                 materialId='',
                 name='Atomistic Resolution',
                 description='Classical molecular dynamics representation',
                 categoryDescription='Full atomistic MD simulation'):
        ResolutionCategory.__init__(self, manager=manager, branch=branch, id=id,
                                    materialId=materialId,
                                    name=name, description=description,
                                    categoryDescription=categoryDescription,
                                    scaleRange='Å-nm',
                                    typicalMethods='MD, LAMMPS, GROMACS, NAMD')
        self.resolutionLevel = self.RESOLUTION_LEVEL
        self.resolutionCategory = self.RESOLUTION_CATEGORY

    def __repr__(self):
        return f"AtomisticResolution(id='{self.id}', materialId='{self.materialId}')"
