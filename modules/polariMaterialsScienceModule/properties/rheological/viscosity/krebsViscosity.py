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
KrebsViscosity Model

Represents a derived viscosity measurement in Krebs Units (KU).
Inherits from Viscosity at abstraction level 2.

The Krebs Unit is a standard measure used in the paint and coatings industry.
A KrebsViscosity record represents the final derived viscosity value for a
material, computed from a set of raw StormerViscosity measurement datapoints.

Abstraction Levels:
- Level 0: MaterialProperty (core reference)
  - RheologicalProperty (flow/deformation category)
    - Level 1: Viscosity (abstract viscosity concept)
    - Level 2: KrebsViscosity (this class - derived/computed values)
    - Level 3: StormerViscosity (raw measurement datapoints)
"""

from objectTreeDecorators import treeObjectInit
from polariMaterialsScienceModule.properties.rheological.viscosity.viscosity import Viscosity


class KrebsViscosity(Viscosity):
    """
    Derived viscosity measurement in Krebs Units (KU).

    This represents a derived viscosity value computed from raw StormerViscosity
    measurements. While StormerViscosity contains specific measurement datapoints
    (time, revolutions, grams), KrebsViscosity represents the final computed
    viscosity in the industry-standard Krebs Unit scale.

    The Krebs Unit is commonly used in paints and coatings but is applicable
    to other fluid materials as well such as 3D printing resins and wax-composites,
    where viscosity is a critical property.

    The derivation uses the Load Formula based on ASTM D562, where L is the load
    in grams needed to make the paddle turn 200 revolutions in 60 seconds,
    eta is the dynamic viscosity in Poise of the calibration fluid (usually oil or water),
    and rho is the density in g/cm³ of the calibration fluid. The constants 6.1 and 906.6
    are empirically derived for the Stormer viscometer machine itself and the paddle geometry
    which is standardized to enable simplification of the formula to directly calculate KU:

        L = [ (6.1 * eta + 906.6 * rho) / 30 ]

    Abstraction level: 2

    Attributes:
        viscosityKU: The derived viscosity value in Krebs Units
        temperature: Reference temperature for the measurement (Celsius)
        measurementDate: Date when the KU value was derived
        notes: Additional notes about the derived value
    """

    ABSTRACTION_LEVEL = 2

    @treeObjectInit
    def __init__(self,
                 manager=None,
                 branch=None,
                 id=None,
                 materialId='',
                 viscosityKU=0.0,
                 temperature=25.0,
                 measurementDate='',
                 notes=''):
        Viscosity.__init__(self, manager=manager, branch=branch, id=id,
                          name='Krebs Viscosity',
                          description='Derived viscosity in Krebs Units (KU)',
                          materialId=materialId)
        self.viscosityKU = viscosityKU
        self.temperature = temperature
        self.measurementDate = measurementDate
        self.notes = notes
        self.abstractionLevel = self.ABSTRACTION_LEVEL

    def calculate_from_stormer_measurements(self, stormer_measurements):
        """
        Calculate Krebs Units (KU) from a set of StormerViscosity measurements.

        Uses the standard conversion where measurements at 200 revolutions
        are normalized and converted to KU.

        Args:
            stormer_measurements: List of StormerViscosity objects

        Returns:
            float: Calculated viscosity in Krebs Units
        """
        if not stormer_measurements:
            return self.viscosityKU

        # Find measurement closest to 200 revolutions or normalize
        total_normalized_grams = 0.0
        count = 0
        for measurement in stormer_measurements:
            if measurement.grams > 0 and measurement.revolutions > 0:
                normalized_grams = measurement.grams * (200 / measurement.revolutions)
                total_normalized_grams += normalized_grams
                count += 1

        if count > 0:
            avg_normalized_grams = total_normalized_grams / count
            self.viscosityKU = (avg_normalized_grams * 2.08) + 15.8

        return self.viscosityKU

    def __repr__(self):
        return f"KrebsViscosity(id='{self.id}', materialId='{self.materialId}', viscosityKU={self.viscosityKU})"
