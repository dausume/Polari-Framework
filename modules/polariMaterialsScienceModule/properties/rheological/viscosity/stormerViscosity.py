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
StormerViscosity Model

Represents a single datapoint from a Stormer viscometer measurement.
Inherits from Viscosity at abstraction level 3 (most specific).

Stormer viscometers measure viscosity by determining the weight (grams)
required to drive a paddle at a specified number of revolutions in a given time.

Each measurement is tied to a Material by reference and contains:
- time: Duration of the measurement in seconds
- revolutions: Number of paddle revolutions (typically 100 or 200)
- grams: Weight applied to achieve the specified revolutions in the time

Multiple measurements can be taken for a material to create a data series
suitable for graphing viscosity behavior over different conditions.

Abstraction Levels:
- Level 0: MaterialProperty (core reference)
  - RheologicalProperty (flow/deformation category)
    - Level 1: Viscosity (abstract viscosity concept)
    - Level 2: KrebsViscosity (derived/computed values)
    - Level 3: StormerViscosity (this class - raw measurement datapoints)
"""

from objectTreeDecorators import treeObjectInit
from polariMaterialsScienceModule.properties.rheological.viscosity.viscosity import Viscosity


class StormerViscosity(Viscosity):
    """
    Stormer viscometer measurement datapoint (most specific raw measurement).

    A Stormer viscometer measures the viscosity of fluids by measuring
    the time required for a weighted paddle to complete a specified
    number of revolutions, or the weight required to achieve a target
    revolution count in a specified time.

    These measurements are commonly used in paints and coatings but are applicable
    to other fluid materials as well such as 3D printing resins and wax-composites,
    where viscosity is a critical property.

    Multiple StormerViscosity measurements can be grouped and used to derive
    a KrebsViscosity value for quality control and formulation purposes.

    Abstraction level: 3 (most specific)

    Attributes:
        krebsViscosityId: ID reference to the parent KrebsViscosity this contributes to
        sequenceNumber: Order of this measurement within the set (for graphing)
        time: Time duration of measurement in seconds
        revolutions: Number of paddle revolutions at this measurement point
        grams: Weight (in terms of force) applied in grams
        temperature: Temperature during measurement (Celsius)
        measurementDate: Date of measurement (ISO format string)
        operator: Name of the person who took the measurement
        equipment: Equipment used for measurement
        notes: Additional notes about the measurement
    """

    ABSTRACTION_LEVEL = 3

    @treeObjectInit
    def __init__(self,
                 manager=None,
                 branch=None,
                 id=None,
                 materialId='',
                 krebsViscosityId='',
                 sequenceNumber=0,
                 time=0.0,
                 revolutions=100,
                 grams=0.0,
                 temperature=25.0,
                 measurementDate='',
                 operator='',
                 equipment='',
                 notes=''):
        Viscosity.__init__(self, manager=manager, branch=branch, id=id,
                          name='Stormer Viscosity',
                          description='Raw Stormer viscometer measurement datapoint',
                          materialId=materialId)
        self.krebsViscosityId = krebsViscosityId
        self.sequenceNumber = sequenceNumber
        self.time = time
        self.revolutions = revolutions
        self.grams = grams
        self.temperature = temperature
        self.measurementDate = measurementDate
        self.operator = operator
        self.equipment = equipment
        self.notes = notes
        self.abstractionLevel = self.ABSTRACTION_LEVEL

    def __repr__(self):
        return f"StormerViscosity(id='{self.id}', materialId='{self.materialId}', time={self.time}s, revolutions={self.revolutions}, grams={self.grams}g)"
