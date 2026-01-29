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
API Profiler REST Endpoints

Provides REST API endpoints for:
- Querying external APIs and analyzing responses
- Matching responses against stored profiles
- Building new profiles from responses
- Converting profiles to Polari classes
"""

from objectTreeDecorators import treeObject, treeObjectInit
from polariApiProfiler.apiProfile import APIProfile
from polariApiProfiler.apiProfiler import APIProfiler
from polariApiProfiler.profileMatcher import ProfileMatcher
from polariApiProfiler import profileTemplates
import falcon
import json


class APIProfilerQueryAPI(treeObject):
    """
    Endpoint: /apiProfiler/query

    Query an external API, analyze the response using Polari typing,
    and optionally match against stored profiles.
    """

    @treeObjectInit
    def __init__(self, polServer, manager=None, **kwargs):
        self.polServer = polServer
        self.apiName = '/apiProfiler/query'
        if polServer is not None:
            polServer.falconServer.add_route(self.apiName, self)

        # Initialize profiler and matcher
        self.profiler = APIProfiler(manager=manager)
        self.matcher = ProfileMatcher(manager=manager)

    def on_post(self, request, response):
        """
        Query an external API and analyze the response.

        Request body:
        {
            "url": "https://api.example.com/endpoint",
            "method": "GET",
            "headers": {"Authorization": "Bearer token"},
            "body": {},  // Optional request body
            "responseRootPath": "data.items",  // Optional path to extract
            "matchProfiles": true,  // Whether to match against stored profiles
            "profileName": "MyProfile"  // Optional: name for new profile
        }

        Response:
        {
            "success": true,
            "response": {...},  // The API response
            "analysis": {
                "fieldCount": 5,
                "fields": ["id", "name", ...],
                "detectedTypes": {...}
            },
            "matches": [...]  // If matchProfiles is true
        }
        """
        try:
            raw_data = request.bounded_stream.read()
            req_body = json.loads(raw_data.decode('utf-8'))

            # Validate required fields
            if 'url' not in req_body:
                response.status = falcon.HTTP_400
                response.media = {'success': False, 'error': 'url is required'}
                return

            url = req_body['url']
            method = req_body.get('method', 'GET')
            headers = req_body.get('headers', {})
            body = req_body.get('body')
            root_path = req_body.get('responseRootPath', '')
            match_profiles = req_body.get('matchProfiles', False)
            profile_name = req_body.get('profileName', '')

            # Query the external API
            api_response, error = self.profiler.query_external_api(
                url=url,
                method=method,
                headers=headers,
                body=body
            )

            if error and api_response is None:
                response.status = falcon.HTTP_502
                response.media = {'success': False, 'error': error}
                return

            # Extract data from path if specified
            data_to_analyze = self.profiler.extract_data_from_path(api_response, root_path)

            if data_to_analyze is None:
                response.status = falcon.HTTP_400
                response.media = {
                    'success': False,
                    'error': f'Could not extract data from path: {root_path}',
                    'response': api_response
                }
                return

            # Build analysis result
            result = {
                'success': True,
                'response': api_response,
                'extractedData': data_to_analyze if data_to_analyze != api_response else None
            }

            # Analyze the response structure
            if isinstance(data_to_analyze, (dict, list)):
                samples = data_to_analyze if isinstance(data_to_analyze, list) else [data_to_analyze]
                dict_samples = [s for s in samples if isinstance(s, dict)]

                if dict_samples:
                    # Collect field info
                    all_fields = set()
                    for sample in dict_samples:
                        all_fields.update(sample.keys())

                    # Get type info from first sample
                    type_info = {}
                    if dict_samples:
                        for key, value in dict_samples[0].items():
                            type_info[key] = type(value).__name__

                    # Use structural matching to suggest profiles
                    structural_matches = profileTemplates.match_structural_profile(data_to_analyze)
                    suggested_profiles = [m['profileName'] for m in structural_matches[:3]]

                    result['analysis'] = {
                        'sampleCount': len(dict_samples),
                        'fieldCount': len(all_fields),
                        'fields': sorted(list(all_fields)),
                        'detectedTypes': type_info,
                        'suggestedProfiles': suggested_profiles
                    }

                    # Create profile if name provided
                    if profile_name:
                        profile, poly_typed_obj = self.profiler.analyze_response_with_polari_typing(
                            data_to_analyze,
                            profile_name=profile_name,
                            display_name=req_body.get('displayName', profile_name)
                        )
                        profile.apiEndpoint = url
                        profile.httpMethod = method
                        profile.responseRootPath = root_path
                        profile.defaultHeaders = headers

                        result['profile'] = profile.to_dict()

            # Match against format profiles if requested
            if match_profiles:
                # Use the new structural matching
                matches = self.matcher.match_response(data_to_analyze)
                result['matches'] = [
                    {
                        'profileName': m['profileName'],
                        'displayName': m.get('displayName', m['profileName']),
                        'confidence': m.get('confidencePercent', round(m['confidence'] * 100, 1)),
                        'isMatch': m['isMatch'],
                        'dataPath': m.get('dataPath', ''),
                        'matchDetails': m.get('matchDetails', {}),
                        'typeAnalysis': m.get('typeAnalysis', {})
                    }
                    for m in matches[:10]  # Top 10 matches
                ]

            response.status = falcon.HTTP_200
            response.media = result

        except json.JSONDecodeError:
            response.status = falcon.HTTP_400
            response.media = {'success': False, 'error': 'Invalid JSON in request body'}
        except Exception as e:
            response.status = falcon.HTTP_500
            response.media = {'success': False, 'error': str(e)}
            import traceback
            traceback.print_exc()

        response.set_header('Powered-By', 'Polari')


class APIProfilerMatchAPI(treeObject):
    """
    Endpoint: /apiProfiler/match

    Match provided response data against stored profiles.
    """

    @treeObjectInit
    def __init__(self, polServer, manager=None, **kwargs):
        self.polServer = polServer
        self.apiName = '/apiProfiler/match'
        if polServer is not None:
            polServer.falconServer.add_route(self.apiName, self)

        self.matcher = ProfileMatcher(manager=manager)

    def on_post(self, request, response):
        """
        Match response data against profiles.

        Request body:
        {
            "responseData": {...} or [...],
            "profileNames": ["Profile1", "Profile2"],  // Optional: specific profiles
            "includeTemplates": true,  // Include built-in templates
            "threshold": 0.7  // Optional confidence threshold
        }

        Response:
        {
            "success": true,
            "matches": [...],
            "summary": {...}
        }
        """
        try:
            raw_data = request.bounded_stream.read()
            req_body = json.loads(raw_data.decode('utf-8'))

            if 'responseData' not in req_body:
                response.status = falcon.HTTP_400
                response.media = {'success': False, 'error': 'responseData is required'}
                return

            response_data = req_body['responseData']
            profile_names = req_body.get('profileNames', [])
            include_templates = req_body.get('includeTemplates', True)
            threshold = req_body.get('threshold')

            # Collect profiles to match against
            candidate_profiles = []

            # Get stored profiles
            stored_profiles = self.manager.getListOfClassInstances('APIProfile')

            # Use structural matching - profile_names can filter results
            matches = self.matcher.match_response(response_data, threshold=threshold)

            # Filter to specific profiles if requested
            if profile_names:
                matches = [m for m in matches if m['profileName'] in profile_names]

            # Build response
            match_results = []
            for m in matches:
                match_results.append({
                    'profileName': m['profileName'],
                    'displayName': m.get('displayName', m['profileName']),
                    'confidence': m.get('confidencePercent', round(m['confidence'] * 100, 1)),
                    'isMatch': m['isMatch'],
                    'threshold': m.get('threshold', threshold),
                    'dataPath': m.get('dataPath', ''),
                    'matchDetails': m.get('matchDetails', {}),
                    'typeAnalysis': m.get('typeAnalysis', {})
                })

            summary = self.matcher.get_match_summary(matches)

            response.status = falcon.HTTP_200
            response.media = {
                'success': True,
                'matches': match_results,
                'summary': summary
            }

        except json.JSONDecodeError:
            response.status = falcon.HTTP_400
            response.media = {'success': False, 'error': 'Invalid JSON in request body'}
        except Exception as e:
            response.status = falcon.HTTP_500
            response.media = {'success': False, 'error': str(e)}
            import traceback
            traceback.print_exc()

        response.set_header('Powered-By', 'Polari')


class APIProfilerBuildAPI(treeObject):
    """
    Endpoint: /apiProfiler/buildProfile

    Build a new profile from response data.
    """

    @treeObjectInit
    def __init__(self, polServer, manager=None, **kwargs):
        self.polServer = polServer
        self.apiName = '/apiProfiler/buildProfile'
        if polServer is not None:
            polServer.falconServer.add_route(self.apiName, self)

        self.profiler = APIProfiler(manager=manager)

    def on_post(self, request, response):
        """
        Build a profile from response data.

        Request body:
        {
            "responseData": {...} or [...],
            "profileName": "MyProfile",
            "displayName": "My Profile",  // Optional
            "description": "Description",  // Optional
            "apiEndpoint": "https://...",  // Optional
            "httpMethod": "GET",  // Optional
            "responseRootPath": "",  // Optional
            "detectTypes": true  // Detect multiple object types
        }

        Response:
        {
            "success": true,
            "profile": {...},
            "detectedTypes": [...]  // If detectTypes is true
        }
        """
        try:
            raw_data = request.bounded_stream.read()
            req_body = json.loads(raw_data.decode('utf-8'))

            if 'responseData' not in req_body:
                response.status = falcon.HTTP_400
                response.media = {'success': False, 'error': 'responseData is required'}
                return

            if 'profileName' not in req_body:
                response.status = falcon.HTTP_400
                response.media = {'success': False, 'error': 'profileName is required'}
                return

            response_data = req_body['responseData']
            profile_name = req_body['profileName']
            display_name = req_body.get('displayName', profile_name)
            description = req_body.get('description', '')
            api_endpoint = req_body.get('apiEndpoint', '')
            http_method = req_body.get('httpMethod', 'GET')
            root_path = req_body.get('responseRootPath', '')
            detect_types = req_body.get('detectTypes', False)
            type_field = req_body.get('objectTypeField', '')

            result = {'success': True}

            # Detect multiple types if requested
            if detect_types:
                detected_types = self.profiler.detect_object_types(
                    response_data,
                    type_field=type_field
                )
                result['detectedTypes'] = detected_types

                # Create sub-profiles for each detected type
                if len(detected_types) > 1:
                    sub_profiles = []
                    for dt in detected_types:
                        sub_name = f"{profile_name}_{dt['typeId']}"
                        sub_profile, _ = self.profiler.analyze_response_with_polari_typing(
                            dt['samples'],
                            profile_name=sub_name,
                            display_name=f"{display_name} - {dt['typeId']}"
                        )
                        sub_profile.apiEndpoint = api_endpoint
                        sub_profile.httpMethod = http_method
                        sub_profiles.append(sub_profile.to_dict())

                    result['subProfiles'] = sub_profiles

            # Build the main profile
            profile, poly_typed_obj = self.profiler.analyze_response_with_polari_typing(
                response_data,
                profile_name=profile_name,
                display_name=display_name
            )

            # Set additional metadata
            profile.description = description
            profile.apiEndpoint = api_endpoint
            profile.httpMethod = http_method
            profile.responseRootPath = root_path

            if type_field:
                profile.objectTypeField = type_field

            # Validate profile
            is_valid, errors = profile.validate()
            if not is_valid:
                response.status = falcon.HTTP_400
                response.media = {'success': False, 'error': 'Invalid profile', 'validationErrors': errors}
                return

            result['profile'] = profile.to_dict()
            result['polyTypedObject'] = {
                'className': poly_typed_obj.className,
                'variableCount': len(poly_typed_obj.polyTypedVars),
                'variables': [
                    {
                        'name': v.name,
                        'type': v.pythonTypeDefault
                    }
                    for v in poly_typed_obj.polyTypedVars
                ]
            }

            response.status = falcon.HTTP_201
            response.media = result

        except json.JSONDecodeError:
            response.status = falcon.HTTP_400
            response.media = {'success': False, 'error': 'Invalid JSON in request body'}
        except Exception as e:
            response.status = falcon.HTTP_500
            response.media = {'success': False, 'error': str(e)}
            import traceback
            traceback.print_exc()

        response.set_header('Powered-By', 'Polari')


class APIProfilerCreateClassAPI(treeObject):
    """
    Endpoint: /apiProfiler/createPolariClass

    Convert a profile to a full Polari class via createClassAPI.
    """

    @treeObjectInit
    def __init__(self, polServer, manager=None, **kwargs):
        self.polServer = polServer
        self.apiName = '/apiProfiler/createPolariClass'
        if polServer is not None:
            polServer.falconServer.add_route(self.apiName, self)

        self.profiler = APIProfiler(manager=manager)

    def on_post(self, request, response):
        """
        Convert a profile to a Polari class.

        Request body:
        {
            "profileName": "MyProfile",  // Name of existing profile
            // OR
            "profileData": {...},  // Profile data directly
            "className": "MyClass",  // Optional: override class name
            "registerCRUDE": true,
            "isStateSpaceObject": true
        }

        Response:
        {
            "success": true,
            "className": "MyClass",
            "apiEndpoint": "/MyClass",
            "variables": [...]
        }
        """
        try:
            raw_data = request.bounded_stream.read()
            req_body = json.loads(raw_data.decode('utf-8'))

            profile = None

            # Get profile from name or data
            if 'profileName' in req_body:
                profile_name = req_body['profileName']
                profiles = self.manager.getListOfClassInstances('APIProfile')
                for p in profiles:
                    if p.profileName == profile_name:
                        profile = p
                        break

                if not profile:
                    response.status = falcon.HTTP_404
                    response.media = {'success': False, 'error': f'Profile not found: {profile_name}'}
                    return

            elif 'profileData' in req_body:
                profile = APIProfile.from_dict(req_body['profileData'], manager=self.manager)
            else:
                response.status = falcon.HTTP_400
                response.media = {'success': False, 'error': 'Either profileName or profileData is required'}
                return

            # Convert profile to class definition
            class_def = self.profiler.profile_to_class_definition(profile)

            # Apply overrides from request
            if 'className' in req_body:
                class_def['className'] = req_body['className']
            if 'registerCRUDE' in req_body:
                class_def['registerCRUDE'] = req_body['registerCRUDE']
            if 'isStateSpaceObject' in req_body:
                class_def['isStateSpaceObject'] = req_body['isStateSpaceObject']

            # Find createClassAPI endpoint
            create_class_api = None
            for api in self.polServer.customAPIsList:
                if hasattr(api, 'apiName') and api.apiName == '/createClass':
                    create_class_api = api
                    break

            if not create_class_api:
                response.status = falcon.HTTP_500
                response.media = {'success': False, 'error': 'createClassAPI not found on server'}
                return

            # Check if class already exists
            class_name = class_def['className']
            if class_name in self.manager.objectTypingDict:
                response.status = falcon.HTTP_409
                response.media = {'success': False, 'error': f'Class {class_name} already exists'}
                return

            # Create the dynamic class
            new_typing = create_class_api._createDynamicClass(
                className=class_def['className'],
                displayName=class_def['classDisplayName'],
                variables=class_def['variables'],
                registerCRUDE=class_def['registerCRUDE'],
                isStateSpaceObject=class_def['isStateSpaceObject']
            )

            response.status = falcon.HTTP_201
            response.media = {
                'success': True,
                'className': class_def['className'],
                'classDisplayName': class_def['classDisplayName'],
                'apiEndpoint': f"/{class_def['className']}",
                'crudeRegistered': class_def['registerCRUDE'],
                'isStateSpaceObject': class_def['isStateSpaceObject'],
                'variableCount': len(class_def['variables']),
                'variables': class_def['variables']
            }

        except json.JSONDecodeError:
            response.status = falcon.HTTP_400
            response.media = {'success': False, 'error': 'Invalid JSON in request body'}
        except Exception as e:
            response.status = falcon.HTTP_500
            response.media = {'success': False, 'error': str(e)}
            import traceback
            traceback.print_exc()

        response.set_header('Powered-By', 'Polari')


class APIProfilerTemplatesAPI(treeObject):
    """
    Endpoint: /apiProfiler/templates

    Get available profile templates.
    """

    @treeObjectInit
    def __init__(self, polServer, manager=None, **kwargs):
        self.polServer = polServer
        self.apiName = '/apiProfiler/templates'
        if polServer is not None:
            polServer.falconServer.add_route(self.apiName, self)

    def on_get(self, request, response):
        """
        Get all available format profiles.

        Response:
        {
            "success": true,
            "formatProfiles": {...},  // All structural format profiles
            "profileNames": [...]
        }
        """
        try:
            format_profiles = profileTemplates.get_all_format_profiles()

            response.status = falcon.HTTP_200
            response.media = {
                'success': True,
                'formatProfiles': format_profiles,
                'profileNames': list(format_profiles.keys()),
                'profileCount': len(format_profiles)
            }

        except Exception as e:
            response.status = falcon.HTTP_500
            response.media = {'success': False, 'error': str(e)}

        response.set_header('Powered-By', 'Polari')


class APIProfilerDetectTypesAPI(treeObject):
    """
    Endpoint: /apiProfiler/detectTypes

    Detect multiple object types in a response.
    """

    @treeObjectInit
    def __init__(self, polServer, manager=None, **kwargs):
        self.polServer = polServer
        self.apiName = '/apiProfiler/detectTypes'
        if polServer is not None:
            polServer.falconServer.add_route(self.apiName, self)

        self.profiler = APIProfiler(manager=manager)

    def on_post(self, request, response):
        """
        Detect multiple object types in response data.

        Request body:
        {
            "responseData": [...],
            "typeField": "type",  // Optional field name for type detection
            "similarityThreshold": 0.7  // Optional threshold for signature clustering
        }

        Response:
        {
            "success": true,
            "detectedTypes": [
                {
                    "typeId": "User",
                    "sampleCount": 5,
                    "fieldSignature": ["id", "name", "email"],
                    "method": "field"
                },
                ...
            ]
        }
        """
        try:
            raw_data = request.bounded_stream.read()
            req_body = json.loads(raw_data.decode('utf-8'))

            if 'responseData' not in req_body:
                response.status = falcon.HTTP_400
                response.media = {'success': False, 'error': 'responseData is required'}
                return

            response_data = req_body['responseData']
            type_field = req_body.get('typeField')
            similarity_threshold = req_body.get('similarityThreshold', 0.7)

            detected_types = self.profiler.detect_object_types(
                response_data,
                type_field=type_field,
                similarity_threshold=similarity_threshold
            )

            response.status = falcon.HTTP_200
            response.media = {
                'success': True,
                'typeCount': len(detected_types),
                'detectedTypes': detected_types
            }

        except json.JSONDecodeError:
            response.status = falcon.HTTP_400
            response.media = {'success': False, 'error': 'Invalid JSON in request body'}
        except Exception as e:
            response.status = falcon.HTTP_500
            response.media = {'success': False, 'error': str(e)}
            import traceback
            traceback.print_exc()

        response.set_header('Powered-By', 'Polari')


class APIDomainAPI(treeObject):
    """
    Endpoint: /apiDomain

    CRUD operations for APIDomain objects (API host/domain configurations with SSL settings).
    """

    @treeObjectInit
    def __init__(self, polServer, manager=None, **kwargs):
        self.polServer = polServer
        self.apiName = '/apiDomain'
        if polServer is not None:
            polServer.falconServer.add_route(self.apiName, self)
            polServer.falconServer.add_route(self.apiName + '/{domain_id}', self)

    def on_get(self, request, response, domain_id=None):
        """
        Get all domains or a specific domain.

        GET /apiDomain - Get all domains (including common pre-defined ones)
        GET /apiDomain/{domain_id} - Get specific domain

        Response:
        {
            "success": true,
            "domains": [...] or "domain": {...}
        }
        """
        try:
            from polariApiProfiler.apiDomain import APIDomain, COMMON_DOMAINS

            stored_domains = self.manager.getListOfClassInstances('APIDomain')

            if domain_id:
                # Find specific domain - check stored first
                for dom in stored_domains:
                    if (hasattr(dom, 'id') and str(dom.id) == str(domain_id)) or dom.name == domain_id:
                        response.status = falcon.HTTP_200
                        response.media = {
                            'success': True,
                            'domain': dom.to_dict()
                        }
                        return

                # Check common domains
                for common in COMMON_DOMAINS:
                    if common['name'] == domain_id:
                        dom = APIDomain.from_dict(common, manager=self.manager)
                        response.status = falcon.HTTP_200
                        response.media = {
                            'success': True,
                            'domain': dom.to_dict(),
                            'isCommon': True
                        }
                        return

                response.status = falcon.HTTP_404
                response.media = {'success': False, 'error': f'Domain not found: {domain_id}'}
                return

            # Return all domains (stored + common)
            all_domains = [dom.to_dict() for dom in stored_domains]

            # Add common domains that aren't already stored
            stored_names = {dom.name for dom in stored_domains}
            for common in COMMON_DOMAINS:
                if common['name'] not in stored_names:
                    dom = APIDomain.from_dict(common, manager=self.manager)
                    dom_dict = dom.to_dict()
                    dom_dict['isCommon'] = True
                    all_domains.append(dom_dict)

            response.status = falcon.HTTP_200
            response.media = {
                'success': True,
                'count': len(all_domains),
                'domains': all_domains
            }

        except Exception as e:
            response.status = falcon.HTTP_500
            response.media = {'success': False, 'error': str(e)}
            import traceback
            traceback.print_exc()

        response.set_header('Powered-By', 'Polari')

    def on_post(self, request, response):
        """
        Create a new APIDomain.

        Request body:
        {
            "name": "my-api-server",
            "displayName": "My API Server",
            "description": "Production server",
            "host": "api.example.com",
            "port": 443,
            "protocol": "https",
            "trustSelfSigned": false,
            "customCertPath": "",
            "verifySSL": true,
            "tags": ["prod"]
        }

        Response:
        {
            "success": true,
            "domain": {...}
        }
        """
        try:
            from polariApiProfiler.apiDomain import APIDomain

            raw_data = request.bounded_stream.read()
            req_body = json.loads(raw_data.decode('utf-8'))

            # Validate required fields
            if not req_body.get('name'):
                response.status = falcon.HTTP_400
                response.media = {'success': False, 'error': 'name is required'}
                return

            if not req_body.get('host'):
                response.status = falcon.HTTP_400
                response.media = {'success': False, 'error': 'host is required'}
                return

            # Check for duplicate name
            existing = self.manager.getListOfClassInstances('APIDomain')
            for dom in existing:
                if dom.name == req_body['name']:
                    response.status = falcon.HTTP_409
                    response.media = {'success': False, 'error': f'Domain with name "{req_body["name"]}" already exists'}
                    return

            # Create the domain
            domain = APIDomain.from_dict(req_body, manager=self.manager)

            # Validate
            is_valid, errors = domain.validate()
            if not is_valid:
                response.status = falcon.HTTP_400
                response.media = {'success': False, 'error': 'Validation failed', 'validationErrors': errors}
                return

            response.status = falcon.HTTP_201
            response.media = {
                'success': True,
                'domain': domain.to_dict()
            }

        except json.JSONDecodeError:
            response.status = falcon.HTTP_400
            response.media = {'success': False, 'error': 'Invalid JSON in request body'}
        except Exception as e:
            response.status = falcon.HTTP_500
            response.media = {'success': False, 'error': str(e)}
            import traceback
            traceback.print_exc()

        response.set_header('Powered-By', 'Polari')

    def on_put(self, request, response, domain_id=None):
        """
        Update an existing APIDomain.

        PUT /apiDomain/{domain_id}

        Request body: Same as POST

        Response:
        {
            "success": true,
            "domain": {...}
        }
        """
        try:
            from polariApiProfiler.apiDomain import APIDomain

            if not domain_id:
                response.status = falcon.HTTP_400
                response.media = {'success': False, 'error': 'domain_id is required'}
                return

            raw_data = request.bounded_stream.read()
            req_body = json.loads(raw_data.decode('utf-8'))

            # Find existing domain
            domains = self.manager.getListOfClassInstances('APIDomain')
            target_domain = None
            for dom in domains:
                if (hasattr(dom, 'id') and str(dom.id) == str(domain_id)) or dom.name == domain_id:
                    target_domain = dom
                    break

            if not target_domain:
                response.status = falcon.HTTP_404
                response.media = {'success': False, 'error': f'Domain not found: {domain_id}'}
                return

            # Update fields
            for key, value in req_body.items():
                if hasattr(target_domain, key) and key not in ['id', 'manager']:
                    setattr(target_domain, key, value)

            # Re-detect host type if host changed
            if 'host' in req_body:
                target_domain.hostType = target_domain._detect_host_type(target_domain.host)

            # Validate
            is_valid, errors = target_domain.validate()
            if not is_valid:
                response.status = falcon.HTTP_400
                response.media = {'success': False, 'error': 'Validation failed', 'validationErrors': errors}
                return

            response.status = falcon.HTTP_200
            response.media = {
                'success': True,
                'domain': target_domain.to_dict()
            }

        except json.JSONDecodeError:
            response.status = falcon.HTTP_400
            response.media = {'success': False, 'error': 'Invalid JSON in request body'}
        except Exception as e:
            response.status = falcon.HTTP_500
            response.media = {'success': False, 'error': str(e)}
            import traceback
            traceback.print_exc()

        response.set_header('Powered-By', 'Polari')

    def on_delete(self, request, response, domain_id=None):
        """
        Delete an APIDomain.

        DELETE /apiDomain/{domain_id}

        Response:
        {
            "success": true,
            "message": "Domain deleted"
        }
        """
        try:
            if not domain_id:
                response.status = falcon.HTTP_400
                response.media = {'success': False, 'error': 'domain_id is required'}
                return

            # Find and remove domain
            domains = self.manager.getListOfClassInstances('APIDomain')
            for dom in domains:
                if (hasattr(dom, 'id') and str(dom.id) == str(domain_id)) or dom.name == domain_id:
                    # Check if any endpoints use this domain
                    endpoints = self.manager.getListOfClassInstances('APIEndpoint')
                    using_endpoints = [ep for ep in endpoints if ep.domainName == dom.name]

                    if using_endpoints:
                        response.status = falcon.HTTP_400
                        response.media = {
                            'success': False,
                            'error': f'Cannot delete domain - {len(using_endpoints)} endpoint(s) are using it',
                            'usingEndpoints': [ep.name for ep in using_endpoints]
                        }
                        return

                    # Remove from manager's list
                    self.manager.removeTreeObject(dom)
                    response.status = falcon.HTTP_200
                    response.media = {
                        'success': True,
                        'message': f'Domain "{dom.name}" deleted'
                    }
                    return

            response.status = falcon.HTTP_404
            response.media = {'success': False, 'error': f'Domain not found: {domain_id}'}

        except Exception as e:
            response.status = falcon.HTTP_500
            response.media = {'success': False, 'error': str(e)}
            import traceback
            traceback.print_exc()

        response.set_header('Powered-By', 'Polari')


class APIEndpointAPI(treeObject):
    """
    Endpoint: /apiEndpoint

    CRUD operations for APIEndpoint objects (API data source configurations).
    """

    @treeObjectInit
    def __init__(self, polServer, manager=None, **kwargs):
        self.polServer = polServer
        self.apiName = '/apiEndpoint'
        if polServer is not None:
            polServer.falconServer.add_route(self.apiName, self)
            polServer.falconServer.add_route(self.apiName + '/{endpoint_id}', self)

    def on_get(self, request, response, endpoint_id=None):
        """
        Get all endpoints or a specific endpoint.

        GET /apiEndpoint - Get all endpoints (includes common pre-defined ones)
        GET /apiEndpoint/{endpoint_id} - Get specific endpoint

        Response:
        {
            "success": true,
            "endpoints": [...] or "endpoint": {...}
        }
        """
        try:
            from polariApiProfiler.apiEndpoint import APIEndpoint, COMMON_ENDPOINTS

            stored_endpoints = self.manager.getListOfClassInstances('APIEndpoint')

            if endpoint_id:
                # Find specific endpoint - check stored first
                for ep in stored_endpoints:
                    if (hasattr(ep, 'id') and str(ep.id) == str(endpoint_id)) or ep.name == endpoint_id:
                        response.status = falcon.HTTP_200
                        response.media = {
                            'success': True,
                            'endpoint': ep.to_dict()
                        }
                        return

                # Check common endpoints
                for common in COMMON_ENDPOINTS:
                    if common['name'] == endpoint_id:
                        ep = APIEndpoint.from_dict(common, manager=self.manager)
                        ep_dict = ep.to_dict()
                        ep_dict['isCommon'] = True
                        response.status = falcon.HTTP_200
                        response.media = {
                            'success': True,
                            'endpoint': ep_dict,
                            'isCommon': True
                        }
                        return

                response.status = falcon.HTTP_404
                response.media = {'success': False, 'error': f'Endpoint not found: {endpoint_id}'}
                return

            # Return all endpoints (stored + common)
            all_endpoints = [ep.to_dict() for ep in stored_endpoints]

            # Add common endpoints that aren't already stored
            stored_names = {ep.name for ep in stored_endpoints}
            for common in COMMON_ENDPOINTS:
                if common['name'] not in stored_names:
                    ep = APIEndpoint.from_dict(common, manager=self.manager)
                    ep_dict = ep.to_dict()
                    ep_dict['isCommon'] = True
                    all_endpoints.append(ep_dict)

            response.status = falcon.HTTP_200
            response.media = {
                'success': True,
                'count': len(all_endpoints),
                'endpoints': all_endpoints
            }

        except Exception as e:
            response.status = falcon.HTTP_500
            response.media = {'success': False, 'error': str(e)}
            import traceback
            traceback.print_exc()

        response.set_header('Powered-By', 'Polari')

    def on_post(self, request, response):
        """
        Create a new APIEndpoint.

        Request body:
        {
            "name": "myEndpoint",
            "displayName": "My Endpoint",
            "description": "Description",
            "url": "https://api.example.com/data",
            "httpMethod": "GET",
            "defaultHeaders": {},
            "responseRootPath": "data",
            "linkedProfileName": "",
            "persistData": false,
            "polariClassName": "",
            "authType": "none",
            "authConfig": ""
        }

        Response:
        {
            "success": true,
            "endpoint": {...}
        }
        """
        try:
            from polariApiProfiler.apiEndpoint import APIEndpoint

            raw_data = request.bounded_stream.read()
            req_body = json.loads(raw_data.decode('utf-8'))

            # Validate required fields
            if not req_body.get('name'):
                response.status = falcon.HTTP_400
                response.media = {'success': False, 'error': 'name is required'}
                return

            if not req_body.get('url'):
                response.status = falcon.HTTP_400
                response.media = {'success': False, 'error': 'url is required'}
                return

            # Check for duplicate name
            existing = self.manager.getListOfClassInstances('APIEndpoint')
            for ep in existing:
                if ep.name == req_body['name']:
                    response.status = falcon.HTTP_409
                    response.media = {'success': False, 'error': f'Endpoint with name "{req_body["name"]}" already exists'}
                    return

            # Create the endpoint
            endpoint = APIEndpoint.from_dict(req_body, manager=self.manager)

            # Validate
            is_valid, errors = endpoint.validate()
            if not is_valid:
                response.status = falcon.HTTP_400
                response.media = {'success': False, 'error': 'Validation failed', 'validationErrors': errors}
                return

            response.status = falcon.HTTP_201
            response.media = {
                'success': True,
                'endpoint': endpoint.to_dict()
            }

        except json.JSONDecodeError:
            response.status = falcon.HTTP_400
            response.media = {'success': False, 'error': 'Invalid JSON in request body'}
        except Exception as e:
            response.status = falcon.HTTP_500
            response.media = {'success': False, 'error': str(e)}
            import traceback
            traceback.print_exc()

        response.set_header('Powered-By', 'Polari')

    def on_put(self, request, response, endpoint_id=None):
        """
        Update an existing APIEndpoint.

        PUT /apiEndpoint/{endpoint_id}

        Request body: Same as POST

        Response:
        {
            "success": true,
            "endpoint": {...}
        }
        """
        try:
            from polariApiProfiler.apiEndpoint import APIEndpoint

            if not endpoint_id:
                response.status = falcon.HTTP_400
                response.media = {'success': False, 'error': 'endpoint_id is required'}
                return

            raw_data = request.bounded_stream.read()
            req_body = json.loads(raw_data.decode('utf-8'))

            # Find existing endpoint
            endpoints = self.manager.getListOfClassInstances('APIEndpoint')
            target_endpoint = None
            for ep in endpoints:
                if (hasattr(ep, 'id') and str(ep.id) == str(endpoint_id)) or ep.name == endpoint_id:
                    target_endpoint = ep
                    break

            if not target_endpoint:
                response.status = falcon.HTTP_404
                response.media = {'success': False, 'error': f'Endpoint not found: {endpoint_id}'}
                return

            # Update fields
            for key, value in req_body.items():
                if hasattr(target_endpoint, key) and key not in ['id', 'manager']:
                    setattr(target_endpoint, key, value)

            # Validate
            is_valid, errors = target_endpoint.validate()
            if not is_valid:
                response.status = falcon.HTTP_400
                response.media = {'success': False, 'error': 'Validation failed', 'validationErrors': errors}
                return

            response.status = falcon.HTTP_200
            response.media = {
                'success': True,
                'endpoint': target_endpoint.to_dict()
            }

        except json.JSONDecodeError:
            response.status = falcon.HTTP_400
            response.media = {'success': False, 'error': 'Invalid JSON in request body'}
        except Exception as e:
            response.status = falcon.HTTP_500
            response.media = {'success': False, 'error': str(e)}
            import traceback
            traceback.print_exc()

        response.set_header('Powered-By', 'Polari')

    def on_delete(self, request, response, endpoint_id=None):
        """
        Delete an APIEndpoint.

        DELETE /apiEndpoint/{endpoint_id}

        Response:
        {
            "success": true,
            "message": "Endpoint deleted"
        }
        """
        try:
            if not endpoint_id:
                response.status = falcon.HTTP_400
                response.media = {'success': False, 'error': 'endpoint_id is required'}
                return

            # Find and remove endpoint
            endpoints = self.manager.getListOfClassInstances('APIEndpoint')
            for ep in endpoints:
                if (hasattr(ep, 'id') and str(ep.id) == str(endpoint_id)) or ep.name == endpoint_id:
                    # Remove from manager's list
                    self.manager.removeTreeObject(ep)
                    response.status = falcon.HTTP_200
                    response.media = {
                        'success': True,
                        'message': f'Endpoint "{ep.name}" deleted'
                    }
                    return

            response.status = falcon.HTTP_404
            response.media = {'success': False, 'error': f'Endpoint not found: {endpoint_id}'}

        except Exception as e:
            response.status = falcon.HTTP_500
            response.media = {'success': False, 'error': str(e)}
            import traceback
            traceback.print_exc()

        response.set_header('Powered-By', 'Polari')


class APIEndpointFetchAPI(treeObject):
    """
    Endpoint: /apiEndpoint/fetch

    Fetch data from an APIEndpoint and optionally persist it.
    """

    @treeObjectInit
    def __init__(self, polServer, manager=None, **kwargs):
        self.polServer = polServer
        self.apiName = '/apiEndpoint/fetch'
        if polServer is not None:
            polServer.falconServer.add_route(self.apiName, self)
            polServer.falconServer.add_route(self.apiName + '/{endpoint_name}', self)

        self.profiler = APIProfiler(manager=manager)

    def on_post(self, request, response, endpoint_name=None):
        """
        Fetch data from an APIEndpoint.

        POST /apiEndpoint/fetch
        POST /apiEndpoint/fetch/{endpoint_name}

        Request body (if not using URL param):
        {
            "endpointName": "myEndpoint",
            "persist": true,  // Override endpoint's persistData setting
            "applyProfile": true  // Apply linked profile for type mapping
        }

        Response:
        {
            "success": true,
            "endpointName": "myEndpoint",
            "recordCount": 10,
            "data": [...],  // If not persisting, returns data
            "persisted": false,
            "persistedClassName": ""  // If persisted, the class name
        }
        """
        try:
            from polariApiProfiler.apiEndpoint import APIEndpoint

            # Get endpoint name from URL or body
            if not endpoint_name:
                raw_data = request.bounded_stream.read()
                if raw_data:
                    req_body = json.loads(raw_data.decode('utf-8'))
                    endpoint_name = req_body.get('endpointName')
                else:
                    req_body = {}

                if not endpoint_name:
                    response.status = falcon.HTTP_400
                    response.media = {'success': False, 'error': 'endpointName is required'}
                    return
            else:
                # Read body for options
                raw_data = request.bounded_stream.read()
                req_body = json.loads(raw_data.decode('utf-8')) if raw_data else {}

            # Find the endpoint
            endpoints = self.manager.getListOfClassInstances('APIEndpoint')
            target_endpoint = None
            for ep in endpoints:
                if ep.name == endpoint_name:
                    target_endpoint = ep
                    break

            if not target_endpoint:
                response.status = falcon.HTTP_404
                response.media = {'success': False, 'error': f'Endpoint not found: {endpoint_name}'}
                return

            if not target_endpoint.isActive:
                response.status = falcon.HTTP_400
                response.media = {'success': False, 'error': f'Endpoint is not active: {endpoint_name}'}
                return

            # Fetch from the API
            headers = target_endpoint.get_headers_with_auth()
            body = None
            if target_endpoint.bodyTemplate and target_endpoint.httpMethod in ['POST', 'PUT', 'PATCH']:
                body = json.loads(target_endpoint.bodyTemplate)

            api_response, error = self.profiler.query_external_api(
                url=target_endpoint.url,
                method=target_endpoint.httpMethod,
                headers=headers,
                body=body
            )

            if error and api_response is None:
                target_endpoint.update_fetch_result(success=False, error=error)
                response.status = falcon.HTTP_502
                response.media = {
                    'success': False,
                    'error': error,
                    'debug': self.profiler.lastQueryDebug
                }
                return

            # Extract data from response root path
            data = self.profiler.extract_data_from_path(api_response, target_endpoint.responseRootPath)

            if data is None:
                target_endpoint.update_fetch_result(success=False, error='Could not extract data from response')
                response.status = falcon.HTTP_400
                response.media = {
                    'success': False,
                    'error': f'Could not extract data from path: {target_endpoint.responseRootPath}',
                    'response': api_response
                }
                return

            # Calculate record count
            record_count = len(data) if isinstance(data, list) else 1

            # Update endpoint with fetch result
            target_endpoint.update_fetch_result(
                success=True,
                response_data=data,
                record_count=record_count
            )

            result = {
                'success': True,
                'endpointName': endpoint_name,
                'recordCount': record_count,
                'fieldCount': target_endpoint.lastResponseFieldCount,
                'fetchTime': target_endpoint.lastFetchTime
            }

            # Determine if we should persist
            should_persist = req_body.get('persist', target_endpoint.persistData)
            apply_profile = req_body.get('applyProfile', True)

            if should_persist and target_endpoint.polariClassName:
                # Check if the class exists
                class_name = target_endpoint.polariClassName

                if class_name not in self.manager.objectTypingDict:
                    # Try to create the class from the linked profile
                    if target_endpoint.linkedProfileName and apply_profile:
                        profiles = self.manager.getListOfClassInstances('APIProfile')
                        linked_profile = None
                        for p in profiles:
                            if p.profileName == target_endpoint.linkedProfileName:
                                linked_profile = p
                                break

                        if linked_profile:
                            # Create class from profile
                            class_def = self.profiler.profile_to_class_definition(linked_profile)
                            class_def['className'] = class_name

                            # Find createClassAPI
                            create_class_api = None
                            for api in self.polServer.customAPIsList:
                                if hasattr(api, 'apiName') and api.apiName == '/createClass':
                                    create_class_api = api
                                    break

                            if create_class_api:
                                create_class_api._createDynamicClass(
                                    className=class_def['className'],
                                    displayName=class_def.get('classDisplayName', class_name),
                                    variables=class_def['variables'],
                                    registerCRUDE=True,
                                    isStateSpaceObject=True
                                )
                                result['classCreated'] = True

                # Persist the data
                if class_name in self.manager.objectTypingDict:
                    items = data if isinstance(data, list) else [data]
                    persisted_count = 0

                    for item in items:
                        if isinstance(item, dict):
                            try:
                                # Create instance of the class
                                cls = self.manager.objectTypingDict[class_name].classCalled
                                instance = cls(manager=self.manager, **item)
                                persisted_count += 1
                            except Exception as create_err:
                                print(f"Error creating instance: {create_err}")

                    result['persisted'] = True
                    result['persistedClassName'] = class_name
                    result['persistedCount'] = persisted_count
                else:
                    result['persisted'] = False
                    result['persistError'] = f'Class {class_name} does not exist'
                    result['data'] = data
            else:
                # Return the data without persisting
                result['persisted'] = False
                result['data'] = data

            response.status = falcon.HTTP_200
            response.media = result

        except json.JSONDecodeError:
            response.status = falcon.HTTP_400
            response.media = {'success': False, 'error': 'Invalid JSON in request body'}
        except Exception as e:
            response.status = falcon.HTTP_500
            response.media = {'success': False, 'error': str(e)}
            import traceback
            traceback.print_exc()

        response.set_header('Powered-By', 'Polari')

    def on_get(self, request, response, endpoint_name=None):
        """
        Get fetch status/history for an endpoint.

        GET /apiEndpoint/fetch/{endpoint_name}

        Response:
        {
            "success": true,
            "endpointName": "myEndpoint",
            "lastFetchTime": "2024-01-15T10:30:00",
            "lastFetchSuccess": true,
            "lastResponseSample": {...},
            "lastResponseRecordCount": 10
        }
        """
        try:
            if not endpoint_name:
                response.status = falcon.HTTP_400
                response.media = {'success': False, 'error': 'endpoint_name is required'}
                return

            # Find the endpoint
            endpoints = self.manager.getListOfClassInstances('APIEndpoint')
            target_endpoint = None
            for ep in endpoints:
                if ep.name == endpoint_name:
                    target_endpoint = ep
                    break

            if not target_endpoint:
                response.status = falcon.HTTP_404
                response.media = {'success': False, 'error': f'Endpoint not found: {endpoint_name}'}
                return

            response.status = falcon.HTTP_200
            response.media = {
                'success': True,
                'endpointName': endpoint_name,
                'displayName': target_endpoint.displayName,
                'url': target_endpoint.url,
                'linkedProfileName': target_endpoint.linkedProfileName,
                'persistData': target_endpoint.persistData,
                'polariClassName': target_endpoint.polariClassName,
                'lastFetchTime': target_endpoint.lastFetchTime,
                'lastFetchSuccess': target_endpoint.lastFetchSuccess,
                'lastFetchError': target_endpoint.lastFetchError,
                'lastResponseSample': target_endpoint.lastResponseSample,
                'lastResponseFieldCount': target_endpoint.lastResponseFieldCount,
                'lastResponseRecordCount': target_endpoint.lastResponseRecordCount,
                'isActive': target_endpoint.isActive
            }

        except Exception as e:
            response.status = falcon.HTTP_500
            response.media = {'success': False, 'error': str(e)}
            import traceback
            traceback.print_exc()

        response.set_header('Powered-By', 'Polari')
