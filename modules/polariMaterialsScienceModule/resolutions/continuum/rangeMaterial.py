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
RangeMaterial Model

Represents a material with lower, average, and upper bound properties.
Used for bounding analysis and design with uncertainty.

Applications:
- Worst-case design
- Safety factor determination
- Tolerance analysis
- Design envelope studies
"""

from objectTreeDecorators import treeObjectInit
from polariMaterialsScienceModule.resolutions.continuum.continuumResolution import ContinuumResolution


class RangeMaterial(ContinuumResolution):
    """
    Material with bounded property ranges.

    Provides lower, average, and upper bounds for material properties
    to support bounding analysis.

    Attributes:
        materialId: ID reference to the parent Material
        youngsModulusLower: Lower bound Young's modulus
        youngsModulusAvg: Average Young's modulus
        youngsModulusUpper: Upper bound Young's modulus
        poissonsRatioLower: Lower bound Poisson's ratio
        poissonsRatioAvg: Average Poisson's ratio
        poissonsRatioUpper: Upper bound Poisson's ratio
    """

    @treeObjectInit
    def __init__(self,
                 manager=None,
                 branch=None,
                 id=None,
                 materialId='',
                 name='Range Material',
                 description='Material with bounded property ranges',
                 youngsModulusLower=0.0,
                 youngsModulusAvg=0.0,
                 youngsModulusUpper=0.0,
                 poissonsRatioLower=0.0,
                 poissonsRatioAvg=0.0,
                 poissonsRatioUpper=0.0,
                 densityLower=0.0,
                 densityAvg=0.0,
                 densityUpper=0.0):
        ContinuumResolution.__init__(self, manager=manager, branch=branch, id=id,
                                     materialId=materialId,
                                     name=name, description=description)
        self.youngsModulusLower = youngsModulusLower
        self.youngsModulusAvg = youngsModulusAvg
        self.youngsModulusUpper = youngsModulusUpper
        self.poissonsRatioLower = poissonsRatioLower
        self.poissonsRatioAvg = poissonsRatioAvg
        self.poissonsRatioUpper = poissonsRatioUpper
        self.densityLower = densityLower
        self.densityAvg = densityAvg
        self.densityUpper = densityUpper

    def __repr__(self):
        return f"RangeMaterial(id='{self.id}', materialId='{self.materialId}', E=[{self.youngsModulusLower}, {self.youngsModulusUpper}])"
