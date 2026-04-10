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
UltimateTensileStrength Model

Represents a derived ultimate tensile strength (UTS) value in MPa.
Inherits from TensileStrength at abstraction level 2.

UTS is the maximum engineering stress reached during a tensile test.
It represents the peak of the stress-strain curve before necking
and fracture occur.

Related derived values:
- UTS (σ_ult): Maximum stress in MPa
- Yield Strength (σ_y): Stress at yield point (0.2% offset typically)
- Elongation at Break: % strain at fracture
- Young's Modulus (E): Slope of elastic region in MPa
- Poisson's Ratio (ν): Lateral strain / axial strain

Calculation:
- Engineering stress: σ = F / A₀ (force / original area)
- True stress: σ_true = F / A (force / instantaneous area)
- Engineering strain: ε = ΔL / L₀
- True strain: ε_true = ln(L / L₀)

Standards References:
- ASTM D638: Specifies Type I-V specimen geometries for plastics
- ASTM E8: Dog-bone specimens for metals
- ISO 527-2: Specimen dimensions for plastics
- Test speed: Typically 5-50 mm/min depending on material

Abstraction Levels:
- Level 0: MaterialProperty (core reference)
  - MechanicalProperty (strength/resistance category)
    - Level 1: TensileStrength (abstract concept)
    - Level 2: UltimateTensileStrength (this class - derived value)
    - Level 3: TensileMeasurement (raw measurement datapoints)
"""

from objectTreeDecorators import treeObjectInit
from polariMaterialsScienceModule.properties.mechanical.tensileStrength.tensileStrength import TensileStrength


class UltimateTensileStrength(TensileStrength):
    """
    Derived ultimate tensile strength value (Level 2).

    Represents the maximum stress a material can withstand during
    tensile testing, calculated from raw force-displacement data.

    Abstraction level: 2

    Attributes:
        utsMPa: Ultimate tensile strength in MPa
        yieldStrengthMPa: Yield strength in MPa (0.2% offset)
        elongationAtBreak: Elongation at break as percentage
        youngsModulusMPa: Young's modulus in MPa
        specimenType: ASTM specimen type (I, II, III, IV, V)
        testSpeed: Crosshead speed in mm/min
        temperature: Test temperature in Celsius
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
                 utsMPa=0.0,
                 yieldStrengthMPa=0.0,
                 elongationAtBreak=0.0,
                 youngsModulusMPa=0.0,
                 specimenType='Type I',
                 testSpeed=5.0,
                 temperature=23.0,
                 measurementDate='',
                 notes=''):
        TensileStrength.__init__(self, manager=manager, branch=branch, id=id,
                                 name='Ultimate Tensile Strength',
                                 description='Derived UTS value in MPa',
                                 materialId=materialId)
        self.utsMPa = utsMPa
        self.yieldStrengthMPa = yieldStrengthMPa
        self.elongationAtBreak = elongationAtBreak
        self.youngsModulusMPa = youngsModulusMPa
        self.specimenType = specimenType
        self.testSpeed = testSpeed
        self.temperature = temperature
        self.measurementDate = measurementDate
        self.notes = notes
        self.abstractionLevel = self.ABSTRACTION_LEVEL

    def calculate_from_measurements(self, measurements, cross_section_area_mm2):
        """
        Calculate UTS from raw TensileMeasurement data.

        Args:
            measurements: List of TensileMeasurement objects
            cross_section_area_mm2: Original cross-sectional area in mm²

        Returns:
            float: Calculated UTS in MPa
        """
        if not measurements or cross_section_area_mm2 <= 0:
            return self.utsMPa

        max_stress = 0.0
        for m in measurements:
            if hasattr(m, 'forceN') and m.forceN > 0:
                stress = m.forceN / cross_section_area_mm2  # MPa
                if stress > max_stress:
                    max_stress = stress

        self.utsMPa = max_stress
        return self.utsMPa

    def __repr__(self):
        return f"UltimateTensileStrength(id='{self.id}', materialId='{self.materialId}', UTS={self.utsMPa} MPa)"
