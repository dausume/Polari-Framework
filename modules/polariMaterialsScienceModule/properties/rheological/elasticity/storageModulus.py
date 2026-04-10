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
StorageModulus Model

Represents a derived storage modulus (G') value in Pascals.
Inherits from Elasticity at abstraction level 2.

The storage modulus represents the elastic (in-phase) component of the
complex modulus in dynamic mechanical analysis. It indicates how much
energy is stored during deformation.

Related derived values:
- G' (Storage Modulus): Elastic component (Pa)
- G'' (Loss Modulus): Viscous component (Pa)
- tan(δ): Loss factor = G''/G' (dimensionless)
- |G*|: Complex modulus magnitude = sqrt(G'^2 + G''^2)

Standards References:
- ASTM D4440: Standard test method for plastics dynamic mechanical properties
- ASTM D5279: Standard test method for plastics dynamic mechanical properties in torsion
- ISO 6721-10: Plastics - Determination of dynamic mechanical properties

Abstraction Levels:
- Level 0: MaterialProperty (core reference)
  - RheologicalProperty (flow/deformation category)
    - Level 1: Elasticity (abstract concept)
    - Level 2: StorageModulus (this class - derived/standard value)
    - Level 3: DMAMeasurement, RheometerMeasurement (raw measurements)
"""

from objectTreeDecorators import treeObjectInit
from polariMaterialsScienceModule.properties.rheological.elasticity.elasticity import Elasticity


class StorageModulus(Elasticity):
    """
    Derived storage modulus (G') value (Level 2).

    Represents the elastic component of material response during
    oscillatory deformation, calculated from raw DMA or rheometer measurements.

    Abstraction level: 2

    Attributes:
        storageModulusPa: Storage modulus G' in Pascals
        lossModulusPa: Loss modulus G'' in Pascals (if available)
        lossFactor: tan(delta) = G''/G' (dimensionless)
        frequency: Measurement frequency in Hz
        temperature: Reference temperature in Celsius
        measurementDate: Date when value was derived
        notes: Additional notes
    """

    ABSTRACTION_LEVEL = 2

    @treeObjectInit
    def __init__(self,
                 manager=None,
                 branch=None,
                 id=None,
                 materialId='',
                 storageModulusPa=0.0,
                 lossModulusPa=0.0,
                 lossFactor=0.0,
                 frequency=1.0,
                 temperature=25.0,
                 measurementDate='',
                 notes=''):
        Elasticity.__init__(self, manager=manager, branch=branch, id=id,
                           name='Storage Modulus',
                           description='Derived storage modulus G\' in Pascals',
                           materialId=materialId)
        self.storageModulusPa = storageModulusPa
        self.lossModulusPa = lossModulusPa
        self.lossFactor = lossFactor
        self.frequency = frequency
        self.temperature = temperature
        self.measurementDate = measurementDate
        self.notes = notes
        self.abstractionLevel = self.ABSTRACTION_LEVEL

    def calculate_complex_modulus(self):
        """Calculate the complex modulus magnitude |G*|."""
        import math
        return math.sqrt(self.storageModulusPa**2 + self.lossModulusPa**2)

    def calculate_loss_factor(self):
        """Calculate loss factor tan(delta) from G' and G''."""
        if self.storageModulusPa > 0:
            self.lossFactor = self.lossModulusPa / self.storageModulusPa
        return self.lossFactor

    def __repr__(self):
        return f"StorageModulus(id='{self.id}', materialId='{self.materialId}', G'={self.storageModulusPa} Pa)"
