from objectTreeDecorators import *
class polariPermissionSet(treeObject):
    @treeObjectInit
    def __init__(self, apiObject, isGeneralized=False, assignedUsers=[],assignedUserGroups=[],
    functionsAll=False, functionsSpecific=[], createAll=True, createSpecific=[],
    readAll=True, readSpecific=[], updateAll=True, updateSpecific=[], delete=True,
    filter = [] ):
        #If this is true, all people by default (even anonymous users) have access according
        #to this permission set.
        self.isGeneralized = isGeneralized
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
        