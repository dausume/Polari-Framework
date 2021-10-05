import jwt
import secrets
from http import cookies
from objectTreeDecorators import treeObject, treeObjectInit

class User(treeObject):
    @treeObjectInit
    def __init__(self, username=None, password=None, unregistered=False):
        #Generally you must register as an anonymous user first, then register,
        #otherwise another user must register you by proxy.
        if(unregistered == False):
            self.username = username
            self.password = password
        else:
            #Create an anonymous / non-registered user with limited access.
            self.username = None
            self.password = None
        #A randomized secret/salt used in creating the session hash.
        self.setRandomSessionSecret()
        #Cookie that is used to identify the users session.
        self.sessionCookie = None
        #Json web token utilizing the id + username + password + secret
        self.sessionJWT = None
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
        #Access Keys this User was given, which grant specific access privilages for different Applications or Polari.
        self.accessKeys = []
        self.UIsInDB = []
        self.UIsActive = []

    def setRandomSessionSecret(self):
        self.sessionSecret = secrets.token_urlsafe(8)

    #Sets the session hash which the user utilizes to identify themselves, but NOT
    #to validate who they are.
    def setSessionHash(self):
        if(self.username == None):
            self.sessionHash = hash(self.id + self.sessionSecret)
        else:
            self.sessionHash = hash(self.id + self.password + self.sessionSecret)

    #Returns a list of all permission set objects with a userCriteriaSharingFilter value
    #that the current user
    def getAccessDicts(self):
        return []

    def getPermissionDicts(self):
        return []

    #Returns a list of all Permission sets associated/assigned to groups this user
    #belongs to.
    def getGroupPermissionSets(self):
        return []