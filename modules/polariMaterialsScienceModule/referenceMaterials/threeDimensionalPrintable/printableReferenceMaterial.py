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
PrintableReferenceMaterial Model

Base class for reference materials that are commonly used in FDM 3D printing.
These materials have well-documented printing parameters and material properties.
"""

from objectTreeDecorators import treeObjectInit
from polariMaterialsScienceModule.referenceMaterials.referenceMaterial import ReferenceMaterial


class PrintableReferenceMaterial(ReferenceMaterial):
    """
    Base class for FDM 3D printable reference materials.

    Extends ReferenceMaterial with typical printing parameters
    and FDM-relevant characteristics.

    Attributes:
        # Typical printing parameters (ranges)
        nozzleTempTypicalMin: Typical minimum nozzle temp (C)
        nozzleTempTypicalMax: Typical maximum nozzle temp (C)
        bedTempTypicalMin: Typical minimum bed temp (C)
        bedTempTypicalMax: Typical maximum bed temp (C)
        printSpeedTypicalMin: Typical minimum print speed (mm/s)
        printSpeedTypicalMax: Typical maximum print speed (mm/s)

        # FDM characteristics
        enclosureRecommended: Whether enclosure is recommended
        dryingRecommended: Whether drying before printing is recommended
        dryingTempTypical: Typical drying temperature (C)
        dryingTimeTypical: Typical drying time (hours)

        # Filament characteristics
        filamentAvailable: Whether commonly available as filament
        commonDiameters: Common filament diameters available
        hygroscopic: Whether material absorbs moisture

        # Print quality characteristics
        warpingTendency: Warping tendency (low, medium, high)
        layerAdhesion: Layer adhesion quality (poor, moderate, good, excellent)
        bridgingCapability: Bridging capability (poor, moderate, good)
        supportRemoval: Support removal ease (difficult, moderate, easy)
        surfaceFinish: Typical surface finish quality

        # Post-processing
        sandable: Whether material can be sanded
        paintable: Whether material can be painted
        acetoneSmoothing: Whether acetone smoothing works
        annealable: Whether material can be annealed

    Class Constants:
        RELEVANT_PROPERTIES: Properties from ThreeDimensionalPrintable that apply
    """

    MATERIAL_TYPE = 'printable_reference'

    # Properties relevant to 3D printability (from ThreeDimensionalPrintable)
    RELEVANT_PROPERTIES = [
        'Elasticity',
        'Hardness',
        'Viscosity',
        'SolidSurfaceEnergy',
        'LiquidSurfaceTension',
        'TensileStrength',
        'MeltingPoint',
        'ThermalExpansion',
        'GlassTransition',
        'SmokingPoint',
        'MeltFlowIndex'
    ]

    @treeObjectInit
    def __init__(self,
                 manager=None,
                 branch=None,
                 id=None,
                 name='',
                 fullName='',
                 description='',
                 category='thermoplastic',
                 chemicalFormula='',
                 casNumber='',
                 materialFamily='',
                 polymerType='thermoplastic',
                 biodegradable=False,
                 foodSafe=False,
                 uvResistant=False,
                 chemicalResistance='',
                 sourceCount=0,
                 notes='',
                 # Typical printing parameters
                 nozzleTempTypicalMin=0.0,
                 nozzleTempTypicalMax=0.0,
                 bedTempTypicalMin=0.0,
                 bedTempTypicalMax=0.0,
                 printSpeedTypicalMin=0.0,
                 printSpeedTypicalMax=0.0,
                 # FDM characteristics
                 enclosureRecommended=False,
                 dryingRecommended=False,
                 dryingTempTypical=0.0,
                 dryingTimeTypical=0.0,
                 # Filament characteristics
                 filamentAvailable=True,
                 commonDiameters='1.75, 2.85',
                 hygroscopic=False,
                 # Print quality characteristics
                 warpingTendency='low',
                 layerAdhesion='good',
                 bridgingCapability='moderate',
                 supportRemoval='moderate',
                 surfaceFinish='',
                 # Post-processing
                 sandable=True,
                 paintable=True,
                 acetoneSmoothing=False,
                 annealable=False):
        ReferenceMaterial.__init__(
            self, manager=manager, branch=branch, id=id,
            name=name, fullName=fullName, description=description,
            category=category, chemicalFormula=chemicalFormula,
            casNumber=casNumber, materialFamily=materialFamily,
            polymerType=polymerType, biodegradable=biodegradable,
            foodSafe=foodSafe, uvResistant=uvResistant,
            chemicalResistance=chemicalResistance,
            sourceCount=sourceCount, notes=notes)

        # Typical printing parameters
        self.nozzleTempTypicalMin = nozzleTempTypicalMin
        self.nozzleTempTypicalMax = nozzleTempTypicalMax
        self.bedTempTypicalMin = bedTempTypicalMin
        self.bedTempTypicalMax = bedTempTypicalMax
        self.printSpeedTypicalMin = printSpeedTypicalMin
        self.printSpeedTypicalMax = printSpeedTypicalMax

        # FDM characteristics
        self.enclosureRecommended = enclosureRecommended
        self.dryingRecommended = dryingRecommended
        self.dryingTempTypical = dryingTempTypical
        self.dryingTimeTypical = dryingTimeTypical

        # Filament characteristics
        self.filamentAvailable = filamentAvailable
        self.commonDiameters = commonDiameters
        self.hygroscopic = hygroscopic

        # Print quality characteristics
        self.warpingTendency = warpingTendency
        self.layerAdhesion = layerAdhesion
        self.bridgingCapability = bridgingCapability
        self.supportRemoval = supportRemoval
        self.surfaceFinish = surfaceFinish

        # Post-processing
        self.sandable = sandable
        self.paintable = paintable
        self.acetoneSmoothing = acetoneSmoothing
        self.annealable = annealable

    def __repr__(self):
        return f"PrintableReferenceMaterial(id='{self.id}', name='{self.name}')"
