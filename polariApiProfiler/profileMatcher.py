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
        Analyze the structure of a response without matching to profiles.

        This is the core structural analysis that determines:
        - Level 0: Root type (dict {} or array [])
        - Level 1: Field types (for objects) or item types (for arrays)
        - Detected patterns matching known formats
        - Field-level typing within the data

        Args:
            response_data: The API response to analyze

        Returns:
            Structure analysis dict with level0, level1, patterns, and typing
        """
        analysis = {
            'level0': {
                'type': None,        # 'array' or 'object' or 'scalar'
                'pythonType': None,  # 'list' or 'dict' or primitive type
                'description': None
            },
            'level1': {
                'fields': {},        # For objects: field name -> type info
                'itemType': None,    # For arrays: type of items
                'itemCount': 0,      # For arrays: number of items
                'uniformItems': None # For arrays: whether all items have same structure
            },
            'detectedPatterns': [],
            'suggestedProfiles': [],
            'dataTyping': {}  # Field-level type analysis
        }

        if isinstance(response_data, list):
            analysis['level0']['type'] = 'array'
            analysis['level0']['pythonType'] = 'list'
            analysis['level0']['description'] = '[] - Array at root (Python list)'
            analysis['level1']['itemCount'] = len(response_data)

            if response_data:
                # Check item types at Level 1
                item_types = set()
                for item in response_data[:10]:
                    item_types.add(type(item).__name__)

                if len(item_types) == 1 and 'dict' in item_types:
                    analysis['level1']['itemType'] = 'object'
                    analysis['level1']['uniformItems'] = True
                    analysis['detectedPatterns'].append('Uniform object array')
                    analysis['suggestedProfiles'].append('uniformArray')

                    # Analyze field structure and typing
                    all_keys = set()
                    for item in response_data[:10]:
                        if isinstance(item, dict):
                            all_keys.update(item.keys())

                    # Check uniformity (all items have same keys)
                    if len(response_data) >= 2:
                        first_keys = set(response_data[0].keys())
                        uniform = all(
                            set(item.keys()) == first_keys
                            for item in response_data[1:10]
                            if isinstance(item, dict)
                        )
                        analysis['level1']['uniformItems'] = uniform

                    # Collect field types
                    for item in response_data[:5]:
                        if isinstance(item, dict):
                            for k, v in item.items():
                                analysis['level1']['fields'][k] = self._get_value_type(v)

                    # Add type analysis for data fields
                    analysis['dataTyping'] = self._analyze_data_types(response_data)
                else:
                    analysis['level1']['itemType'] = 'mixed'
                    analysis['level1']['uniformItems'] = False
                    analysis['detectedPatterns'].append('Mixed type array')
            else:
                analysis['level1']['uniformItems'] = None  # Empty array

        elif isinstance(response_data, dict):
            analysis['level0']['type'] = 'object'
            analysis['level0']['pythonType'] = 'dict'
            analysis['level0']['description'] = '{} - Object at root (Python dict)'

            # Analyze Level 1 fields
            for key, value in response_data.items():
                value_type = type(value).__name__
                analysis['level1']['fields'][key] = {
                    'type': value_type,
                    'isArray': isinstance(value, list),
                    'isObject': isinstance(value, dict),
                    'hasValue': value is not None
                }

            # Detect patterns based on structural fields
            keys = set(response_data.keys())

            # Check for known patterns
            if 'class' in keys and 'instances' in keys:
                analysis['detectedPatterns'].append('Polari CRUDE response')
                analysis['suggestedProfiles'].append('polariCrude')

            if 'data' in keys and 'errors' in keys:
                analysis['detectedPatterns'].append('GraphQL response')
                analysis['suggestedProfiles'].append('graphql')

            if '_links' in keys and '_embedded' in keys:
                analysis['detectedPatterns'].append('HAL+JSON response')
                analysis['suggestedProfiles'].append('hal')

            if 'type' in keys and response_data.get('type') == 'FeatureCollection':
                analysis['detectedPatterns'].append('GeoJSON FeatureCollection')
                analysis['suggestedProfiles'].append('geoJson')

            if 'success' in keys:
                if response_data.get('success') is True:
                    analysis['detectedPatterns'].append('Success response')
                    analysis['suggestedProfiles'].append('polariSuccess')
                elif 'error' in keys:
                    analysis['detectedPatterns'].append('Error response')
                    analysis['suggestedProfiles'].append('polariError')

            # Check for pagination patterns
            pagination_fields = {'page', 'count', 'total', 'next', 'previous', 'offset', 'limit'}
            data_fields = {'results', 'items', 'data', 'records'}
            if keys & pagination_fields and keys & data_fields:
                analysis['detectedPatterns'].append('Paginated response')
                analysis['suggestedProfiles'].append('paginated')

            if 'data' in keys and isinstance(response_data.get('data'), list):
                analysis['detectedPatterns'].append('Wrapped data response')
                analysis['suggestedProfiles'].append('wrappedResponse')

            if not analysis['suggestedProfiles']:
                analysis['suggestedProfiles'].append('singleObject')

        else:
            analysis['level0']['type'] = 'scalar'
            analysis['level0']['pythonType'] = type(response_data).__name__
            analysis['level0']['description'] = f'{type(response_data).__name__} - Scalar value (not dict or list)'

        return analysis

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
