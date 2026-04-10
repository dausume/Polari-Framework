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
GeopolymerConcreteMoldMaterial Model

Base class for geopolymer concrete mold fabrication.
Geopolymer concrete is an alkali-activated aluminosilicate binder
(e.g., fly ash or metakaolin + sodium silicate/hydroxide) that is
cast/poured into forms to create molds.

Advantages over Portland cement for molds:
- Faster curing possible
- Better chemical resistance
- Lower shrinkage achievable
- Good compressive strength
- Can be formulated for high temperature use
"""

from objectTreeDecorators import treeObjectInit
from polariMaterialsScienceModule.purposes.moldFabrication.moldFabricationPurpose import MoldFabricationPurpose


class GeopolymerConcreteMoldMaterial(MoldFabricationPurpose):
    """
    Geopolymer concrete mold fabrication purpose.

    Defines material suitability for creating molds by casting
    geopolymer concrete into a form/pattern. The geopolymer binder
    is mixed, poured, and cured to create a rigid mold.

    Attributes:
        # Binder system
        binderType: Type of aluminosilicate source (fly_ash, metakaolin, slag, blended)
        activatorType: Alkali activator type (sodium_silicate, sodium_hydroxide, potassium_silicate, blended)
        activatorToBinderRatio: Activator to binder ratio by weight
        waterToSolidsRatio: Water to solids ratio
        silicateToHydroxideRatio: Silicate to hydroxide ratio if blended activator

        # Aggregate
        aggregateType: Type of aggregate (sand, fine_gravel, none, custom)
        aggregateSize: Maximum aggregate particle size (mm)
        aggregateToBinderRatio: Aggregate to binder ratio by weight
        aggregateSource: Where aggregate comes from

        # Mixing and casting
        mixingMethod: Mixing method (hand, drill_mixer, mechanical_mixer)
        potLife: Working time after mixing before setting (minutes)
        pouringViscosity: Qualitative pouring viscosity (thin, medium, thick)
        vibrationRequired: Whether vibration is needed to remove air bubbles
        moldReleaseAgent: Release agent for the casting form

        # Curing
        curingMethod: Curing method (ambient, heat, steam, sealed)
        curingTemperature: Curing temperature if heat-cured (C)
        curingTime: Initial cure time to demold (hours)
        fullCureTime: Time to reach full strength (days)
        curingHumidity: Humidity requirements during cure

        # Mechanical properties of the mold
        compressiveStrength: Compressive strength (MPa)
        flexuralStrength: Flexural strength (MPa)
        shrinkageDuringCure: Shrinkage during cure (%)
        porosity: Porosity level (low, moderate, high)

        # Chemical properties
        chemicalResistance: Chemical resistance description
        phResistance: pH range resistance
        waterAbsorption: Water absorption (%)

        # Mold-specific
        formType: Type of casting form used (3d_printed, cnc_machined, silicone, wood, etc.)
        formReusable: Whether the casting form is reusable
        surfaceSealerRequired: Whether surface sealer is needed after casting
        surfaceSealer: Surface sealer type if required

        Inherits all from MoldFabricationPurpose
    """

    PURPOSE_CATEGORY = 'geopolymer_concrete_mold'

    @treeObjectInit
    def __init__(self,
                 manager=None,
                 branch=None,
                 id=None,
                 materialId='',
                 name='Geopolymer Concrete Mold',
                 description='Geopolymer concrete mold fabrication by casting',
                 # MoldFabricationPurpose params
                 minFeatureSize=1.0,
                 surfaceFinishRa=6.0,
                 dimensionalAccuracy=0.5,
                 thermalStabilityMax=300.0,
                 releaseAngleMin=3.0,
                 expectedMoldLife=50,
                 postProcessingRequired='Surface sealing, sanding if needed',
                 # Binder system
                 binderType='metakaolin',
                 activatorType='sodium_silicate',
                 activatorToBinderRatio=0.5,
                 waterToSolidsRatio=0.3,
                 silicateToHydroxideRatio=2.5,
                 # Aggregate
                 aggregateType='sand',
                 aggregateSize=2.0,
                 aggregateToBinderRatio=2.0,
                 aggregateSource='',
                 # Mixing and casting
                 mixingMethod='drill_mixer',
                 potLife=30.0,
                 pouringViscosity='medium',
                 vibrationRequired=True,
                 moldReleaseAgent='',
                 # Curing
                 curingMethod='ambient',
                 curingTemperature=25.0,
                 curingTime=24.0,
                 fullCureTime=7,
                 curingHumidity='covered to retain moisture',
                 # Mechanical properties
                 compressiveStrength=40.0,
                 flexuralStrength=5.0,
                 shrinkageDuringCure=0.5,
                 porosity='moderate',
                 # Chemical properties
                 chemicalResistance='Good acid and chemical resistance',
                 phResistance='3-14',
                 waterAbsorption=5.0,
                 # Mold-specific
                 formType='',
                 formReusable=True,
                 surfaceSealerRequired=True,
                 surfaceSealer=''):
        MoldFabricationPurpose.__init__(
            self, manager=manager, branch=branch, id=id,
            materialId=materialId, name=name, description=description,
            categoryDescription='Geopolymer concrete mold casting',
            fabricationMethod='geopolymer_casting',
            minFeatureSize=minFeatureSize,
            surfaceFinishRa=surfaceFinishRa,
            dimensionalAccuracy=dimensionalAccuracy,
            thermalStabilityMax=thermalStabilityMax,
            releaseAngleMin=releaseAngleMin,
            expectedMoldLife=expectedMoldLife,
            postProcessingRequired=postProcessingRequired)

        # Binder system
        self.binderType = binderType
        self.activatorType = activatorType
        self.activatorToBinderRatio = activatorToBinderRatio
        self.waterToSolidsRatio = waterToSolidsRatio
        self.silicateToHydroxideRatio = silicateToHydroxideRatio

        # Aggregate
        self.aggregateType = aggregateType
        self.aggregateSize = aggregateSize
        self.aggregateToBinderRatio = aggregateToBinderRatio
        self.aggregateSource = aggregateSource

        # Mixing and casting
        self.mixingMethod = mixingMethod
        self.potLife = potLife
        self.pouringViscosity = pouringViscosity
        self.vibrationRequired = vibrationRequired
        self.moldReleaseAgent = moldReleaseAgent

        # Curing
        self.curingMethod = curingMethod
        self.curingTemperature = curingTemperature
        self.curingTime = curingTime
        self.fullCureTime = fullCureTime
        self.curingHumidity = curingHumidity

        # Mechanical properties
        self.compressiveStrength = compressiveStrength
        self.flexuralStrength = flexuralStrength
        self.shrinkageDuringCure = shrinkageDuringCure
        self.porosity = porosity

        # Chemical properties
        self.chemicalResistance = chemicalResistance
        self.phResistance = phResistance
        self.waterAbsorption = waterAbsorption

        # Mold-specific
        self.formType = formType
        self.formReusable = formReusable
        self.surfaceSealerRequired = surfaceSealerRequired
        self.surfaceSealer = surfaceSealer

    def __repr__(self):
        return f"GeopolymerConcreteMoldMaterial(id='{self.id}', materialId='{self.materialId}', binder='{self.binderType}')"
