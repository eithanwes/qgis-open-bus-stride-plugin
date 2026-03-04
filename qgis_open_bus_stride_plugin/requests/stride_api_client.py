"""
Stride API Client Module

This module provides functionality to interact with the Open Bus Stride API.
It handles network requests, response parsing, and error handling.
"""

import json
import urllib.parse

from qgis.core import QgsNetworkAccessManager, QgsProcessingException
from qgis.PyQt.QtCore import QUrl
from qgis.PyQt.QtNetwork import QNetworkReply, QNetworkRequest


class StrideAPIClient:
    """
    Client for interacting with the Open Bus Stride API.

    Handles HTTP requests to the Stride API and provides methods for fetching
    vehicle location data with proper error handling and progress feedback.
    """

    BASE_URL = "https://open-bus-stride-api.hasadna.org.il"

    def __init__(self, feedback=None):
        """
        Initialize the Stride API client.

        Args:
            feedback: QgsProcessingFeedback object for progress reporting (optional)
        """
        self.feedback = feedback
        self.manager = QgsNetworkAccessManager.instance()

    def fetch_data(self, api_path, params=None):
        """
        Fetch data from the Stride API.

        Args:
            api_path (str): API endpoint path (e.g., '/siri_vehicle_locations/list')
            params (dict): Query parameters for the request (optional)

        Returns:
            list: Parsed JSON response data

        Raises:
            QgsProcessingException: If the request fails or response is invalid
        """
        if params is None:
            params = {}

        # Build the request URL
        url = self._build_url(api_path, params)

        # Log the request
        if self.feedback:
            url_str = url.toString()
            message = f'Requesting data from: <a href="{url_str}">{url_str}</a>'
            self.feedback.pushFormattedMessage(message, message)

        # Execute the request
        data = self._execute_request(url)

        # Validate response
        if not isinstance(data, list):
            if self.feedback:
                self.feedback.pushWarning("Response did not contain a list of items.")
            return []

        return data

    def _build_url(self, api_path, params):
        """
        Build the complete URL with query parameters.

        Args:
            api_path (str): API endpoint path
            params (dict): Query parameters

        Returns:
            QUrl: Complete URL with encoded parameters
        """
        query_string = urllib.parse.urlencode(params, safe=":")
        url = QUrl(f"{self.BASE_URL}{api_path}")
        url.setQuery(query_string)
        return url

    def _execute_request(self, url):
        """
        Execute the network request and parse the response.

        Args:
            url (QUrl): Request URL

        Returns:
            dict/list: Parsed JSON response

        Raises:
            QgsProcessingException: If the request fails or JSON parsing fails
        """
        request = QNetworkRequest(url)
        reply = self.manager.blockingGet(request)

        # Check for network errors
        if reply.error() != QNetworkReply.NetworkError.NoError:
            raise QgsProcessingException(
                f"Network request failed: {reply.errorString()}"
            )

        # Check HTTP status code
        status_code = reply.attribute(QNetworkRequest.Attribute.HttpStatusCodeAttribute)
        if status_code != 200:
            raise QgsProcessingException(
                f"API request failed with HTTP status code {status_code}"
            )

        # Parse JSON response
        try:
            response_body = bytes(reply.content())
            data = json.loads(response_body.decode("utf-8"))
            return data
        except json.JSONDecodeError as e:
            raise QgsProcessingException(f"Failed to parse JSON response: {e}")
