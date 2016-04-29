from django.core.mail import get_connection
from django.test import SimpleTestCase
from django.test.utils import override_settings

from .utils import AnymailTestMixin


class BackendSettingsTests(SimpleTestCase, AnymailTestMixin):
    """Test settings initializations for Anymail EmailBackends"""

    # We should add a "GenericBackend" or something basic for testing.
    # For now, we just access real backends directly.

    @override_settings(ANYMAIL={'MAILGUN_API_KEY': 'api_key_from_settings'})
    def test_connection_kwargs_overrides_settings(self):
        connection = get_connection('anymail.backends.mailgun.MailgunBackend')
        self.assertEqual(connection.api_key, 'api_key_from_settings')

        connection = get_connection('anymail.backends.mailgun.MailgunBackend',
                                    api_key='api_key_from_kwargs')
        self.assertEqual(connection.api_key, 'api_key_from_kwargs')

    @override_settings(ANYMAIL={'SENDGRID_USERNAME': 'username_from_settings',
                                'SENDGRID_PASSWORD': 'password_from_settings'})
    def test_username_password_kwargs_overrides(self):
        # Additional checks for username and password, which are special-cased
        # because of Django core mail function defaults.
        connection = get_connection('anymail.backends.sendgrid.SendGridBackend')
        self.assertEqual(connection.username, 'username_from_settings')
        self.assertEqual(connection.password, 'password_from_settings')

        connection = get_connection('anymail.backends.sendgrid.SendGridBackend',
                                    username='username_from_kwargs', password='password_from_kwargs')
        self.assertEqual(connection.username, 'username_from_kwargs')
        self.assertEqual(connection.password, 'password_from_kwargs')
