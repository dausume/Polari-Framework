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
MeltingPointValue Model

Represents a derived melting point temperature in Celsius.
Inherits from MeltingPoint at abstraction level 2.

DSC determines melting point from endothermic peak:
- Onset temperature (Tm,onset): Intersection of baseline and tangent
- Peak temperature (Tm,peak): Maximum of endothermic peak
- Endset temperature: End of melting transition
- Heat of fusion (ΔHf): Area under the peak (J/g)

Crystallinity calculation:
- % Crystallinity = (ΔHf / ΔHf,100%) × 100
- ΔHf,100% is heat of fusion for 100% crystalline material

Standards References:
- ASTM D3418: Transition temperatures and enthalpies by DSC
- ASTM E794: Melting temperatures by thermal analysis
- ISO 11357-3: DSC - Determination of temperature and enthalpy
- Heating rate: Typically 10°C/min for standard measurements

Abstraction Levels:
- Level 0: MaterialProperty (core reference)
  - ThermalProperty (temperature-dependent category)
    - Level 1: MeltingPoint (abstract concept)
    - Level 2: MeltingPointValue (this class - derived value)
    - Level 3: DSCMeltingMeasurement, VisualMeltingMeasurement
"""

from objectTreeDecorators import treeObjectInit
from polariMaterialsScienceModule.properties.thermal.meltingPoint.meltingPoint import MeltingPoint


class MeltingPointValue(MeltingPoint):
    """
    Derived melting point value (Level 2).

    Represents the melting temperature in Celsius calculated from
    DSC or visual observation measurements.

    Abstraction level: 2

    Attributes:
        meltingPointC: Melting point in Celsius (onset or peak)
        meltingPointOnsetC: Onset temperature in Celsius
        meltingPointPeakC: Peak temperature in Celsius
        heatOfFusionJg: Heat of fusion in J/g
        crystallinityPercent: Calculated crystallinity percentage
        measurementMethod: Method used (DSC, DTA, visual)
        heatingRate: Heating rate in °C/min
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
                 meltingPointC=0.0,
                 meltingPointOnsetC=0.0,
                 meltingPointPeakC=0.0,
                 heatOfFusionJg=0.0,
                 crystallinityPercent=0.0,
                 measurementMethod='DSC',
                 heatingRate=10.0,
                 measurementDate='',
                 notes=''):
        MeltingPoint.__init__(self, manager=manager, branch=branch, id=id,
                              name='Melting Point Value',
                              description='Derived melting temperature in Celsius',
                              materialId=materialId)
        self.meltingPointC = meltingPointC
        self.meltingPointOnsetC = meltingPointOnsetC
        self.meltingPointPeakC = meltingPointPeakC
        self.heatOfFusionJg = heatOfFusionJg
        self.crystallinityPercent = crystallinityPercent
        self.measurementMethod = measurementMethod
        self.heatingRate = heatingRate
        self.measurementDate = measurementDate
        self.notes = notes
        self.abstractionLevel = self.ABSTRACTION_LEVEL

    def calculate_crystallinity(self, reference_heat_of_fusion):
        """
        Calculate crystallinity from heat of fusion.

        Args:
            reference_heat_of_fusion: ΔHf for 100% crystalline material (J/g)

        Returns:
            float: Crystallinity percentage
        """
        if reference_heat_of_fusion > 0:
            self.crystallinityPercent = (self.heatOfFusionJg / reference_heat_of_fusion) * 100
        return self.crystallinityPercent

    def __repr__(self):
        return f"MeltingPointValue(id='{self.id}', materialId='{self.materialId}', Tm={self.meltingPointC}°C)"
