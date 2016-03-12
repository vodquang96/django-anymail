from __future__ import unicode_literals

import os
import unittest
from datetime import datetime, timedelta

from django.test import SimpleTestCase
from django.test.utils import override_settings

from anymail.exceptions import AnymailAPIError
from anymail.message import AnymailMessage

from .utils import AnymailTestMixin, sample_image_path

SENDGRID_TEST_API_KEY = os.getenv('SENDGRID_TEST_API_KEY')


@unittest.skipUnless(SENDGRID_TEST_API_KEY,
                     "Set SENDGRID_TEST_API_KEY environment variable "
                     "to run SendGrid integration tests")
@override_settings(ANYMAIL_SENDGRID_API_KEY=SENDGRID_TEST_API_KEY,
                   EMAIL_BACKEND="anymail.backends.sendgrid.SendGridBackend")
class SendGridBackendIntegrationTests(SimpleTestCase, AnymailTestMixin):
    """SendGrid API integration tests

    These tests run against the **live** SendGrid API, using the
    environment variable `SENDGRID_TEST_API_KEY` as the API key
    If those variables are not set, these tests won't run.

    SendGrid doesn't offer a test mode -- it tries to send everything
    you ask. To avoid stacking up a pile of undeliverable @example.com
    emails, the tests use SendGrid's "sink domain" @sink.sendgrid.net.
    https://support.sendgrid.com/hc/en-us/articles/201995663-Safely-Test-Your-Sending-Speed

    """

    def setUp(self):
        super(SendGridBackendIntegrationTests, self).setUp()
        self.message = AnymailMessage('Anymail SendGrid integration test', 'Text content',
                                      'from@example.com', ['to@sink.sendgrid.net'])
        self.message.attach_alternative('<p>HTML content</p>', "text/html")

    def test_simple_send(self):
        # Example of getting the SendGrid send status and message id from the message
        sent_count = self.message.send()
        self.assertEqual(sent_count, 1)

        anymail_status = self.message.anymail_status
        sent_status = anymail_status.recipients['to@sink.sendgrid.net'].status
        message_id = anymail_status.recipients['to@sink.sendgrid.net'].message_id

        self.assertEqual(sent_status, 'queued')  # SendGrid always queues
        self.assertRegex(message_id, r'\<.+@example\.com\>')  # should use from_email's domain
        self.assertEqual(anymail_status.status, {sent_status})  # set of all recipient statuses
        self.assertEqual(anymail_status.message_id, message_id)

    def test_all_options(self):
        send_at = datetime.now().replace(microsecond=0) + timedelta(minutes=2)
        message = AnymailMessage(
            subject="Anymail all-options integration test FILES",
            body="This is the text body",
            from_email="Test From <from@example.com>",
            to=["to1@sink.sendgrid.net", "Recipient 2 <to2@sink.sendgrid.net>"],
            cc=["cc1@sink.sendgrid.net", "Copy 2 <cc2@sink.sendgrid.net>"],
            bcc=["bcc1@sink.sendgrid.net", "Blind Copy 2 <bcc2@sink.sendgrid.net>"],
            reply_to=["reply1@example.com", "Reply 2 <reply2@example.com>"],
            headers={"X-Anymail-Test": "value"},

            metadata={"meta1": "simple string", "meta2": 2},
            send_at=send_at,
            tags=["tag 1", "tag 2"],
            track_clicks=True,
            track_opens=True,
        )
        message.attach("attachment1.txt", "Here is some\ntext for you", "text/plain")
        message.attach("attachment2.csv", "ID,Name\n1,Amy Lina", "text/csv")
        cid = message.attach_inline_image_file(sample_image_path())
        message.attach_alternative(
            "<p><b>HTML:</b> with <a href='http://example.com'>link</a>"
            "and image: <img src='cid:%s'></div>" % cid,
            "text/html")

        message.send()
        self.assertEqual(message.anymail_status.status, {'queued'})  # SendGrid always queues

    @override_settings(ANYMAIL_SENDGRID_API_KEY="Hey, that's not an API key!")
    def test_invalid_api_key(self):
        with self.assertRaises(AnymailAPIError) as cm:
            self.message.send()
        err = cm.exception
        self.assertEqual(err.status_code, 400)
        # Make sure the exception message includes SendGrid's response:
        self.assertIn("authorization grant is invalid", str(err))
