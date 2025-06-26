"""
Provides an implementation for interacting with Cirrus CI API.
"""

import base64
import socket

import requests

from app.infrastructure.config.settings import app_settings


class CirrusClient:
    """
    Class to interact with the Cirrus API.

    Attributes:
        settings (dict): Dictionary containing the Cirrus API settings.
        token_url (str): URL for retrieving an access token from
            the authentication server.
        egress_rules_url (str): URL for retrieving egress rules from
            the Cirrus API.
    """

    def __init__(self) -> None:
        """
        Initialize the CirrusClient.
        """

        self.settings = app_settings
        self.token_url = (
            f"{self.settings.CIRRUS_API_URL}/"
            f"{self.settings.CIRRUS_API_VERSION}/"
            f"{self.settings.CIRRUS_ENDPOINT_TOKEN}"
        )
        self.egress_rules_url = (
            f"{self.settings.CIRRUS_API_URL}/"
            f"{self.settings.CIRRUS_API_VERSION}/"
            f"{self.settings.CIRRUS_ENDPOINT_FIREWALL}"
        )

    def _get_auth_headers(self) -> dict[str, str]:
        """
        Returns a dictionary containing the authentication headers for Cirrus.
        """

        api_key_str = (
            f"{self.settings.CIRRUS_USER}:{self.settings.CIRRUS_PASSWORD}"
        )
        x_api_key = base64.b64encode(api_key_str.encode("utf-8")).decode(
            "utf-8"
        )
        return {"x-api-key": x_api_key}

    def _get_access_token(self) -> str:
        """Gets an access token from the authentication server.

        Args:
            self (class instance): The class instance that calls this method.

        Returns:
            str: The access token retrieved from the authentication server.

        Raises:
            requests.exceptions.HTTPError: If the request to the authentication
                server fails.
        """

        headers = self._get_auth_headers()
        response = requests.post(self.token_url, headers=headers, timeout=10)
        response.raise_for_status()
        data = response.json()
        return data["access_token"]

    def check_egress_firewall(self, lpar_hostname: str) -> bool:
        """
        Check if egress firewall is enabled for a given LPAR hostname.

        Args:
            lpar_hostname (str): The hostname of the LPAR to check.

        Returns:
            bool: True if egress firewall is enabled, False otherwise.

        Raises:
            requests.exceptions.RequestException: If an error occurs
                while making the HTTP request.
        """

        lpar_ip_address = socket.gethostbyname(lpar_hostname)
        access_token = self._get_access_token

        headers = {"Authorization": f"Bearer {access_token}"}
        egress_rules_url = (
            f"{self.settings.CIRRUS_API_URL}/"
            f"{self.settings.CIRRUS_API_VERSION}/"
            f"{self.settings.CIRRUS_PROJECT_ID}/"
            f"{self.settings.CIRRUS_CLUSTER_ID}"
        )

        response = requests.get(egress_rules_url, headers=headers, timeout=10)
        response.raise_for_status()
        data = response.json()

        for egress in data.get("egress", []):
            if egress.get("destination_ip") == lpar_ip_address:
                return True
        return False
