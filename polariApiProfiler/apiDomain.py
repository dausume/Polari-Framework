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
APIDomain - Data model for storing API domain configurations.

An APIDomain stores information about a host/domain that APIs are served from,
including certificate trust settings, protocol, and port configurations.
"""

from objectTreeDecorators import treeObject, treeObjectInit
from typing import Dict, Optional
import re


class APIDomain(treeObject):
    """
    Stores configuration for an API domain (host).

    This allows you to:
    - Track known API hosts separately from endpoint paths
    - Configure SSL/TLS certificate trust per domain
    - Handle different protocols and ports
    - Support localhost, IPv4, IPv6, and domain names

    Attributes:
        name: Unique identifier for this domain (e.g., "localhost-8800", "polari-prod")
        displayName: Human-readable name
        description: Description of this domain/environment
        host: The hostname or IP (e.g., "localhost", "192.168.1.1", "api.example.com")
        port: Port number (optional, None for default 80/443)
        protocol: "http" or "https"
        trustSelfSigned: Whether to trust self-signed certificates
        customCertPath: Path to custom CA certificate file
        verifySSL: Whether to verify SSL certificates at all
        hostType: Type of host ("localhost", "ipv4", "ipv6", "domain")
        isDefault: Whether this is the default domain for new endpoints
        tags: Tags for categorization (e.g., ["dev", "staging", "prod"])
    """

    @treeObjectInit
    def __init__(
        self,
        name: str = '',
        displayName: str = '',
        description: str = '',
        host: str = '',
        port: int = None,
        protocol: str = 'https',
        trustSelfSigned: bool = False,
        customCertPath: str = '',
        verifySSL: bool = True,
        hostType: str = '',
        isDefault: bool = False,
        tags: list = None,
        manager=None,
        **kwargs
    ):
        self.name = name
        self.displayName = displayName or name
        self.description = description
        # Clean the host - strip any accidental protocol prefix
        cleaned_host, detected_protocol = self._clean_host(host)
        self.host = cleaned_host
        self.port = port
        # Use detected protocol from URL if provided, otherwise use explicit protocol
        self.protocol = (detected_protocol or protocol or 'https').lower()
        self.trustSelfSigned = trustSelfSigned
        self.customCertPath = customCertPath
        self.verifySSL = verifySSL
        self.hostType = hostType or self._detect_host_type(cleaned_host)
        self.isDefault = isDefault
        self.tags = tags or []

    def _clean_host(self, host: str) -> tuple:
        """
        Clean the host string by stripping any protocol prefix.
        Also extracts the protocol if one was provided.

        Args:
            host: The hostname or URL that may contain a protocol

        Returns:
            Tuple of (cleaned_host, detected_protocol)
        """
        if not host:
            return ('', None)

        detected_protocol = None
        cleaned = host.strip()

        # Strip protocol prefixes
        if cleaned.lower().startswith('https://'):
            detected_protocol = 'https'
            cleaned = cleaned[8:]  # len('https://')
        elif cleaned.lower().startswith('http://'):
            detected_protocol = 'http'
            cleaned = cleaned[7:]  # len('http://')

        # Strip trailing slashes and paths
        if '/' in cleaned:
            cleaned = cleaned.split('/')[0]

        return (cleaned, detected_protocol)

    def _detect_host_type(self, host: str) -> str:
        """
        Detect the type of host from the host string.

        Args:
            host: The hostname or IP

        Returns:
            Host type: "localhost", "ipv4", "ipv6", or "domain"
        """
        if not host:
            return ''

        host_lower = host.lower()

        # Check for localhost
        if host_lower in ('localhost', '127.0.0.1', '::1'):
            return 'localhost'

        # Check for IPv6 (contains colons and possibly brackets)
        if ':' in host and not host.startswith('http'):
            # Could be IPv6 like "::1" or "2001:db8::1"
            # But watch out for port notation like "host:port"
            if host.startswith('[') or host.count(':') > 1:
                return 'ipv6'

        # Check for IPv4 (four octets)
        ipv4_pattern = r'^(\d{1,3}\.){3}\d{1,3}$'
        if re.match(ipv4_pattern, host):
            return 'ipv4'

        # Otherwise it's a domain name
        return 'domain'

    def get_base_url(self) -> str:
        """
        Get the full base URL for this domain.

        Returns:
            Base URL string (e.g., "https://api.example.com:8080")
        """
        url = f"{self.protocol}://"

        # Handle IPv6 addresses (need brackets)
        if self.hostType == 'ipv6' and not self.host.startswith('['):
            url += f"[{self.host}]"
        else:
            url += self.host

        # Add port if not default
        if self.port:
            default_port = 443 if self.protocol == 'https' else 80
            if self.port != default_port:
                url += f":{self.port}"

        return url

    def get_request_kwargs(self) -> dict:
        """
        Get kwargs for requests library based on SSL settings.

        Returns:
            Dict with verify and cert settings for requests
        """
        kwargs = {}

        if not self.verifySSL:
            kwargs['verify'] = False
        elif self.customCertPath:
            kwargs['verify'] = self.customCertPath
        elif self.trustSelfSigned:
            # For self-signed, we still verify but would need the cert
            # In practice, this might mean verify=False or a custom cert bundle
            kwargs['verify'] = False
        else:
            kwargs['verify'] = True

        return kwargs

    def to_dict(self) -> dict:
        """
        Convert to dictionary for JSON serialization.

        Returns:
            Dictionary representation
        """
        return {
            'id': self.id if hasattr(self, 'id') else None,
            'name': self.name,
            'displayName': self.displayName,
            'description': self.description,
            'host': self.host,
            'port': self.port,
            'protocol': self.protocol,
            'trustSelfSigned': self.trustSelfSigned,
            'customCertPath': self.customCertPath,
            'verifySSL': self.verifySSL,
            'hostType': self.hostType,
            'isDefault': self.isDefault,
            'tags': self.tags,
            'baseUrl': self.get_base_url()
        }

    @classmethod
    def from_dict(cls, data: dict, manager=None) -> 'APIDomain':
        """
        Create an APIDomain from a dictionary.

        Args:
            data: Dictionary with domain data
            manager: Manager object

        Returns:
            New APIDomain instance
        """
        return cls(
            name=data.get('name', ''),
            displayName=data.get('displayName', ''),
            description=data.get('description', ''),
            host=data.get('host', ''),
            port=data.get('port'),
            protocol=data.get('protocol', 'https'),
            trustSelfSigned=data.get('trustSelfSigned', False),
            customCertPath=data.get('customCertPath', ''),
            verifySSL=data.get('verifySSL', True),
            hostType=data.get('hostType', ''),
            isDefault=data.get('isDefault', False),
            tags=data.get('tags', []),
            manager=manager
        )

    @classmethod
    def from_url(cls, url: str, name: str = '', manager=None) -> 'APIDomain':
        """
        Create an APIDomain by parsing a URL.

        Args:
            url: Full URL to parse
            name: Optional name for the domain
            manager: Manager object

        Returns:
            New APIDomain instance
        """
        from urllib.parse import urlparse

        parsed = urlparse(url)

        host = parsed.hostname or ''
        port = parsed.port
        protocol = parsed.scheme or 'https'

        # Generate name if not provided
        if not name:
            name = host.replace('.', '-')
            if port:
                name += f"-{port}"

        return cls(
            name=name,
            host=host,
            port=port,
            protocol=protocol,
            manager=manager
        )

    def validate(self) -> tuple:
        """
        Validate this domain configuration.

        Returns:
            Tuple of (is_valid: bool, errors: list)
        """
        errors = []

        if not self.name:
            errors.append("Domain name is required")

        if not self.host:
            errors.append("Host is required")

        if self.protocol not in ('http', 'https'):
            errors.append(f"Invalid protocol: {self.protocol}")

        if self.port is not None and (self.port < 1 or self.port > 65535):
            errors.append(f"Invalid port: {self.port}")

        return (len(errors) == 0, errors)

    def __repr__(self):
        return f"APIDomain(name='{self.name}', url='{self.get_base_url()}')"


# Pre-defined common domains for convenience
COMMON_DOMAINS = [
    # Local development
    {
        'name': 'localhost-default',
        'displayName': 'Localhost (default port)',
        'host': 'localhost',
        'port': None,
        'protocol': 'http',
        'trustSelfSigned': True,
        'verifySSL': False,
        'hostType': 'localhost',
        'tags': ['dev', 'local']
    },
    {
        'name': 'localhost-3000',
        'displayName': 'Localhost :3000 (Polari PRF)',
        'host': 'localhost',
        'port': 3000,
        'protocol': 'http',
        'trustSelfSigned': True,
        'verifySSL': False,
        'hostType': 'localhost',
        'tags': ['dev', 'local', 'polari', 'prf']
    },
    {
        'name': 'localhost-8800',
        'displayName': 'Localhost :8800 (Polari default)',
        'host': 'localhost',
        'port': 8800,
        'protocol': 'http',
        'trustSelfSigned': True,
        'verifySSL': False,
        'hostType': 'localhost',
        'tags': ['dev', 'local', 'polari']
    },
    {
        'name': 'localhost-https',
        'displayName': 'Localhost HTTPS',
        'host': 'localhost',
        'port': 443,
        'protocol': 'https',
        'trustSelfSigned': True,
        'verifySSL': False,
        'hostType': 'localhost',
        'tags': ['dev', 'local']
    },
    # External mock APIs
    {
        'name': 'jsonplaceholder',
        'displayName': 'JSONPlaceholder (Mock API)',
        'description': 'Free fake API for testing and prototyping',
        'host': 'jsonplaceholder.typicode.com',
        'port': None,
        'protocol': 'https',
        'trustSelfSigned': False,
        'verifySSL': True,
        'hostType': 'domain',
        'tags': ['mock', 'test', 'external']
    },
    # nip.io for local network access (mirrors production subdomain structure)
    {
        'name': 'nip-io-base',
        'displayName': '10.0.0.102.nip.io (Base)',
        'host': '10.0.0.102.nip.io',
        'port': None,
        'protocol': 'https',
        'trustSelfSigned': True,
        'verifySSL': False,
        'hostType': 'domain',
        'tags': ['dev', 'local', 'nip.io']
    },
    {
        'name': 'nip-io-api-prf',
        'displayName': 'api.prf.10.0.0.102.nip.io (PRF API)',
        'host': 'api.prf.10.0.0.102.nip.io',
        'port': None,
        'protocol': 'https',
        'trustSelfSigned': True,
        'verifySSL': False,
        'hostType': 'domain',
        'tags': ['dev', 'local', 'nip.io', 'prf', 'api']
    },
    {
        'name': 'nip-io-api-psc',
        'displayName': 'api.psc.10.0.0.102.nip.io (PSC API)',
        'host': 'api.psc.10.0.0.102.nip.io',
        'port': None,
        'protocol': 'https',
        'trustSelfSigned': True,
        'verifySSL': False,
        'hostType': 'domain',
        'tags': ['dev', 'local', 'nip.io', 'psc', 'api']
    },
    {
        'name': 'nip-io-prf',
        'displayName': 'prf.10.0.0.102.nip.io (PRF)',
        'host': 'prf.10.0.0.102.nip.io',
        'port': None,
        'protocol': 'https',
        'trustSelfSigned': True,
        'verifySSL': False,
        'hostType': 'domain',
        'tags': ['dev', 'local', 'nip.io', 'prf']
    },
    {
        'name': 'nip-io-psc',
        'displayName': 'psc.10.0.0.102.nip.io (PSC)',
        'host': 'psc.10.0.0.102.nip.io',
        'port': None,
        'protocol': 'https',
        'trustSelfSigned': True,
        'verifySSL': False,
        'hostType': 'domain',
        'tags': ['dev', 'local', 'nip.io', 'psc']
    },
    # Polari Systems production domains
    {
        'name': 'polari-systems-org',
        'displayName': 'polari-systems.org',
        'host': 'polari-systems.org',
        'port': None,
        'protocol': 'https',
        'trustSelfSigned': False,
        'verifySSL': True,
        'hostType': 'domain',
        'tags': ['prod', 'polari']
    },
    {
        'name': 'api-prf-polari-systems',
        'displayName': 'api.prf.polari-systems.org (PRF API)',
        'host': 'api.prf.polari-systems.org',
        'port': None,
        'protocol': 'https',
        'trustSelfSigned': False,
        'verifySSL': True,
        'hostType': 'domain',
        'tags': ['prod', 'polari', 'prf', 'api']
    },
    {
        'name': 'api-psc-polari-systems',
        'displayName': 'api.psc.polari-systems.org (PSC API)',
        'host': 'api.psc.polari-systems.org',
        'port': None,
        'protocol': 'https',
        'trustSelfSigned': False,
        'verifySSL': True,
        'hostType': 'domain',
        'tags': ['prod', 'polari', 'psc', 'api']
    },
]
