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
SolidSurfaceEnergy Model

Represents the abstract concept of solid surface energy - the excess
energy at the surface of a solid compared to its bulk. Inherits from
SurfaceProperty at abstraction level 1.

Surface energy determines:
- Wettability (how liquids spread on surfaces)
- Adhesion (bonding between materials)
- Printability (ink acceptance)
- Coating compatibility
- Biocompatibility

Components (Owens-Wendt theory):
- Dispersive component (γᵈ): London dispersion forces
- Polar component (γᵖ): Polar interactions (H-bonding, dipole)
- Total surface energy: γ = γᵈ + γᵖ

Measurement approaches:
- Contact angle method: Measure angles with probe liquids
- Zisman method: Critical surface tension from cos(θ) vs γL plot
- Inverse gas chromatography (IGC): Powder surface energy

Standards References:
- ASTM D5946: Contact angle measurement on polymer films
- ASTM D7490: Water contact angle on coating surfaces
- ISO 19403: Wettability - Determination of contact angle
- ASTM D2578: Wetting tension of polyethylene films

Open Source References:
- OpenDrop: Open source contact angle software (github.com/opendrop)
- ImageJ plugins: Contact angle analysis from images
- DIY goniometers: Webcam + syringe + image analysis
- Python droplet analysis libraries (e.g., sessile-drop-analysis)

Abstraction Levels:
- Level 0: MaterialProperty (core reference)
  - SurfaceProperty (interfacial phenomena category)
    - Level 1: SolidSurfaceEnergy (this class - abstract concept)
    - Level 2: CriticalSurfaceTension (derived/standard value)
    - Level 3: ContactAngleMeasurement (raw measurement datapoints)
"""

from objectTreeDecorators import treeObjectInit
from polariMaterialsScienceModule.properties.surface.surfaceProperty import SurfaceProperty


class SolidSurfaceEnergy(SurfaceProperty):
    """
    Abstract solid surface energy property (Level 1).

    Represents the concept of surface free energy for solids - the
    thermodynamic work required to create new surface area.

    Abstraction level: 1 (abstract concept)

    Attributes:
        materialId: ID reference to the parent Material
    """

    ABSTRACTION_LEVEL = 1

    @treeObjectInit
    def __init__(self,
                 manager=None,
                 branch=None,
                 id=None,
                 name='Solid Surface Energy',
                 description='Excess energy at solid surface compared to bulk',
                 materialId=''):
        SurfaceProperty.__init__(self, manager=manager, branch=branch, id=id,
                                 name=name, description=description,
                                 materialId=materialId)
        self.abstractionLevel = self.ABSTRACTION_LEVEL

    def __repr__(self):
        return f"SolidSurfaceEnergy(id='{self.id}', materialId='{self.materialId}')"
