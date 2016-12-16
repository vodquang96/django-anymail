import json
from datetime import datetime
# noinspection PyUnresolvedReferences
from six.moves.urllib.parse import urljoin

import hashlib
import hmac
from base64 import b64encode
from django.core.exceptions import ImproperlyConfigured
from django.test import override_settings
from django.utils.timezone import utc
from mock import ANY

from anymail.signals import AnymailTrackingEvent
from anymail.webhooks.mandrill import MandrillTrackingWebhookView

from .webhook_cases import WebhookTestCase, WebhookBasicAuthTestsMixin

TEST_WEBHOOK_KEY = 'TEST_WEBHOOK_KEY'


def mandrill_args(events=None, url='/anymail/mandrill/tracking/', key=TEST_WEBHOOK_KEY):
    """Returns TestClient.post kwargs for Mandrill webhook call with events

    Computes correct signature.
    """
    if events is None:
        events = []
    url = urljoin('http://testserver/', url)
    mandrill_events = json.dumps(events)
    signed_data = url + 'mandrill_events' + mandrill_events
    signature = b64encode(hmac.new(key=key.encode('ascii'),
                                   msg=signed_data.encode('utf-8'),
                                   digestmod=hashlib.sha1).digest())
    return {
        'path': url,
        'data': {'mandrill_events': mandrill_events},
        'HTTP_X_MANDRILL_SIGNATURE': signature,
    }


class MandrillWebhookSettingsTestCase(WebhookTestCase):
    def test_requires_webhook_key(self):
        with self.assertRaisesRegex(ImproperlyConfigured, r'MANDRILL_WEBHOOK_KEY'):
            self.client.post('/anymail/mandrill/tracking/',
                             data={'mandrill_events': '[]'})

    def test_head_does_not_require_webhook_key(self):
        # Mandrill issues an unsigned HEAD request to verify the wehbook url.
        # Only *after* that succeeds will Mandrill will tell you the webhook key.
        # So make sure that HEAD request will go through without any key set:
        response = self.client.head('/anymail/mandrill/tracking/')
        self.assertEqual(response.status_code, 200)


@override_settings(ANYMAIL_MANDRILL_WEBHOOK_KEY=TEST_WEBHOOK_KEY)
class MandrillWebhookSecurityTestCase(WebhookTestCase, WebhookBasicAuthTestsMixin):
    should_warn_if_no_auth = False  # because we check webhook signature

    def call_webhook(self):
        kwargs = mandrill_args([{'event': 'send'}])
        return self.client.post(**kwargs)

    # Additional tests are in WebhookBasicAuthTestsMixin

    def test_verifies_correct_signature(self):
        kwargs = mandrill_args([{'event': 'send'}])
        response = self.client.post(**kwargs)
        self.assertEqual(response.status_code, 200)

    def test_verifies_missing_signature(self):
        response = self.client.post('/anymail/mandrill/tracking/',
                                    data={'mandrill_events': '[{"event":"send"}]'})
        self.assertEqual(response.status_code, 400)

    def test_verifies_bad_signature(self):
        kwargs = mandrill_args([{'event': 'send'}], key="wrong API key")
        response = self.client.post(**kwargs)
        self.assertEqual(response.status_code, 400)


@override_settings(ANYMAIL_MANDRILL_WEBHOOK_KEY=TEST_WEBHOOK_KEY)
class MandrillTrackingTestCase(WebhookTestCase):

    def test_head_request(self):
        # Mandrill verifies webhooks at config time with a HEAD request
        response = self.client.head('/anymail/mandrill/tracking/')
        self.assertEqual(response.status_code, 200)

    def test_post_request_invalid_json(self):
        kwargs = mandrill_args()
        kwargs['data'] = {'mandrill_events': "GARBAGE DATA"}
        response = self.client.post(**kwargs)
        self.assertEqual(response.status_code, 400)

    def test_send_event(self):
        raw_events = [{
            "event": "send",
            "msg": {
                "ts": 1461095211,  # time send called
                "subject": "Webhook Test",
                "email": "recipient@example.com",
                "sender": "sender@example.com",
                "tags": ["tag1", "tag2"],
                "metadata": {"custom1": "value1", "custom2": "value2"},
                "_id": "abcdef012345789abcdef012345789"
            },
            "_id": "abcdef012345789abcdef012345789",
            "ts": 1461095246  # time of event
        }]
        response = self.client.post(**mandrill_args(events=raw_events))
        self.assertEqual(response.status_code, 200)
        kwargs = self.assert_handler_called_once_with(self.tracking_handler, sender=MandrillTrackingWebhookView,
                                                      event=ANY, esp_name='Mandrill')
        event = kwargs['event']
        self.assertIsInstance(event, AnymailTrackingEvent)
        self.assertEqual(event.event_type, "sent")
        self.assertEqual(event.timestamp, datetime(2016, 4, 19, 19, 47, 26, tzinfo=utc))
        self.assertEqual(event.esp_event, raw_events[0])
        self.assertEqual(event.message_id, "abcdef012345789abcdef012345789")
        self.assertEqual(event.recipient, "recipient@example.com")
        self.assertEqual(event.tags, ["tag1", "tag2"])
        self.assertEqual(event.metadata, {"custom1": "value1", "custom2": "value2"})

    def test_hard_bounce_event(self):
        raw_events = [{
            "event": "hard_bounce",
            "msg": {
                "ts": 1461095211,  # time send called
                "subject": "Webhook Test",
                "email": "bounce@example.com",
                "sender": "sender@example.com",
                "bounce_description": "bad_mailbox",
                "bgtools_code": 10,
                "diag": "smtp;550 5.1.1 The email account that you tried to reach does not exist.",
                "_id": "abcdef012345789abcdef012345789"
            },
            "_id": "abcdef012345789abcdef012345789",
            "ts": 1461095246  # time of event
        }]
        response = self.client.post(**mandrill_args(events=raw_events))
        self.assertEqual(response.status_code, 200)
        kwargs = self.assert_handler_called_once_with(self.tracking_handler, sender=MandrillTrackingWebhookView,
                                                      event=ANY, esp_name='Mandrill')
        event = kwargs['event']
        self.assertIsInstance(event, AnymailTrackingEvent)
        self.assertEqual(event.event_type, "bounced")
        self.assertEqual(event.esp_event, raw_events[0])
        self.assertEqual(event.message_id, "abcdef012345789abcdef012345789")
        self.assertEqual(event.recipient, "bounce@example.com")
        self.assertEqual(event.mta_response,
                         "smtp;550 5.1.1 The email account that you tried to reach does not exist.")

    def test_click_event(self):
        raw_events = [{
            "event": "click",
            "msg": {
                "ts": 1461095211,  # time send called
                "subject": "Webhook Test",
                "email": "recipient@example.com",
                "sender": "sender@example.com",
                "opens": [{"ts": 1461095242}],
                "clicks": [{"ts": 1461095246, "url": "http://example.com"}],
                "_id": "abcdef012345789abcdef012345789"
            },
            "user_agent": "Mozilla/5.0 (Windows NT 5.1; rv:11.0) Gecko Firefox/11.0",
            "url": "http://example.com",
            "_id": "abcdef012345789abcdef012345789",
            "ts": 1461095246  # time of event
        }]
        response = self.client.post(**mandrill_args(events=raw_events))
        self.assertEqual(response.status_code, 200)
        kwargs = self.assert_handler_called_once_with(self.tracking_handler, sender=MandrillTrackingWebhookView,
                                                      event=ANY, esp_name='Mandrill')
        event = kwargs['event']
        self.assertIsInstance(event, AnymailTrackingEvent)
        self.assertEqual(event.event_type, "clicked")
        self.assertEqual(event.esp_event, raw_events[0])
        self.assertEqual(event.click_url, "http://example.com")
        self.assertEqual(event.user_agent, "Mozilla/5.0 (Windows NT 5.1; rv:11.0) Gecko Firefox/11.0")

    def test_sync_event(self):
        # Mandrill sync events use a different format from other events
        # https://mandrill.zendesk.com/hc/en-us/articles/205583297-Sync-Event-Webhook-format
        raw_events = [{
            "type": "blacklist",
            "action": "add",
            "reject": {
                "email": "recipient@example.com",
                "reason": "manual edit"
            }
        }]
        response = self.client.post(**mandrill_args(events=raw_events))
        self.assertEqual(response.status_code, 200)
        kwargs = self.assert_handler_called_once_with(self.tracking_handler, sender=MandrillTrackingWebhookView,
                                                      event=ANY, esp_name='Mandrill')
        event = kwargs['event']
        self.assertEqual(event.event_type, "unknown")
        self.assertEqual(event.recipient, "recipient@example.com")
        self.assertEqual(event.description, "manual edit")
