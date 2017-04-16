import json
from datetime import datetime

from django.utils.timezone import get_fixed_timezone
from mock import ANY

from anymail.signals import AnymailTrackingEvent
from anymail.webhooks.postmark import PostmarkTrackingWebhookView
from .webhook_cases import WebhookBasicAuthTestsMixin, WebhookTestCase


class PostmarkWebhookSecurityTestCase(WebhookTestCase, WebhookBasicAuthTestsMixin):
    def call_webhook(self):
        return self.client.post('/anymail/postmark/tracking/',
                                content_type='application/json', data=json.dumps({}))

    # Actual tests are in WebhookBasicAuthTestsMixin


class PostmarkDeliveryTestCase(WebhookTestCase):
    def test_bounce_event(self):
        raw_event = {
            "ID": 901542550,
            "Type": "HardBounce",
            "TypeCode": 1,
            "Name": "Hard bounce",
            "MessageID": "2706ee8a-737c-4285-b032-ccd317af53ed",
            "Description": "The server was unable to deliver your message (ex: unknown user, mailbox not found).",
            "Details": "smtp;550 5.1.1 The email account that you tried to reach does not exist.",
            "Email": "bounce@example.com",
            "BouncedAt": "2016-04-27T16:28:50.3963933-04:00",
            "DumpAvailable": True,
            "Inactive": True,
            "CanActivate": True,
            "Subject": "Postmark event test",
            "Content": "..."
        }
        response = self.client.post('/anymail/postmark/tracking/',
                                    content_type='application/json', data=json.dumps(raw_event))
        self.assertEqual(response.status_code, 200)
        kwargs = self.assert_handler_called_once_with(self.tracking_handler, sender=PostmarkTrackingWebhookView,
                                                      event=ANY, esp_name='Postmark')
        event = kwargs['event']
        self.assertIsInstance(event, AnymailTrackingEvent)
        self.assertEqual(event.event_type, "bounced")
        self.assertEqual(event.esp_event, raw_event)
        self.assertEqual(event.timestamp, datetime(2016, 4, 27, 16, 28, 50, microsecond=396393,
                                                   tzinfo=get_fixed_timezone(-4*60)))
        self.assertEqual(event.message_id, "2706ee8a-737c-4285-b032-ccd317af53ed")
        self.assertEqual(event.event_id, "901542550")
        self.assertEqual(event.recipient, "bounce@example.com")
        self.assertEqual(event.reject_reason, "bounced")
        self.assertEqual(event.description,
                         "The server was unable to deliver your message (ex: unknown user, mailbox not found).")
        self.assertEqual(event.mta_response,
                         "smtp;550 5.1.1 The email account that you tried to reach does not exist.")

    def test_delivered_event(self):
        raw_event = {
            "ServerId": 23,
            "MessageID": "883953f4-6105-42a2-a16a-77a8eac79483",
            "Recipient": "recipient@example.com",
            "Tag": "welcome-email",
            "DeliveredAt": "2014-08-01T13:28:10.2735393-04:00",
            "Details": "Test delivery webhook details"
        }
        response = self.client.post('/anymail/postmark/tracking/',
                                    content_type='application/json', data=json.dumps(raw_event))
        self.assertEqual(response.status_code, 200)
        kwargs = self.assert_handler_called_once_with(self.tracking_handler, sender=PostmarkTrackingWebhookView,
                                                      event=ANY, esp_name='Postmark')
        event = kwargs['event']
        self.assertIsInstance(event, AnymailTrackingEvent)
        self.assertEqual(event.event_type, "delivered")
        self.assertEqual(event.esp_event, raw_event)
        self.assertEqual(event.timestamp, datetime(2014, 8, 1, 13, 28, 10, microsecond=273539,
                                                   tzinfo=get_fixed_timezone(-4*60)))
        self.assertEqual(event.message_id, "883953f4-6105-42a2-a16a-77a8eac79483")
        self.assertEqual(event.recipient, "recipient@example.com")
        self.assertEqual(event.tags, ["welcome-email"])

    def test_open_event(self):
        raw_event = {
            "FirstOpen": True,
            "Client": {"Name": "Gmail", "Company": "Google", "Family": "Gmail"},
            "OS": {"Name": "unknown", "Company": "unknown", "Family": "unknown"},
            "Platform": "Unknown",
            "UserAgent": "Mozilla/5.0 (Windows NT 5.1; rv:11.0) Gecko Firefox/11.0",
            "ReadSeconds": 0,
            "Geo": {},
            "MessageID": "f4830d10-9c35-4f0c-bca3-3d9b459821f8",
            "ReceivedAt": "2016-04-27T16:21:41.2493688-04:00",
            "Recipient": "recipient@example.com"
        }
        response = self.client.post('/anymail/postmark/tracking/',
                                    content_type='application/json', data=json.dumps(raw_event))
        self.assertEqual(response.status_code, 200)
        kwargs = self.assert_handler_called_once_with(self.tracking_handler, sender=PostmarkTrackingWebhookView,
                                                      event=ANY, esp_name='Postmark')
        event = kwargs['event']
        self.assertIsInstance(event, AnymailTrackingEvent)
        self.assertEqual(event.event_type, "opened")
        self.assertEqual(event.esp_event, raw_event)
        self.assertEqual(event.timestamp, datetime(2016, 4, 27, 16, 21, 41, microsecond=249368,
                                                   tzinfo=get_fixed_timezone(-4*60)))
        self.assertEqual(event.message_id, "f4830d10-9c35-4f0c-bca3-3d9b459821f8")
        self.assertEqual(event.recipient, "recipient@example.com")
        self.assertEqual(event.user_agent, "Mozilla/5.0 (Windows NT 5.1; rv:11.0) Gecko Firefox/11.0")
