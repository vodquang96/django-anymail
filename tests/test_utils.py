# Tests for the anymail/utils.py module
# (not to be confused with utilities for testing found in in tests/utils.py)

from django.test import SimpleTestCase

from anymail.exceptions import AnymailInvalidAddress
from anymail.utils import ParsedEmail


class ParsedEmailTests(SimpleTestCase):
    """Test utils.ParsedEmail"""

    # Anymail (and Djrill) have always used EmailMessage.encoding, which defaults to None.
    # (Django substitutes settings.DEFAULT_ENCODING='utf-8' when converting to a mime message,
    # but Anymail has never used that code.)
    ADDRESS_ENCODING = None

    def test_simple_email(self):
        parsed = ParsedEmail("test@example.com", self.ADDRESS_ENCODING)
        self.assertEqual(parsed.email, "test@example.com")
        self.assertEqual(parsed.name, "")
        self.assertEqual(parsed.address, "test@example.com")

    def test_display_name(self):
        parsed = ParsedEmail('"Display Name, Inc." <test@example.com>', self.ADDRESS_ENCODING)
        self.assertEqual(parsed.email, "test@example.com")
        self.assertEqual(parsed.name, "Display Name, Inc.")
        self.assertEqual(parsed.address, '"Display Name, Inc." <test@example.com>')

    def test_obsolete_display_name(self):
        # you can get away without the quotes if there are no commas or parens
        # (but it's not recommended)
        parsed = ParsedEmail('Display Name <test@example.com>', self.ADDRESS_ENCODING)
        self.assertEqual(parsed.email, "test@example.com")
        self.assertEqual(parsed.name, "Display Name")
        self.assertEqual(parsed.address, 'Display Name <test@example.com>')

    def test_unicode_display_name(self):
        parsed = ParsedEmail(u'"Unicode \N{HEAVY BLACK HEART}" <test@example.com>', self.ADDRESS_ENCODING)
        self.assertEqual(parsed.email, "test@example.com")
        self.assertEqual(parsed.name, u"Unicode \N{HEAVY BLACK HEART}")
        # display-name automatically shifts to quoted-printable/base64 for non-ascii chars:
        self.assertEqual(parsed.address, '=?utf-8?b?VW5pY29kZSDinaQ=?= <test@example.com>')

    def test_invalid_display_name(self):
        with self.assertRaises(AnymailInvalidAddress):
            # this parses as multiple email addresses, because of the comma:
            ParsedEmail('Display Name, Inc. <test@example.com>', self.ADDRESS_ENCODING)

    def test_none_address(self):
        # used for, e.g., telling Mandrill to use template default from_email
        parsed = ParsedEmail(None, self.ADDRESS_ENCODING)
        self.assertEqual(parsed.email, None)
        self.assertEqual(parsed.name, None)
        self.assertEqual(parsed.address, None)

    def test_empty_address(self):
        with self.assertRaises(AnymailInvalidAddress):
            ParsedEmail('', self.ADDRESS_ENCODING)

    def test_whitespace_only_address(self):
        with self.assertRaises(AnymailInvalidAddress):
            ParsedEmail(' ', self.ADDRESS_ENCODING)
