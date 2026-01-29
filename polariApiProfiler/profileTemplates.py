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
Profile Templates - Structural profile definitions for API response matching.

Profiles are matched based on structural signatures:
- Level 0: Root structure type - {} (object) or [] (array)
- Level 1: Structural fields - Required fields that identify the format
- Data Path: Where the actual data records live

Matching logic:
1. First check Level 0 - eliminates incompatible profiles immediately
2. Then check Level 1 structural fields - required fields must be present
3. Calculate confidence based on structural field matches
"""

from typing import Dict, List, Any, Optional


# =============================================================================
# STRUCTURAL FORMAT PROFILES
# =============================================================================
# Each profile defines:
#   - rootType: "object" or "array" (Level 0)
#   - structuralFields: Dict of field_name -> {"required": bool, "type": str}
#   - dataPath: JSONPath to the data records (empty string = root)
#   - level1ExpectedType: What type is expected at Level 1 ("object" or "array")
# =============================================================================

FORMAT_PROFILES = {
    # -------------------------------------------------------------------------
    # UNIFORM ARRAY PROFILES (Level 0 = [])
    # -------------------------------------------------------------------------
    'uniformArray': {
        'profileName': 'uniformArray',
        'displayName': 'Uniform Object Array',
        'description': 'Array of objects with identical structure - most common REST collection format',
        'rootType': 'array',  # Level 0 is []
        'level1ExpectedType': 'object',  # Level 1 items are all {}
        'structuralFields': {},  # No structural fields at Level 1 - it's just array elements
        'dataPath': '',  # Data is at root
        'sampleSchema': '[\n  { <field>: <type>, ... },\n  { <field>: <type>, ... },\n  ...\n]'
    },

    # -------------------------------------------------------------------------
    # OBJECT WRAPPER PROFILES (Level 0 = {})
    # -------------------------------------------------------------------------
    'polariCrude': {
        'profileName': 'polariCrude',
        'displayName': 'Polari CRUDE Response',
        'description': 'Polari standard CRUDE endpoint response format',
        'rootType': 'object',  # Level 0 is {}
        'level1ExpectedType': 'mixed',  # Level 1 has string and array
        'structuralFields': {
            'class': {'required': True, 'type': 'str', 'description': 'Class name'},
            'instances': {'required': True, 'type': 'array', 'description': 'Array of instances'}
        },
        'dataPath': 'instances',  # Data records are in instances array
        'sampleSchema': '{\n  "class": "<ClassName>",\n  "instances": [ {...}, ... ]\n}'
    },

    'graphql': {
        'profileName': 'graphql',
        'displayName': 'GraphQL Response',
        'description': 'Standard GraphQL response envelope with data and errors',
        'rootType': 'object',  # Level 0 is {}
        'level1ExpectedType': 'mixed',
        'structuralFields': {
            'data': {'required': True, 'type': 'object', 'description': 'Query results'},
            'errors': {'required': False, 'type': 'array', 'description': 'Error list (optional)'}
        },
        'dataPath': 'data.<queryName>',  # Dynamic - depends on query
        'sampleSchema': '{\n  "data": { "<query>": [...] },\n  "errors": null\n}'
    },

    'wrappedResponse': {
        'profileName': 'wrappedResponse',
        'displayName': 'Wrapped Data Response',
        'description': 'Data nested under "data" key with optional metadata',
        'rootType': 'object',  # Level 0 is {}
        'level1ExpectedType': 'mixed',
        'structuralFields': {
            'data': {'required': True, 'type': 'array', 'description': 'Array of data records'},
            'meta': {'required': False, 'type': 'object', 'description': 'Metadata (optional)'},
            'metadata': {'required': False, 'type': 'object', 'description': 'Metadata alternate name'},
        },
        'dataPath': 'data',
        'sampleSchema': '{\n  "data": [ {...}, ... ],\n  "meta": { <pagination> }\n}'
    },

    'paginated': {
        'profileName': 'paginated',
        'displayName': 'Paginated Response',
        'description': 'Paginated list with count and navigation',
        'rootType': 'object',  # Level 0 is {}
        'level1ExpectedType': 'mixed',
        'structuralFields': {
            # Common pagination patterns - at least one data field required
            'results': {'required': False, 'type': 'array', 'description': 'Results array'},
            'items': {'required': False, 'type': 'array', 'description': 'Items array (alt)'},
            'data': {'required': False, 'type': 'array', 'description': 'Data array (alt)'},
            'records': {'required': False, 'type': 'array', 'description': 'Records array (alt)'},
            # Pagination indicators - at least one should be present
            'count': {'required': False, 'type': 'int', 'description': 'Total count'},
            'total': {'required': False, 'type': 'int', 'description': 'Total count (alt)'},
            'page': {'required': False, 'type': 'int', 'description': 'Current page'},
            'next': {'required': False, 'type': 'str', 'description': 'Next page URL'},
            'previous': {'required': False, 'type': 'str', 'description': 'Previous page URL'},
            'offset': {'required': False, 'type': 'int', 'description': 'Offset position'},
            'limit': {'required': False, 'type': 'int', 'description': 'Page size limit'},
        },
        'requiredGroups': [
            ['results', 'items', 'data', 'records'],  # Need at least one data array
            ['count', 'total', 'page', 'next', 'offset']  # Need at least one pagination field
        ],
        'dataPath': 'results',  # Most common, but could be items/data/records
        'sampleSchema': '{\n  "results": [ {...}, ... ],\n  "count": <int>,\n  "next": <url|null>\n}'
    },

    'hal': {
        'profileName': 'hal',
        'displayName': 'HAL+JSON Response',
        'description': 'Hypermedia API Language format with embedded resources',
        'rootType': 'object',  # Level 0 is {}
        'level1ExpectedType': 'object',
        'structuralFields': {
            '_links': {'required': True, 'type': 'object', 'description': 'Hypermedia links'},
            '_embedded': {'required': True, 'type': 'object', 'description': 'Embedded resources'}
        },
        'dataPath': '_embedded.items',  # Common pattern
        'sampleSchema': '{\n  "_links": { "self": {...} },\n  "_embedded": { "items": [...] }\n}'
    },

    'geoJson': {
        'profileName': 'geoJson',
        'displayName': 'GeoJSON FeatureCollection',
        'description': 'Standard GeoJSON format for geographic data',
        'rootType': 'object',  # Level 0 is {}
        'level1ExpectedType': 'mixed',
        'structuralFields': {
            'type': {'required': True, 'type': 'str', 'expectedValue': 'FeatureCollection'},
            'features': {'required': True, 'type': 'array', 'description': 'Feature array'}
        },
        'dataPath': 'features',
        'sampleSchema': '{\n  "type": "FeatureCollection",\n  "features": [\n    { "geometry": {...}, "properties": {...} }\n  ]\n}'
    },

    'singleObject': {
        'profileName': 'singleObject',
        'displayName': 'Single Object Response',
        'description': 'Single object (not an array) - typically a resource detail endpoint',
        'rootType': 'object',  # Level 0 is {}
        'level1ExpectedType': 'mixed',  # Fields can be various types
        'structuralFields': {
            'id': {'required': False, 'type': 'str|int', 'description': 'Resource identifier'}
        },
        'dataPath': '',  # Data is the object itself
        'sampleSchema': '{\n  "id": <str|int>,\n  <field>: <type>,\n  ...\n}'
    },

    # -------------------------------------------------------------------------
    # ERROR/STATUS PROFILES
    # -------------------------------------------------------------------------
    'polariSuccess': {
        'profileName': 'polariSuccess',
        'displayName': 'Polari Success Response',
        'description': 'Polari standard success response',
        'rootType': 'object',
        'level1ExpectedType': 'mixed',
        'structuralFields': {
            'success': {'required': True, 'type': 'bool', 'expectedValue': True}
        },
        'dataPath': '',
        'sampleSchema': '{\n  "success": true,\n  ...\n}'
    },

    'polariError': {
        'profileName': 'polariError',
        'displayName': 'Polari Error Response',
        'description': 'Polari standard error response',
        'rootType': 'object',
        'level1ExpectedType': 'mixed',
        'structuralFields': {
            'success': {'required': True, 'type': 'bool', 'expectedValue': False},
            'error': {'required': True, 'type': 'str', 'description': 'Error message'}
        },
        'dataPath': '',
        'sampleSchema': '{\n  "success": false,\n  "error": "<message>"\n}'
    },
}


def get_format_profile(profile_name: str) -> Optional[Dict[str, Any]]:
    """
    Get a format profile by name.

    Args:
        profile_name: Name of the profile

    Returns:
        Profile dict or None if not found
    """
    return FORMAT_PROFILES.get(profile_name)


def get_all_format_profiles() -> Dict[str, Dict[str, Any]]:
    """
    Get all format profiles.

    Returns:
        Dict of all format profiles
    """
    return FORMAT_PROFILES.copy()


def match_structural_profile(response_data: Any) -> List[Dict[str, Any]]:
    """
    Match a response against all structural profiles.

    This is the main matching function that uses the structural approach:
    1. Check Level 0 (root type: object vs array)
    2. Check Level 1 structural fields
    3. Calculate match confidence

    Args:
        response_data: The API response to match

    Returns:
        List of matches sorted by confidence, each containing:
            - profileName: Name of the matched profile
            - confidence: Match confidence (0-1)
            - matchDetails: Details about what matched
    """
    matches = []

    # Determine Level 0 type
    if isinstance(response_data, list):
        root_type = 'array'
        # For arrays, check if Level 1 items are all objects
        level1_type = 'object' if all(isinstance(item, dict) for item in response_data[:10] if item) else 'mixed'
    elif isinstance(response_data, dict):
        root_type = 'object'
        level1_type = 'mixed'  # Objects have mixed field types
    else:
        # Scalar value - no structural profile matches
        return []

    # Check each profile
    for profile_name, profile in FORMAT_PROFILES.items():
        # Level 0 check - must match root type
        if profile['rootType'] != root_type:
            continue

        # Calculate match confidence
        confidence, details = _calculate_structural_match(response_data, profile, root_type)

        if confidence > 0:
            matches.append({
                'profileName': profile_name,
                'displayName': profile['displayName'],
                'confidence': confidence,
                'confidencePercent': round(confidence * 100, 1),
                'matchDetails': details,
                'dataPath': profile['dataPath'],
                'isMatch': confidence >= 0.7  # Default threshold
            })

    # Sort by confidence descending
    matches.sort(key=lambda x: x['confidence'], reverse=True)

    return matches


def _calculate_structural_match(
    response_data: Any,
    profile: Dict[str, Any],
    root_type: str
) -> tuple:
    """
    Calculate structural match confidence between response and profile.

    Args:
        response_data: The response data
        profile: The profile definition
        root_type: 'array' or 'object'

    Returns:
        Tuple of (confidence, details_dict)
    """
    details = {
        'rootTypeMatch': True,
        'structuralFieldsChecked': [],
        'structuralFieldsMatched': [],
        'structuralFieldsMissing': [],
        'requiredGroupsMatched': []
    }

    # For array profiles, just check that it's an array of objects
    if root_type == 'array':
        if profile['profileName'] == 'uniformArray':
            # Check all items are objects with same-ish structure
            if len(response_data) == 0:
                return (0.5, details)  # Empty array - partial match

            all_objects = all(isinstance(item, dict) for item in response_data[:10])
            if not all_objects:
                return (0.0, details)

            # Check field consistency
            if len(response_data) >= 2:
                first_keys = set(response_data[0].keys()) if response_data[0] else set()
                consistent = True
                for item in response_data[1:10]:
                    if isinstance(item, dict):
                        item_keys = set(item.keys())
                        # Allow some variation but should be mostly consistent
                        overlap = len(first_keys & item_keys) / max(len(first_keys | item_keys), 1)
                        if overlap < 0.7:
                            consistent = False
                            break

                confidence = 1.0 if consistent else 0.7
                details['fieldConsistency'] = consistent
                return (confidence, details)

            return (0.9, details)  # Single item array

        return (0.0, details)  # Other profiles don't match array root

    # For object profiles, check structural fields
    if root_type == 'object':
        structural_fields = profile.get('structuralFields', {})
        required_groups = profile.get('requiredGroups', [])

        if not structural_fields and not required_groups:
            # No structural requirements - weak match for object
            return (0.3, details)

        total_required = 0
        matched_required = 0
        total_optional = 0
        matched_optional = 0

        response_keys = set(response_data.keys())

        for field_name, field_spec in structural_fields.items():
            details['structuralFieldsChecked'].append(field_name)
            is_required = field_spec.get('required', False)

            if field_name in response_keys:
                # Check expected value if specified
                expected_val = field_spec.get('expectedValue')
                if expected_val is not None:
                    if response_data[field_name] == expected_val:
                        details['structuralFieldsMatched'].append(field_name)
                        if is_required:
                            matched_required += 1
                        else:
                            matched_optional += 1
                    else:
                        if is_required:
                            details['structuralFieldsMissing'].append(f"{field_name} (wrong value)")
                else:
                    details['structuralFieldsMatched'].append(field_name)
                    if is_required:
                        matched_required += 1
                    else:
                        matched_optional += 1
            elif is_required:
                details['structuralFieldsMissing'].append(field_name)

            if is_required:
                total_required += 1
            else:
                total_optional += 1

        # Check required groups (at least one from each group must be present)
        groups_satisfied = 0
        for group in required_groups:
            if any(field in response_keys for field in group):
                groups_satisfied += 1
                details['requiredGroupsMatched'].append(group)

        # Calculate confidence
        if total_required > 0:
            required_score = matched_required / total_required
            if required_score < 1.0:
                # Missing required fields - major penalty
                confidence = required_score * 0.5
            else:
                # All required fields present
                confidence = 0.7
                # Bonus for optional fields
                if total_optional > 0:
                    optional_score = matched_optional / total_optional
                    confidence += optional_score * 0.2
                # Bonus for group matches
                if required_groups:
                    group_score = groups_satisfied / len(required_groups)
                    confidence += group_score * 0.1
        elif required_groups:
            # No required fields but has required groups
            if groups_satisfied == len(required_groups):
                confidence = 0.8
            else:
                confidence = 0.4 * (groups_satisfied / len(required_groups))
        else:
            # No required fields, no groups - use optional matches
            if total_optional > 0:
                confidence = 0.5 + (matched_optional / total_optional) * 0.3
            else:
                confidence = 0.3

        return (min(confidence, 1.0), details)

    return (0.0, details)


def get_data_from_response(response_data: Any, profile_name: str) -> Any:
    """
    Extract the data array from a response using the profile's dataPath.

    Args:
        response_data: The full API response
        profile_name: Name of the profile to use

    Returns:
        The extracted data (usually an array of records)
    """
    profile = get_format_profile(profile_name)
    if not profile:
        return response_data

    data_path = profile.get('dataPath', '')
    if not data_path:
        return response_data

    # Navigate the path
    current = response_data
    for key in data_path.split('.'):
        if key.startswith('<') and key.endswith('>'):
            # Dynamic key placeholder - skip or take first key
            if isinstance(current, dict) and current:
                current = current[next(iter(current.keys()))]
        elif isinstance(current, dict) and key in current:
            current = current[key]
        else:
            # Path not found
            return response_data

    return current


# Legacy compatibility - map old template names
LEGACY_TEMPLATE_MAP = {
    'PolariCRUDEResponse': 'polariCrude',
    'PolariCRUDEInstance': 'polariCrude',
    'PolariTypingAnalysis': 'singleObject',
    'PolariPolyTypedVar': 'singleObject',
    'PolariStateSpaceConfig': 'singleObject',
    'PolariErrorResponse': 'polariError',
    'PolariSuccessResponse': 'polariSuccess',
    'PaginationResponse': 'paginated',
    'RESTCollectionResponse': 'uniformArray',
    'RESTResourceResponse': 'singleObject',
}


def get_template(template_name: str) -> Dict[str, Any]:
    """
    Get a template by name (legacy compatibility).

    Args:
        template_name: Name of the template

    Returns:
        Template/profile dictionary
    """
    # Try direct match first
    if template_name in FORMAT_PROFILES:
        return FORMAT_PROFILES[template_name]

    # Try legacy mapping
    mapped_name = LEGACY_TEMPLATE_MAP.get(template_name)
    if mapped_name and mapped_name in FORMAT_PROFILES:
        return FORMAT_PROFILES[mapped_name]

    return {}


def get_all_template_names() -> List[str]:
    """
    Get list of all available profile names.

    Returns:
        List of profile names
    """
    return list(FORMAT_PROFILES.keys())
