"""
Configured Formatted API Endpoints

This package contains the formatted API endpoint classes that serve
object instances in different data formats (Flat JSON, D3 Column, GeoJSON).

These endpoints are registered dynamically when a user enables a specific
format for an object type via the API Config page.
"""

from polariApiServer.configuredFormattedAPIs.flatJsonAPI import FlatJsonAPI
from polariApiServer.configuredFormattedAPIs.d3ColumnAPI import D3ColumnAPI
from polariApiServer.configuredFormattedAPIs.geoJsonAPI import GeoJsonAPI
