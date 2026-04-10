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
ABS (Acrylonitrile Butadiene Styrene) Reference Material

Strong, durable thermoplastic. Common in industrial applications.
Requires higher temperatures and enclosure for best results.
"""

from objectTreeDecorators import treeObjectInit
from polariMaterialsScienceModule.referenceMaterials.threeDimensionalPrintable.printableReferenceMaterial import PrintableReferenceMaterial


class ABS(PrintableReferenceMaterial):
    """
    Acrylonitrile Butadiene Styrene (ABS) reference material.

    Strong, impact-resistant engineering thermoplastic. Common in
    automotive parts, LEGO bricks, and electronics housings.

    Typical properties:
    - Glass transition: 105 C
    - Tensile strength: 40-50 MPa
    - Good impact resistance
    - Higher warping tendency
    - Requires heated bed and enclosure

    Attributes:
        Inherits all from PrintableReferenceMaterial with ABS-specific defaults
    """

    MATERIAL_TYPE = 'abs'

    @treeObjectInit
    def __init__(self,
                 manager=None,
                 branch=None,
                 id=None,
                 name='ABS',
                 fullName='Acrylonitrile Butadiene Styrene',
                 description='Strong, impact-resistant engineering thermoplastic. Requires enclosure.',
                 category='thermoplastic',
                 chemicalFormula='(C8H8)x(C4H6)y(C3H3N)z',
                 casNumber='9003-56-9',
                 materialFamily='styrenic',
                 polymerType='thermoplastic',
                 biodegradable=False,
                 foodSafe=False,
                 uvResistant=False,
                 chemicalResistance='Good resistance to acids and bases, poor to solvents',
                 sourceCount=0,
                 notes='Emits fumes during printing - ventilation recommended',
                 # Typical printing parameters for ABS
                 nozzleTempTypicalMin=220.0,
                 nozzleTempTypicalMax=250.0,
                 bedTempTypicalMin=90.0,
                 bedTempTypicalMax=110.0,
                 printSpeedTypicalMin=40.0,
                 printSpeedTypicalMax=80.0,
                 # FDM characteristics
                 enclosureRecommended=True,
                 dryingRecommended=True,
                 dryingTempTypical=80.0,
                 dryingTimeTypical=4.0,
                 # Filament characteristics
                 filamentAvailable=True,
                 commonDiameters='1.75, 2.85',
                 hygroscopic=True,
                 # Print quality characteristics
                 warpingTendency='high',
                 layerAdhesion='excellent',
                 bridgingCapability='moderate',
                 supportRemoval='moderate',
                 surfaceFinish='Matte, can be smoothed',
                 # Post-processing
                 sandable=True,
                 paintable=True,
                 acetoneSmoothing=True,
                 annealable=False):
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
        return f"ABS(id='{self.id}', name='{self.name}')"
