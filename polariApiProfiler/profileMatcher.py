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
ProfileMatcher - Structural matching for API response profiles.

Matches API responses against format profiles using structural analysis:
- Level 0: Root type (object vs array)
- Level 1: Structural fields that identify the format
- Data path: Where the actual records live

This replaces the old field-by-field matching with a structural approach.
"""

from objectTreeDecorators import treeObject, treeObjectInit
from polariApiProfiler.profileTemplates import (
    FORMAT_PROFILES,
    match_structural_profile,
    get_format_profile,
    get_data_from_response
)
from typing import Dict, List, Any, Tuple, Optional


class ProfileMatcher(treeObject):
    """
    Matches API responses against format profiles using structural analysis.

    Structural matching approach:
    1. Level 0 Check: Is root {} or []? This eliminates incompatible profiles.
    2. Level 1 Check: What structural fields are present?
    3. Confidence Score: Based on required field matches and optional bonuses.
    """

    @treeObjectInit
    def __init__(self, manager=None, **kwargs):
        self.lastMatchResults = []
        self.defaultConfidenceThreshold = 0.7

    def match_response(
        self,
        response_data: Any,
        threshold: float = None,
        include_type_analysis: bool = True
    ) -> List[Dict[str, Any]]:
        """
        Match a response against all format profiles.

        Uses a two-phase approach:
        1. Structural Matching: Determine Level 0/1 structure (format/envelope)
        2. Type Analysis: Analyze field types within the data

        Args:
            response_data: The API response to match
            threshold: Minimum confidence threshold (default 0.7)
            include_type_analysis: Whether to include type info in results

        Returns:
            List of match results sorted by confidence
        """
        threshold = threshold if threshold is not None else self.defaultConfidenceThreshold

        # Phase 1: Structural matching (Level 0 and Level 1)
        matches = match_structural_profile(response_data)

        # Phase 2: Add type analysis for data fields
        if include_type_analysis and matches:
            for match in matches:
                # Extract data using the profile's dataPath
                profile_name = match['profileName']
                data = get_data_from_response(response_data, profile_name)

                # Analyze types of the data
                type_info = self._analyze_data_types(data)
                match['typeAnalysis'] = type_info

        # Apply threshold filter
        for match in matches:
            match['isMatch'] = match['confidence'] >= threshold
            match['threshold'] = threshold

        self.lastMatchResults = matches
        return matches

    def _analyze_data_types(self, data: Any) -> Dict[str, Any]:
        """
        Analyze the types of fields in the data.

        This complements structural matching by examining the actual
        data content after extracting it from the response envelope.

        Args:
            data: The extracted data (usually array of objects or single object)

        Returns:
            Dict with type information for each field
        """
        if data is None:
            return {'fields': {}, 'itemCount': 0}

        # Normalize to list
        items = data if isinstance(data, list) else [data]
        dict_items = [item for item in items if isinstance(item, dict)]

        if not dict_items:
            return {'fields': {}, 'itemCount': len(items), 'itemType': type(items[0]).__name__ if items else 'unknown'}

        # Collect field types across all samples
        field_types = {}
        for item in dict_items[:20]:  # Sample up to 20 items
            for key, value in item.items():
                if key not in field_types:
                    field_types[key] = {
                        'types': set(),
                        'nullable': False,
                        'samples': []
                    }

                value_type = self._get_value_type(value)
                field_types[key]['types'].add(value_type)

                if value is None:
                    field_types[key]['nullable'] = True

                # Keep a few sample values (for primitives)
                if len(field_types[key]['samples']) < 3 and value is not None:
                    if isinstance(value, (str, int, float, bool)):
                        field_types[key]['samples'].append(value)

        # Consolidate type info
        fields = {}
        for key, info in field_types.items():
            types_list = list(info['types'])
            fields[key] = {
                'primaryType': types_list[0] if len(types_list) == 1 else 'mixed',
                'allTypes': types_list,
                'nullable': info['nullable'],
                'sampleValues': info['samples'][:2] if info['samples'] else []
            }

        return {
            'fields': fields,
            'fieldCount': len(fields),
            'itemCount': len(dict_items),
            'itemsAreUniform': len({frozenset(item.keys()) for item in dict_items[:10]}) == 1
        }

    def _get_value_type(self, value: Any) -> str:
        """Get a descriptive type string for a value."""
        if value is None:
            return 'null'
        elif isinstance(value, bool):
            return 'bool'
        elif isinstance(value, int):
            return 'int'
        elif isinstance(value, float):
            return 'float'
        elif isinstance(value, str):
            return 'str'
        elif isinstance(value, list):
            if value and isinstance(value[0], dict):
                return 'array[object]'
            elif value:
                return f'array[{type(value[0]).__name__}]'
            return 'array'
        elif isinstance(value, dict):
            return 'object'
        else:
            return type(value).__name__

    def match_response_to_profiles(
        self,
        response_data: Any,
        candidate_profiles: List = None,
        threshold: float = None
    ) -> List[Dict[str, Any]]:
        """
        Match a response against format profiles.

        This is the main API for profile matching. If candidate_profiles
        is provided, only those profiles are checked. Otherwise, all
        format profiles are checked.

        Args:
            response_data: The API response to match
            candidate_profiles: Optional list of profile names to check
            threshold: Minimum confidence threshold

        Returns:
            List of match results sorted by confidence
        """
        if candidate_profiles is None:
            return self.match_response(response_data, threshold)

        # Filter matches to only include specified profiles
        all_matches = self.match_response(response_data, threshold)

        if isinstance(candidate_profiles, list):
            # Extract profile names if they're objects
            profile_names = []
            for p in candidate_profiles:
                if isinstance(p, str):
                    profile_names.append(p)
                elif hasattr(p, 'profileName'):
                    profile_names.append(p.profileName)
                elif isinstance(p, dict) and 'profileName' in p:
                    profile_names.append(p['profileName'])

            if profile_names:
                all_matches = [m for m in all_matches if m['profileName'] in profile_names]

        return all_matches

    def find_best_match(
        self,
        response_data: Any,
        threshold: float = None
    ) -> Optional[Dict[str, Any]]:
        """
        Find the single best matching profile for a response.

        Args:
            response_data: The API response to match
            threshold: Minimum confidence threshold

        Returns:
            The best match result dict, or None if no match above threshold
        """
        matches = self.match_response(response_data, threshold)

        for match in matches:
            if match['isMatch']:
                return match

        return matches[0] if matches else None

    def analyze_structure(self, response_data: Any) -> Dict[str, Any]:
        """
        Analyze the structure of a response and build a generic APIProfile.

        This builds a profile by recursively analyzing the data structure:
        - typeSignatures: Dict of level -> list of unique types at that depth
        - fieldSignatures: Dict of level -> list of field names at that level
        - totalFieldSignatures: Count of all unique fields
        - totalTypeSignatures: Count of all unique type signatures across all levels

        LEVEL NUMBERING (depth-based):
        Level 0 = root container ({} or [])
        Level 1 = keys in root dict, OR items in root array
        Level 2 = values of root dict keys, OR keys inside array items
        ...and so on

        Example: {"name": "John", "items": [{"id": 1}]}
        - Level 0: types=['dict']
        - Level 1: fields=['name', 'items']
        - Level 2: types=['str', 'list[dict]'] (values of name and items)
        - Level 3: types=['dict'] (list items)
        - Level 4: fields=['id']

        For arrays: [{"a": 1}, {"a": 2}]
        - Level 0: types=['list[dict]']
        - Level 1: types=['dict'] (array items)
        - Level 2: fields=['a']

        Args:
            response_data: The API response to analyze

        Returns:
            Dict containing fieldSignatures, typeSignatures, totals, and metadata
        """
        # Build the generic profile structure
        field_signatures: Dict[int, List[str]] = {}
        type_signatures: Dict[int, List[str]] = {}  # Now a list of types per level

        # Recursively analyze the structure using depth-based level numbering
        self._analyze_level(response_data, 0, field_signatures, type_signatures)

        # Calculate totals
        total_fields = sum(len(fields) for fields in field_signatures.values())
        total_types = sum(len(types) for types in type_signatures.values())

        # Get root type (first type at level 0)
        root_types = type_signatures.get(0, [])
        root_type = root_types[0] if root_types else 'unknown'

        analysis = {
            'fieldSignatures': field_signatures,
            'typeSignatures': type_signatures,
            'totalFieldSignatures': total_fields,
            'totalTypeSignatures': total_types,
            # Additional metadata for convenience
            'maxDepth': max(type_signatures.keys()) if type_signatures else 0,
            'rootType': root_type,
        }

        return analysis

    def _analyze_level(
        self,
        data: Any,
        level: int,
        field_signatures: Dict[int, List[str]],
        type_signatures: Dict[int, List[str]],
        max_depth: int = 15
    ):
        """
        Recursively analyze a data structure using depth-based level numbering.

        Level numbering:
        - Containers ({}, []) get a level for their structure
        - Field names (dict keys) get the next level
        - Values get the next level after that
        - Array items get a level

        For dict at level N:
        - type_signatures[N] appends 'dict'
        - field_signatures[N+1] = list of keys
        - Each value is analyzed at level N+2

        For list at level N:
        - type_signatures[N] appends 'list[itemtype]'
        - Items are analyzed at level N+1

        Args:
            data: The data to analyze at this level
            level: Current depth level (0 = root)
            field_signatures: Dict to populate with level -> field names
            type_signatures: Dict to populate with level -> list of types
            max_depth: Maximum recursion depth to prevent infinite loops
        """
        if level > max_depth:
            return

        def add_type(lvl: int, type_str: str):
            """Add a type to the level if not already present."""
            if lvl not in type_signatures:
                type_signatures[lvl] = []
            if type_str not in type_signatures[lvl]:
                type_signatures[lvl].append(type_str)

        if data is None:
            add_type(level, 'null')
            return

        if isinstance(data, dict):
            add_type(level, 'dict')

            if data:
                # Field names go at level+1
                field_names = list(data.keys())
                if level + 1 not in field_signatures:
                    field_signatures[level + 1] = []
                for name in field_names:
                    if name not in field_signatures[level + 1]:
                        field_signatures[level + 1].append(name)

                # Values are at level+2, recursively analyze them
                for key, value in data.items():
                    self._analyze_level(value, level + 2, field_signatures, type_signatures, max_depth)

        elif isinstance(data, list):
            if not data:
                add_type(level, 'list')
                return

            # Determine the type of items in the list
            item_types = set()
            for item in data[:10]:  # Sample first 10 items
                item_types.add(type(item).__name__)

            if len(item_types) == 1:
                item_type = list(item_types)[0]
                add_type(level, f'list[{item_type}]')

                # Array items are at level+1
                if item_type == 'dict':
                    # Items are dicts, their type goes at level+1
                    add_type(level + 1, 'dict')

                    # Collect all unique field names from sampled items
                    all_fields = set()
                    for item in data[:10]:
                        if isinstance(item, dict):
                            all_fields.update(item.keys())

                    # Store fields at level+2 (keys inside the dict items)
                    if level + 2 not in field_signatures:
                        field_signatures[level + 2] = []
                    for name in all_fields:
                        if name not in field_signatures[level + 2]:
                            field_signatures[level + 2].append(name)

                    # Recursively analyze nested values from first item (values at level+3)
                    if data and isinstance(data[0], dict):
                        for key, value in data[0].items():
                            self._analyze_level(value, level + 3, field_signatures, type_signatures, max_depth)

                elif item_type == 'list' and data[0]:
                    # Items are lists, recursively analyze at level+1
                    self._analyze_level(data[0], level + 1, field_signatures, type_signatures, max_depth)
            else:
                add_type(level, f'list[mixed:{",".join(sorted(item_types))}]')

        elif isinstance(data, bool):
            add_type(level, 'bool')
        elif isinstance(data, int):
            add_type(level, 'int')
        elif isinstance(data, float):
            add_type(level, 'float')
        elif isinstance(data, str):
            add_type(level, 'str')
        else:
            add_type(level, type(data).__name__)

    def create_profile_from_response(
        self,
        response_data: Any,
        profile_name: str = '',
        display_name: str = '',
        description: str = '',
        api_endpoint: str = ''
    ) -> Dict[str, Any]:
        """
        Create a new APIProfile dict from analyzing a response.

        This is the main method for generating custom profiles from API responses.
        It analyzes the structure and returns a dict that can be used to create
        an APIProfile instance.

        Args:
            response_data: The API response to analyze
            profile_name: Name for the profile (auto-generated if not provided)
            display_name: Display name for the profile
            description: Description of the profile
            api_endpoint: The API endpoint this profile was created from

        Returns:
            Dict with all APIProfile fields populated from analysis
        """
        # Analyze the structure
        analysis = self.analyze_structure(response_data)

        # Generate profile name if not provided
        if not profile_name:
            root_type = analysis.get('rootType', 'unknown')
            field_count = analysis.get('totalFieldSignatures', 0)
            profile_name = f'custom_{root_type}_{field_count}fields'

        return {
            'profileName': profile_name,
            'displayName': display_name or profile_name,
            'description': description or f'Auto-generated profile with {analysis["totalFieldSignatures"]} fields across {analysis["totalTypeSignatures"]} levels',
            'apiEndpoint': api_endpoint,
            'httpMethod': 'GET',
            'responseRootPath': '',
            'fieldSignatures': analysis['fieldSignatures'],
            'typeSignatures': analysis['typeSignatures'],
            'totalFieldSignatures': analysis['totalFieldSignatures'],
            'totalTypeSignatures': analysis['totalTypeSignatures'],
            'sampleCount': 1,
            'isTemplate': False,
            'matchConfidenceThreshold': 0.7,
        }

    def compare_to_profile(
        self,
        response_data: Any,
        target_profile: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Compare a response's structure against a target profile.

        This compares fieldSignatures and typeSignatures at each level
        to determine how well the response matches the target profile.

        Args:
            response_data: The API response to analyze
            target_profile: The profile to compare against (dict with fieldSignatures/typeSignatures)

        Returns:
            Dict with match scores and details per level
        """
        # Analyze the response
        analysis = self.analyze_structure(response_data)

        response_fields = analysis['fieldSignatures']
        response_types = analysis['typeSignatures']

        target_fields = target_profile.get('fieldSignatures', {})
        target_types = target_profile.get('typeSignatures', {})

        # Compare at each level
        level_matches = {}
        all_levels = set(response_types.keys()) | set(target_types.keys())

        total_field_score = 0
        total_type_score = 0
        levels_checked = 0

        for level in sorted(all_levels):
            level_result = {
                'typeMatch': False,
                'fieldMatchRatio': 0.0,
                'matchedFields': [],
                'missingFields': [],
                'extraFields': []
            }

            # Compare types
            resp_type = response_types.get(level)
            target_type = target_types.get(level)
            if resp_type == target_type:
                level_result['typeMatch'] = True
                total_type_score += 1

            # Compare fields
            resp_fields_at_level = set(response_fields.get(level, []))
            target_fields_at_level = set(target_fields.get(level, []))

            if target_fields_at_level:
                matched = resp_fields_at_level & target_fields_at_level
                missing = target_fields_at_level - resp_fields_at_level
                extra = resp_fields_at_level - target_fields_at_level

                level_result['matchedFields'] = list(matched)
                level_result['missingFields'] = list(missing)
                level_result['extraFields'] = list(extra)
                level_result['fieldMatchRatio'] = len(matched) / len(target_fields_at_level)
                total_field_score += level_result['fieldMatchRatio']
                levels_checked += 1

            level_matches[level] = level_result

        # Calculate overall confidence
        type_confidence = total_type_score / len(all_levels) if all_levels else 0
        field_confidence = total_field_score / levels_checked if levels_checked > 0 else 0
        overall_confidence = (type_confidence * 0.3) + (field_confidence * 0.7)

        return {
            'overallConfidence': overall_confidence,
            'typeConfidence': type_confidence,
            'fieldConfidence': field_confidence,
            'levelMatches': level_matches,
            'responseAnalysis': analysis
        }

    def match_with_signature_details(
        self,
        response_data: Any,
        target_profile: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Match a response against a profile and return detailed signature match information.

        This is designed for frontend display, returning arrays of signature matches
        with matched/unmatched status for each.

        Supports both new levelSignatures format and legacy separate signatures.

        Args:
            response_data: The API response to analyze
            target_profile: The profile to compare against

        Returns:
            Dict with:
                - profileName, displayName, confidence, isMatch
                - typeSignatureMatches: [{level, expected, found, matched}, ...]
                - fieldSignatureMatches: [{level, field, expectedType, matched, required}, ...]
                - matchedTypeSignatures, totalTypeSignatures
                - matchedFieldSignatures, totalFieldSignatures
        """
        # Analyze the response
        analysis = self.analyze_structure(response_data)

        response_fields = analysis['fieldSignatures']
        response_types = analysis['typeSignatures']

        # Extract signatures from profile - support new levelSignatures format
        level_signatures = target_profile.get('levelSignatures', {})

        if level_signatures:
            # New format: extract from levelSignatures
            target_required_types = {}  # level -> list of required types
            target_optional_types = {}  # level -> list of optional types
            target_required_fields = {}
            target_optional_fields = {}

            for level, level_sig in level_signatures.items():
                level_int = int(level)
                # Required types (list)
                if 'requiredTypes' in level_sig:
                    target_required_types[level_int] = level_sig['requiredTypes']
                # Optional types (list)
                if 'optionalTypes' in level_sig:
                    target_optional_types[level_int] = level_sig['optionalTypes']
                # Legacy containerType support - treat as required
                if 'containerType' in level_sig and level_sig['containerType']:
                    if level_int not in target_required_types:
                        target_required_types[level_int] = []
                    if level_sig['containerType'] not in target_required_types[level_int]:
                        target_required_types[level_int].append(level_sig['containerType'])
                # Required fields with their expected types
                if 'requiredFields' in level_sig:
                    target_required_fields[level_int] = level_sig['requiredFields']
                # Optional fields with their expected types
                if 'optionalFields' in level_sig:
                    target_optional_fields[level_int] = level_sig['optionalFields']
        else:
            # Legacy format: use separate signature dicts
            legacy_types = target_profile.get('typeSignatures', {})
            target_required_types = {}
            target_optional_types = {}
            # Convert legacy single types to required types list
            for level, type_val in legacy_types.items():
                level_int = int(level)
                if type_val:
                    target_required_types[level_int] = [type_val]
                    target_optional_types[level_int] = []

            target_required_fields = target_profile.get('requiredFieldSignatures', {})
            target_optional_fields = target_profile.get('optionalFieldSignatures', {})

            # Backwards compatibility: if no required/optional, use fieldSignatures as required
            if not target_required_fields and not target_optional_fields:
                legacy_fields = target_profile.get('fieldSignatures', {})
                if legacy_fields:
                    # Convert list format to dict format (field: 'any')
                    target_required_fields = {
                        int(k): {f: 'any' for f in v} if isinstance(v, list) else v
                        for k, v in legacy_fields.items()
                    }

        # Normalize target keys to int (in case they came from JSON as strings)
        if target_required_fields:
            target_required_fields = {int(k): v for k, v in target_required_fields.items()}
        if target_optional_fields:
            target_optional_fields = {int(k): v for k, v in target_optional_fields.items()}
        if target_required_types:
            target_required_types = {int(k): v for k, v in target_required_types.items()}
        if target_optional_types:
            target_optional_types = {int(k): v for k, v in target_optional_types.items()}

        # Build type signature matches array
        # Separate tracking for required vs optional type signatures
        type_signature_matches = []
        matched_required_type_count = 0
        matched_optional_type_count = 0
        total_required_type_count = 0
        total_optional_type_count = 0

        # Get all levels that have types defined
        all_type_levels = set(target_required_types.keys()) | set(target_optional_types.keys()) | set(response_types.keys())

        def types_match(expected: str, found: str) -> bool:
            """Check if two type strings match (with flexibility for list types)."""
            if not expected or not found:
                return False
            if expected == found:
                return True
            # Allow list[dict] to match list[dict] even if exact string differs slightly
            if expected.startswith('list') and found.startswith('list'):
                return True
            # Allow dict to match dict variants
            if expected == 'dict' and found == 'dict':
                return True
            # Allow 'array' to match list types (template vs analyzer terminology)
            if expected == 'array' and found.startswith('list'):
                return True
            if expected.startswith('list') and found == 'array':
                return True
            # Allow 'list' to match 'list[type]'
            if expected == 'list' and found.startswith('list'):
                return True
            # Allow 'any' to match anything
            if expected == 'any':
                return True
            return False

        def type_in_found_list(expected: str, found_list: List[str]) -> bool:
            """Check if expected type matches any type in the found list."""
            if not found_list:
                return False
            for found in found_list:
                if types_match(expected, found):
                    return True
            return False

        for level in sorted(all_type_levels):
            required_types_at_level = target_required_types.get(level, [])
            optional_types_at_level = target_optional_types.get(level, [])
            found_types = response_types.get(level, [])  # Now a list of types

            # Track REQUIRED type matches at this level
            for expected_type in required_types_at_level:
                matched = type_in_found_list(expected_type, found_types)
                if matched:
                    matched_required_type_count += 1
                total_required_type_count += 1

                type_signature_matches.append({
                    'level': level,
                    'expected': expected_type,
                    'found': found_types,  # Return the list of found types
                    'matched': matched,
                    'required': True,
                    'optional': False,
                    'extra': False
                })

            # Track OPTIONAL type matches at this level
            for expected_type in optional_types_at_level:
                matched = type_in_found_list(expected_type, found_types)
                if matched:
                    matched_optional_type_count += 1
                total_optional_type_count += 1

                type_signature_matches.append({
                    'level': level,
                    'expected': expected_type,
                    'found': found_types,  # Return the list of found types
                    'matched': matched,
                    'required': False,
                    'optional': True,
                    'extra': False
                })

            # If this level has no expected types but we found types, mark as extra
            if not required_types_at_level and not optional_types_at_level and found_types:
                # Check if level is defined at all in profile (might be field-only level)
                if level not in target_required_types and level not in target_optional_types:
                    type_signature_matches.append({
                        'level': level,
                        'expected': None,
                        'found': found_types,
                        'matched': True,  # Don't penalize for extra depth
                        'required': False,
                        'optional': False,
                        'extra': True
                    })

        # Build field signature matches array
        # Separate tracking for required vs optional fields
        field_signature_matches = []
        matched_required_count = 0
        matched_optional_count = 0
        total_required_fields = 0
        total_optional_fields = 0

        # Get all levels that have required or optional fields defined
        all_field_levels = set(target_required_fields.keys()) | set(target_optional_fields.keys()) | set(response_fields.keys())

        for level in sorted(all_field_levels):
            # Handle both dict format (field: expectedType) and list format (legacy)
            required_fields_raw = target_required_fields.get(level, {})
            optional_fields_raw = target_optional_fields.get(level, {})

            # Normalize to dict format {field: expectedType}
            if isinstance(required_fields_raw, list):
                required_fields = {f: 'any' for f in required_fields_raw}
            else:
                required_fields = required_fields_raw or {}

            if isinstance(optional_fields_raw, list):
                optional_fields = {f: 'any' for f in optional_fields_raw}
            else:
                optional_fields = optional_fields_raw or {}

            found_fields = response_fields.get(level, [])
            found_set = set(found_fields) if found_fields else set()
            all_expected = set(required_fields.keys()) | set(optional_fields.keys())

            # Track REQUIRED field matches (must be present for a valid match)
            for field, expected_type in required_fields.items():
                matched = field in found_set
                if matched:
                    matched_required_count += 1
                total_required_fields += 1

                field_signature_matches.append({
                    'level': level,
                    'field': field,
                    'expectedType': expected_type,
                    'found': field if matched else None,
                    'matched': matched,
                    'required': True
                })

            # Track OPTIONAL field matches (increase confidence but not required)
            for field, expected_type in optional_fields.items():
                matched = field in found_set
                if matched:
                    matched_optional_count += 1
                total_optional_fields += 1

                field_signature_matches.append({
                    'level': level,
                    'field': field,
                    'expectedType': expected_type,
                    'found': field if matched else None,
                    'matched': matched,
                    'required': False,
                    'optional': True
                })

            # Note extra fields found but not expected (for info)
            extra_fields = found_set - all_expected
            for field in extra_fields:
                field_signature_matches.append({
                    'level': level,
                    'field': field,
                    'expectedType': None,
                    'found': field,
                    'matched': False,
                    'extra': True  # Mark as extra/unexpected field
                })

        # =================================================================
        # MATCH CATEGORY AND RANKING SCORE CALCULATION
        # =================================================================
        #
        # Static weights for ranking equation (displayed to user):
        #   W1 = 0.40 - Raw count of required signatures matched (highest)
        #   W2 = 0.30 - Percentage of required signatures matched
        #   W3 = 0.20 - Raw count of optional signatures matched
        #   W4 = 0.10 - Percentage of optional signatures matched
        #
        # Categories:
        #   "Match" = 100% of required signatures
        #   "Partial Match" = >60% of required signatures
        #   None = <60% (filtered out)
        # =================================================================

        # Calculate totals
        total_required = total_required_type_count + total_required_fields
        matched_required = matched_required_type_count + matched_required_count
        total_optional = total_optional_type_count + total_optional_fields
        matched_optional = matched_optional_type_count + matched_optional_count

        # Required percentage (for category determination)
        required_pct = matched_required / total_required if total_required > 0 else 1.0

        # Determine match category
        if required_pct >= 1.0:
            match_category = 'Match'
        elif required_pct >= 0.6:
            match_category = 'Partial Match'
        else:
            match_category = None  # Will be filtered out

        # Calculate optional percentage
        optional_pct = matched_optional / total_optional if total_optional > 0 else 0.0

        # Raw score components (before normalization)
        # These are used in the weighted ranking equation
        raw_score_components = {
            'requiredCount': matched_required,        # Term 1
            'requiredPct': required_pct,              # Term 2
            'optionalCount': matched_optional,        # Term 3
            'optionalPct': optional_pct               # Term 4
        }

        # Static weights
        weights = {
            'requiredCount': 0.40,
            'requiredPct': 0.30,
            'optionalCount': 0.20,
            'optionalPct': 0.10
        }

        # Calculate raw weighted score (will be normalized later across all profiles)
        # Note: requiredCount and optionalCount need to be normalized by max across profiles
        raw_weighted_score = (
            weights['requiredCount'] * matched_required +
            weights['requiredPct'] * required_pct +
            weights['optionalCount'] * matched_optional +
            weights['optionalPct'] * optional_pct
        )

        return {
            'profileName': target_profile.get('profileName', 'unknown'),
            'displayName': target_profile.get('displayName', target_profile.get('profileName', 'unknown')),
            'matchCategory': match_category,
            'isMatch': match_category == 'Match',
            'isPartialMatch': match_category == 'Partial Match',
            'isTemplate': target_profile.get('isTemplate', False),
            'dataPath': target_profile.get('dataPath', target_profile.get('responseRootPath', '')),
            # Ranking components (before normalization)
            'rawScoreComponents': raw_score_components,
            'weights': weights,
            'rawWeightedScore': raw_weighted_score,
            # Type signature details
            'typeSignatureMatches': type_signature_matches,
            'matchedTypeSignatures': matched_required_type_count + matched_optional_type_count,
            'totalTypeSignatures': total_required_type_count + total_optional_type_count,
            # Separate required/optional type counts
            'matchedRequiredTypes': matched_required_type_count,
            'totalRequiredTypes': total_required_type_count,
            'matchedOptionalTypes': matched_optional_type_count,
            'totalOptionalTypes': total_optional_type_count,
            # Field signature details (combined required + optional)
            'fieldSignatureMatches': field_signature_matches,
            'matchedFieldSignatures': matched_required_count + matched_optional_count,
            'totalFieldSignatures': total_required_fields + total_optional_fields,
            # Separate required/optional field counts
            'matchedRequiredFields': matched_required_count,
            'totalRequiredFields': total_required_fields,
            'matchedOptionalFields': matched_optional_count,
            'totalOptionalFields': total_optional_fields,
            # Level signatures for structured display (if available)
            'levelSignatures': level_signatures if level_signatures else None,
            # Response analysis for reference
            'responseAnalysis': analysis
        }

    def match_response_with_details(
        self,
        response_data: Any,
        profiles: List[Dict[str, Any]],
        threshold: float = 0.6
    ) -> List[Dict[str, Any]]:
        """
        Match a response against multiple profiles with weighted ranking.

        Uses a normalized weighted linear equation for ranking:
        - W1 = 0.40: Raw count of required signatures matched
        - W2 = 0.30: Percentage of required signatures matched
        - W3 = 0.20: Raw count of optional signatures matched
        - W4 = 0.10: Percentage of optional signatures matched

        Categories:
        - "Match": 100% of required signatures
        - "Partial Match": >60% of required signatures
        - Filtered out: <60% of required signatures

        Rankings are normalized within each category (lowest=0, highest=1).

        Args:
            response_data: The API response to analyze
            profiles: List of profile dicts to match against
            threshold: Minimum required percentage (default 0.6 = 60%)

        Returns:
            List of match results sorted by category and ranking
        """
        all_results = []

        # Phase 1: Collect all match results
        for profile in profiles:
            match_result = self.match_with_signature_details(response_data, profile)
            all_results.append(match_result)

        # Phase 2: Filter out non-matches (< threshold required)
        valid_results = [r for r in all_results if r.get('matchCategory') is not None]

        if not valid_results:
            return []

        # Phase 3: Separate by category
        full_matches = [r for r in valid_results if r.get('matchCategory') == 'Match']
        partial_matches = [r for r in valid_results if r.get('matchCategory') == 'Partial Match']

        # Phase 4: Normalize and rank within each category
        def normalize_and_rank(results: List[Dict]) -> List[Dict]:
            if not results:
                return []

            if len(results) == 1:
                # Single result gets normalized score of 1.0 and rank 1
                results[0]['normalizedScore'] = 1.0
                results[0]['categoryRank'] = 1
                return results

            # Find max values for normalization of raw counts
            max_req_count = max(r['rawScoreComponents']['requiredCount'] for r in results)
            max_opt_count = max(r['rawScoreComponents']['optionalCount'] for r in results)

            # Calculate normalized weighted scores
            weights = results[0]['weights']  # Same for all
            for r in results:
                comp = r['rawScoreComponents']

                # Normalize count components by max in this category
                norm_req_count = comp['requiredCount'] / max_req_count if max_req_count > 0 else 0
                norm_opt_count = comp['optionalCount'] / max_opt_count if max_opt_count > 0 else 0

                # Weighted score using normalized counts and raw percentages
                weighted_score = (
                    weights['requiredCount'] * norm_req_count +
                    weights['requiredPct'] * comp['requiredPct'] +
                    weights['optionalCount'] * norm_opt_count +
                    weights['optionalPct'] * comp['optionalPct']
                )
                r['weightedScore'] = weighted_score

            # Find min/max for final normalization to [0, 1]
            scores = [r['weightedScore'] for r in results]
            min_score = min(scores)
            max_score = max(scores)
            score_range = max_score - min_score

            # Normalize to [0, 1] - lowest = 0, highest = 1
            for r in results:
                if score_range > 0:
                    r['normalizedScore'] = (r['weightedScore'] - min_score) / score_range
                else:
                    r['normalizedScore'] = 1.0  # All same score

            # Sort by normalized score descending and assign ranks
            results.sort(key=lambda x: x['normalizedScore'], reverse=True)
            for i, r in enumerate(results):
                r['categoryRank'] = i + 1

            return results

        # Apply normalization and ranking to each category
        full_matches = normalize_and_rank(full_matches)
        partial_matches = normalize_and_rank(partial_matches)

        # Phase 5: Combine results - Matches first, then Partial Matches
        combined = full_matches + partial_matches

        # Add total counts for display
        for r in combined:
            r['totalMatches'] = len(full_matches)
            r['totalPartialMatches'] = len(partial_matches)

        return combined

    # -------------------------------------------------------------------------
    # COMMENTED OUT: Old static pattern matching logic
    # This has been replaced by the generic profile building above.
    # Keeping for reference during transition.
    # -------------------------------------------------------------------------
    # def _analyze_structure_old(self, response_data: Any) -> Dict[str, Any]:
    #     """
    #     Old analyze_structure that matched against static profiles.
    #     """
    #     analysis = {
    #         'level0': {
    #             'type': None,
    #             'pythonType': None,
    #             'description': None
    #         },
    #         'level1': {
    #             'fields': {},
    #             'itemType': None,
    #             'itemCount': 0,
    #             'uniformItems': None
    #         },
    #         'detectedPatterns': [],
    #         'suggestedProfiles': [],
    #         'dataTyping': {}
    #     }
    #
    #     if isinstance(response_data, list):
    #         analysis['level0']['type'] = 'array'
    #         analysis['level0']['pythonType'] = 'list'
    #         analysis['level0']['description'] = '[] - Array at root (Python list)'
    #         analysis['level1']['itemCount'] = len(response_data)
    #         # ... static pattern detection ...
    #
    #     elif isinstance(response_data, dict):
    #         analysis['level0']['type'] = 'object'
    #         analysis['level0']['pythonType'] = 'dict'
    #         # ... static pattern detection for known formats ...
    #         # if 'class' in keys and 'instances' in keys:
    #         #     analysis['suggestedProfiles'].append('polariCrude')
    #         # etc.
    #
    #     return analysis

    def get_match_summary(self, results: List[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Get a summary of match results.

        Args:
            results: Match results to summarize (uses lastMatchResults if None)

        Returns:
            Summary dict with counts and best match info
        """
        results = results or self.lastMatchResults

        if not results:
            return {
                'totalProfiles': 0,
                'matchingProfiles': 0,
                'bestMatch': None,
                'bestConfidence': 0,
                'allMatches': []
            }

        matching = [r for r in results if r.get('isMatch', False)]

        return {
            'totalProfiles': len(results),
            'matchingProfiles': len(matching),
            'bestMatch': results[0]['profileName'] if results else None,
            'bestConfidence': results[0]['confidence'] if results else 0,
            'bestDataPath': results[0].get('dataPath', '') if results else '',
            'allMatches': [
                {
                    'profileName': r['profileName'],
                    'displayName': r.get('displayName', r['profileName']),
                    'confidence': r.get('confidencePercent', round(r['confidence'] * 100, 1)),
                    'isMatch': r.get('isMatch', False),
                    'dataPath': r.get('dataPath', '')
                }
                for r in results
            ]
        }

    def extract_data(
        self,
        response_data: Any,
        profile_name: str = None
    ) -> Any:
        """
        Extract the data records from a response using a profile's dataPath.

        If no profile is specified, uses the best matching profile.

        Args:
            response_data: The full API response
            profile_name: Name of the profile to use for extraction

        Returns:
            The extracted data (usually an array of records)
        """
        if profile_name is None:
            # Find best match
            best = self.find_best_match(response_data)
            if best:
                profile_name = best['profileName']
            else:
                return response_data

        return get_data_from_response(response_data, profile_name)
