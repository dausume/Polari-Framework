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
SurfaceTensionValue Model

Represents a derived surface tension value in mN/m.
Inherits from LiquidSurfaceTension at abstraction level 2.

Reference values at 20°C:
- Water: 72.8 mN/m
- Ethanol: 22.1 mN/m
- Acetone: 25.2 mN/m
- Mercury: 485.5 mN/m
- Typical paints: 25-35 mN/m
- Typical resins: 30-45 mN/m

Temperature dependence:
- Surface tension generally decreases with temperature
- Eötvös rule: γV^(2/3) = k(Tc - T - 6)
- Where Tc is critical temperature, k ≈ 2.1 for many liquids

Standards References:
- ASTM D1331: Ring and plate methods for solutions
- ASTM D971: Ring method for petroleum products
- ISO 304: Surface active agents measurement
- ASTM D3825: Pendant drop for low interfacial tension

Abstraction Levels:
- Level 0: MaterialProperty (core reference)
  - SurfaceProperty (interfacial phenomena category)
    - Level 1: LiquidSurfaceTension (abstract concept)
    - Level 2: SurfaceTensionValue (this class - derived value)
    - Level 3: WilhelmyMeasurement, DuNouyMeasurement, PendantDropMeasurement
"""

from objectTreeDecorators import treeObjectInit
from polariMaterialsScienceModule.properties.surface.liquidSurfaceTension.liquidSurfaceTension import LiquidSurfaceTension


class SurfaceTensionValue(LiquidSurfaceTension):
    """
    Derived surface tension value (Level 2).

    Represents a liquid surface tension value in mN/m calculated
    from raw tensiometer or pendant drop measurements.

    Abstraction level: 2

    Attributes:
        surfaceTensionMNm: Surface tension in mN/m
        interfacialTensionMNm: Interfacial tension with another phase (if measured)
        secondPhase: Second phase for interfacial measurement (air, water, oil)
        measurementMethod: Method used (Wilhelmy, Du Noüy, pendant drop)
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
                 surfaceTensionMNm=0.0,
                 interfacialTensionMNm=0.0,
                 secondPhase='air',
                 measurementMethod='',
                 temperature=20.0,
                 measurementDate='',
                 notes=''):
        LiquidSurfaceTension.__init__(self, manager=manager, branch=branch, id=id,
                                      name='Surface Tension Value',
                                      description='Derived surface tension in mN/m',
                                      materialId=materialId)
        self.surfaceTensionMNm = surfaceTensionMNm
        self.interfacialTensionMNm = interfacialTensionMNm
        self.secondPhase = secondPhase
        self.measurementMethod = measurementMethod
        self.temperature = temperature
        self.measurementDate = measurementDate
        self.notes = notes
        self.abstractionLevel = self.ABSTRACTION_LEVEL

    def calculate_from_measurements(self, measurements):
        """
        Calculate average surface tension from measurements.

        Args:
            measurements: List of measurement objects with surfaceTensionMNm attribute

        Returns:
            float: Average surface tension in mN/m
        """
        if not measurements:
            return self.surfaceTensionMNm

        total = 0.0
        count = 0
        for m in measurements:
            if hasattr(m, 'surfaceTensionMNm') and m.surfaceTensionMNm > 0:
                total += m.surfaceTensionMNm
                count += 1

        if count > 0:
            self.surfaceTensionMNm = total / count

        return self.surfaceTensionMNm

    def __repr__(self):
        return f"SurfaceTensionValue(id='{self.id}', materialId='{self.materialId}', γ={self.surfaceTensionMNm} mN/m)"
