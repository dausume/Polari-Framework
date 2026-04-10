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
GlassTransitionTemp Model

Represents a derived glass transition temperature (Tg) in Celsius.
Inherits from GlassTransition at abstraction level 2.

Tg determination methods:
- DSC: Midpoint of step change in heat capacity
- DMA: Multiple definitions
  - Onset of E' drop
  - Peak of E'' (loss modulus)
  - Peak of tan(δ) (highest value, most common)
- TMA: Onset of change in expansion coefficient

Note: Different methods give different Tg values for same material:
- tan(δ) peak > E'' peak > E' onset > DSC midpoint
- Always report method used for meaningful comparison

Reference Tg values:
- Polystyrene (PS): ~100°C
- PMMA: ~105°C
- PET: ~70°C
- Epoxy (cured): 120-180°C
- PLA: ~60°C

Standards References:
- ASTM E1356: Defines inflection point, half-height, onset methods
- ASTM D7028: Defines E' onset, E'' peak, tan(δ) peak
- ISO 11357-2: Half-step height extrapolation method
- Heating rate: Typically 10°C/min (DSC) or 2-5°C/min (DMA)

Abstraction Levels:
- Level 0: MaterialProperty (core reference)
  - ThermalProperty (temperature-dependent category)
    - Level 1: GlassTransition (abstract concept)
    - Level 2: GlassTransitionTemp (this class - derived value)
    - Level 3: DSCGlassTransitionMeasurement, DMAGlassTransitionMeasurement
"""

from objectTreeDecorators import treeObjectInit
from polariMaterialsScienceModule.properties.thermal.glassTransition.glassTransition import GlassTransition


class GlassTransitionTemp(GlassTransition):
    """
    Derived glass transition temperature value (Level 2).

    Represents Tg in Celsius determined from DSC or DMA measurements.

    Abstraction level: 2

    Attributes:
        tgCelsius: Glass transition temperature in Celsius
        tgOnset: Onset temperature in Celsius
        tgMidpoint: Midpoint temperature in Celsius
        tgEndset: Endset temperature in Celsius
        deltaCp: Change in heat capacity at Tg (J/g·°C, DSC)
        measurementMethod: Method used (DSC, DMA-tanδ, DMA-E'', etc.)
        heatingRate: Heating rate in °C/min
        frequency: Frequency in Hz (for DMA)
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
                 tgCelsius=0.0,
                 tgOnset=0.0,
                 tgMidpoint=0.0,
                 tgEndset=0.0,
                 deltaCp=0.0,
                 measurementMethod='DSC',
                 heatingRate=10.0,
                 frequency=1.0,
                 measurementDate='',
                 notes=''):
        GlassTransition.__init__(self, manager=manager, branch=branch, id=id,
                                 name='Glass Transition Temperature',
                                 description='Derived Tg value in Celsius',
                                 materialId=materialId)
        self.tgCelsius = tgCelsius
        self.tgOnset = tgOnset
        self.tgMidpoint = tgMidpoint
        self.tgEndset = tgEndset
        self.deltaCp = deltaCp
        self.measurementMethod = measurementMethod
        self.heatingRate = heatingRate
        self.frequency = frequency
        self.measurementDate = measurementDate
        self.notes = notes
        self.abstractionLevel = self.ABSTRACTION_LEVEL

    def __repr__(self):
        return f"GlassTransitionTemp(id='{self.id}', materialId='{self.materialId}', Tg={self.tgCelsius}°C ({self.measurementMethod}))"
