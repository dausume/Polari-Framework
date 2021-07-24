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

from objectTreeDecorators import *
class polariPermissionSet(treeObject):
    @treeObjectInit
    def __init__(self, apiObject, Name=None, environment="all", forAllAnonymousUsers=False, forAllAuthUsers=False, assignedUsers=[],assignedUserGroups=["AdminGroup"],
    userCriteriaSharingFilter = [],
    functionsAll=False, functionsSpecific=[], createAll=True, createSpecific=[],
    readAll=True, readSpecific=[], updateAll=True, updateSpecific=[], delete=True,
    filter = [] ):
        #If this is true, all people by default (even anonymous users) have access according
        #to this permission set.
        self.Name = Name
        self.forAllAnonymousUsers = forAllAnonymousUsers
        self.forAllAuthUsers = forAllAuthUsers
        self.apiObject = apiObject
        for someUser in assignedUsers:
            print("Assuring all assigned users are actually valid user objects for the current manager object.")
        for someGroup in assignedUserGroups:
            print("Assuring all groups are valid groups for this manager.")
        self.assignedUsers = assignedUsers
        self.assignedUserGroups = assignedUserGroups
        self.functionsAll = functionsAll
        self.functionsSpecific = functionsSpecific
        self.createAll = createAll
        self.createSpecific = createSpecific
        self.readAll = readAll
        self.readSpecific = readSpecific
        self.updateAll = updateAll
        self.updateSpecific = updateSpecific
        self.delete = delete
        self.filter = filter
        