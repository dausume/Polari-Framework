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
ConsistentFiniteElementMaterial Model

Represents a material with consistent properties throughout the domain.
All finite elements share the same material property values.

This is the most common FEM material representation, used when:
- Material is homogeneous
- Property variations are negligible
- Deterministic analysis is sufficient
"""

from objectTreeDecorators import treeObjectInit
from polariMaterialsScienceModule.resolutions.continuum.continuumResolution import ContinuumResolution


class ConsistentFiniteElementMaterial(ContinuumResolution):
    """
    Consistent FEM material with uniform properties.

    All elements in the mesh share identical material properties.

    Attributes:
        materialId: ID reference to the parent Material
        youngsModulus: Young's modulus in Pa
        poissonsRatio: Poisson's ratio (dimensionless)
        density: Density in kg/m³
        thermalConductivity: Thermal conductivity in W/(m·K)
        specificHeat: Specific heat in J/(kg·K)
        thermalExpansion: CTE in 1/K
    """

    @treeObjectInit
    def __init__(self,
                 manager=None,
                 branch=None,
                 id=None,
                 materialId='',
                 name='Consistent FEM Material',
                 description='Uniform material properties for FEM',
                 youngsModulus=0.0,
                 poissonsRatio=0.0,
                 density=0.0,
                 thermalConductivity=0.0,
                 specificHeat=0.0,
                 thermalExpansion=0.0):
        ContinuumResolution.__init__(self, manager=manager, branch=branch, id=id,
                                     materialId=materialId,
                                     name=name, description=description)
        self.youngsModulus = youngsModulus
        self.poissonsRatio = poissonsRatio
        self.density = density
        self.thermalConductivity = thermalConductivity
        self.specificHeat = specificHeat
        self.thermalExpansion = thermalExpansion

    def __repr__(self):
        return f"ConsistentFiniteElementMaterial(id='{self.id}', materialId='{self.materialId}', E={self.youngsModulus})"
