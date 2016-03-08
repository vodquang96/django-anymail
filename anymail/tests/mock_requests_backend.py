import json

from django.test import SimpleTestCase
import requests
import six
from mock import patch

from .utils import AnymailTestMixin

UNSET = object()


class RequestsBackendMockAPITestCase(SimpleTestCase, AnymailTestMixin):
    """TestCase that uses Djrill EmailBackend with a mocked Mandrill API"""

    DEFAULT_RAW_RESPONSE = b"""{"subclass": "should override"}"""

    class MockResponse(requests.Response):
        """requests.request return value mock sufficient for testing"""
        def __init__(self, status_code=200, raw=b"RESPONSE", encoding='utf-8'):
            super(RequestsBackendMockAPITestCase.MockResponse, self).__init__()
            self.status_code = status_code
            self.encoding = encoding
            self.raw = six.BytesIO(raw)

    def setUp(self):
        super(RequestsBackendMockAPITestCase, self).setUp()
        self.patch = patch('requests.Session.request', autospec=True)
        self.mock_request = self.patch.start()
        self.addCleanup(self.patch.stop)
        self.set_mock_response()

    def set_mock_response(self, status_code=200, raw=UNSET, encoding='utf-8'):
        if raw is UNSET:
            raw = self.DEFAULT_RAW_RESPONSE
        mock_response = self.MockResponse(status_code, raw, encoding)
        self.mock_request.return_value = mock_response
        return mock_response

    def assert_esp_called(self, url, method="POST"):
        """Verifies the (mock) ESP API was called on endpoint.

        url can be partial, and is just checked against the end of the url requested"
        """
        # This assumes the last (or only) call to requests.Session.request is the API call of interest.
        if self.mock_request.call_args is None:
            raise AssertionError("No ESP API was called")
        (args, kwargs) = self.mock_request.call_args
        try:
            actual_method = kwargs.get('method', None) or args[1]
            actual_url = kwargs.get('url', None) or args[2]
        except IndexError:
            raise AssertionError("API was called without a method or url (?!)")
        if actual_method != method:
            raise AssertionError("API was not called using %s. (%s was used instead.)"
                                 % (method, actual_method))
        if not actual_url.endswith(url):
            raise AssertionError("API was not called at %s\n(It was called at %s)"
                                 % (url, actual_url))

    def get_api_call_arg(self, kwarg, pos, required=True):
        """Returns an argument passed to the mock ESP API.

        Fails test if API wasn't called.
        """
        if self.mock_request.call_args is None:
            raise AssertionError("API was not called")
        (args, kwargs) = self.mock_request.call_args
        try:
            return kwargs.get(kwarg, None) or args[pos]
        except IndexError:
            if required:
                raise AssertionError("API was called without required %s" % kwarg)
            else:
                return None

    def get_api_call_params(self, required=True):
        """Returns the query params sent to the mock ESP API."""
        return self.get_api_call_arg('params', 3, required)

    def get_api_call_data(self, required=True):
        """Returns the raw data sent to the mock ESP API."""
        return self.get_api_call_arg('data', 4, required)

    def get_api_call_json(self, required=True):
        """Returns the data sent to the mock ESP API, json-parsed"""
        return json.loads(self.get_api_call_data(required))

    def get_api_call_headers(self, required=True):
        """Returns the headers sent to the mock ESP API"""
        return self.get_api_call_arg('headers', 5, required)

    def get_api_call_files(self, required=True):
        """Returns the files sent to the mock ESP API"""
        return self.get_api_call_arg('files', 7, required)

    def get_api_call_auth(self, required=True):
        """Returns the auth sent to the mock ESP API"""
        return self.get_api_call_arg('auth', 8, required)

    def assert_esp_not_called(self, msg=None):
        if self.mock_request.called:
            raise AssertionError(msg or "ESP API was called and shouldn't have been")
