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
APIProfile - Data model for storing API response profile metadata.

An APIProfile stores information about an external API's response structure,
leveraging Polari's existing polyTypedObject system for type analysis.
"""

from objectTreeDecorators import treeObject, treeObjectInit
from typing import Dict, List, Optional, Any


class APIProfile(treeObject):
    """
    Stores metadata about an API profile including the analyzed type structure.

    Instead of duplicating type analysis, APIProfile holds a reference to a
    polyTypedObject that contains all the typing information analyzed using
    Polari's existing system.

    Attributes:
        profileName: Unique identifier for this profile
        displayName: Human-readable name for display
        description: Description of what this API/profile represents
        apiEndpoint: The API endpoint URL this profile was created from
        httpMethod: HTTP method used (GET, POST, etc.)
        responseRootPath: JSONPath to the data array (e.g., "data.items")
        polyTypedObjectRef: Reference to the polyTypedObject with typing data
        objectTypeField: Field name indicating object type for multi-type responses
        objectTypeMapping: Maps type field values to sub-profile names
        storedCredentials: Optional encrypted credentials for the API
        defaultHeaders: Default headers to include with requests
        isTemplate: True for pre-defined/built-in templates
        matchConfidenceThreshold: Minimum confidence score to consider a match
        sampleCount: Number of samples used to build this profile
        fieldSignatures: Set of field names present in analyzed samples
    """

    @treeObjectInit
    def __init__(
        self,
        profileName: str = '',
        displayName: str = '',
        description: str = '',
        apiEndpoint: str = '',
        httpMethod: str = 'GET',
        responseRootPath: str = '',
        polyTypedObjectRef: str = None,  # className of the associated polyTypedObject
        objectTypeField: str = '',
        objectTypeMapping: Dict[str, str] = None,
        storedCredentials: str = '',  # Encrypted credentials
        defaultHeaders: Dict[str, str] = None,
        isTemplate: bool = False,
        matchConfidenceThreshold: float = 0.7,
        sampleCount: int = 0,
        fieldSignatures: List[str] = None,
        manager=None,
        **kwargs
    ):
        self.profileName = profileName
        self.displayName = displayName or profileName
        self.description = description
        self.apiEndpoint = apiEndpoint
        self.httpMethod = httpMethod.upper() if httpMethod else 'GET'
        self.responseRootPath = responseRootPath
        self.polyTypedObjectRef = polyTypedObjectRef
        self.objectTypeField = objectTypeField
        self.objectTypeMapping = objectTypeMapping or {}
        self.storedCredentials = storedCredentials
        self.defaultHeaders = defaultHeaders or {}
        self.isTemplate = isTemplate
        self.matchConfidenceThreshold = max(0.0, min(1.0, matchConfidenceThreshold))
        self.sampleCount = sampleCount
        self.fieldSignatures = fieldSignatures or []

        # Track child profiles for multi-type APIs
        self.childProfiles = []

        # Metadata about when the profile was created/updated
        self.createdFromUrl = ''
        self.lastUpdated = ''

    def get_poly_typed_object(self):
        """
        Retrieve the associated polyTypedObject from the manager.

        Returns:
            polyTypedObject or None if not found
        """
        if not self.polyTypedObjectRef or not self.manager:
            return None
        return self.manager.objectTypingDict.get(self.polyTypedObjectRef)

    def set_poly_typed_object(self, poly_typed_obj):
        """
        Associate a polyTypedObject with this profile.

        Args:
            poly_typed_obj: The polyTypedObject to associate
        """
        if poly_typed_obj:
            self.polyTypedObjectRef = poly_typed_obj.className

    def get_field_names(self) -> List[str]:
        """
        Get the list of field names from the associated polyTypedObject.

        Returns:
            List of field names
        """
        pto = self.get_poly_typed_object()
        if pto:
            return [v.name for v in pto.polyTypedVars]
        return self.fieldSignatures

    def get_field_types(self) -> Dict[str, str]:
        """
        Get a mapping of field names to their Python types.

        Returns:
            Dict mapping field name to type string
        """
        pto = self.get_poly_typed_object()
        if pto:
            return {v.name: v.pythonTypeDefault for v in pto.polyTypedVars}
        return {}

    def get_required_fields(self) -> List[str]:
        """
        Get fields that are always present (required) based on analysis.

        For now, returns all fields. Could be enhanced to track which fields
        were present in all samples vs optional fields.

        Returns:
            List of required field names
        """
        return self.fieldSignatures.copy()

    def add_child_profile(self, child_profile: 'APIProfile'):
        """
        Add a child profile for multi-type API responses.

        Args:
            child_profile: The child APIProfile to add
        """
        if child_profile.profileName not in [c for c in self.childProfiles]:
            self.childProfiles.append(child_profile.profileName)

    def get_child_profiles(self) -> List['APIProfile']:
        """
        Retrieve all child profiles from the manager.

        Returns:
            List of child APIProfile instances
        """
        if not self.manager:
            return []

        children = []
        profiles = self.manager.getListOfClassInstances('APIProfile')
        for profile in profiles:
            if profile.profileName in self.childProfiles:
                children.append(profile)
        return children

    def to_dict(self) -> dict:
        """
        Convert profile to dictionary for JSON serialization.

        Returns:
            Dictionary representation of the profile
        """
        return {
            'id': self.id if hasattr(self, 'id') else None,
            'profileName': self.profileName,
            'displayName': self.displayName,
            'description': self.description,
            'apiEndpoint': self.apiEndpoint,
            'httpMethod': self.httpMethod,
            'responseRootPath': self.responseRootPath,
            'polyTypedObjectRef': self.polyTypedObjectRef,
            'objectTypeField': self.objectTypeField,
            'objectTypeMapping': self.objectTypeMapping,
            'defaultHeaders': self.defaultHeaders,
            'isTemplate': self.isTemplate,
            'matchConfidenceThreshold': self.matchConfidenceThreshold,
            'sampleCount': self.sampleCount,
            'fieldSignatures': self.fieldSignatures,
            'childProfiles': self.childProfiles,
            'fieldTypes': self.get_field_types()
        }

    @classmethod
    def from_dict(cls, data: dict, manager=None) -> 'APIProfile':
        """
        Create an APIProfile from a dictionary.

        Args:
            data: Dictionary with profile data
            manager: Manager object for tree registration

        Returns:
            New APIProfile instance
        """
        return cls(
            profileName=data.get('profileName', ''),
            displayName=data.get('displayName', ''),
            description=data.get('description', ''),
            apiEndpoint=data.get('apiEndpoint', ''),
            httpMethod=data.get('httpMethod', 'GET'),
            responseRootPath=data.get('responseRootPath', ''),
            polyTypedObjectRef=data.get('polyTypedObjectRef'),
            objectTypeField=data.get('objectTypeField', ''),
            objectTypeMapping=data.get('objectTypeMapping', {}),
            storedCredentials=data.get('storedCredentials', ''),
            defaultHeaders=data.get('defaultHeaders', {}),
            isTemplate=data.get('isTemplate', False),
            matchConfidenceThreshold=data.get('matchConfidenceThreshold', 0.7),
            sampleCount=data.get('sampleCount', 0),
            fieldSignatures=data.get('fieldSignatures', []),
            manager=manager
        )

    def validate(self) -> tuple:
        """
        Validate this profile.

        Returns:
            Tuple of (is_valid: bool, errors: list)
        """
        errors = []

        if not self.profileName:
            errors.append("Profile name is required")

        if not self.profileName.replace('_', '').isalnum():
            errors.append("Profile name must be alphanumeric (underscores allowed)")

        if self.httpMethod not in ['GET', 'POST', 'PUT', 'DELETE', 'PATCH']:
            errors.append(f"Invalid HTTP method: {self.httpMethod}")

        if self.matchConfidenceThreshold < 0 or self.matchConfidenceThreshold > 1:
            errors.append("Match confidence threshold must be between 0 and 1")

        return (len(errors) == 0, errors)

    def __repr__(self):
        return f"APIProfile(profileName='{self.profileName}', endpoint='{self.apiEndpoint}', fields={len(self.fieldSignatures)})"
