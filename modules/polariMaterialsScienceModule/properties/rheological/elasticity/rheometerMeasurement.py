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
RheometerMeasurement Model

Represents a single datapoint from a rotational rheometer measurement.
Inherits from StorageModulus at abstraction level 3 (most specific).

Rotational rheometers measure fluids and soft solids using rotating
geometries (cone-plate, parallel plate, concentric cylinder).

Measurement Modes:
- Oscillatory: Storage/loss moduli (G', G'')
- Steady shear: Viscosity vs shear rate
- Creep/recovery: Time-dependent behavior
- Stress relaxation: Stress decay after step strain

Standards References:
- ASTM D4440: Plastics, dynamic mechanical properties (melt rheology)
- ASTM D4473: Plastics, cure properties of thermosetting resins
- ISO 3219: Plastics - Polymers/resins in liquid state - Viscosity
- ISO 6721-10: Plastics - DMA - Complex shear viscosity

Open Source / DIY References:
- OpenRheometer: github.com/openrheometer (open source rheometer project)
- Rheopy: Python rheological data analysis package
- DIY rheometers: Modified stepper motor + torque sensor designs
- CheapStat analogy: Similar to open source potentiostat movement
- Note: Precision instruments are expensive; DIY versions provide
  educational value and approximate measurements

openSourceImplementationExists: True (DIY designs exist using stepper motors)

Abstraction Levels:
- Level 0: MaterialProperty (core reference)
  - RheologicalProperty (flow/deformation category)
    - Level 1: Elasticity (abstract concept)
    - Level 2: StorageModulus (derived/standard value)
    - Level 3: RheometerMeasurement (this class - raw measurement datapoint)
"""

from objectTreeDecorators import treeObjectInit
from polariMaterialsScienceModule.properties.rheological.elasticity.storageModulus import StorageModulus


class RheometerMeasurement(StorageModulus):
    """
    Rotational rheometer measurement datapoint (most specific raw measurement).

    Rotational rheometers measure viscoelastic properties of fluids and
    soft solids using oscillatory or steady shear deformation.

    Abstraction level: 3 (most specific)

    Attributes:
        storageModulusId: ID reference to parent StorageModulus this contributes to
        sequenceNumber: Order of this measurement within the set
        geometry: Measurement geometry (cone-plate, parallel-plate, concentric-cylinder)
        gapDistance: Gap between plates in mm
        strain: Applied strain amplitude (%)
        shearRate: Shear rate in 1/s (for steady shear)
        torque: Measured torque in mN·m
        normalForce: Normal force in N (if measured)
        temperature: Temperature during measurement (Celsius)
        measurementDate: Date of measurement
        operator: Person who performed measurement
        equipment: Rheometer model used
        notes: Additional notes
        openSourceImplementationExists: Whether DIY/open source version exists
    """

    ABSTRACTION_LEVEL = 3

    @treeObjectInit
    def __init__(self,
                 manager=None,
                 branch=None,
                 id=None,
                 materialId='',
                 storageModulusId='',
                 sequenceNumber=0,
                 geometry='parallel-plate',
                 gapDistance=1.0,
                 strain=0.0,
                 shearRate=0.0,
                 torque=0.0,
                 normalForce=0.0,
                 storageModulusPa=0.0,
                 lossModulusPa=0.0,
                 frequency=1.0,
                 temperature=25.0,
                 measurementDate='',
                 operator='',
                 equipment='',
                 notes='',
                 openSourceImplementationExists=True):
        StorageModulus.__init__(self, manager=manager, branch=branch, id=id,
                                materialId=materialId,
                                storageModulusPa=storageModulusPa,
                                lossModulusPa=lossModulusPa,
                                frequency=frequency,
                                temperature=temperature,
                                measurementDate=measurementDate,
                                notes=notes)
        self.storageModulusId = storageModulusId
        self.sequenceNumber = sequenceNumber
        self.geometry = geometry
        self.gapDistance = gapDistance
        self.strain = strain
        self.shearRate = shearRate
        self.torque = torque
        self.normalForce = normalForce
        self.operator = operator
        self.equipment = equipment
        self.openSourceImplementationExists = openSourceImplementationExists
        self.abstractionLevel = self.ABSTRACTION_LEVEL

    def __repr__(self):
        return f"RheometerMeasurement(id='{self.id}', materialId='{self.materialId}', G'={self.storageModulusPa} Pa, geometry='{self.geometry}')"
