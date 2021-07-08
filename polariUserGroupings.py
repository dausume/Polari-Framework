from objectTreeDecorators import *
class UserGroup(treeObject):
    @treeObjectInit
    def __init__(self, groupname=None, permissionSets=[]):
        #The Username this user leverages
        self.groupName = groupname
        #All permission sets which are granted to users of the group.
        self.permissionSets = permissionSets
        #The following are auto-generated pseudo-permission sets, which take all of
        #the defined permission sets and permission sets of sub-groups and compress
        #them into a single permission set with all of the 
        self.compressedPseudoPermissionSets = []
        #Users that were directly assigned to the group.
        self.assignedUsers = []
        #May Define a query which dynamically determines which users are members of the
        #group.
        self.userMembersFilter = []
        #If this User Group should always contains all of the users in a given group,
        #then this is a super-set of that group, while that group is a sub-set
        #of this group, and the group will appear here.
        #The actual assigned users for this Group would be self.assignedUsers +
        #all of the unique users in each of the sub-groups in this list.
        self.UserSuperGroupOf = []
        #Whenever a new user is placed in assignedUsers or a sub-group of this group,
        #then the super-groups which this group is a sub-group of will be updated
        #accordingly
        self.UserSubGroupOf = []
        #All Permissions granted to any of the Groups below are similarly applied
        #to this permission set.
        self.permissionSuperGroupOf = []
        #All permissions applied to this group are passed up to the groups on this
        #variable for their compressedPseudoPermissionSets.
        self.permissionSubGroupOf = []

    #Temporarily transforms the Permission set into a maximum-level Admin user group.
    #Such that all 
    #Begins tracing the behavior of users using this grouping to determine
    #what objects and variables are necessarily accessed, created, or modified
    #when tracing is finished, auto-generated permission sets will be created
    #for each action performed.
    #ALL COMPONENTS ON A PAGE THAT SHOULD NOT BE SHOWN FOR A USER MUST BE HIDDEN BEFORE
    #RUNNING THIS FUNCTION.  THIS WILL TEMPORARILY
    def traceAndAutoGeneratePermissions(self):
        return

