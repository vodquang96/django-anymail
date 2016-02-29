import json
import requests

from django.core.mail.backends.base import BaseEmailBackend

from .._version import __version__
from ..exceptions import AnymailError, AnymailRequestsAPIError, AnymailSerializationError, AnymailImproperlyConfigured


class AnymailBaseBackend(BaseEmailBackend):
    """
    Base Anymail email backend
    """

    def open(self):
        """
        Open and persist a connection to the ESP's API, and whether
        a new connection was created.

        Callers must ensure they later call close, if (and only if) open
        returns True.
        """
        # Subclasses should use an instance property to maintain a cached
        # connection, and return True iff they initialize that instance
        # property in _this_ open call. (If the cached connection already
        # exists, just do nothing and return False.)
        #
        # Subclasses should swallow operational errors if self.fail_silently
        # (e.g., network errors), but otherwise can raise any errors.
        #
        # (Returning a bool to indicate whether connection was created is
        # borrowed from django.core.email.backends.SMTPBackend)
        return False

    def close(self):
        """
        Close the cached connection created by open.

        You must only call close if your code called open and it returned True.
        """
        # Subclasses should tear down the cached connection and clear
        # the instance property.
        #
        # Subclasses should swallow operational errors if self.fail_silently
        # (e.g., network errors), but otherwise can raise any errors.
        pass

    def send_messages(self, email_messages):
        """
        Sends one or more EmailMessage objects and returns the number of email
        messages sent.
        """
        # This API is specified by Django's core BaseEmailBackend
        # (so you can't change it to, e.g., return detailed status).
        # Subclasses shouldn't need to override.

        num_sent = 0
        if not email_messages:
            return num_sent

        created_session = self.open()

        try:
            for message in email_messages:
                try:
                    sent = self._send(message)
                except AnymailError:
                    if self.fail_silently:
                        sent = False
                    else:
                        raise
                if sent:
                    num_sent += 1
        finally:
            if created_session:
                self.close()

        return num_sent

    def _send(self, message):
        """Sends the EmailMessage message, and returns True if the message was sent.

        This should only be called by the base send_messages loop.

        Implementations must raise exceptions derived from AnymailError for
        anticipated failures that should be suppressed in fail_silently mode.
        """
        message.anymail_status = None
        esp_response_attr = "%s_response" % self.esp_name.lower()  # e.g., message.mandrill_response
        setattr(message, esp_response_attr, None)  # until we have a response
        if not message.recipients():
            return False

        payload = self.build_message_payload(message)
        # FUTURE: if pre-send-signal OK...
        response = self.post_to_esp(payload, message)

        parsed_response = self.deserialize_response(response, payload, message)
        setattr(message, esp_response_attr, parsed_response)
        message.anymail_status = self.validate_response(parsed_response, response, payload, message)
        # FUTURE: post-send signal

        return True

    def build_message_payload(self, message):
        """Return a payload with all message-specific options for ESP send call.

        message is an EmailMessage, possibly with additional Anymail-specific attrs

        Can raise AnymailUnsupportedFeature for unsupported options in message.
        """
        raise NotImplementedError("%s.%s must implement build_message_payload" %
                                  (self.__class__.__module__, self.__class__.__name__))

    def post_to_esp(self, payload, message):
        """Post payload to ESP send API endpoint, and return the raw response.

        payload is the result of build_message_payload
        message is the original EmailMessage
        return should be a raw response

        Can raise AnymailAPIError (or derived exception) for problems posting to the ESP
        """
        raise NotImplementedError("%s.%s must implement build_message_payload" %
                                  (self.__class__.__module__, self.__class__.__name__))

    def deserialize_response(self, response, payload, message):
        """Deserialize a raw ESP response

        Can raise AnymailAPIError (or derived exception) if response is unparsable
        """
        raise NotImplementedError("%s.%s must implement build_message_payload" %
                                  (self.__class__.__module__, self.__class__.__name__))

    def validate_response(self, parsed_response, response, payload, message):
        """Validate parsed_response, raising exceptions for any problems, and return normalized status.

        Extend this to provide your own validation checks.
        Validation exceptions should inherit from anymail.exceptions.AnymailError
        for proper fail_silently behavior.

        If *all* recipients are refused or invalid, should raise AnymailRecipientsRefused

        Returns one of "sent", "queued", "refused", "error" or "multi"
        """
        raise NotImplementedError("%s.%s must implement validate_response" %
                                  (self.__class__.__module__, self.__class__.__name__))

    @property
    def esp_name(self):
        """
        Read-only name of the ESP for this backend.

        (E.g., MailgunBackend will return "Mailgun")
        """
        return self.__class__.__name__.replace("Backend", "")


class AnymailRequestsBackend(AnymailBaseBackend):
    """
    Base Anymail email backend for ESPs that use an HTTP API via requests
    """

    def __init__(self, api_url, **kwargs):
        """Init options from Django settings"""
        self.api_url = api_url
        super(AnymailRequestsBackend, self).__init__(**kwargs)
        self.session = None

    def open(self):
        if self.session:
            return False  # already exists

        try:
            self.session = requests.Session()
        except requests.RequestException:
            if not self.fail_silently:
                raise
        else:
            self.session.headers["User-Agent"] = "Anymail/%s %s" % (
                __version__, self.session.headers.get("User-Agent", ""))
            return True

    def close(self):
        if self.session is None:
            return
        try:
            self.session.close()
        except requests.RequestException:
            if not self.fail_silently:
                raise
        finally:
            self.session = None

    def _send(self, message):
        if self.session is None:
            class_name = self.__class__.__name__
            raise RuntimeError(
                "Session has not been opened in {class_name}._send. "
                "(This is either an implementation error in {class_name}, "
                "or you are incorrectly calling _send directly.)".format(class_name=class_name))
        return super(AnymailRequestsBackend, self)._send(message)

    def get_api_url(self, payload, message):
        """Return the correct ESP url for sending payload

        Override this to substitute your own logic for determining API endpoint.
        """
        return self.api_url

    def serialize_payload(self, payload, message):
        """Return payload serialized to post data.

        Should raise AnymailSerializationError if payload is not serializable
        """
        try:
            return json.dumps(payload)
        except TypeError as err:
            # Add some context to the "not JSON serializable" message
            raise AnymailSerializationError(orig_err=err, email_message=message, payload=payload)

    def post_to_esp(self, payload, message):
        """Post payload to ESP send API endpoint, and return the raw response.

        payload is the result of build_message_payload
        message is the original EmailMessage
        return should be a requests.Response

        Can raise AnymailRequestsAPIError for HTTP errors in the post
        """
        api_url = self.get_api_url(payload, message)
        post_data = self.serialize_payload(payload, message)

        response = self.session.post(api_url, data=post_data)
        if response.status_code != 200:
            raise AnymailRequestsAPIError(email_message=message, payload=payload, response=response)
        return response

    def deserialize_response(self, response, payload, message):
        """Return parsed ESP API response

        Can raise AnymailRequestsAPIError if response is unparsable
        """
        try:
            return response.json()
        except ValueError:
            raise AnymailRequestsAPIError("Invalid JSON in %s API response" % self.esp_name,
                                          email_message=message, payload=payload, response=response)
