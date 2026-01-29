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
Polari API Profiler Module

This module provides functionality for:
1. Querying external APIs and analyzing response structures using Polari's typing system
2. Matching responses to known/pre-defined profiles
3. Dynamically creating new Polari objects from matched profiles via createClassAPI
4. Building/nesting profiles from scratch
5. Distinguishing between multiple object types from a single API
"""

from polariApiProfiler.apiProfile import APIProfile
from polariApiProfiler.apiDomain import APIDomain, COMMON_DOMAINS
from polariApiProfiler.apiEndpoint import APIEndpoint, COMMON_ENDPOINTS
from polariApiProfiler.apiProfiler import APIProfiler
from polariApiProfiler.profileMatcher import ProfileMatcher
from polariApiProfiler.profileTemplates import (
    FORMAT_PROFILES,
    get_format_profile,
    get_all_format_profiles,
    match_structural_profile,
    get_data_from_response,
    get_all_template_names
)
from polariApiProfiler.apiProfilerAPI import (
    APIProfilerQueryAPI,
    APIProfilerMatchAPI,
    APIProfilerBuildAPI,
    APIProfilerCreateClassAPI,
    APIProfilerTemplatesAPI,
    APIProfilerDetectTypesAPI,
    APIDomainAPI,
    APIEndpointAPI,
    APIEndpointFetchAPI
)

__all__ = [
    'APIProfile',
    'APIDomain',
    'COMMON_DOMAINS',
    'APIEndpoint',
    'COMMON_ENDPOINTS',
    'APIProfiler',
    'ProfileMatcher',
    'FORMAT_PROFILES',
    'get_format_profile',
    'get_all_format_profiles',
    'match_structural_profile',
    'get_data_from_response',
    'get_all_template_names',
    'APIProfilerQueryAPI',
    'APIProfilerMatchAPI',
    'APIProfilerBuildAPI',
    'APIProfilerCreateClassAPI',
    'APIProfilerTemplatesAPI',
    'APIProfilerDetectTypesAPI',
    'APIDomainAPI',
    'APIEndpointAPI',
    'APIEndpointFetchAPI'
]
