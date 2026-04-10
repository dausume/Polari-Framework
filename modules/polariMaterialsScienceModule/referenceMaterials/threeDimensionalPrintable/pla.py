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
PLA (Polylactic Acid) Reference Material

The most common FDM 3D printing material. Biodegradable thermoplastic
derived from renewable resources (corn starch, sugarcane).
Easy to print, low warping, good for beginners.
"""

from objectTreeDecorators import treeObjectInit
from polariMaterialsScienceModule.referenceMaterials.threeDimensionalPrintable.printableReferenceMaterial import PrintableReferenceMaterial


class PLA(PrintableReferenceMaterial):
    """
    Polylactic Acid (PLA) reference material.

    Most popular FDM filament material. Derived from renewable resources,
    biodegradable, easy to print with minimal warping.

    Typical properties:
    - Glass transition: 55-65 C
    - Melting point: 150-160 C
    - Tensile strength: 50-70 MPa
    - Good dimensional accuracy
    - Low warping
    - Brittle compared to ABS

    Attributes:
        Inherits all from PrintableReferenceMaterial with PLA-specific defaults
    """

    MATERIAL_TYPE = 'pla'

    @treeObjectInit
    def __init__(self,
                 manager=None,
                 branch=None,
                 id=None,
                 name='PLA',
                 fullName='Polylactic Acid',
                 description='Biodegradable thermoplastic from renewable resources. Most common FDM material.',
                 category='thermoplastic',
                 chemicalFormula='(C3H4O2)n',
                 casNumber='26100-51-6',
                 materialFamily='polyester',
                 polymerType='thermoplastic',
                 biodegradable=True,
                 foodSafe=True,
                 uvResistant=False,
                 chemicalResistance='Poor resistance to water, acids, and bases over time',
                 sourceCount=0,
                 notes='',
                 # Typical printing parameters for PLA
                 nozzleTempTypicalMin=190.0,
                 nozzleTempTypicalMax=220.0,
                 bedTempTypicalMin=20.0,
                 bedTempTypicalMax=60.0,
                 printSpeedTypicalMin=40.0,
                 printSpeedTypicalMax=100.0,
                 # FDM characteristics
                 enclosureRecommended=False,
                 dryingRecommended=False,
                 dryingTempTypical=45.0,
                 dryingTimeTypical=4.0,
                 # Filament characteristics
                 filamentAvailable=True,
                 commonDiameters='1.75, 2.85',
                 hygroscopic=True,
                 # Print quality characteristics
                 warpingTendency='low',
                 layerAdhesion='good',
                 bridgingCapability='good',
                 supportRemoval='easy',
                 surfaceFinish='Smooth, slightly glossy',
                 # Post-processing
                 sandable=True,
                 paintable=True,
                 acetoneSmoothing=False,
                 annealable=True):
        PrintableReferenceMaterial.__init__(
            self, manager=manager, branch=branch, id=id,
            name=name, fullName=fullName, description=description,
            category=category, chemicalFormula=chemicalFormula,
            casNumber=casNumber, materialFamily=materialFamily,
            polymerType=polymerType, biodegradable=biodegradable,
            foodSafe=foodSafe, uvResistant=uvResistant,
            chemicalResistance=chemicalResistance,
            sourceCount=sourceCount, notes=notes,
            nozzleTempTypicalMin=nozzleTempTypicalMin,
            nozzleTempTypicalMax=nozzleTempTypicalMax,
            bedTempTypicalMin=bedTempTypicalMin,
            bedTempTypicalMax=bedTempTypicalMax,
            printSpeedTypicalMin=printSpeedTypicalMin,
            printSpeedTypicalMax=printSpeedTypicalMax,
            enclosureRecommended=enclosureRecommended,
            dryingRecommended=dryingRecommended,
            dryingTempTypical=dryingTempTypical,
            dryingTimeTypical=dryingTimeTypical,
            filamentAvailable=filamentAvailable,
            commonDiameters=commonDiameters,
            hygroscopic=hygroscopic,
            warpingTendency=warpingTendency,
            layerAdhesion=layerAdhesion,
            bridgingCapability=bridgingCapability,
            supportRemoval=supportRemoval,
            surfaceFinish=surfaceFinish,
            sandable=sandable,
            paintable=paintable,
            acetoneSmoothing=acetoneSmoothing,
            annealable=annealable)

    def __repr__(self):
        return f"PLA(id='{self.id}', name='{self.name}')"
