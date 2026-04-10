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
Nylon (Polyamide) Reference Material

Strong, flexible engineering thermoplastic. Excellent wear resistance.
Very hygroscopic - requires drying. Multiple grades available (PA6, PA12, etc.)
"""

from objectTreeDecorators import treeObjectInit
from polariMaterialsScienceModule.referenceMaterials.threeDimensionalPrintable.printableReferenceMaterial import PrintableReferenceMaterial


class Nylon(PrintableReferenceMaterial):
    """
    Nylon/Polyamide (PA) reference material.

    Strong, flexible engineering material with excellent wear resistance.
    Highly hygroscopic - must be dried before printing.
    Common grades: PA6, PA66, PA12.

    Typical properties:
    - Melting point: 220-260 C (varies by grade)
    - Tensile strength: 70-85 MPa
    - Excellent wear resistance
    - High impact strength
    - Very hygroscopic

    Attributes:
        nylonGrade: Specific nylon grade (PA6, PA66, PA12, etc.)
        Inherits all from PrintableReferenceMaterial with Nylon-specific defaults
    """

    MATERIAL_TYPE = 'nylon'

    @treeObjectInit
    def __init__(self,
                 manager=None,
                 branch=None,
                 id=None,
                 name='Nylon',
                 fullName='Polyamide',
                 description='Strong, flexible engineering thermoplastic with excellent wear resistance.',
                 category='thermoplastic',
                 chemicalFormula='',
                 casNumber='',
                 materialFamily='polyamide',
                 polymerType='thermoplastic',
                 biodegradable=False,
                 foodSafe=True,
                 uvResistant=False,
                 chemicalResistance='Excellent resistance to oils, fuels, and many chemicals',
                 sourceCount=0,
                 notes='Very hygroscopic - must be dried before printing',
                 # Typical printing parameters for Nylon
                 nozzleTempTypicalMin=240.0,
                 nozzleTempTypicalMax=270.0,
                 bedTempTypicalMin=70.0,
                 bedTempTypicalMax=100.0,
                 printSpeedTypicalMin=30.0,
                 printSpeedTypicalMax=60.0,
                 # FDM characteristics
                 enclosureRecommended=True,
                 dryingRecommended=True,
                 dryingTempTypical=80.0,
                 dryingTimeTypical=12.0,
                 # Filament characteristics
                 filamentAvailable=True,
                 commonDiameters='1.75, 2.85',
                 hygroscopic=True,
                 # Print quality characteristics
                 warpingTendency='high',
                 layerAdhesion='excellent',
                 bridgingCapability='poor',
                 supportRemoval='moderate',
                 surfaceFinish='Matte, slightly waxy',
                 # Post-processing
                 sandable=True,
                 paintable=False,
                 acetoneSmoothing=False,
                 annealable=False,
                 # Nylon specific
                 nylonGrade='PA6'):
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

        self.nylonGrade = nylonGrade

    def __repr__(self):
        return f"Nylon(id='{self.id}', name='{self.name}', grade='{self.nylonGrade}')"
