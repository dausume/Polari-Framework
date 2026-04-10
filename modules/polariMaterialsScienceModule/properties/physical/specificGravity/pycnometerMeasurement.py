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
PycnometerMeasurement Model

Level 3 - Raw specific gravity measurement using a pycnometer.

A pycnometer (or specific gravity bottle) is a glass flask with a close-fitting
ground glass stopper with a capillary tube through it. This allows air bubbles
to escape and excess liquid to overflow, ensuring a precise, repeatable volume.

The measurement involves:
1. Weighing the empty pycnometer (W1)
2. Weighing the pycnometer filled with reference liquid - usually water (W2)
3. Weighing the pycnometer filled with sample (W3)

Specific Gravity = (W3 - W1) / (W2 - W1)

Abstraction Levels:
- Level 0: MaterialProperty (core reference)
- Level 1: SpecificGravity (abstract specific gravity concept)
- Level 2: ReferentialSpecificGravity (normalized against reference)
- Level 3: PycnometerMeasurement (this class - raw measurement)
"""

from objectTreeDecorators import treeObjectInit
from polariMaterialsScienceModule.properties.physical.specificGravity.specificGravity import SpecificGravity


class PycnometerMeasurement(SpecificGravity):
    """
    Raw specific gravity measurement using a pycnometer.

    A pycnometer measurement involves weighing the flask empty, with reference
    liquid, and with sample to calculate specific gravity.

    Abstraction level: 3 (most specific)

    Attributes:
        referentialSpecificGravityId: ID reference to parent ReferentialSpecificGravity
        sequenceNumber: Order of this measurement within a set
        emptyWeight: Weight of empty pycnometer (grams)
        referenceWeight: Weight with reference liquid (grams)
        sampleWeight: Weight with sample (grams)
        specificGravityValue: Calculated specific gravity from weights
        temperature: Temperature during measurement (Celsius)
        pycnometerVolume: Volume of pycnometer (mL)
        measurementDate: Date of measurement (ISO format string)
        operator: Name of the person who took the measurement
        equipment: Equipment/pycnometer identifier
        notes: Additional notes about the measurement
    """

    ABSTRACTION_LEVEL = 3

    @treeObjectInit
    def __init__(self,
                 manager=None,
                 branch=None,
                 id=None,
                 materialId='',
                 referentialSpecificGravityId='',
                 sequenceNumber=0,
                 emptyWeight=0.0,
                 referenceWeight=0.0,
                 sampleWeight=0.0,
                 specificGravityValue=0.0,
                 temperature=25.0,
                 pycnometerVolume=0.0,
                 measurementDate='',
                 operator='',
                 equipment='',
                 notes=''):
        SpecificGravity.__init__(self, manager=manager, branch=branch, id=id,
                                 name='Pycnometer Measurement',
                                 description='Raw pycnometer specific gravity measurement',
                                 materialId=materialId)
        self.referentialSpecificGravityId = referentialSpecificGravityId
        self.sequenceNumber = sequenceNumber
        self.emptyWeight = emptyWeight
        self.referenceWeight = referenceWeight
        self.sampleWeight = sampleWeight
        self.specificGravityValue = specificGravityValue
        self.temperature = temperature
        self.pycnometerVolume = pycnometerVolume
        self.measurementDate = measurementDate
        self.operator = operator
        self.equipment = equipment
        self.notes = notes
        self.abstractionLevel = self.ABSTRACTION_LEVEL

    def calculate_specific_gravity(self):
        """
        Calculate specific gravity from pycnometer weights.

        Formula: SG = (W3 - W1) / (W2 - W1)
        Where:
            W1 = empty weight
            W2 = reference weight (with water)
            W3 = sample weight

        Returns:
            float: Calculated specific gravity
        """
        reference_mass = self.referenceWeight - self.emptyWeight
        sample_mass = self.sampleWeight - self.emptyWeight

        if reference_mass > 0:
            self.specificGravityValue = sample_mass / reference_mass

        return self.specificGravityValue

    def __repr__(self):
        return f"PycnometerMeasurement(id='{self.id}', materialId='{self.materialId}', SG={self.specificGravityValue})"
