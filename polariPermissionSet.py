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
    def __init__(self, Name, forAllAnonymousUsers=False, forAllAuthUsers=False, assignedUsers={}, assignedUserGroups=["AdminGroup"], sharedUsersQuery = []):
        #If this is true, all people by default (even anonymous users) have access according
        #to this permission set.
        self.Name = Name
        #Multi-object list of query dictionaries that specify what all objects can be accessed by
        #those that have this permission set.
        self.setAccessQueries = setAccessQueries
        #List of Query Dictionaries paired with lists of variables that determine
        #which variables on given objects are allowed to be accessed.
        self.setPermissionQuery = setPermissionQuery
        #Styled like an access query, specifies by conditions what Users should have this
        #permission set.
        self.sharedUsersQuery = sharedUsersQuery
        #References to users that were directly assigned this permission set
        #format {"userId":userInst}
        self.assignedUsers = assignedUsers
        #A list of API names which this permission set should grant absolute access to.
        self.fullAPIaccess = []
        #Names of User Groups where all Users in those groups should have this
        #permission set assigned to them.
        self.assignedUserGroups = assignedUserGroups
        #Says if this group
        self.forAllAnonymousUsers = forAllAnonymousUsers
        self.forAllAuthUsers = forAllAuthUsers
        for someUser in assignedUsers:
            print("Assuring all assigned users are actually valid user objects for the current manager object.")
        for someGroup in assignedUserGroups:
            print("Assuring all groups are valid groups for this manager.")

    #Uses a query to get a set of users for the permissions to be conditionally
    #shared with.
    def getSharedUsers(self):
        if(self.sharedUsersQuery != None):
            return self.manager.getListOfInstancesByAttributes(className="polariUser", attributeQueryDict=self.sharedUsersQuery)
        return {}

    def getAssignedGroupUsers(self):
        userGroupDictsList = []
        unionedUsersDict = {}
        if(self.assignedUserGroups != None):
            for userGroupName in self.assignedUserGroups:
                usersInGroup = self.manager.userGroups[userGroupName].assignedUsers
                userGroupDictsList.append(usersInGroup)
            unionedUsersDict = set().union(*userGroupDictsList)
        return unionedUsersDict

    def isUserSharedWith(self, userInst):
        if(userInst.id in self.getSharedUsers().keys()):
            return True
        else:
            return False

    def isUserAssigned(self, userInst):
        if(userInst.id in self.assignedUsers.keys()):
            return True
        else:
            return False