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
StochasticFiniteElementMaterial Model

Represents a material with spatially varying properties.
Properties are assigned to elements based on statistical distributions.

Used for:
- Heterogeneous materials
- Uncertainty quantification
- Monte Carlo simulations
- Reliability analysis
"""

from objectTreeDecorators import treeObjectInit
from polariMaterialsScienceModule.resolutions.continuum.continuumResolution import ContinuumResolution


class StochasticFiniteElementMaterial(ContinuumResolution):
    """
    Stochastic FEM material with spatially varying properties.

    Properties are sampled from statistical distributions to
    capture material variability and uncertainty.

    Attributes:
        materialId: ID reference to the parent Material
        meanYoungsModulus: Mean Young's modulus
        stdYoungsModulus: Standard deviation of Young's modulus
        distributionType: Statistical distribution (normal, lognormal, weibull)
        correlationLength: Spatial correlation length
        randomSeed: Seed for reproducible random sampling
    """

    @treeObjectInit
    def __init__(self,
                 manager=None,
                 branch=None,
                 id=None,
                 materialId='',
                 name='Stochastic FEM Material',
                 description='Spatially varying material properties for FEM',
                 meanYoungsModulus=0.0,
                 stdYoungsModulus=0.0,
                 meanPoissonsRatio=0.0,
                 stdPoissonsRatio=0.0,
                 meanDensity=0.0,
                 stdDensity=0.0,
                 distributionType='normal',
                 correlationLength=0.0,
                 randomSeed=None):
        ContinuumResolution.__init__(self, manager=manager, branch=branch, id=id,
                                     materialId=materialId,
                                     name=name, description=description)
        self.meanYoungsModulus = meanYoungsModulus
        self.stdYoungsModulus = stdYoungsModulus
        self.meanPoissonsRatio = meanPoissonsRatio
        self.stdPoissonsRatio = stdPoissonsRatio
        self.meanDensity = meanDensity
        self.stdDensity = stdDensity
        self.distributionType = distributionType
        self.correlationLength = correlationLength
        self.randomSeed = randomSeed

    def __repr__(self):
        return f"StochasticFiniteElementMaterial(id='{self.id}', materialId='{self.materialId}', E_mean={self.meanYoungsModulus})"
