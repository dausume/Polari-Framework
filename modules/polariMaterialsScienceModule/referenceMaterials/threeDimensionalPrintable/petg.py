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
PETG (Polyethylene Terephthalate Glycol-modified) Reference Material

Balance of ease-of-printing and mechanical properties.
Good chemical resistance, food-safe grades available.
"""

from objectTreeDecorators import treeObjectInit
from polariMaterialsScienceModule.referenceMaterials.threeDimensionalPrintable.printableReferenceMaterial import PrintableReferenceMaterial


class PETG(PrintableReferenceMaterial):
    """
    Polyethylene Terephthalate Glycol-modified (PETG) reference material.

    Combines ease of PLA printing with better mechanical properties.
    Good chemical resistance and clarity. Food-safe grades available.

    Typical properties:
    - Glass transition: 80 C
    - Tensile strength: 50 MPa
    - Good impact resistance
    - Low warping
    - Good layer adhesion

    Attributes:
        Inherits all from PrintableReferenceMaterial with PETG-specific defaults
    """

    MATERIAL_TYPE = 'petg'

    @treeObjectInit
    def __init__(self,
                 manager=None,
                 branch=None,
                 id=None,
                 name='PETG',
                 fullName='Polyethylene Terephthalate Glycol-modified',
                 description='Balance of printability and strength. Good chemical resistance.',
                 category='thermoplastic',
                 chemicalFormula='(C10H8O4)n',
                 casNumber='25038-91-9',
                 materialFamily='polyester',
                 polymerType='thermoplastic',
                 biodegradable=False,
                 foodSafe=True,
                 uvResistant=False,
                 chemicalResistance='Good resistance to chemicals, oils, and greases',
                 sourceCount=0,
                 notes='Can be stringy - tuning retraction helps',
                 # Typical printing parameters for PETG
                 nozzleTempTypicalMin=220.0,
                 nozzleTempTypicalMax=250.0,
                 bedTempTypicalMin=70.0,
                 bedTempTypicalMax=85.0,
                 printSpeedTypicalMin=30.0,
                 printSpeedTypicalMax=70.0,
                 # FDM characteristics
                 enclosureRecommended=False,
                 dryingRecommended=True,
                 dryingTempTypical=65.0,
                 dryingTimeTypical=4.0,
                 # Filament characteristics
                 filamentAvailable=True,
                 commonDiameters='1.75, 2.85',
                 hygroscopic=True,
                 # Print quality characteristics
                 warpingTendency='low',
                 layerAdhesion='excellent',
                 bridgingCapability='moderate',
                 supportRemoval='difficult',
                 surfaceFinish='Glossy, slightly transparent',
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
        return f"PETG(id='{self.id}', name='{self.name}')"
