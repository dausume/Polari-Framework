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
DataProvenance Model

Container for credibility metadata attachable to any data point.
Tracks version, credibility level, and links to individual data sources.
"""

from objectTreeDecorators import treeObject, treeObjectInit


class DataProvenance(treeObject):
    """
    Credibility metadata container for any data point in the system.

    Attributes:
        version: Version string for this provenance record
        credibilityLevel: Overall credibility (verified, peer_reviewed,
            manufacturer_stated, community_consensus, unverified)
        sourceIds: Comma-separated list of DataSource IDs backing this record
        notes: Additional notes about data credibility
    """

    @treeObjectInit
    def __init__(self,
                 manager=None,
                 branch=None,
                 id=None,
                 version='',
                 credibilityLevel='unverified',
                 sourceIds='',
                 notes=''):
        treeObject.__init__(self, manager=manager, branch=branch, id=id)
        self.version = version
        self.credibilityLevel = credibilityLevel
        self.sourceIds = sourceIds
        self.notes = notes

    def __repr__(self):
        return f"DataProvenance(id='{getattr(self, 'id', '?')}', credibility='{getattr(self, 'credibilityLevel', '?')}')"
