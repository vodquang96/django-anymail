import json
from datetime import datetime

import hashlib
import hmac
from django.core.exceptions import ImproperlyConfigured
from django.test import override_settings
from django.utils.timezone import utc
from mock import ANY

from anymail.signals import AnymailTrackingEvent
from anymail.webhooks.mailgun import MailgunTrackingWebhookView

from .webhook_cases import WebhookTestCase, WebhookBasicAuthTestsMixin

TEST_API_KEY = 'TEST_API_KEY'


def mailgun_sign(data, api_key=TEST_API_KEY):
    """Add a Mailgun webhook signature to data dict"""
    # Modifies the dict in place
    data.setdefault('timestamp', '1234567890')
    data.setdefault('token', '1234567890abcdef1234567890abcdef')
    data['signature'] = hmac.new(key=api_key.encode('ascii'),
                                 msg='{timestamp}{token}'.format(**data).encode('ascii'),
                                 digestmod=hashlib.sha256).hexdigest()
    return data


def querydict_to_postdict(qd):
    """Converts a Django QueryDict to a TestClient.post(data)-style dict

    Single-value fields appear as normal
    Multi-value fields appear as a list (differs from QueryDict.dict)
    """
    return {
        key: values if len(values) > 1 else values[0]
        for key, values in qd.lists()
    }


class MailgunWebhookSettingsTestCase(WebhookTestCase):
    def test_requires_api_key(self):
        with self.assertRaises(ImproperlyConfigured):
            self.client.post('/anymail/mailgun/tracking/',
                             data=mailgun_sign({'event': 'delivered'}))


@override_settings(ANYMAIL_MAILGUN_API_KEY=TEST_API_KEY)
class MailgunWebhookSecurityTestCase(WebhookTestCase, WebhookBasicAuthTestsMixin):
    should_warn_if_no_auth = False  # because we check webhook signature

    def call_webhook(self):
        return self.client.post('/anymail/mailgun/tracking/',
                                data=mailgun_sign({'event': 'delivered'}))

    # Additional tests are in WebhookBasicAuthTestsMixin

    def test_verifies_correct_signature(self):
        response = self.client.post('/anymail/mailgun/tracking/',
                                    data=mailgun_sign({'event': 'delivered'}))
        self.assertEqual(response.status_code, 200)

    def test_verifies_missing_signature(self):
        response = self.client.post('/anymail/mailgun/tracking/',
                                    data={'event': 'delivered'})
        self.assertEqual(response.status_code, 400)

    def test_verifies_bad_signature(self):
        data = mailgun_sign({'event': 'delivered'}, api_key="wrong API key")
        response = self.client.post('/anymail/mailgun/tracking/', data=data)
        self.assertEqual(response.status_code, 400)


@override_settings(ANYMAIL_MAILGUN_API_KEY=TEST_API_KEY)
class MailgunDeliveryTestCase(WebhookTestCase):

    def test_delivered_event(self):
        raw_event = mailgun_sign({
            'domain': 'example.com',
            'message-headers': json.dumps([
                ["Sender", "from=example.com"],
                ["Date", "Thu, 21 Apr 2016 17:55:29 +0000"],
                ["X-Mailgun-Sid", "WyIxZmY4ZSIsICJtZWRtdW5kc0BnbWFpbC5jb20iLCAiZjFjNzgyIl0="],
                ["Received", "by luna.mailgun.net with HTTP; Thu, 21 Apr 2016 17:55:29 +0000"],
                ["Message-Id", "<20160421175529.19495.89030.B3AE3728@example.com>"],
                ["To", "recipient@example.com"],
                ["From", "from@example.com"],
                ["Subject", "Webhook testing"],
                ["Mime-Version", "1.0"],
                ["Content-Type", ["multipart/alternative", {"boundary": "74fb561763da440d8e6a034054974251"}]]
            ]),
            'X-Mailgun-Sid': 'WyIxZmY4ZSIsICJtZWRtdW5kc0BnbWFpbC5jb20iLCAiZjFjNzgyIl0=',
            'token': '06c96bafc3f42a66b9edd546347a2fe18dc23461fe80dc52f0',
            'timestamp': '1461261330',
            'Message-Id': '<20160421175529.19495.89030.B3AE3728@example.com>',
            'recipient': 'recipient@example.com',
            'event': 'delivered',
        })
        response = self.client.post('/anymail/mailgun/tracking/', data=raw_event)
        self.assertEqual(response.status_code, 200)
        kwargs = self.assert_handler_called_once_with(self.tracking_handler, sender=MailgunTrackingWebhookView,
                                                      event=ANY, esp_name='Mailgun')
        event = kwargs['event']
        self.assertIsInstance(event, AnymailTrackingEvent)
        self.assertEqual(event.event_type, "delivered")
        self.assertEqual(event.timestamp, datetime(2016, 4, 21, 17, 55, 30, tzinfo=utc))
        self.assertEqual(event.message_id, "<20160421175529.19495.89030.B3AE3728@example.com>")
        self.assertEqual(event.event_id, "06c96bafc3f42a66b9edd546347a2fe18dc23461fe80dc52f0")
        self.assertEqual(event.recipient, "recipient@example.com")
        self.assertEqual(querydict_to_postdict(event.esp_event), raw_event)
        self.assertEqual(event.tags, [])
        self.assertEqual(event.metadata, {})

    def test_dropped_bounce(self):
        raw_event = mailgun_sign({
            'code': '605',
            'domain': 'example.com',
            'description': 'Not delivering to previously bounced address',
            'attachment-count': '1',
            'Message-Id': '<20160421180324.70521.79375.96884DDB@example.com>',
            'reason': 'hardfail',
            'event': 'dropped',
            'message-headers': json.dumps([
                ["X-Mailgun-Sid", "WyI3Y2VjMyIsICJib3VuY2VAZXhhbXBsZS5jb20iLCAiZjFjNzgyIl0="],
                ["Received", "by luna.mailgun.net with HTTP; Thu, 21 Apr 2016 18:03:24 +0000"],
                ["Message-Id", "<20160421180324.70521.79375.96884DDB@example.com>"],
                ["To", "bounce@example.com"],
                ["From", "from@example.com"],
                ["Subject", "Webhook testing"],
                ["Mime-Version", "1.0"],
                ["Content-Type", ["multipart/alternative", {"boundary": "a5b51388a4e3455d8feb8510bb8c9fa2"}]]
            ]),
            'recipient': 'bounce@example.com',
            'timestamp': '1461261330',
            'X-Mailgun-Sid': 'WyI3Y2VjMyIsICJib3VuY2VAZXhhbXBsZS5jb20iLCAiZjFjNzgyIl0=',
            'token': 'a3fe1fa1640349ac552b84ddde373014b4c41645830c8dd3fc',
        })
        response = self.client.post('/anymail/mailgun/tracking/', data=raw_event)
        self.assertEqual(response.status_code, 200)
        kwargs = self.assert_handler_called_once_with(self.tracking_handler, sender=MailgunTrackingWebhookView,
                                                      event=ANY, esp_name='Mailgun')
        event = kwargs['event']
        self.assertIsInstance(event, AnymailTrackingEvent)
        self.assertEqual(event.event_type, "rejected")
        self.assertEqual(event.timestamp, datetime(2016, 4, 21, 17, 55, 30, tzinfo=utc))
        self.assertEqual(event.message_id, "<20160421180324.70521.79375.96884DDB@example.com>")
        self.assertEqual(event.event_id, "a3fe1fa1640349ac552b84ddde373014b4c41645830c8dd3fc")
        self.assertEqual(event.recipient, "bounce@example.com")
        self.assertEqual(event.reject_reason, "bounced")
        self.assertEqual(event.description, 'Not delivering to previously bounced address')
        self.assertEqual(querydict_to_postdict(event.esp_event), raw_event)

    def test_dropped_spam(self):
        raw_event = mailgun_sign({
            'code': '607',
            'description': 'Not delivering to a user who marked your messages as spam',
            'reason': 'hardfail',
            'event': 'dropped',
            'recipient': 'complaint@example.com',
            # (omitting some fields that aren't relevant to the test)
        })
        response = self.client.post('/anymail/mailgun/tracking/', data=raw_event)
        self.assertEqual(response.status_code, 200)
        kwargs = self.assert_handler_called_once_with(self.tracking_handler, sender=MailgunTrackingWebhookView,
                                                      event=ANY, esp_name='Mailgun')
        event = kwargs['event']
        self.assertEqual(event.event_type, "rejected")
        self.assertEqual(event.reject_reason, "spam")
        self.assertEqual(event.description, 'Not delivering to a user who marked your messages as spam')

    def test_dropped_timed_out(self):
        raw_event = mailgun_sign({
            'code': '499',
            'description': 'Unable to connect to MX servers: [example.com]',
            'reason': 'old',
            'event': 'dropped',
            'recipient': 'complaint@example.com',
            # (omitting some fields that aren't relevant to the test)
        })
        response = self.client.post('/anymail/mailgun/tracking/', data=raw_event)
        self.assertEqual(response.status_code, 200)
        kwargs = self.assert_handler_called_once_with(self.tracking_handler, sender=MailgunTrackingWebhookView,
                                                      event=ANY, esp_name='Mailgun')
        event = kwargs['event']
        self.assertEqual(event.event_type, "rejected")
        self.assertEqual(event.reject_reason, "timed_out")
        self.assertEqual(event.description, 'Unable to connect to MX servers: [example.com]')

    def test_invalid_mailbox(self):
        raw_event = mailgun_sign({
            'code': '550',
            'error': "550 5.1.1 The email account that you tried to reach does not exist. Please try "
                     "    5.1.1 double-checking the recipient's email address for typos or "
                     "    5.1.1 unnecessary spaces.",
            'event': 'bounced',
            'recipient': 'noreply@example.com',
            # (omitting some fields that aren't relevant to the test)
        })
        response = self.client.post('/anymail/mailgun/tracking/', data=raw_event)
        self.assertEqual(response.status_code, 200)
        kwargs = self.assert_handler_called_once_with(self.tracking_handler, sender=MailgunTrackingWebhookView,
                                                      event=ANY, esp_name='Mailgun')
        event = kwargs['event']
        self.assertEqual(event.event_type, "bounced")
        self.assertEqual(event.reject_reason, "bounced")
        self.assertIn("The email account that you tried to reach does not exist", event.mta_response)

    def test_alt_smtp_code(self):
        # In some cases, Mailgun uses RFC-3463 extended SMTP status codes (x.y.z, rather than nnn).
        # See issue #62.
        raw_event = mailgun_sign({
            'code': '5.1.1',
            'error': 'smtp;550 5.1.1 RESOLVER.ADR.RecipNotFound; not found',
            'event': 'bounced',
            'recipient': 'noreply@example.com',
            # (omitting some fields that aren't relevant to the test)
        })
        response = self.client.post('/anymail/mailgun/tracking/', data=raw_event)
        self.assertEqual(response.status_code, 200)
        kwargs = self.assert_handler_called_once_with(self.tracking_handler, sender=MailgunTrackingWebhookView,
                                                      event=ANY, esp_name='Mailgun')
        event = kwargs['event']
        self.assertEqual(event.event_type, "bounced")
        self.assertEqual(event.reject_reason, "bounced")
        self.assertIn("RecipNotFound", event.mta_response)

    def test_metadata(self):
        # Metadata fields are interspersed with other data, but also in message-headers
        raw_event = mailgun_sign({
            'event': 'delivered',
            'message-headers': json.dumps([
                ["X-Mailgun-Variables", "{\"custom1\": \"value1\", \"custom2\": \"{\\\"key\\\":\\\"value\\\"}\"}"],
            ]),
            'custom1': 'value',
            'custom2': '{"key":"value"}',  # you can store JSON, but you'll need to unpack it yourself
        })
        self.client.post('/anymail/mailgun/tracking/', data=raw_event)
        kwargs = self.assert_handler_called_once_with(self.tracking_handler)
        event = kwargs['event']
        self.assertEqual(event.metadata, {"custom1": "value1", "custom2": '{"key":"value"}'})

    def test_tags(self):
        # Most events include multiple 'tag' fields for message's tags
        raw_event = mailgun_sign({
            'tag': ['tag1', 'tag2'],  # Django TestClient encodes list as multiple field values
            'event': 'opened',
        })
        self.client.post('/anymail/mailgun/tracking/', data=raw_event)
        kwargs = self.assert_handler_called_once_with(self.tracking_handler)
        event = kwargs['event']
        self.assertEqual(event.tags, ["tag1", "tag2"])

    def test_x_tags(self):
        # Delivery events don't include 'tag', but do include 'X-Mailgun-Tag' fields
        raw_event = mailgun_sign({
            'X-Mailgun-Tag': ['tag1', 'tag2'],
            'event': 'delivered',
        })
        self.client.post('/anymail/mailgun/tracking/', data=raw_event)
        kwargs = self.assert_handler_called_once_with(self.tracking_handler)
        event = kwargs['event']
        self.assertEqual(event.tags, ["tag1", "tag2"])
