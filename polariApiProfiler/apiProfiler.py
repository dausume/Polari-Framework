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
APIProfiler - Core profiling logic that wraps Polari's existing typing system.

This class provides functionality to:
1. Query external APIs and parse responses
2. Analyze response structures using polyTypedObject/polyTypedVariable
3. Refine profiles with additional samples
4. Detect multiple object types in heterogeneous responses
"""

from objectTreeDecorators import treeObject, treeObjectInit
from polariDataTyping.polyTyping import polyTypedObject
from polariDataTyping.polyTypedVars import polyTypedVariable
from polariApiProfiler.apiProfile import APIProfile
from typing import Dict, List, Optional, Any, Tuple
import json
import urllib.request
import urllib.error
import ssl
import socket
from datetime import datetime

# Try to import requests for better HTTP handling
try:
    import requests
    HAS_REQUESTS = True
except ImportError:
    HAS_REQUESTS = False
    print("[APIProfiler] requests library not available, using urllib")


class APIProfiler(treeObject):
    """
    Core profiling class that wraps Polari's existing typing system for API analysis.

    Uses the existing polyTypedObject.analyzeInstance() and polyTypedVariable
    infrastructure to analyze JSON response structures.
    """

    @treeObjectInit
    def __init__(self, manager=None, **kwargs):
        self.lastQueryUrl = ''
        self.lastQueryResponse = None
        self.lastQueryError = ''
        self.lastQueryDebug = {}
        self.requestTimeout = 60  # seconds - increased for slower connections
        self.useRequests = HAS_REQUESTS  # Use requests library if available

    def _clean_url(self, url: str) -> str:
        """
        Clean up a URL, fixing common issues like double protocols.

        Args:
            url: The URL to clean

        Returns:
            Cleaned URL
        """
        if not url:
            return url

        original_url = url
        url = url.strip()

        # Fix double protocol issue (https://https:// or http://http://)
        while 'https://https://' in url:
            url = url.replace('https://https://', 'https://')
            print(f"[APIProfiler] Fixed double https:// in URL")

        while 'http://http://' in url:
            url = url.replace('http://http://', 'http://')
            print(f"[APIProfiler] Fixed double http:// in URL")

        # Fix mixed protocol issue (https://http:// or http://https://)
        if 'https://http://' in url:
            url = url.replace('https://http://', 'http://')
            print(f"[APIProfiler] Fixed https://http:// in URL")

        if 'http://https://' in url:
            url = url.replace('http://https://', 'https://')
            print(f"[APIProfiler] Fixed http://https:// in URL")

        if url != original_url:
            print(f"[APIProfiler] URL cleaned: {original_url} -> {url}")

        return url

    def query_external_api(
        self,
        url: str,
        method: str = 'GET',
        headers: Dict[str, str] = None,
        body: Any = None,
        timeout: int = None,
        verify_ssl: bool = False
    ) -> Tuple[Any, Optional[str]]:
        """
        Fetch from an external API and return parsed JSON.

        Args:
            url: The API endpoint URL
            method: HTTP method (GET, POST, etc.)
            headers: Optional HTTP headers dict
            body: Optional request body (for POST/PUT)
            timeout: Request timeout in seconds
            verify_ssl: Whether to verify SSL certificates (default False for dev)

        Returns:
            Tuple of (parsed_response, error_message)
            If successful, error_message is None
            If failed, parsed_response is None
        """
        # Clean up URL - fix double protocol issues
        url = self._clean_url(url)

        self.lastQueryUrl = url
        self.lastQueryResponse = None
        self.lastQueryError = ''
        self.lastQueryDebug = {
            'url': url,
            'method': method,
            'timeout': timeout or self.requestTimeout,
            'has_body': body is not None,
            'using_requests': self.useRequests and HAS_REQUESTS
        }

        headers = headers or {}
        timeout = timeout or self.requestTimeout

        # Ensure we have required headers
        if 'User-Agent' not in headers:
            headers['User-Agent'] = 'PolariAPIProfiler/1.0'
        if 'Accept' not in headers:
            headers['Accept'] = 'application/json'

        print(f"[APIProfiler] Querying: {method} {url}")
        print(f"[APIProfiler] Timeout: {timeout}s, SSL verify: {verify_ssl}")

        # Use requests library if available (better SSL handling)
        if self.useRequests and HAS_REQUESTS:
            return self._query_with_requests(url, method, headers, body, timeout, verify_ssl)
        else:
            return self._query_with_urllib(url, method, headers, body, timeout, verify_ssl)

    def _query_with_requests(
        self,
        url: str,
        method: str,
        headers: Dict[str, str],
        body: Any,
        timeout: int,
        verify_ssl: bool
    ) -> Tuple[Any, Optional[str]]:
        """Query using the requests library."""
        try:
            # Prepare request body
            json_body = None
            data_body = None

            if body is not None:
                if isinstance(body, (dict, list)):
                    json_body = body
                elif isinstance(body, str):
                    data_body = body
                elif isinstance(body, bytes):
                    data_body = body

            # Suppress SSL warnings if not verifying
            if not verify_ssl:
                import urllib3
                urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

            # Make request
            response = requests.request(
                method=method.upper(),
                url=url,
                headers=headers,
                json=json_body,
                data=data_body,
                timeout=timeout,
                verify=verify_ssl
            )

            self.lastQueryDebug['status_code'] = response.status_code
            self.lastQueryDebug['response_size'] = len(response.content)

            print(f"[APIProfiler] Response: {response.status_code}, size: {len(response.content)} bytes")

            # Check for HTTP errors
            if response.status_code >= 400:
                error_msg = f"HTTP Error {response.status_code}: {response.reason}"
                self.lastQueryError = error_msg
                # Try to get error body
                try:
                    error_body = response.json()
                    self.lastQueryDebug['error_body'] = error_body
                except:
                    self.lastQueryDebug['error_body'] = response.text[:500]
                return (None, error_msg)

            # Try to parse as JSON
            try:
                parsed = response.json()
                self.lastQueryResponse = parsed
                return (parsed, None)
            except json.JSONDecodeError as e:
                # Return raw string if not JSON
                self.lastQueryResponse = response.text
                return (response.text, f"Response is not valid JSON: {str(e)}")

        except requests.exceptions.Timeout as e:
            error_msg = f"Request timed out after {timeout} seconds"
            self.lastQueryError = error_msg
            self.lastQueryDebug['error_type'] = 'timeout'
            print(f"[APIProfiler] ERROR: {error_msg}")
            return (None, error_msg)
        except requests.exceptions.SSLError as e:
            error_msg = f"SSL Error: {str(e)}"
            self.lastQueryError = error_msg
            self.lastQueryDebug['error_type'] = 'ssl'
            print(f"[APIProfiler] ERROR: {error_msg}")
            return (None, error_msg)
        except requests.exceptions.ConnectionError as e:
            error_msg = f"Connection Error: {str(e)}"
            self.lastQueryError = error_msg
            self.lastQueryDebug['error_type'] = 'connection'
            print(f"[APIProfiler] ERROR: {error_msg}")
            return (None, error_msg)
        except Exception as e:
            error_msg = f"Request failed: {type(e).__name__}: {str(e)}"
            self.lastQueryError = error_msg
            self.lastQueryDebug['error_type'] = type(e).__name__
            print(f"[APIProfiler] ERROR: {error_msg}")
            return (None, error_msg)

    def _query_with_urllib(
        self,
        url: str,
        method: str,
        headers: Dict[str, str],
        body: Any,
        timeout: int,
        verify_ssl: bool
    ) -> Tuple[Any, Optional[str]]:
        """Query using urllib (fallback if requests not available)."""
        try:
            # Prepare request body
            data = None
            if body is not None:
                if isinstance(body, (dict, list)):
                    data = json.dumps(body).encode('utf-8')
                    if 'Content-Type' not in headers:
                        headers['Content-Type'] = 'application/json'
                elif isinstance(body, str):
                    data = body.encode('utf-8')
                elif isinstance(body, bytes):
                    data = body

            # Create request
            request = urllib.request.Request(
                url,
                data=data,
                headers=headers,
                method=method.upper()
            )

            # Create SSL context
            ssl_context = ssl.create_default_context()
            if not verify_ssl:
                ssl_context.check_hostname = False
                ssl_context.verify_mode = ssl.CERT_NONE

            # Make request
            with urllib.request.urlopen(request, timeout=timeout, context=ssl_context) as response:
                response_data = response.read().decode('utf-8')
                self.lastQueryDebug['status_code'] = response.status
                self.lastQueryDebug['response_size'] = len(response_data)

                print(f"[APIProfiler] Response: {response.status}, size: {len(response_data)} bytes")

                # Try to parse as JSON
                try:
                    parsed = json.loads(response_data)
                    self.lastQueryResponse = parsed
                    return (parsed, None)
                except json.JSONDecodeError as e:
                    # Return raw string if not JSON
                    self.lastQueryResponse = response_data
                    return (response_data, f"Response is not valid JSON: {str(e)}")

        except urllib.error.HTTPError as e:
            error_msg = f"HTTP Error {e.code}: {e.reason}"
            self.lastQueryError = error_msg
            self.lastQueryDebug['error_type'] = 'http'
            print(f"[APIProfiler] ERROR: {error_msg}")
            return (None, error_msg)
        except urllib.error.URLError as e:
            error_msg = f"URL Error: {str(e.reason)}"
            self.lastQueryError = error_msg
            self.lastQueryDebug['error_type'] = 'url'
            print(f"[APIProfiler] ERROR: {error_msg}")
            return (None, error_msg)
        except socket.timeout as e:
            error_msg = f"Request timed out after {timeout} seconds"
            self.lastQueryError = error_msg
            self.lastQueryDebug['error_type'] = 'timeout'
            print(f"[APIProfiler] ERROR: {error_msg}")
            return (None, error_msg)
        except ssl.SSLError as e:
            error_msg = f"SSL Error: {str(e)}"
            self.lastQueryError = error_msg
            self.lastQueryDebug['error_type'] = 'ssl'
            print(f"[APIProfiler] ERROR: {error_msg}")
            return (None, error_msg)
        except Exception as e:
            error_msg = f"Request failed: {type(e).__name__}: {str(e)}"
            self.lastQueryError = error_msg
            self.lastQueryDebug['error_type'] = type(e).__name__
            print(f"[APIProfiler] ERROR: {error_msg}")
            return (None, error_msg)

    def extract_data_from_path(self, response: Any, root_path: str = '') -> Any:
        """
        Extract data from a response using a dot-notation path.

        Args:
            response: The parsed JSON response
            root_path: Dot-notation path to the data (e.g., "data.items")

        Returns:
            The extracted data, or the original response if path is empty
        """
        if not root_path:
            return response

        parts = root_path.split('.')
        current = response

        for part in parts:
            if isinstance(current, dict) and part in current:
                current = current[part]
            elif isinstance(current, list) and part.isdigit():
                idx = int(part)
                if 0 <= idx < len(current):
                    current = current[idx]
                else:
                    return None
            else:
                return None

        return current

    def analyze_response_with_polari_typing(
        self,
        response_data: Any,
        profile_name: str,
        display_name: str = ''
    ) -> Tuple[APIProfile, polyTypedObject]:
        """
        Use Polari's existing typing system to analyze API response structure.

        Creates a temporary class from the response structure, wraps it with
        polyTypedObject, and uses analyzeInstance()/analyzeVariableValue()
        to build typing information.

        Args:
            response_data: The parsed API response (dict or list of dicts)
            profile_name: Name for the profile/class being created
            display_name: Human-readable display name

        Returns:
            Tuple of (APIProfile, polyTypedObject)
        """
        display_name = display_name or profile_name

        # Build field and type signatures using recursive analysis
        field_signatures, type_signatures = self._analyze_structure_recursive(response_data)

        # Normalize to list for consistent handling of top-level data
        samples = response_data if isinstance(response_data, list) else [response_data]

        # Filter to only dict samples (JSON objects)
        dict_samples = [s for s in samples if isinstance(s, dict)]

        if not dict_samples:
            raise ValueError("No valid object samples found in response data")

        # Get field names for class creation (from level 0 for objects, level 1 for arrays)
        if isinstance(response_data, list):
            class_fields = field_signatures.get(1, [])
        else:
            class_fields = field_signatures.get(0, [])

        # Create a dynamic class to hold the analyzed structure
        class_name = self._make_class_name(profile_name)

        # Build default values from first sample
        first_sample = dict_samples[0]
        var_defaults = {}
        for field in class_fields:
            if field in first_sample:
                var_defaults[field] = self._get_default_for_value(first_sample[field])
            else:
                var_defaults[field] = None

        # Create dynamic class
        DynamicClass = self._create_analysis_class(class_name, var_defaults)

        # Create polyTypedObject for the class
        poly_typed_obj = polyTypedObject(
            className=class_name,
            manager=self.manager,
            sourceFiles=[],
            identifierVariables=['id'],
            objectReferencesDict={},
            classDefinition=DynamicClass,
            kwRequiredParams=[],
            kwDefaultParams=list(var_defaults.keys()),
            allowClassEdit=True,
            isStateSpaceObject=False,
            excludeFromCRUDE=True  # Don't auto-register CRUDE for analysis classes
        )

        # Analyze each sample to build up typing variations
        for sample in dict_samples:
            # Create instance-like object for analysis
            for field_name, field_value in sample.items():
                poly_typed_obj.analyzeVariableValue(varName=field_name, varVal=field_value)

        # Calculate totals
        total_fields = sum(len(fields) for fields in field_signatures.values())
        total_types = len(type_signatures)

        # Create the APIProfile with new signature format
        profile = APIProfile(
            profileName=profile_name,
            displayName=display_name,
            polyTypedObjectRef=class_name,
            sampleCount=len(dict_samples),
            fieldSignatures=field_signatures,
            typeSignatures=type_signatures,
            totalFieldSignatures=total_fields,
            totalTypeSignatures=total_types,
            manager=self.manager
        )

        # Register with manager if available
        if self.manager:
            if class_name not in self.manager.objectTypingDict:
                self.manager.objectTypingDict[class_name] = poly_typed_obj
                if poly_typed_obj not in self.manager.objectTyping:
                    self.manager.objectTyping.append(poly_typed_obj)

        return (profile, poly_typed_obj)

    def _analyze_structure_recursive(
        self,
        data: Any,
        level: int = 0,
        field_sigs: Dict[int, List[str]] = None,
        type_sigs: Dict[int, str] = None,
        max_depth: int = 10
    ) -> Tuple[Dict[int, List[str]], Dict[int, str]]:
        """
        Recursively analyze data structure to build field and type signatures.

        Args:
            data: The data to analyze
            level: Current nesting level (0 = root)
            field_sigs: Dict to populate with level -> field names
            type_sigs: Dict to populate with level -> type description
            max_depth: Maximum recursion depth

        Returns:
            Tuple of (fieldSignatures, typeSignatures)
        """
        if field_sigs is None:
            field_sigs = {}
        if type_sigs is None:
            type_sigs = {}

        if level > max_depth:
            return (field_sigs, type_sigs)

        if data is None:
            type_sigs[level] = 'null'
            return (field_sigs, type_sigs)

        if isinstance(data, dict):
            type_sigs[level] = 'dict'

            if data:
                field_names = list(data.keys())
                if level not in field_sigs:
                    field_sigs[level] = []
                for name in field_names:
                    if name not in field_sigs[level]:
                        field_sigs[level].append(name)

                # Recursively analyze nested values
                for key, value in data.items():
                    self._analyze_structure_recursive(value, level + 1, field_sigs, type_sigs, max_depth)

        elif isinstance(data, list):
            if not data:
                type_sigs[level] = 'list'
                return (field_sigs, type_sigs)

            # Determine item types
            item_types = set()
            for item in data[:10]:
                item_types.add(type(item).__name__)

            if len(item_types) == 1:
                item_type = list(item_types)[0]
                type_sigs[level] = f'list[{item_type}]'

                if item_type == 'dict':
                    # Collect fields from all sampled items
                    all_fields = set()
                    for item in data[:10]:
                        if isinstance(item, dict):
                            all_fields.update(item.keys())

                    if level + 1 not in field_sigs:
                        field_sigs[level + 1] = []
                    for name in all_fields:
                        if name not in field_sigs[level + 1]:
                            field_sigs[level + 1].append(name)

                    # Recursively analyze first item's nested values
                    if data and isinstance(data[0], dict):
                        for key, value in data[0].items():
                            self._analyze_structure_recursive(value, level + 2, field_sigs, type_sigs, max_depth)

                elif item_type == 'list' and data[0]:
                    self._analyze_structure_recursive(data[0], level + 1, field_sigs, type_sigs, max_depth)
            else:
                type_sigs[level] = f'list[mixed:{",".join(sorted(item_types))}]'

        elif isinstance(data, bool):
            type_sigs[level] = 'bool'
        elif isinstance(data, int):
            type_sigs[level] = 'int'
        elif isinstance(data, float):
            type_sigs[level] = 'float'
        elif isinstance(data, str):
            type_sigs[level] = 'str'
        else:
            type_sigs[level] = type(data).__name__

        return (field_sigs, type_sigs)

    def refine_profile_with_sample(
        self,
        profile: APIProfile,
        new_sample: Any
    ) -> APIProfile:
        """
        Add more samples to an existing profile to refine type analysis.

        Uses the existing analyzeInstance() to update type variations
        in the associated polyTypedObject.

        Args:
            profile: The existing APIProfile to refine
            new_sample: New sample data (dict or list of dicts)

        Returns:
            The updated APIProfile
        """
        poly_typed_obj = profile.get_poly_typed_object()
        if not poly_typed_obj:
            raise ValueError(f"No polyTypedObject found for profile '{profile.profileName}'")

        # Normalize to list
        samples = new_sample if isinstance(new_sample, list) else [new_sample]
        dict_samples = [s for s in samples if isinstance(s, dict)]

        # Analyze new sample structure and merge with existing signatures
        new_field_sigs, new_type_sigs = self._analyze_structure_recursive(new_sample)

        # Merge field signatures - add new fields at each level
        for level, fields in new_field_sigs.items():
            if level not in profile.fieldSignatures:
                profile.fieldSignatures[level] = []
            for field in fields:
                if field not in profile.fieldSignatures[level]:
                    profile.fieldSignatures[level].append(field)

        # Merge type signatures - keep existing types, add new levels
        for level, type_str in new_type_sigs.items():
            if level not in profile.typeSignatures:
                profile.typeSignatures[level] = type_str

        # Update totals
        profile.update_counts()

        # Analyze new samples for polyTypedObject
        for sample in dict_samples:
            for field_name, field_value in sample.items():
                poly_typed_obj.analyzeVariableValue(varName=field_name, varVal=field_value)

        profile.sampleCount += len(dict_samples)
        profile.lastUpdated = datetime.now().isoformat()

        return profile

    def detect_object_types(
        self,
        response_data: Any,
        type_field: str = None,
        similarity_threshold: float = 0.7
    ) -> List[Dict[str, Any]]:
        """
        Detect multiple object types in a heterogeneous API response.

        Method 1 (Field-based): If type_field specified, group by that field's values
        Method 2 (Signature-based): Cluster by field presence patterns using Jaccard similarity

        Args:
            response_data: List of response objects to analyze
            type_field: Optional field name that indicates object type
            similarity_threshold: Threshold for signature-based clustering (0-1)

        Returns:
            List of dicts with keys:
                - typeId: Identifier for this type
                - sampleCount: Number of items of this type
                - fieldSignature: List of fields present
                - method: 'field' or 'signature'
                - samples: Sample items of this type
        """
        # Normalize to list
        items = response_data if isinstance(response_data, list) else [response_data]
        dict_items = [item for item in items if isinstance(item, dict)]

        if not dict_items:
            return []

        detected_types = []

        # Method 1: Field-based detection
        if type_field:
            type_groups = {}
            untyped_items = []

            for item in dict_items:
                if type_field in item and item[type_field] is not None:
                    type_value = str(item[type_field])
                    if type_value not in type_groups:
                        type_groups[type_value] = []
                    type_groups[type_value].append(item)
                else:
                    untyped_items.append(item)

            for type_value, items_list in type_groups.items():
                # Get field signature for this type
                all_fields = set()
                for item in items_list:
                    all_fields.update(item.keys())

                detected_types.append({
                    'typeId': type_value,
                    'sampleCount': len(items_list),
                    'fieldSignature': sorted(list(all_fields)),
                    'method': 'field',
                    'samples': items_list[:3]  # Include up to 3 samples
                })

            # Process untyped items with signature-based detection
            if untyped_items:
                signature_types = self._detect_by_signature(untyped_items, similarity_threshold)
                detected_types.extend(signature_types)

        else:
            # Method 2: Signature-based detection only
            detected_types = self._detect_by_signature(dict_items, similarity_threshold)

        return detected_types

    def _detect_by_signature(
        self,
        items: List[dict],
        similarity_threshold: float
    ) -> List[Dict[str, Any]]:
        """
        Cluster items by field presence patterns using Jaccard similarity.

        Args:
            items: List of dict items to cluster
            similarity_threshold: Minimum Jaccard similarity to merge clusters

        Returns:
            List of detected type dicts
        """
        if not items:
            return []

        # Get field signature for each item
        signatures = []
        for item in items:
            sig = frozenset(item.keys())
            signatures.append(sig)

        # Simple clustering: group by exact signature first
        signature_groups = {}
        for i, sig in enumerate(signatures):
            if sig not in signature_groups:
                signature_groups[sig] = []
            signature_groups[sig].append(items[i])

        # Merge similar signatures
        merged_groups = []
        used_sigs = set()

        for sig, group in signature_groups.items():
            if sig in used_sigs:
                continue

            merged_items = list(group)
            merged_fields = set(sig)
            used_sigs.add(sig)

            # Try to merge with similar signatures
            for other_sig, other_group in signature_groups.items():
                if other_sig in used_sigs:
                    continue

                # Calculate Jaccard similarity
                intersection = len(sig & other_sig)
                union = len(sig | other_sig)
                similarity = intersection / union if union > 0 else 0

                if similarity >= similarity_threshold:
                    merged_items.extend(other_group)
                    merged_fields.update(other_sig)
                    used_sigs.add(other_sig)

            merged_groups.append({
                'items': merged_items,
                'fields': merged_fields
            })

        # Convert to output format
        detected_types = []
        for i, group in enumerate(merged_groups):
            type_id = f"type_{i+1}"

            # Try to infer a better type name from common fields
            fields = group['fields']
            if 'type' in fields and group['items']:
                # Use 'type' field value if present
                type_vals = set()
                for item in group['items']:
                    if 'type' in item and item['type']:
                        type_vals.add(str(item['type']))
                if len(type_vals) == 1:
                    type_id = list(type_vals)[0]

            detected_types.append({
                'typeId': type_id,
                'sampleCount': len(group['items']),
                'fieldSignature': sorted(list(group['fields'])),
                'method': 'signature',
                'samples': group['items'][:3]
            })

        return detected_types

    def _make_class_name(self, profile_name: str) -> str:
        """
        Convert a profile name to a valid Python class name.

        Args:
            profile_name: The profile name

        Returns:
            Valid PascalCase class name
        """
        # Remove non-alphanumeric characters and split
        parts = ''.join(c if c.isalnum() or c == '_' else ' ' for c in profile_name).split()

        # PascalCase
        class_name = ''.join(part.capitalize() for part in parts)

        # Ensure starts with letter
        if class_name and not class_name[0].isalpha():
            class_name = 'Profile' + class_name

        return class_name or 'UnnamedProfile'

    def _get_default_for_value(self, value: Any) -> Any:
        """
        Get a default value based on the type of the provided value.

        Args:
            value: Sample value to infer type from

        Returns:
            Appropriate default value for that type
        """
        if value is None:
            return None
        if isinstance(value, bool):
            return False
        if isinstance(value, int):
            return 0
        if isinstance(value, float):
            return 0.0
        if isinstance(value, str):
            return ''
        if isinstance(value, list):
            return []
        if isinstance(value, dict):
            return {}
        return None

    def _create_analysis_class(self, class_name: str, var_defaults: Dict[str, Any]) -> type:
        """
        Create a dynamic class for analysis purposes.

        Args:
            class_name: Name for the class
            var_defaults: Dict of variable names to default values

        Returns:
            The created class
        """
        from objectTreeDecorators import treeObject, treeObjectInit

        # Filter out tree-object base params
        base_params = {'id', 'manager', 'branch', 'inTree'}
        custom_defaults = {k: v for k, v in var_defaults.items() if k not in base_params}

        # Build parameter string for dynamic init
        param_names = list(custom_defaults.keys())
        param_str = ', '.join([f"{name}={repr(default)}" for name, default in custom_defaults.items()])
        if param_str:
            param_str = ', ' + param_str

        # Build body assignments
        body_assignments = '\n'.join([f'    self.{name} = {name}' for name in param_names])
        if not body_assignments:
            body_assignments = '    pass'

        func_code = f'''
def dynamic_init(self, manager=None, branch=None, id=None{param_str}):
    treeObject.__init__(self, manager=manager, branch=branch, id=id)
{body_assignments}
'''

        # Execute to create the function
        local_ns = {'treeObject': treeObject}
        exec(func_code, local_ns)
        dynamic_init = local_ns['dynamic_init']

        # Create class attributes
        class_attrs = {
            '__init__': treeObjectInit(dynamic_init),
            '_analysisClass': True,
            '_fieldDefaults': var_defaults
        }

        # Create the class
        DynamicClass = type(class_name, (treeObject,), class_attrs)
        return DynamicClass

    def profile_to_class_definition(self, profile: APIProfile) -> Dict[str, Any]:
        """
        Convert an APIProfile's polyTypedObject info to createClassAPI format.

        Uses profile.polyTypedObject.polyTypedVars to build variable definitions.

        Args:
            profile: The APIProfile to convert

        Returns:
            Dict in createClassAPI format for dynamic class creation
        """
        poly_typed_obj = profile.get_poly_typed_object()

        variables = []
        if poly_typed_obj and poly_typed_obj.polyTypedVars:
            for poly_var in poly_typed_obj.polyTypedVars:
                var_type = self._map_polari_type_to_simple(poly_var.pythonTypeDefault)
                variables.append({
                    'varName': poly_var.name,
                    'varType': var_type,
                    'varDisplayName': poly_var.name.replace('_', ' ').title()
                })
        else:
            # Fallback to field signatures if no polyTypedVars
            # Use all fields from all levels
            all_fields = profile.get_field_names()
            for field in all_fields:
                variables.append({
                    'varName': field,
                    'varType': 'str',  # Default to string
                    'varDisplayName': field.replace('_', ' ').title()
                })

        return {
            'className': self._make_class_name(profile.profileName),
            'classDisplayName': profile.displayName,
            'variables': variables,
            'registerCRUDE': True,
            'isStateSpaceObject': True
        }

    def _map_polari_type_to_simple(self, polari_type: str) -> str:
        """
        Map a Polari type string to a simple type for createClassAPI.

        Args:
            polari_type: The Polari type string (e.g., 'str', 'int', 'list(str,)')

        Returns:
            Simple type string ('str', 'int', 'float', 'list', 'dict', 'bool')
        """
        if not polari_type:
            return 'str'

        polari_type = polari_type.lower()

        # Direct mappings
        simple_types = ['str', 'int', 'float', 'bool', 'list', 'dict']
        for simple in simple_types:
            if polari_type == simple:
                return simple

        # Complex type mappings
        if polari_type.startswith('list(') or polari_type.startswith('tuple('):
            return 'list'
        if polari_type.startswith('dict('):
            return 'dict'
        if 'int' in polari_type or 'float' in polari_type:
            return 'float'
        if 'bool' in polari_type:
            return 'bool'
        if polari_type == 'nonetype':
            return 'str'  # Default None to string

        # Default to string for unknown types
        return 'str'
