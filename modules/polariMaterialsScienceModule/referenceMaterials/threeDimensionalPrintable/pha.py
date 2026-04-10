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
PHA (Polyhydroxyalkanoate) Reference Material

Biodegradable bio-based thermoplastic produced by microorganisms.
More flexible than PLA with better impact resistance.
Fully marine-biodegradable.
"""

from objectTreeDecorators import treeObjectInit
from polariMaterialsScienceModule.referenceMaterials.threeDimensionalPrintable.printableReferenceMaterial import PrintableReferenceMaterial


class PHA(PrintableReferenceMaterial):
    """
    Polyhydroxyalkanoate (PHA) reference material.

    Biodegradable, bio-based thermoplastic produced by bacterial
    fermentation. Marine-biodegradable. More flexible than PLA.

    Typical properties:
    - Glass transition: -30 to 10 C (varies by type)
    - Melting point: 140-180 C
    - Tensile strength: 20-40 MPa
    - Better impact resistance than PLA
    - Fully biodegradable including marine

    Attributes:
        phaType: Type of PHA (PHB, PHBV, PHBHHx, etc.)
        Inherits all from PrintableReferenceMaterial with PHA-specific defaults
    """

    MATERIAL_TYPE = 'pha'

    @treeObjectInit
    def __init__(self,
                 manager=None,
                 branch=None,
                 id=None,
                 name='PHA',
                 fullName='Polyhydroxyalkanoate',
                 description='Biodegradable, bio-based thermoplastic. Marine-biodegradable.',
                 category='thermoplastic',
                 chemicalFormula='',
                 casNumber='',
                 materialFamily='polyester',
                 polymerType='thermoplastic',
                 biodegradable=True,
                 foodSafe=True,
                 uvResistant=False,
                 chemicalResistance='Moderate chemical resistance',
                 sourceCount=0,
                 notes='Often blended with PLA for improved properties',
                 # Typical printing parameters for PHA
                 nozzleTempTypicalMin=170.0,
                 nozzleTempTypicalMax=200.0,
                 bedTempTypicalMin=20.0,
                 bedTempTypicalMax=60.0,
                 printSpeedTypicalMin=30.0,
                 printSpeedTypicalMax=60.0,
                 # FDM characteristics
                 enclosureRecommended=False,
                 dryingRecommended=True,
                 dryingTempTypical=50.0,
                 dryingTimeTypical=4.0,
                 # Filament characteristics
                 filamentAvailable=True,
                 commonDiameters='1.75, 2.85',
                 hygroscopic=True,
                 # Print quality characteristics
                 warpingTendency='low',
                 layerAdhesion='good',
                 bridgingCapability='moderate',
                 supportRemoval='easy',
                 surfaceFinish='Matte, natural appearance',
                 # Post-processing
                 sandable=True,
                 paintable=True,
                 acetoneSmoothing=False,
                 annealable=False,
                 # PHA specific
                 phaType='PHBV'):
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

        self.phaType = phaType

    def __repr__(self):
        return f"PHA(id='{self.id}', name='{self.name}', type='{self.phaType}')"
