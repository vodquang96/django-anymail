import os
import unittest

from django.test import SimpleTestCase
from django.test.utils import override_settings

from anymail.exceptions import AnymailAPIError
from anymail.message import AnymailMessage

from .utils import AnymailTestMixin, sample_image_path, RUN_LIVE_TESTS

MAILJET_TEST_API_KEY = os.getenv('MAILJET_TEST_API_KEY')
MAILJET_TEST_SECRET_KEY = os.getenv('MAILJET_TEST_SECRET_KEY')


@unittest.skipUnless(RUN_LIVE_TESTS, "RUN_LIVE_TESTS disabled in this environment")
@unittest.skipUnless(MAILJET_TEST_API_KEY and MAILJET_TEST_SECRET_KEY,
                     "Set MAILJET_TEST_API_KEY and MAILJET_TEST_SECRET_KEY "
                     "environment variables to run Mailjet integration tests")
@override_settings(ANYMAIL_MAILJET_API_KEY=MAILJET_TEST_API_KEY,
                   ANYMAIL_MAILJET_SECRET_KEY=MAILJET_TEST_SECRET_KEY,
                   EMAIL_BACKEND="anymail.backends.mailjet.EmailBackend")
class MailjetBackendIntegrationTests(SimpleTestCase, AnymailTestMixin):
    """Mailjet API integration tests

    These tests run against the **live** Mailjet API, using the
    environment variables `MAILJET_TEST_API_KEY` and `MAILJET_TEST_SECRET_KEY`
    as the API key and API secret key, respectively.
    If those variables are not set, these tests won't run.

    Mailjet doesn't (in v3.0) offer a test/sandbox mode -- it tries to send everything
    you ask.

    Mailjet also doesn't support unverified senders (so no from@example.com).
    We've set up @test-mj.anymail.info as a validated sending domain for these tests.

    """

    def setUp(self):
        super(MailjetBackendIntegrationTests, self).setUp()
        self.message = AnymailMessage('Anymail Mailjet integration test', 'Text content',
                                      'test@test-mj.anymail.info', ['anymail-test-to1@mailinator.com'])
        self.message.attach_alternative('<p>HTML content</p>', "text/html")

    def test_simple_send(self):
        # Example of getting the Mailjet send status and message id from the message
        sent_count = self.message.send()
        self.assertEqual(sent_count, 1)

        anymail_status = self.message.anymail_status
        sent_status = anymail_status.recipients['anymail-test-to1@mailinator.com'].status
        message_id = anymail_status.recipients['anymail-test-to1@mailinator.com'].message_id

        self.assertEqual(sent_status, 'sent')
        self.assertRegex(message_id, r'.+')
        self.assertEqual(anymail_status.status, {sent_status})  # set of all recipient statuses
        self.assertEqual(anymail_status.message_id, message_id)

    def test_all_options(self):
        message = AnymailMessage(
            subject="Anymail Mailjet all-options integration test",
            body="This is the text body",
            from_email='"Test Sender, Inc." <test@test-mj.anymail.info>',
            to=['anymail-test-to1@mailinator.com', '"Recipient, 2nd" <anymail-test-to2@mailinator.com>'],
            cc=['anymail-test-cc1@mailinator.com', 'Copy 2 <anymail-test-cc1@mailinator.com>'],
            bcc=['anymail-test-bcc1@mailinator.com', 'Blind Copy 2 <anymail-test-bcc2@mailinator.com>'],
            reply_to=['reply1@example.com', '"Reply, 2nd" <reply2@example.com>'],
            headers={"X-Anymail-Test": "value"},

            metadata={"meta1": "simple string", "meta2": 2},
            tags=["tag 1"],  # Mailjet only allows a single tag
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
        self.assertEqual(message.anymail_status.status, {'sent'})

    def test_merge_data(self):
        message = AnymailMessage(
            subject="Anymail Mailjet merge_data test",  # Mailjet doesn't support merge fields in the subject
            body="This body includes merge data: [[var:value]]\n"
                 "And global merge data: [[var:global]]",
            from_email="Test From <test@test-mj.anymail.info>",
            to=["anymail-test-to1@mailinator.com", "Recipient 2 <anymail-test-to2@mailinator.com>"],
            merge_data={
                'anymail-test-to1@mailinator.com': {'value': 'one'},
                'anymail-test-to2@mailinator.com': {'value': 'two'},
            },
            merge_global_data={
                'global': 'global_value'
            },
        )
        message.send()
        recipient_status = message.anymail_status.recipients
        self.assertEqual(recipient_status['anymail-test-to1@mailinator.com'].status, 'sent')
        self.assertEqual(recipient_status['anymail-test-to2@mailinator.com'].status, 'sent')

    def test_stored_template(self):
        message = AnymailMessage(
            template_id='176375',  # ID of the real template named 'test-template' in our Mailjet test account
            to=["anymail-test-to1@mailinator.com"],
            merge_data={
                'anymail-test-to1@mailinator.com': {
                    'name': "Test Recipient",
                }
            },
            merge_global_data={
                'order': '12345',
            },
        )
        message.from_email = None  # use the template's sender email/name
        message.send()
        recipient_status = message.anymail_status.recipients
        self.assertEqual(recipient_status['anymail-test-to1@mailinator.com'].status, 'sent')

    @override_settings(ANYMAIL_MAILJET_API_KEY="Hey, that's not an API key!")
    def test_invalid_api_key(self):
        with self.assertRaises(AnymailAPIError) as cm:
            self.message.send()
        err = cm.exception
        self.assertEqual(err.status_code, 401)
        self.assertIn("Invalid Mailjet API key or secret", str(err))
