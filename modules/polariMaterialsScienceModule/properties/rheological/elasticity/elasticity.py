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
Elasticity Model

Represents the abstract concept of elasticity - a material's ability to
return to its original shape after deformation. Inherits from
RheologicalProperty at abstraction level 1.

Elasticity encompasses several related properties:
- Storage Modulus (G'): Energy stored during deformation (elastic response)
- Loss Modulus (G''): Energy dissipated during deformation (viscous response)
- Complex Modulus (G*): Combined elastic and viscous response
- Young's Modulus (E): Stiffness in tension/compression
- Shear Modulus (G): Stiffness in shear

Standards References:
- ASTM D4440: Plastics, dynamic mechanical properties (melt rheology)
- ASTM D5279: Plastics, dynamic mechanical properties in torsion
- ASTM D5023: Plastics, dynamic mechanical properties in flexure
- ISO 6721: Plastics - Determination of dynamic mechanical properties

Open Source References:
- OpenRheology project: github.com/openrheology (rheological data analysis)
- Rheopy: Python package for rheological data analysis
- RepRap community: DIY rheometer designs using stepper motors

Abstraction Levels:
- Level 0: MaterialProperty (core reference)
  - RheologicalProperty (flow/deformation category)
    - Level 1: Elasticity (this class - abstract concept)
    - Level 2: StorageModulus (derived/standard value)
    - Level 3: DMAMeasurement, RheometerMeasurement (raw measurements)
"""

from objectTreeDecorators import treeObjectInit
from polariMaterialsScienceModule.properties.rheological.rheologicalProperty import RheologicalProperty


class Elasticity(RheologicalProperty):
    """
    Abstract elasticity property (Level 1).

    Represents the concept of material elasticity - the ability to store
    and return energy during deformation. This is the abstract parent
    for specific modulus types and measurements.

    Abstraction level: 1 (abstract concept)

    Attributes:
        materialId: ID reference to the parent Material
    """

    ABSTRACTION_LEVEL = 1

    @treeObjectInit
    def __init__(self,
                 manager=None,
                 branch=None,
                 id=None,
                 name='Elasticity',
                 description='Material ability to return to original shape after deformation',
                 materialId=''):
        RheologicalProperty.__init__(self, manager=manager, branch=branch, id=id,
                                     name=name, description=description,
                                     materialId=materialId)
        self.abstractionLevel = self.ABSTRACTION_LEVEL

    def __repr__(self):
        return f"Elasticity(id='{self.id}', materialId='{self.materialId}')"
