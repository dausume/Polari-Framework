class User():
    def __init__(self, username=None):
        #The Username this user leverages
        self.username = username
        #Groups the user is assigned to, these groups may grant permissions.
        self.groups = []
        #Permission sets which have been assigned to the specific user.
        self.assignedPermissionSets = []
        #Permission sets where the given user meets the filter criteria defined by
        #the variable userCriteriaSharingFilter on the PS.
        self.criteriaSharedPermissionSets = []
        self.managerAccess = []
        self.appAccess = []
        self.pageAccess = []
        #Pages this User has for different applications.
        #Holds onto things such as partially entered but not submitted data or
        #objects that are generated purely for the purpose of interfacing and designed
        #EX: The user is designing an AI, the specific configuration of how that model
        #appears on their Interface and how it has been modified to help them analyze it
        #that sort of data to render such a view and present it again in the future would
        #be saved here.
        self.customizedPages = []
        self.identifier = None
        #The Password this user chooses for accessing their account.
        self.password = None
        #Access Keys this User was given, which grant specific access privilages for different Applications or Polari.
        self.accessKeys = []
        self.UIsInDB = []
        self.UIsActive = []

    #Returns a list of all permission set objects with a userCriteriaSharingFilter value
    #that the current user
    def getCriteriaSharedPermissionSets(self):
        return []

    #Returns a list of all Permission sets associated/assigned to groups this user
    #belongs to.
    def getGroupPermissionSets(self):
        return []