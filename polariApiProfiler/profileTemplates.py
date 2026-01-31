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

# =============================================================================
# LEVEL NUMBERING EXPLANATION
# =============================================================================
# Levels represent the depth in the JSON structure, counting each structural
# step (containers, keys, values, array items) as a level increment.
#
# Level 0 = the root container itself ({} or [])
# Level 1 = keys/field names directly inside the root
# Level 2 = values of those keys (or array items if root is array)
# Level 3 = if level 2 is an array, the items; if dict, the keys inside
# Level 4 = keys inside level 3 structures
# ... and so on
#
# Example 1 - Simple object:
#   {                              <- Level 0 (containerType: dict)
#     "name": "John",              <- "name" is at Level 1, value "John" is at Level 2
#     "age": 30                    <- "age" is at Level 1, value 30 is at Level 2
#   }
#
#   - Level 0: containerType = 'dict'
#   - Level 1: fields = ['name', 'age']
#
# Example 2 - GeoJSON:
#   {                              <- Level 0 (containerType: dict)
#     "type": "FeatureCollection", <- Level 1 field, Level 2 value
#     "features": [                <- Level 1 field
#       {                          <- Level 2 value (array), Level 3 items (dicts)
#         "type": "Feature",       <- Level 4 field
#         "geometry": {...},       <- Level 4 field
#         "properties": {...}      <- Level 4 field
#       }
#     ]
#   }
#
#   - Level 0: containerType = 'dict'
#   - Level 1: fields = ['type', 'features', 'bbox', 'metadata', 'crs']
#   - Level 2: containerType = 'list' (for features value)
#   - Level 3: containerType = 'dict' (for array items)
#   - Level 4: fields = ['type', 'geometry', 'properties', 'id']
#
# Example 3 - Uniform array:
#   [                              <- Level 0 (containerType: list[dict])
#     {"id": 1, "name": "A"},      <- Level 1 items (dicts)
#     {"id": 2, "name": "B"}
#   ]
#
#   - Level 0: containerType = 'list[dict]'
#   - Level 1: containerType = 'dict' (array items)
#   - Level 2: fields = ['id', 'name']
#
# KEY INSIGHT: Fields are always at (parent dict level + 1).
# For root {}, fields are at level 1.
# For root [], items are at level 1, and if items are dicts, their fields are at level 2.
# =============================================================================

Matching logic:
1. First check Level 0 type - eliminates incompatible profiles immediately
2. Check required fields at each level - all must be present for a match
3. Check optional fields - increase confidence if present
4. Calculate overall confidence based on type and field matches
"""

from typing import Dict, List, Any, Optional


# =============================================================================
# STRUCTURAL FORMAT PROFILES
# =============================================================================
# Each profile defines:
#   - typeSignatures: Dict[level, type_string] - expected type at each nesting level
#   - requiredFieldSignatures: Dict[level, List[field_names]] - fields that MUST be present
#   - optionalFieldSignatures: Dict[level, List[field_names]] - fields that MAY be present
#   - dataPath: JSONPath to extract the actual data records (empty string = root)
#
# Note: "Level N fields" refers to keys CONTAINED WITHIN the structure at level N,
# not keys that ARE level N. See module docstring for detailed examples.
# =============================================================================

FORMAT_PROFILES = {
    # -------------------------------------------------------------------------
    # UNIFORM ARRAY PROFILES (Level 0 = [])
    # -------------------------------------------------------------------------
    'uniformArray': {
        'profileName': 'uniformArray',
        'displayName': 'Uniform Object Array',
        'description': 'Array of objects with identical structure - most common REST collection format',
        'rootType': 'array',
        'dataPath': '',  # Data is at root
        'sampleSchema': '[\n  { <field>: <type>, ... },\n  { <field>: <type>, ... },\n  ...\n]',
        # Level-based signatures using depth-based numbering:
        # Level 0 = root array [], Level 1 = array items (dicts), Level 2 = keys inside items
        'levelSignatures': {
            0: {
                'requiredTypes': ['list[dict]'],  # Root is list of dicts
                'optionalTypes': [],
                'requiredFields': {},
                'optionalFields': {}
            },
            1: {
                'requiredTypes': ['dict'],  # Array items are dicts
                'optionalTypes': [],
                'requiredFields': {},
                'optionalFields': {}
            }
            # Level 2 fields are dynamic (the object properties) - not predefined
        },
        'isTemplate': True
    },

    # -------------------------------------------------------------------------
    # OBJECT WRAPPER PROFILES (Level 0 = {})
    # -------------------------------------------------------------------------
    'polariCrude': {
        'profileName': 'polariCrude',
        'displayName': 'Polari CRUDE Response',
        'description': 'Polari standard CRUDE endpoint response format',
        'rootType': 'object',
        'dataPath': 'instances',
        'sampleSchema': '{\n  "class": "<ClassName>",\n  "instances": [ {...}, ... ]\n}',
        # Level-based signatures using depth-based numbering:
        # Level 0 = root {}, Level 1 = root keys, Level 2 = values (instances is list),
        # Level 3 = list items (dicts), Level 4 = keys inside items
        'levelSignatures': {
            0: {
                'requiredTypes': ['dict'],
                'optionalTypes': [],
                'requiredFields': {},
                'optionalFields': {}
            },
            1: {
                'requiredTypes': [],  # Level 1 is field names
                'optionalTypes': [],
                'requiredFields': {
                    'class': 'str',           # Class name string
                    'instances': 'list[dict]' # Array of instance objects
                },
                'optionalFields': {}
            },
            2: {
                'requiredTypes': ['str', 'list[dict]'],  # from class and instances values
                'optionalTypes': [],
                'requiredFields': {},
                'optionalFields': {}
            },
            3: {
                'requiredTypes': ['dict'],  # List items are dicts
                'optionalTypes': [],
                'requiredFields': {},
                'optionalFields': {}
            }
            # Level 4 fields are dynamic (instance properties)
        },
        'isTemplate': True
    },

    'graphql': {
        'profileName': 'graphql',
        'displayName': 'GraphQL Response',
        'description': 'Standard GraphQL response envelope with data and errors',
        'rootType': 'object',
        'dataPath': 'data.<queryName>',  # Dynamic - depends on query
        'sampleSchema': '{\n  "data": { "<query>": [...] },\n  "errors": null\n}',
        # Level 0 = root {}, Level 1 = root keys, Level 2 = values (data is dict)
        'levelSignatures': {
            0: {
                'requiredTypes': ['dict'],
                'optionalTypes': [],
                'requiredFields': {},
                'optionalFields': {}
            },
            1: {
                'requiredTypes': [],  # Level 1 is field names
                'optionalTypes': [],
                'requiredFields': {
                    'data': 'dict'        # Query results object
                },
                'optionalFields': {
                    'errors': 'list',     # Error list (null or array)
                    'extensions': 'dict'  # GraphQL extensions object
                }
            },
            2: {
                'requiredTypes': ['dict'],        # from data value
                'optionalTypes': ['list', 'dict', 'null'],  # from errors, extensions
                'requiredFields': {},     # Query names are dynamic
                'optionalFields': {}
            }
        },
        'isTemplate': True
    },

    'wrappedResponse': {
        'profileName': 'wrappedResponse',
        'displayName': 'Wrapped Data Response',
        'description': 'Data nested under a wrapper key (data, message, result, etc.) with optional status/metadata',
        'rootType': 'object',
        'dataPath': 'data',  # Default, but could be message/result/response
        'sampleSchema': '{\n  "data": [...] | "message": "...",\n  "status": "success"\n}',
        # Required groups - at least one from each group must be present
        'requiredGroups': [
            ['data', 'message', 'result', 'response'],  # Need at least one data wrapper
        ],
        # Level 0 = root {}, Level 1 = root keys
        'levelSignatures': {
            0: {
                'requiredTypes': ['dict'],
                'optionalTypes': [],
                'requiredFields': {},
                'optionalFields': {}
            },
            1: {
                'requiredTypes': [],  # Level 1 is field names
                'optionalTypes': [],
                'requiredFields': {},  # Uses requiredGroups instead
                'optionalFields': {
                    # Data wrapper keys (one should be present via requiredGroups)
                    'data': 'any',        # Data wrapper (common)
                    'message': 'any',     # Message/data wrapper
                    'result': 'any',      # Result wrapper
                    'response': 'any',    # Response wrapper
                    # Status/metadata keys
                    'status': 'str',      # Status indicator
                    'success': 'bool',    # Success indicator
                    'meta': 'dict',       # Metadata
                    'metadata': 'dict'    # Metadata alternate
                }
            },
            2: {
                'requiredTypes': [],
                'optionalTypes': ['any', 'str', 'bool', 'dict'],  # Various value types
                'requiredFields': {},
                'optionalFields': {}
            }
        },
        'isTemplate': True
    },

    'paginated': {
        'profileName': 'paginated',
        'displayName': 'Paginated Response',
        'description': 'Paginated list with count and navigation',
        'rootType': 'object',
        'dataPath': 'results',  # Most common, but could be items/data/records
        'sampleSchema': '{\n  "results": [ {...}, ... ],\n  "count": <int>,\n  "next": <url|null>\n}',
        # Required groups - at least one from each group must be present
        'requiredGroups': [
            ['results', 'items', 'data', 'records'],  # Need at least one data array
            ['count', 'total', 'page', 'next', 'offset']  # Need at least one pagination field
        ],
        # Level 0 = root {}, Level 1 = root keys, Level 2 = values (results is list),
        # Level 3 = list items (dicts), Level 4 = keys inside items
        'levelSignatures': {
            0: {
                'requiredTypes': ['dict'],
                'optionalTypes': [],
                'requiredFields': {},
                'optionalFields': {}
            },
            1: {
                'requiredTypes': [],  # Level 1 is field names
                'optionalTypes': [],
                'requiredFields': {},  # Uses requiredGroups instead
                'optionalFields': {
                    # Data array keys (one should be present via requiredGroups)
                    'results': 'list[dict]',  # Results array
                    'items': 'list[dict]',    # Items array (alt)
                    'data': 'list[dict]',     # Data array (alt)
                    'records': 'list[dict]',  # Records array (alt)
                    # Pagination indicators (one should be present via requiredGroups)
                    'count': 'int',       # Total count
                    'total': 'int',       # Total count (alt)
                    'page': 'int',        # Current page
                    'next': 'str|null',   # Next page URL
                    'previous': 'str|null',  # Previous page URL
                    'offset': 'int',      # Offset position
                    'limit': 'int'        # Page size limit
                }
            },
            2: {
                'requiredTypes': [],
                'optionalTypes': ['list[dict]', 'int', 'str', 'null'],  # Various value types
                'requiredFields': {},
                'optionalFields': {}
            },
            3: {
                'requiredTypes': [],
                'optionalTypes': ['dict'],  # List items are dicts
                'requiredFields': {},
                'optionalFields': {}
            }
            # Level 4 fields are dynamic (record properties)
        },
        'isTemplate': True
    },

    'hal': {
        'profileName': 'hal',
        'displayName': 'HAL+JSON Response',
        'description': 'Hypermedia API Language format with embedded resources',
        'rootType': 'object',
        'dataPath': '_embedded.items',  # Common pattern
        'sampleSchema': '{\n  "_links": { "self": {...} },\n  "_embedded": { "items": [...] }\n}',
        # Level 0 = root {}, Level 1 = root keys, Level 2 = values (_embedded is dict),
        # Level 3 = keys inside _embedded (like "items")
        'levelSignatures': {
            0: {
                'requiredTypes': ['dict'],
                'optionalTypes': [],
                'requiredFields': {},
                'optionalFields': {}
            },
            1: {
                'requiredTypes': [],  # Level 1 is field names
                'optionalTypes': [],
                'requiredFields': {
                    '_links': 'dict',     # Hypermedia links object
                    '_embedded': 'dict'   # Embedded resources object
                },
                'optionalFields': {}
            },
            2: {
                'requiredTypes': ['dict'],  # _links and _embedded values are dicts
                'optionalTypes': [],
                'requiredFields': {},
                'optionalFields': {}
            },
            3: {
                'requiredTypes': [],  # Level 3 is field names inside _links/_embedded
                'optionalTypes': [],
                'requiredFields': {},
                'optionalFields': {
                    'self': 'dict',       # Self link (in _links)
                    'items': 'list[dict]' # Embedded items (in _embedded)
                }
            },
            4: {
                'requiredTypes': [],
                'optionalTypes': ['dict', 'list[dict]'],  # from self and items values
                'requiredFields': {},
                'optionalFields': {}
            }
        },
        'isTemplate': True
    },

    'geoJson': {
        'profileName': 'geoJson',
        'displayName': 'GeoJSON FeatureCollection',
        'description': 'Standard GeoJSON format for geographic data',
        'rootType': 'object',
        'dataPath': 'features',
        'sampleSchema': '{\n  "type": "FeatureCollection",\n  "features": [\n    { "geometry": {...}, "properties": {...} }\n  ]\n}',
        # Level-based signatures using depth-based numbering:
        # Level 0 = root container, Level 1 = root keys, Level 2 = values,
        # Level 3 = array items, Level 4 = keys inside array items
        'levelSignatures': {
            0: {
                'requiredTypes': ['dict'],  # Root is a dict {}
                'optionalTypes': [],
                'requiredFields': {},
                'optionalFields': {}
            },
            1: {
                'requiredTypes': [],  # Level 1 is field names (keys) - no container type
                'optionalTypes': [],
                'requiredFields': {
                    'type': 'str',        # value should be string "FeatureCollection"
                    'features': 'list[dict]'  # value should be a list of feature dicts
                },
                'optionalFields': {
                    'bbox': 'list[float]',    # bounding box array of floats
                    'metadata': 'dict',       # optional metadata object
                    'crs': 'dict'             # coordinate reference system
                }
            },
            2: {
                # Level 2 = values of level 1 fields
                'requiredTypes': ['str', 'list[dict]'],  # from type and features values
                'optionalTypes': ['list[float]', 'dict'],  # from bbox, metadata, crs values
                'requiredFields': {},
                'optionalFields': {}
            },
            3: {
                'requiredTypes': ['dict'],  # List items are dicts (Feature objects)
                'optionalTypes': [],
                'requiredFields': {},
                'optionalFields': {}
            },
            4: {
                'requiredTypes': [],  # Level 4 is field names inside Feature objects
                'optionalTypes': [],
                'requiredFields': {
                    'type': 'str',        # should be "Feature"
                    'geometry': 'dict',   # geometry object
                    'properties': 'dict'  # properties object
                },
                'optionalFields': {
                    'id': 'str|int'       # optional feature ID
                }
            },
            5: {
                # Level 5 = values of level 4 fields (inside Feature objects)
                'requiredTypes': ['str', 'dict'],  # from type, geometry, properties
                'optionalTypes': ['str', 'int'],   # from id (can be either)
                'requiredFields': {},
                'optionalFields': {}
            }
        },
        'isTemplate': True
    },

    'singleObject': {
        'profileName': 'singleObject',
        'displayName': 'Single Object Response',
        'description': 'Single object (not an array) - typically a resource detail endpoint',
        'rootType': 'object',
        'dataPath': '',  # Data is the object itself
        'sampleSchema': '{\n  "id": <str|int>,\n  <field>: <type>,\n  ...\n}',
        # Level 0 = root {}, Level 1 = root keys
        # This is a generic fallback profile - minimal requirements
        'levelSignatures': {
            0: {
                'requiredTypes': ['dict'],
                'optionalTypes': [],
                'requiredFields': {},
                'optionalFields': {}
            },
            1: {
                'requiredTypes': [],  # Level 1 is field names
                'optionalTypes': [],
                'requiredFields': {},     # No required fields - generic fallback
                'optionalFields': {
                    'id': 'str|int'       # Common but not required
                }
            },
            2: {
                'requiredTypes': [],
                'optionalTypes': ['str', 'int'],  # from id value
                'requiredFields': {},
                'optionalFields': {}
            }
        },
        'isTemplate': True
    },

    # -------------------------------------------------------------------------
    # ERROR/STATUS PROFILES
    # -------------------------------------------------------------------------
    'polariSuccess': {
        'profileName': 'polariSuccess',
        'displayName': 'Polari Success Response',
        'description': 'Polari standard success response',
        'rootType': 'object',
        'dataPath': '',
        'sampleSchema': '{\n  "success": true,\n  ...\n}',
        # Level 0 = root {}, Level 1 = root keys
        'levelSignatures': {
            0: {
                'requiredTypes': ['dict'],
                'optionalTypes': [],
                'requiredFields': {},
                'optionalFields': {}
            },
            1: {
                'requiredTypes': [],  # Level 1 is field names
                'optionalTypes': [],
                'requiredFields': {
                    'success': 'bool'     # Must be true for success response
                },
                'optionalFields': {
                    'message': 'str',     # Optional success message
                    'data': 'any'         # Optional response data
                }
            },
            2: {
                'requiredTypes': ['bool'],  # from success value
                'optionalTypes': ['str', 'any'],  # from message, data values
                'requiredFields': {},
                'optionalFields': {}
            }
        },
        # Expected values for validation (separate from type signatures)
        'expectedValues': {
            'success': True
        },
        'isTemplate': True
    },

    'polariError': {
        'profileName': 'polariError',
        'displayName': 'Polari Error Response',
        'description': 'Polari standard error response',
        'rootType': 'object',
        'dataPath': '',
        'sampleSchema': '{\n  "success": false,\n  "error": "<message>"\n}',
        # Level 0 = root {}, Level 1 = root keys
        'levelSignatures': {
            0: {
                'requiredTypes': ['dict'],
                'optionalTypes': [],
                'requiredFields': {},
                'optionalFields': {}
            },
            1: {
                'requiredTypes': [],  # Level 1 is field names
                'optionalTypes': [],
                'requiredFields': {
                    'success': 'bool',    # Must be false for error response
                    'error': 'str'        # Error message
                },
                'optionalFields': {
                    'details': 'any',     # Additional error details
                    'code': 'str|int',    # Error code
                    'trace': 'str'        # Stack trace
                }
            },
            2: {
                'requiredTypes': ['bool', 'str'],  # from success, error values
                'optionalTypes': ['any', 'str', 'int'],  # from details, code, trace values
                'requiredFields': {},
                'optionalFields': {}
            }
        },
        # Expected values for validation (separate from type signatures)
        'expectedValues': {
            'success': False
        },
        'isTemplate': True
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
