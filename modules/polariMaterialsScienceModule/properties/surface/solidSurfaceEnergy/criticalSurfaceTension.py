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
CriticalSurfaceTension Model

Represents a derived surface energy value in mN/m (mJ/m²).
Inherits from SolidSurfaceEnergy at abstraction level 2.

Critical surface tension (γc) is determined from Zisman plot:
- Plot cos(θ) vs surface tension of probe liquids
- Extrapolate to cos(θ) = 1 (complete wetting)
- γc is the surface tension at which complete wetting occurs

Owens-Wendt method for total surface energy:
- Use two probe liquids (one polar, one dispersive)
- Solve for dispersive and polar components separately
- Common probes: Water (72.8 mN/m), Diiodomethane (50.8 mN/m)

Young's Equation:
- γSV = γSL + γLV·cos(θ)
- γSV: Solid-vapor surface energy
- γSL: Solid-liquid interfacial energy
- γLV: Liquid-vapor surface tension
- θ: Contact angle

Standards References:
- ASTM D5946: Contact angle measurement procedures
- ISO 19403-2: Owens-Wendt-Rabel-Kaelble (OWRK) method
- ISO 19403-3: Zisman method for critical surface tension

Abstraction Levels:
- Level 0: MaterialProperty (core reference)
  - SurfaceProperty (interfacial phenomena category)
    - Level 1: SolidSurfaceEnergy (abstract concept)
    - Level 2: CriticalSurfaceTension (this class - derived value)
    - Level 3: ContactAngleMeasurement (raw measurement datapoints)
"""

from objectTreeDecorators import treeObjectInit
from polariMaterialsScienceModule.properties.surface.solidSurfaceEnergy.solidSurfaceEnergy import SolidSurfaceEnergy


class CriticalSurfaceTension(SolidSurfaceEnergy):
    """
    Derived critical surface tension value (Level 2).

    Represents surface energy in mN/m calculated from contact angle
    measurements using Zisman or Owens-Wendt methods.

    Abstraction level: 2

    Attributes:
        surfaceEnergyMNm: Total surface energy in mN/m
        dispersiveComponent: Dispersive component γᵈ in mN/m
        polarComponent: Polar component γᵖ in mN/m
        calculationMethod: Method used (Zisman, Owens-Wendt, etc.)
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
                 surfaceEnergyMNm=0.0,
                 dispersiveComponent=0.0,
                 polarComponent=0.0,
                 calculationMethod='Owens-Wendt',
                 temperature=23.0,
                 measurementDate='',
                 notes=''):
        SolidSurfaceEnergy.__init__(self, manager=manager, branch=branch, id=id,
                                    name='Critical Surface Tension',
                                    description='Derived surface energy in mN/m',
                                    materialId=materialId)
        self.surfaceEnergyMNm = surfaceEnergyMNm
        self.dispersiveComponent = dispersiveComponent
        self.polarComponent = polarComponent
        self.calculationMethod = calculationMethod
        self.temperature = temperature
        self.measurementDate = measurementDate
        self.notes = notes
        self.abstractionLevel = self.ABSTRACTION_LEVEL

    def calculate_from_owens_wendt(self, water_angle, diiodomethane_angle):
        """
        Calculate surface energy using Owens-Wendt method.

        Uses water (γL=72.8, γLᵈ=21.8, γLᵖ=51.0) and
        diiodomethane (γL=50.8, γLᵈ=50.8, γLᵖ=0) as probe liquids.

        Args:
            water_angle: Contact angle with water in degrees
            diiodomethane_angle: Contact angle with diiodomethane in degrees

        Returns:
            tuple: (total, dispersive, polar) surface energy in mN/m
        """
        import math

        # Probe liquid properties (mN/m)
        water_total = 72.8
        water_d = 21.8
        water_p = 51.0
        diio_total = 50.8
        diio_d = 50.8
        diio_p = 0.0

        # Convert angles to radians
        theta_w = math.radians(water_angle)
        theta_d = math.radians(diiodomethane_angle)

        # From diiodomethane (purely dispersive)
        # γSᵈ = [(γL(1+cosθ))/(2√γLᵈ)]²
        self.dispersiveComponent = ((diio_total * (1 + math.cos(theta_d))) / (2 * math.sqrt(diio_d))) ** 2

        # From water using dispersive component
        # γSᵖ = [(γL(1+cosθ) - 2√(γSᵈγLᵈ))/(2√γLᵖ)]²
        numerator = water_total * (1 + math.cos(theta_w)) - 2 * math.sqrt(self.dispersiveComponent * water_d)
        self.polarComponent = (numerator / (2 * math.sqrt(water_p))) ** 2

        self.surfaceEnergyMNm = self.dispersiveComponent + self.polarComponent
        self.calculationMethod = 'Owens-Wendt'

        return (self.surfaceEnergyMNm, self.dispersiveComponent, self.polarComponent)

    def __repr__(self):
        return f"CriticalSurfaceTension(id='{self.id}', materialId='{self.materialId}', γ={self.surfaceEnergyMNm} mN/m)"
