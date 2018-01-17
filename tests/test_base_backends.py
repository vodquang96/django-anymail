from django.test import override_settings

from anymail.backends.base_requests import AnymailRequestsBackend, RequestsPayload
from anymail.message import AnymailMessage, AnymailRecipientStatus

from .mock_requests_backend import RequestsBackendMockAPITestCase


class MinimalRequestsBackend(AnymailRequestsBackend):
    """(useful only for these tests)"""

    esp_name = "Example"

    def __init__(self, **kwargs):
        super(MinimalRequestsBackend, self).__init__("https://esp.example.com/api/", **kwargs)

    def build_message_payload(self, message, defaults):
        return MinimalRequestsPayload(message, defaults, self)

    def parse_recipient_status(self, response, payload, message):
        return {'to@example.com': AnymailRecipientStatus('message-id', 'sent')}


class MinimalRequestsPayload(RequestsPayload):
    def init_payload(self):
        pass

    def _noop(self, *args, **kwargs):
        pass

    set_from_email = _noop
    set_recipients = _noop
    set_subject = _noop
    set_reply_to = _noop
    set_extra_headers = _noop
    set_text_body = _noop
    set_html_body = _noop
    add_attachment = _noop


@override_settings(EMAIL_BACKEND='tests.test_base_backends.MinimalRequestsBackend')
class RequestsBackendBaseTestCase(RequestsBackendMockAPITestCase):
    """Test common functionality in AnymailRequestsBackend"""

    def setUp(self):
        super(RequestsBackendBaseTestCase, self).setUp()
        self.message = AnymailMessage('Subject', 'Text Body', 'from@example.com', ['to@example.com'])

    def test_minimal_requests_backend(self):
        """Make sure the testing backend defined above actually works"""
        self.message.send()
        self.assert_esp_called("https://esp.example.com/api/")

    def test_timeout_default(self):
        """All requests have a 30 second default timeout"""
        self.message.send()
        timeout = self.get_api_call_arg('timeout')
        self.assertEqual(timeout, 30)

    @override_settings(ANYMAIL_REQUESTS_TIMEOUT=5)
    def test_timeout_setting(self):
        """You can use the Anymail setting REQUESTS_TIMEOUT to override the default"""
        self.message.send()
        timeout = self.get_api_call_arg('timeout')
        self.assertEqual(timeout, 5)
