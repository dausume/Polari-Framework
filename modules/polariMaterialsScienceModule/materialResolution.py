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
MaterialResolution Model

Base class for material resolution-level definitions in multi-scale modeling.
MaterialResolution defines how a Material is represented at different
simulation scales, from experimental (real-world) to quantum (DFT).

Resolution Levels:
- Level 0: Experimental (Real World / Human Scale)
  - RawExperimentalMaterial, RulesOfMixturesExperimentalMaterial

- Level 1: Continuum (Finite Element Methods)
  - ConsistentFiniteElementMaterial, StochasticFiniteElementMaterial
  - ChosenMaterial, RangeMaterial

- Level 2: Mesoscale (Coarse-Grained Molecular Dynamics)
  - CoarsegrainedMolecularDynamicsMaterial

- Level 3: Atomistic (Classical Molecular Dynamics)
  - MolecularDynamicsMaterial

- Level 4: Quantum (Density Functional Theory)
  - DensityFunctionalMaterial

Each resolution level provides a different view of the same material,
suitable for different simulation approaches and scales.
"""

from objectTreeDecorators import treeObject, treeObjectInit


class MaterialResolution(treeObject):
    """
    Base class for material resolution-level definitions.

    A MaterialResolution represents how a Material is defined at a specific
    simulation scale. The same physical material can have multiple resolution
    definitions for use in different simulation contexts.

    Attributes:
        materialId: ID reference to the parent Material
        name: Name for this resolution definition
        description: Description of this resolution definition
        resolutionLevel: Numeric level (0=experimental, 1=FEM, 2=CGMD, 3=MD, 4=DFT)
        resolutionCategory: Category name (experimental, continuum, mesoscale, atomistic, quantum)
    """

    RESOLUTION_LEVEL = None  # Override in subclasses
    RESOLUTION_CATEGORY = ''  # Override in subclasses

    @treeObjectInit
    def __init__(self,
                 manager=None,
                 branch=None,
                 id=None,
                 materialId='',
                 name='',
                 description=''):
        treeObject.__init__(self, manager=manager, branch=branch, id=id)
        self.materialId = materialId
        self.name = name
        self.description = description
        self.resolutionLevel = self.RESOLUTION_LEVEL
        self.resolutionCategory = self.RESOLUTION_CATEGORY

    def __repr__(self):
        return f"MaterialResolution(id='{self.id}', materialId='{self.materialId}', level={self.resolutionLevel})"
