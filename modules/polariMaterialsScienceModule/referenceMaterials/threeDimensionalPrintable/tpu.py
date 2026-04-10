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
TPU/TPE (Thermoplastic Polyurethane/Elastomer) Reference Material

Flexible, rubber-like material. Wide range of hardness (Shore A).
Excellent abrasion resistance and elasticity.
"""

from objectTreeDecorators import treeObjectInit
from polariMaterialsScienceModule.referenceMaterials.threeDimensionalPrintable.printableReferenceMaterial import PrintableReferenceMaterial


class TPU(PrintableReferenceMaterial):
    """
    Thermoplastic Polyurethane/Elastomer (TPU/TPE) reference material.

    Flexible, rubber-like thermoplastic elastomer. Wide range of
    hardness available (typically Shore 85A-95A for filament).
    Excellent abrasion and impact resistance.

    Typical properties:
    - Shore hardness: 85A-95A (filament range)
    - Tensile strength: 30-50 MPa
    - Elongation at break: 300-600%
    - Excellent abrasion resistance
    - Requires direct drive extruder ideally

    Attributes:
        shoreHardness: Shore A hardness rating
        elongationAtBreak: Typical elongation at break (%)
        Inherits all from PrintableReferenceMaterial with TPU-specific defaults
    """

    MATERIAL_TYPE = 'tpu'

    @treeObjectInit
    def __init__(self,
                 manager=None,
                 branch=None,
                 id=None,
                 name='TPU',
                 fullName='Thermoplastic Polyurethane',
                 description='Flexible, rubber-like thermoplastic elastomer with excellent abrasion resistance.',
                 category='thermoplastic',
                 chemicalFormula='',
                 casNumber='',
                 materialFamily='polyurethane',
                 polymerType='elastomer',
                 biodegradable=False,
                 foodSafe=False,
                 uvResistant=True,
                 chemicalResistance='Good resistance to oils, greases, and many solvents',
                 sourceCount=0,
                 notes='Direct drive extruder recommended for softer grades',
                 # Typical printing parameters for TPU
                 nozzleTempTypicalMin=210.0,
                 nozzleTempTypicalMax=240.0,
                 bedTempTypicalMin=40.0,
                 bedTempTypicalMax=60.0,
                 printSpeedTypicalMin=15.0,
                 printSpeedTypicalMax=40.0,
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
                 layerAdhesion='excellent',
                 bridgingCapability='poor',
                 supportRemoval='difficult',
                 surfaceFinish='Smooth, slightly rubbery',
                 # Post-processing
                 sandable=False,
                 paintable=False,
                 acetoneSmoothing=False,
                 annealable=False,
                 # TPU specific
                 shoreHardness='95A',
                 elongationAtBreak=450.0):
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

        self.shoreHardness = shoreHardness
        self.elongationAtBreak = elongationAtBreak

    def __repr__(self):
        return f"TPU(id='{self.id}', name='{self.name}', shore='{self.shoreHardness}')"
