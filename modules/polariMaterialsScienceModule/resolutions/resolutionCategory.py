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
ResolutionCategory Model

Base class for resolution categories in multi-scale material modeling.
Categories group related resolution types that share similar scale
and simulation methodologies.

Categories:
- ExperimentalResolution: Real-world measurements (Level 0)
- ContinuumResolution: Finite Element Methods (Level 1)
- MesoscaleResolution: Coarse-Grained Molecular Dynamics (Level 2)
- AtomisticResolution: Classical Molecular Dynamics (Level 3)
- QuantumResolution: Density Functional Theory (Level 4)
"""

from objectTreeDecorators import treeObjectInit
from polariMaterialsScienceModule.materialResolution import MaterialResolution


class ResolutionCategory(MaterialResolution):
    """
    Base class for resolution categories.

    Categories serve as organizational groupings for related resolution types.
    Each category represents a scale of simulation (experimental, continuum,
    mesoscale, atomistic, quantum).

    Attributes:
        materialId: ID reference to the parent Material
        categoryDescription: Description of what this resolution category encompasses
        scaleRange: Typical length scale range for this category (e.g., "nm-µm")
        typicalMethods: Simulation methods used at this scale
    """

    @treeObjectInit
    def __init__(self,
                 manager=None,
                 branch=None,
                 id=None,
                 materialId='',
                 name='Resolution Category',
                 description='Base category for material resolutions',
                 categoryDescription='',
                 scaleRange='',
                 typicalMethods=''):
        MaterialResolution.__init__(self, manager=manager, branch=branch, id=id,
                                    materialId=materialId,
                                    name=name, description=description)
        self.categoryDescription = categoryDescription
        self.scaleRange = scaleRange
        self.typicalMethods = typicalMethods

    def __repr__(self):
        return f"ResolutionCategory(id='{self.id}', name='{self.name}')"
