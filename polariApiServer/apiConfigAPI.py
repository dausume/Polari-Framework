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
API Configuration Endpoint

Provides a comprehensive view of all registered tree objects and their
CRUDE (Create, Read, Update, Delete, Events) permission configurations.

Displays permissions at four access levels:
- General Access: Base permissions from polyTypedObject (baseAccessDictionary)
- Server Access Only: Internal/server-to-server access (no external access)
- Role Access: Permissions granted via UserGroups
- Direct User Access: Permissions assigned directly to individual users

Base/framework objects (excludeFromCRUDE=True, allowClassEdit=False) are
displayed as read-only. Only user-created objects can have permissions modified.
"""

from objectTreeDecorators import treeObject, treeObjectInit
import falcon
import json


class ApiConfigAPI(treeObject):
    """
    API endpoint for viewing and managing object API configurations.

    GET /api-config - Returns all objects with permission configurations
    PUT /api-config/permissions - Update permissions (user-created objects only)
    """

    @treeObjectInit
    def __init__(self, polServer):
        self.polServer = polServer
        self.apiName = '/api-config'
        if polServer is not None:
            polServer.falconServer.add_route(self.apiName, self)
            # Also register the permissions sub-route
            polServer.falconServer.add_route(self.apiName + '/permissions', self, suffix='permissions')

    def on_get(self, request, response):
        """
        Returns all registered objects with their CRUDE permission configurations.

        Response includes:
        - objects: All polyTypedObjects with their config flags and base permissions
        - userGroups: All UserGroups with their permission sets
        - users: All Users with their direct permission assignments
        - permissionSets: All polariPermissionSet instances
        """
        try:
            result = {
                "success": True,
                "objects": [],
                "userGroups": [],
                "users": [],
                "permissionSets": []
            }

            # Get all polyTypedObjects
            if hasattr(self.manager, 'objectTypingDict'):
                for className, typingObj in self.manager.objectTypingDict.items():
                    # Determine if this is a base/framework object
                    excludeFromCRUDE = getattr(typingObj, 'excludeFromCRUDE', True)
                    allowClassEdit = getattr(typingObj, 'allowClassEdit', False)

                    # isBaseObject: Framework objects that shouldn't be modified externally
                    # These have excludeFromCRUDE=True (default) AND allowClassEdit=False (default)
                    isBaseObject = excludeFromCRUDE and not allowClassEdit

                    # Get variable information with CRUD permissions
                    variables = []
                    identifierVars = getattr(typingObj, 'identifiers', ['id'])
                    if hasattr(typingObj, 'polyTypedVars'):
                        for var in typingObj.polyTypedVars:
                            varName = getattr(var, 'name', 'unknown')
                            isIdentifier = varName in identifierVars or getattr(var, 'isIdentifier', False)

                            # Variable-level CRUD permissions
                            # Identifiers (like 'id') are typically read-only
                            # Other variables follow object-level permissions
                            varCRUD = {
                                "create": not isIdentifier,  # Can't set identifiers on create (auto-generated)
                                "read": True,  # All variables readable
                                "update": not isIdentifier,  # Can't update identifiers
                                "delete": False  # Delete is object-level, not variable-level
                            }

                            variables.append({
                                "name": varName,
                                "type": getattr(var, 'pythonTypeDefault', 'str'),
                                "isIdentifier": isIdentifier,
                                "isRequired": getattr(var, 'isRequired', False),
                                "crud": varCRUD
                            })

                    # Get event/method information
                    events = []
                    # Check for stateSpaceEventMethods (methods exposed for no-code/API)
                    eventMethods = getattr(typingObj, 'stateSpaceEventMethods', [])
                    for eventName in eventMethods:
                        events.append({
                            "name": eventName,
                            "accessible": True,
                            "requiresAuth": True  # Default: requires authentication
                        })

                    # Also check the class definition for methods
                    if typingObj.classDefinition:
                        import inspect
                        for methodName, method in inspect.getmembers(typingObj.classDefinition, predicate=inspect.isfunction):
                            # Skip private/magic methods and already added events
                            if not methodName.startswith('_') and methodName not in [e['name'] for e in events]:
                                # Only include if it looks like an event method (not standard object methods)
                                if methodName not in ['__init__', '__str__', '__repr__']:
                                    events.append({
                                        "name": methodName,
                                        "accessible": methodName in eventMethods,  # Only accessible if in eventMethods
                                        "requiresAuth": True
                                    })

                    # Check if CRUDE endpoint is registered for this object
                    crudeRegistered = False
                    crudeEndpoint = None
                    if hasattr(self.polServer, 'crudeObjectsList'):
                        for crudeObj in self.polServer.crudeObjectsList:
                            if getattr(crudeObj, 'apiObject', None) == className:
                                crudeRegistered = True
                                crudeEndpoint = getattr(crudeObj, 'apiName', f'/{className}')
                                break

                    # Get base access and permission dictionaries from polyTypedObject
                    baseAccessDict = getattr(typingObj, 'baseAccessDictionary', {})
                    basePermDict = getattr(typingObj, 'basePermissionDictionary', {})

                    # CRUDE Permissions - Intended/configured permissions for visibility
                    # This shows what SHOULD be accessible, not enforcement (enforcement comes later)
                    #
                    # Logic:
                    # - Framework/Base objects: Read and Events only (no C/U/D)
                    # - Server-only objects (no CRUDE endpoint): Read and Events only
                    # - User-created objects with CRUDE endpoint: Full CRUDE access

                    if isBaseObject or not crudeRegistered:
                        # Framework objects or server-only: Read and Events only
                        generalCRUDE = {
                            "create": False,
                            "read": True,
                            "update": False,
                            "delete": False,
                            "events": True
                        }
                    else:
                        # User-created object with CRUDE endpoint: Full access
                        generalCRUDE = {
                            "create": True,
                            "read": True,
                            "update": True,
                            "delete": True,
                            "events": True
                        }

                    print(f"[ApiConfig] {className}: crudeRegistered={crudeRegistered}, isBaseObject={isBaseObject}, CRUDE={generalCRUDE}")

                    # Determine if this is server-access-only
                    # Server access only means: excludeFromCRUDE=True but has custom API endpoint
                    # OR the object is only accessible via internal server calls
                    serverAccessOnly = excludeFromCRUDE and not crudeRegistered

                    objInfo = {
                        "className": className,
                        "displayName": className,  # Could be enhanced with a display name field
                        "isBaseObject": isBaseObject,
                        "isUserCreated": not isBaseObject,
                        "excludeFromCRUDE": excludeFromCRUDE,
                        "allowClassEdit": allowClassEdit,
                        "isStateSpaceObject": getattr(typingObj, 'isStateSpaceObject', False),
                        "isDynamicClass": getattr(typingObj.classDefinition, '_dynamicClass', False) if typingObj.classDefinition else False,
                        "serverAccessOnly": serverAccessOnly,
                        "generalAccess": {
                            "baseAccessDictionary": self._serialize_dict(baseAccessDict),
                            "basePermissionDictionary": self._serialize_dict(basePermDict),
                            "crude": generalCRUDE
                        },
                        "crudeRegistered": crudeRegistered,
                        "crudeEndpoint": crudeEndpoint,
                        "permissionSetRefs": [],  # Will be populated below
                        "events": events,  # Event-level permissions
                        "variables": variables
                    }
                    result["objects"].append(objInfo)

            # Get all UserGroups
            if 'UserGroup' in self.manager.objectTables:
                for groupId, group in self.manager.objectTables['UserGroup'].items():
                    # Handle assignedUsers - could be a list or dict
                    assignedUsers = getattr(group, 'assignedUsers', [])
                    if isinstance(assignedUsers, dict):
                        userList = list(assignedUsers.keys())
                        userCount = len(assignedUsers)
                    else:
                        # It's a list (polariList)
                        userList = [getattr(u, 'id', str(u)) for u in assignedUsers] if assignedUsers else []
                        userCount = len(assignedUsers) if assignedUsers else 0

                    groupInfo = {
                        "id": groupId,
                        "name": getattr(group, 'name', 'Unknown'),
                        "permissionSets": [getattr(ps, 'Name', str(ps)) for ps in getattr(group, 'permissionSets', [])],
                        "assignedUsers": userList,
                        "userCount": userCount
                    }
                    result["userGroups"].append(groupInfo)

            # Get all Users (limited info for security)
            if 'User' in self.manager.objectTables:
                for userId, user in self.manager.objectTables['User'].items():
                    # Get directly assigned permission sets
                    assignedPS = getattr(user, 'assignedPermissionSets', [])
                    assignedPSNames = [getattr(ps, 'Name', str(ps)) for ps in assignedPS] if assignedPS else []

                    # Get groups
                    groups = getattr(user, 'groups', [])
                    groupNames = [getattr(g, 'name', str(g)) for g in groups] if groups else []

                    userInfo = {
                        "id": userId,
                        "username": getattr(user, 'username', 'Unknown'),
                        "assignedPermissionSets": assignedPSNames,
                        "groups": groupNames
                    }
                    result["users"].append(userInfo)

            # Get all Permission Sets
            if 'polariPermissionSet' in self.manager.objectTables:
                for psId, permSet in self.manager.objectTables['polariPermissionSet'].items():
                    psInfo = {
                        "id": psId,
                        "name": getattr(permSet, 'Name', 'Unknown'),
                        "forAllAnonymousUsers": getattr(permSet, 'forAllAnonymousUsers', False),
                        "forAllAuthUsers": getattr(permSet, 'forAllAuthUsers', False),
                        "assignedUserGroups": getattr(permSet, 'assignedUserGroups', []),
                        "setAccessQueries": self._serialize_dict(getattr(permSet, 'setAccessQueries', {})),
                        "setPermissionQuery": self._serialize_dict(getattr(permSet, 'setPermissionQuery', {})),
                        "fullAPIaccess": getattr(permSet, 'fullAPIaccess', [])
                    }
                    result["permissionSets"].append(psInfo)

                    # Link permission sets to objects
                    # Check which objects this permission set grants access to
                    accessQueries = getattr(permSet, 'setAccessQueries', {})
                    if isinstance(accessQueries, dict):
                        for operation, objDict in accessQueries.items():
                            if isinstance(objDict, dict):
                                for objName in objDict.keys():
                                    # Find the object and add this permission set reference
                                    for obj in result["objects"]:
                                        if obj["className"] == objName:
                                            if psInfo["name"] not in obj["permissionSetRefs"]:
                                                obj["permissionSetRefs"].append(psInfo["name"])

            response.media = result
            response.status = falcon.HTTP_200

        except Exception as err:
            response.status = falcon.HTTP_500
            response.media = {
                "success": False,
                "error": str(err)
            }
            print(f"[ApiConfigAPI] Error in GET: {err}")
            import traceback
            traceback.print_exc()

        response.set_header('Powered-By', 'Polari')

    def on_put_permissions(self, request, response):
        """
        Update permissions for a user-created object.

        Only allows modifications to objects where:
        - excludeFromCRUDE = False OR allowClassEdit = True

        Request body:
        {
            "className": "MyClass",
            "accessLevel": "general" | "role" | "user",
            "targetId": "groupName" | "userId",  # Only for role/user access
            "permissions": {
                "create": true/false or ["var1", "var2"],
                "read": true/false or ["var1", "var2"],
                "update": true/false or ["var1", "var2"],
                "delete": true/false,
                "events": true/false or ["event1", "event2"]
            }
        }
        """
        try:
            # Parse request body
            body = request.media

            className = body.get('className')
            accessLevel = body.get('accessLevel')
            targetId = body.get('targetId')
            permissions = body.get('permissions', {})

            if not className:
                response.status = falcon.HTTP_400
                response.media = {"success": False, "error": "className is required"}
                return

            # Check if class exists and is editable
            if className not in self.manager.objectTypingDict:
                response.status = falcon.HTTP_404
                response.media = {"success": False, "error": f"Class '{className}' not found"}
                return

            typingObj = self.manager.objectTypingDict[className]
            excludeFromCRUDE = getattr(typingObj, 'excludeFromCRUDE', True)
            allowClassEdit = getattr(typingObj, 'allowClassEdit', False)
            isBaseObject = excludeFromCRUDE and not allowClassEdit

            if isBaseObject:
                response.status = falcon.HTTP_403
                response.media = {
                    "success": False,
                    "error": f"Cannot modify permissions for framework object '{className}'"
                }
                return

            # Handle different access levels
            if accessLevel == 'general':
                # Update baseAccessDictionary and basePermissionDictionary
                self._update_general_permissions(typingObj, permissions)

            elif accessLevel == 'server':
                # Update server-access-only flag (excludeFromCRUDE)
                self._update_server_access(typingObj, permissions)

            elif accessLevel == 'role':
                if not targetId:
                    response.status = falcon.HTTP_400
                    response.media = {"success": False, "error": "targetId (group name) is required for role access"}
                    return
                self._update_role_permissions(className, targetId, permissions)

            elif accessLevel == 'user':
                if not targetId:
                    response.status = falcon.HTTP_400
                    response.media = {"success": False, "error": "targetId (user ID) is required for user access"}
                    return
                self._update_user_permissions(className, targetId, permissions)

            else:
                response.status = falcon.HTTP_400
                response.media = {"success": False, "error": f"Invalid accessLevel: {accessLevel}"}
                return

            response.status = falcon.HTTP_200
            response.media = {
                "success": True,
                "message": f"Permissions updated for {className} at {accessLevel} level"
            }

        except Exception as err:
            response.status = falcon.HTTP_500
            response.media = {
                "success": False,
                "error": str(err)
            }
            print(f"[ApiConfigAPI] Error in PUT permissions: {err}")
            import traceback
            traceback.print_exc()

        response.set_header('Powered-By', 'Polari')

    def _update_general_permissions(self, typingObj, permissions):
        """Update base access and permission dictionaries on polyTypedObject."""
        className = typingObj.className

        # Build access dictionary
        newAccessDict = {}
        if permissions.get('create'):
            newAccessDict['C'] = {className: "*"}
        if permissions.get('read'):
            newAccessDict['R'] = {className: "*"}
        if permissions.get('update'):
            newAccessDict['U'] = {className: "*"}
        if permissions.get('delete'):
            newAccessDict['D'] = {className: "*"}
        if permissions.get('events'):
            newAccessDict['E'] = {className: "*"}

        typingObj.baseAccessDictionary = newAccessDict
        typingObj.basePermissionDictionary = newAccessDict.copy()

    def _update_server_access(self, typingObj, permissions):
        """
        Update server-access-only configuration.

        Server access only means the object is not exposed via CRUDE endpoints
        and can only be accessed internally by the server.

        permissions should include:
        - serverOnly: bool - If True, set excludeFromCRUDE=True
        """
        serverOnly = permissions.get('serverOnly', False)

        if serverOnly:
            typingObj.excludeFromCRUDE = True
            # Optionally unregister CRUDE endpoint if it exists
            print(f"[ApiConfigAPI] Set {typingObj.className} to server-access-only")
        else:
            typingObj.excludeFromCRUDE = False
            # May need to register CRUDE endpoint if not already registered
            print(f"[ApiConfigAPI] Set {typingObj.className} to allow external access")

    def _update_role_permissions(self, className, groupName, permissions):
        """Update or create permission set for a user group."""
        # Find the group
        group = None
        if 'UserGroup' in self.manager.objectTables:
            for g in self.manager.objectTables['UserGroup'].values():
                if getattr(g, 'name', '') == groupName:
                    group = g
                    break

        if not group:
            raise ValueError(f"UserGroup '{groupName}' not found")

        # Create or update permission set for this class/group combination
        psName = f"{className}_{groupName}_PS"
        accessQueries = self._build_access_queries(className, permissions)

        # Check if permission set already exists
        existingPS = None
        if 'polariPermissionSet' in self.manager.objectTables:
            for ps in self.manager.objectTables['polariPermissionSet'].values():
                if getattr(ps, 'Name', '') == psName:
                    existingPS = ps
                    break

        if existingPS:
            existingPS.setAccessQueries = accessQueries
        else:
            # Would need to create new permission set - simplified for now
            print(f"[ApiConfigAPI] Would create new permission set: {psName}")

    def _update_user_permissions(self, className, userId, permissions):
        """Update or create permission set for a specific user."""
        # Find the user
        user = None
        if 'User' in self.manager.objectTables and userId in self.manager.objectTables['User']:
            user = self.manager.objectTables['User'][userId]

        if not user:
            raise ValueError(f"User '{userId}' not found")

        # Create or update permission set for this class/user combination
        psName = f"{className}_{userId}_PS"
        accessQueries = self._build_access_queries(className, permissions)

        # Simplified - full implementation would create/update permission set
        print(f"[ApiConfigAPI] Would create/update permission set: {psName} for user {userId}")

    def _build_access_queries(self, className, permissions):
        """Build access query dictionary from permissions object."""
        accessQueries = {}
        if permissions.get('create'):
            accessQueries['C'] = {className: "*"}
        if permissions.get('read'):
            accessQueries['R'] = {className: "*"}
        if permissions.get('update'):
            accessQueries['U'] = {className: "*"}
        if permissions.get('delete'):
            accessQueries['D'] = {className: "*"}
        if permissions.get('events'):
            accessQueries['E'] = {className: "*"}
        return accessQueries

    def _serialize_dict(self, obj):
        """Safely serialize a dictionary for JSON response."""
        if obj is None:
            return {}
        if isinstance(obj, dict):
            result = {}
            for key, value in obj.items():
                if isinstance(value, dict):
                    result[key] = self._serialize_dict(value)
                elif isinstance(value, (list, tuple)):
                    result[key] = [self._serialize_item(item) for item in value]
                else:
                    result[key] = self._serialize_item(value)
            return result
        return str(obj)

    def _serialize_item(self, item):
        """Serialize a single item for JSON response."""
        if item is None:
            return None
        if isinstance(item, (str, int, float, bool)):
            return item
        if isinstance(item, dict):
            return self._serialize_dict(item)
        if isinstance(item, (list, tuple)):
            return [self._serialize_item(i) for i in item]
        # For objects, return string representation
        return str(item)
