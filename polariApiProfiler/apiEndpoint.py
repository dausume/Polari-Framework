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
APIEndpoint - Data model for storing external API endpoint configurations.

An APIEndpoint stores information about an external API data source,
including its URL, authentication, linked profile, and data persistence settings.
"""

from objectTreeDecorators import treeObject, treeObjectInit
from typing import Dict, List, Optional, Any
from datetime import datetime


class APIEndpoint(treeObject):
    """
    Stores configuration for an external API endpoint (data source).

    This allows you to:
    - Define external API endpoints with their configuration
    - Link them to APIProfiles for type mapping
    - Choose whether to persist data locally or fetch on-demand
    - Track fetch history and response samples

    Attributes:
        name: Unique identifier for this endpoint
        displayName: Human-readable name
        description: Description of what this API provides
        domainName: Name of the APIDomain this endpoint uses
        endpointPath: The path part of the URL (e.g., "/api/v1/users")
        url: (Deprecated) Full URL - kept for backwards compatibility
        httpMethod: HTTP method (GET, POST, etc.)
        defaultHeaders: Headers to include with every request
        bodyTemplate: Template for request body (for POST/PUT)
        responseRootPath: JSONPath to extract data from response
        linkedProfileName: Name of the APIProfile to use for typing
        persistData: Whether to store fetched data locally in Polari
        polariClassName: If persisting, the Polari class name to store data as
        fetchIntervalMinutes: How often to auto-refresh (0 = manual only)
        lastFetchTime: When data was last fetched
        lastFetchSuccess: Whether the last fetch succeeded
        lastFetchError: Error message from last failed fetch
        lastResponseSample: Small sample of last response (for preview)
        lastResponseFieldCount: Number of fields in last response
        lastResponseRecordCount: Number of records in last response
        isActive: Whether this endpoint is active for fetching
        authType: Authentication type (none, bearer, apikey, basic)
        authConfig: Authentication configuration (encrypted)
    """

    @treeObjectInit
    def __init__(
        self,
        name: str = '',
        displayName: str = '',
        description: str = '',
        domainName: str = '',
        endpointPath: str = '',
        url: str = '',  # Kept for backwards compatibility
        httpMethod: str = 'GET',
        defaultHeaders: Dict[str, str] = None,
        bodyTemplate: str = '',
        responseRootPath: str = '',
        linkedProfileName: str = '',
        persistData: bool = False,
        polariClassName: str = '',
        fetchIntervalMinutes: int = 0,
        lastFetchTime: str = '',
        lastFetchSuccess: bool = False,
        lastFetchError: str = '',
        lastResponseSample: Dict = None,
        lastResponseFieldCount: int = 0,
        lastResponseRecordCount: int = 0,
        isActive: bool = True,
        authType: str = 'none',
        authConfig: str = '',
        manager=None,
        **kwargs
    ):
        self.name = name
        self.displayName = displayName or name
        self.description = description
        self.domainName = domainName
        self.endpointPath = endpointPath
        self._url = url  # Store raw URL for backwards compatibility
        self.httpMethod = httpMethod.upper() if httpMethod else 'GET'
        self.defaultHeaders = defaultHeaders or {}
        self.bodyTemplate = bodyTemplate
        self.responseRootPath = responseRootPath
        self.linkedProfileName = linkedProfileName
        self.persistData = persistData
        self.polariClassName = polariClassName
        self.fetchIntervalMinutes = fetchIntervalMinutes
        self.lastFetchTime = lastFetchTime
        self.lastFetchSuccess = lastFetchSuccess
        self.lastFetchError = lastFetchError
        self.lastResponseSample = lastResponseSample
        self.lastResponseFieldCount = lastResponseFieldCount
        self.lastResponseRecordCount = lastResponseRecordCount
        self.isActive = isActive
        self.authType = authType  # none, bearer, apikey, basic
        self.authConfig = authConfig  # encrypted credentials

    @property
    def url(self) -> str:
        """
        Get the full URL for this endpoint.
        If domainName is set, constructs URL from domain + path.
        Otherwise returns the legacy _url value.
        """
        if self.domainName and self.manager:
            domain = self.get_domain()
            if domain:
                base = domain.get_base_url()
                path = self.endpointPath or ''
                if path and not path.startswith('/'):
                    path = '/' + path
                return base + path
        return self._url or ''

    @url.setter
    def url(self, value: str):
        """Set the legacy URL value."""
        self._url = value

    def get_domain(self):
        """
        Get the linked APIDomain from the manager.

        Returns:
            APIDomain or None
        """
        if not self.domainName or not self.manager:
            return None

        domains = self.manager.getListOfClassInstances('APIDomain')
        for domain in domains:
            if domain.name == self.domainName:
                return domain
        return None

    def get_headers_with_auth(self) -> Dict[str, str]:
        """
        Get headers including authentication if configured.

        Returns:
            Dict of headers with auth applied
        """
        headers = dict(self.defaultHeaders)

        if self.authType == 'bearer' and self.authConfig:
            headers['Authorization'] = f'Bearer {self.authConfig}'
        elif self.authType == 'apikey' and self.authConfig:
            # Assume API key goes in header; format: "HeaderName:Value"
            if ':' in self.authConfig:
                key_name, key_value = self.authConfig.split(':', 1)
                headers[key_name] = key_value
            else:
                headers['X-API-Key'] = self.authConfig
        elif self.authType == 'basic' and self.authConfig:
            import base64
            encoded = base64.b64encode(self.authConfig.encode()).decode()
            headers['Authorization'] = f'Basic {encoded}'

        return headers

    def get_request_kwargs(self) -> dict:
        """
        Get kwargs for requests library, including domain SSL settings.

        Returns:
            Dict with verify and other settings for requests
        """
        kwargs = {}

        # Get SSL settings from domain if available
        domain = self.get_domain()
        if domain:
            kwargs.update(domain.get_request_kwargs())
        else:
            # Default: verify SSL
            kwargs['verify'] = True

        return kwargs

    def update_fetch_result(
        self,
        success: bool,
        response_data: Any = None,
        error: str = '',
        record_count: int = 0
    ):
        """
        Update the endpoint with fetch results.

        Args:
            success: Whether the fetch succeeded
            response_data: The response data (for sampling)
            error: Error message if failed
            record_count: Number of records fetched
        """
        self.lastFetchTime = datetime.now().isoformat()
        self.lastFetchSuccess = success
        self.lastFetchError = error if not success else ''
        self.lastResponseRecordCount = record_count

        if success and response_data is not None:
            # Store a sample (first item if list, or truncated dict)
            if isinstance(response_data, list) and len(response_data) > 0:
                sample = response_data[0] if isinstance(response_data[0], dict) else {'_sample': str(response_data[0])[:200]}
                self.lastResponseSample = sample
                self.lastResponseFieldCount = len(sample.keys()) if isinstance(sample, dict) else 0
            elif isinstance(response_data, dict):
                # Truncate large values for the sample
                sample = {}
                for k, v in list(response_data.items())[:10]:
                    if isinstance(v, str) and len(v) > 100:
                        sample[k] = v[:100] + '...'
                    elif isinstance(v, (list, dict)):
                        sample[k] = f'[{type(v).__name__}]'
                    else:
                        sample[k] = v
                self.lastResponseSample = sample
                self.lastResponseFieldCount = len(response_data.keys())
            else:
                self.lastResponseSample = {'_raw': str(response_data)[:200]}
                self.lastResponseFieldCount = 0

    def get_linked_profile(self):
        """
        Get the linked APIProfile from the manager.

        Returns:
            APIProfile or None
        """
        if not self.linkedProfileName or not self.manager:
            return None

        profiles = self.manager.getListOfClassInstances('APIProfile')
        for profile in profiles:
            if profile.profileName == self.linkedProfileName:
                return profile
        return None

    def set_linked_profile(self, profile):
        """
        Link this endpoint to an APIProfile.

        Args:
            profile: The APIProfile to link
        """
        if profile:
            self.linkedProfileName = profile.profileName

    def to_dict(self) -> dict:
        """
        Convert to dictionary for JSON serialization.

        Returns:
            Dictionary representation (excludes sensitive auth data)
        """
        return {
            'id': self.id if hasattr(self, 'id') else None,
            'name': self.name,
            'displayName': self.displayName,
            'description': self.description,
            'domainName': self.domainName,
            'endpointPath': self.endpointPath,
            'url': self.url,  # Computed full URL for convenience
            'httpMethod': self.httpMethod,
            'defaultHeaders': self.defaultHeaders,
            'bodyTemplate': self.bodyTemplate,
            'responseRootPath': self.responseRootPath,
            'linkedProfileName': self.linkedProfileName,
            'persistData': self.persistData,
            'polariClassName': self.polariClassName,
            'fetchIntervalMinutes': self.fetchIntervalMinutes,
            'lastFetchTime': self.lastFetchTime,
            'lastFetchSuccess': self.lastFetchSuccess,
            'lastFetchError': self.lastFetchError,
            'lastResponseSample': self.lastResponseSample,
            'lastResponseFieldCount': self.lastResponseFieldCount,
            'lastResponseRecordCount': self.lastResponseRecordCount,
            'isActive': self.isActive,
            'authType': self.authType,
            'hasAuth': bool(self.authConfig)  # Don't expose actual credentials
        }

    @classmethod
    def from_dict(cls, data: dict, manager=None) -> 'APIEndpoint':
        """
        Create an APIEndpoint from a dictionary.

        Args:
            data: Dictionary with endpoint data
            manager: Manager object

        Returns:
            New APIEndpoint instance
        """
        return cls(
            name=data.get('name', ''),
            displayName=data.get('displayName', ''),
            description=data.get('description', ''),
            domainName=data.get('domainName', ''),
            endpointPath=data.get('endpointPath', ''),
            url=data.get('url', ''),  # Legacy support
            httpMethod=data.get('httpMethod', 'GET'),
            defaultHeaders=data.get('defaultHeaders', {}),
            bodyTemplate=data.get('bodyTemplate', ''),
            responseRootPath=data.get('responseRootPath', ''),
            linkedProfileName=data.get('linkedProfileName', ''),
            persistData=data.get('persistData', False),
            polariClassName=data.get('polariClassName', ''),
            fetchIntervalMinutes=data.get('fetchIntervalMinutes', 0),
            isActive=data.get('isActive', True),
            authType=data.get('authType', 'none'),
            authConfig=data.get('authConfig', ''),
            manager=manager
        )

    def validate(self) -> tuple:
        """
        Validate this endpoint configuration.

        Returns:
            Tuple of (is_valid: bool, errors: list)
        """
        errors = []

        if not self.name:
            errors.append("Endpoint name is required")

        if not self.url:
            errors.append("URL is required")

        if self.httpMethod not in ['GET', 'POST', 'PUT', 'DELETE', 'PATCH']:
            errors.append(f"Invalid HTTP method: {self.httpMethod}")

        if self.persistData and not self.polariClassName:
            errors.append("Polari class name required when persisting data")

        if self.authType not in ['none', 'bearer', 'apikey', 'basic']:
            errors.append(f"Invalid auth type: {self.authType}")

        return (len(errors) == 0, errors)

    def __repr__(self):
        return f"APIEndpoint(name='{self.name}', url='{self.url}', profile='{self.linkedProfileName}')"


# Pre-defined common endpoints for convenience
COMMON_ENDPOINTS = [
    # Mock API - JSONPlaceholder Users
    {
        'name': 'mock-users',
        'displayName': 'Mock Users (JSONPlaceholder)',
        'description': 'Free fake API for testing - returns 10 mock user objects',
        'domainName': '',
        'endpointPath': '',
        'url': 'https://jsonplaceholder.typicode.com/users',
        'httpMethod': 'GET',
        'defaultHeaders': {},
        'responseRootPath': '',
        'linkedProfileName': 'uniformArray',
        'persistData': False,
        'polariClassName': '',
        'isActive': True,
        'authType': 'none',
        'tags': ['mock', 'test', 'users']
    },
    # Mock API - JSONPlaceholder Posts
    {
        'name': 'mock-posts',
        'displayName': 'Mock Posts (JSONPlaceholder)',
        'description': 'Free fake API for testing - returns 100 mock post objects',
        'domainName': '',
        'endpointPath': '',
        'url': 'https://jsonplaceholder.typicode.com/posts',
        'httpMethod': 'GET',
        'defaultHeaders': {},
        'responseRootPath': '',
        'linkedProfileName': 'uniformArray',
        'persistData': False,
        'polariClassName': '',
        'isActive': True,
        'authType': 'none',
        'tags': ['mock', 'test', 'posts']
    },
    # Mock API - JSONPlaceholder Todos
    {
        'name': 'mock-todos',
        'displayName': 'Mock Todos (JSONPlaceholder)',
        'description': 'Free fake API for testing - returns 200 mock todo objects',
        'domainName': '',
        'endpointPath': '',
        'url': 'https://jsonplaceholder.typicode.com/todos',
        'httpMethod': 'GET',
        'defaultHeaders': {},
        'responseRootPath': '',
        'linkedProfileName': 'uniformArray',
        'persistData': False,
        'polariClassName': '',
        'isActive': True,
        'authType': 'none',
        'tags': ['mock', 'test', 'todos']
    },
    # Polari API - Local TestObject CRUDE
    {
        'name': 'polari-testobject',
        'displayName': 'Polari TestObject (Local)',
        'description': 'Polari CRUDE endpoint for TestObject - uses local backend',
        'domainName': 'localhost-3000',
        'endpointPath': '/TestObject',
        'url': 'http://localhost:3000/TestObject',
        'httpMethod': 'GET',
        'defaultHeaders': {},
        'responseRootPath': 'instances',
        'linkedProfileName': 'polariCrude',
        'persistData': False,
        'polariClassName': '',
        'isActive': True,
        'authType': 'none',
        'tags': ['polari', 'crude', 'local']
    },
    # Polari API - PRF Backend via nip.io
    {
        'name': 'polari-prf-testobject',
        'displayName': 'Polari TestObject (PRF nip.io)',
        'description': 'Polari CRUDE endpoint via prod-local nip.io proxy',
        'domainName': 'nip-io-api-prf',
        'endpointPath': '/TestObject',
        'url': 'https://api.prf.10.0.0.102.nip.io/TestObject',
        'httpMethod': 'GET',
        'defaultHeaders': {},
        'responseRootPath': 'instances',
        'linkedProfileName': 'polariCrude',
        'persistData': False,
        'polariClassName': '',
        'isActive': True,
        'authType': 'none',
        'tags': ['polari', 'crude', 'nip.io', 'prf']
    },
]
