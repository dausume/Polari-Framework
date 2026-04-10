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
RheologicalProperty Model

Rheological properties relate to the flow and deformation of matter.
This serves as a category beneath PropertyCategory for properties like:
- Viscosity (resistance to flow)
- Elasticity / Storage modulus (energy stored during deformation)
- Loss modulus (energy dissipated during deformation)
- Yield stress (stress required to initiate flow)
- Thixotropy (time-dependent shear thinning)
- Melt Flow Index (polymer processability)

Rheology is particularly important for:
- Paints and coatings
- Polymers and plastics
- Food products
- Cosmetics
- Pharmaceuticals
- 3D printing materials

Standards References:
- ASTM D2196: Rheological properties of non-Newtonian materials
- ASTM D4440: Plastics dynamic mechanical properties
- ISO 3219: Polymers/resins - Determination of viscosity
"""

from objectTreeDecorators import treeObjectInit
from polariMaterialsScienceModule.properties.propertyCategory import PropertyCategory


class RheologicalProperty(PropertyCategory):
    """
    Rheological property category inheriting from PropertyCategory.

    Rheology is the study of flow and deformation of matter. This class
    serves as a parent category for specific rheological properties like
    Viscosity, Elasticity, Melt Flow Index, etc.

    Child Properties:
    - viscosity/: Viscosity → KrebsViscosity → StormerViscosity
    - elasticity/: Elasticity → StorageModulus → DMA/Rheometer measurements
    - meltFlowIndex/: MeltFlowIndex → MFIValue → MFIMeasurement

    Attributes:
        materialId: ID reference to the parent Material
    """

    @treeObjectInit
    def __init__(self,
                 manager=None,
                 branch=None,
                 id=None,
                 name='Rheological Property',
                 description='Property relating to flow and deformation of matter',
                 materialId='',
                 categoryDescription='Flow and deformation properties including viscosity, elasticity, and melt flow'):
        PropertyCategory.__init__(self, manager=manager, branch=branch, id=id,
                                  name=name, description=description,
                                  materialId=materialId, categoryDescription=categoryDescription)

    def __repr__(self):
        return f"RheologicalProperty(id='{self.id}', name='{self.name}', materialId='{self.materialId}')"
