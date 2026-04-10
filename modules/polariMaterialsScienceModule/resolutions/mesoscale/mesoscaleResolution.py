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
MesoscaleResolution Model

Level 2 resolution category for Coarse-Grained Molecular Dynamics (CGMD).
This level represents materials using simplified molecular representations
where groups of atoms are combined into "beads."

CGMD bridges the gap between atomistic MD and continuum FEM, allowing:
- Longer time scales than atomistic MD
- Larger system sizes
- Polymer chain dynamics
- Self-assembly phenomena
"""

from objectTreeDecorators import treeObjectInit
from polariMaterialsScienceModule.resolutions.resolutionCategory import ResolutionCategory


class MesoscaleResolution(ResolutionCategory):
    """
    Mesoscale resolution category (Level 2).

    Represents materials at the coarse-grained molecular dynamics scale
    where groups of atoms are represented as single interaction sites.

    Resolution level: 2

    Attributes:
        materialId: ID reference to the parent Material
    """

    RESOLUTION_LEVEL = 2
    RESOLUTION_CATEGORY = 'mesoscale'

    @treeObjectInit
    def __init__(self,
                 manager=None,
                 branch=None,
                 id=None,
                 materialId='',
                 name='Mesoscale Resolution',
                 description='Coarse-grained molecular dynamics representation',
                 categoryDescription='CGMD simulation with grouped atom beads'):
        ResolutionCategory.__init__(self, manager=manager, branch=branch, id=id,
                                    materialId=materialId,
                                    name=name, description=description,
                                    categoryDescription=categoryDescription,
                                    scaleRange='nm-µm',
                                    typicalMethods='CGMD, Martini, DPD')
        self.resolutionLevel = self.RESOLUTION_LEVEL
        self.resolutionCategory = self.RESOLUTION_CATEGORY

    def __repr__(self):
        return f"MesoscaleResolution(id='{self.id}', materialId='{self.materialId}')"
