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
DMAMeasurement Model

Represents a single datapoint from a Dynamic Mechanical Analysis (DMA) measurement.
Inherits from StorageModulus at abstraction level 3 (most specific).

DMA applies oscillatory stress/strain to a solid sample and measures the
material's response as a function of temperature, frequency, or time.

Measurement Modes:
- Temperature sweep: Vary T at fixed frequency
- Frequency sweep: Vary f at fixed temperature
- Time sweep: Monitor changes over time (curing, aging)

Standards References:
- ASTM D4065: Plastics, DMA procedures
- ASTM D5023: Plastics, DMA in flexure (three-point bending)
- ASTM D5026: Plastics, DMA in tension
- ASTM D5279: Plastics, DMA in torsion
- ISO 6721: Plastics - Determination of dynamic mechanical properties

Open Source / DIY References:
- OpenDMA project: Arduino-based DMA for educational purposes
- RepRap community: Modified 3D printer frames as basic DMA platforms
- PyDMA: Python package for DMA data analysis (github.com/pydma)
- Note: Commercial DMA instruments (TA, Mettler, Netzsch) are typically required
  for precise measurements; DIY options exist for educational/approximate use

openSourceImplementationExists: True (educational/approximate DIY versions exist)

Abstraction Levels:
- Level 0: MaterialProperty (core reference)
  - RheologicalProperty (flow/deformation category)
    - Level 1: Elasticity (abstract concept)
    - Level 2: StorageModulus (derived/standard value)
    - Level 3: DMAMeasurement (this class - raw measurement datapoint)
"""

from objectTreeDecorators import treeObjectInit
from polariMaterialsScienceModule.properties.rheological.elasticity.storageModulus import StorageModulus


class DMAMeasurement(StorageModulus):
    """
    DMA measurement datapoint (most specific raw measurement).

    Dynamic Mechanical Analysis applies oscillatory deformation to solids
    and measures the viscoelastic response (storage and loss moduli).

    Abstraction level: 3 (most specific)

    Attributes:
        storageModulusId: ID reference to parent StorageModulus this contributes to
        sequenceNumber: Order of this measurement within the set
        strain: Applied strain amplitude (%)
        stress: Measured stress amplitude (Pa)
        phaseAngle: Phase angle delta between stress and strain (degrees)
        sampleLength: Sample length in mm
        sampleWidth: Sample width in mm
        sampleThickness: Sample thickness in mm
        clampType: Clamping geometry (tension, three-point bend, single cantilever, etc.)
        temperature: Temperature during measurement (Celsius)
        measurementDate: Date of measurement
        operator: Person who performed measurement
        equipment: DMA instrument used
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
                 strain=0.0,
                 stress=0.0,
                 phaseAngle=0.0,
                 storageModulusPa=0.0,
                 lossModulusPa=0.0,
                 frequency=1.0,
                 sampleLength=0.0,
                 sampleWidth=0.0,
                 sampleThickness=0.0,
                 clampType='',
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
        self.strain = strain
        self.stress = stress
        self.phaseAngle = phaseAngle
        self.sampleLength = sampleLength
        self.sampleWidth = sampleWidth
        self.sampleThickness = sampleThickness
        self.clampType = clampType
        self.operator = operator
        self.equipment = equipment
        self.openSourceImplementationExists = openSourceImplementationExists
        self.abstractionLevel = self.ABSTRACTION_LEVEL

    def __repr__(self):
        return f"DMAMeasurement(id='{self.id}', materialId='{self.materialId}', G'={self.storageModulusPa} Pa, T={self.temperature}°C)"
