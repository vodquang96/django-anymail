import json

import requests

from django.conf import settings
from django.core.mail.backends.base import BaseEmailBackend

from ..exceptions import AnymailError, AnymailRequestsAPIError, AnymailSerializationError, AnymailUnsupportedFeature
from ..utils import Attachment, ParsedEmail, UNSET, combine, last
from .._version import __version__


class AnymailBaseBackend(BaseEmailBackend):
    """
    Base Anymail email backend
    """

    def __init__(self, *args, **kwargs):
        super(AnymailBaseBackend, self).__init__(*args, **kwargs)
        self.send_defaults = getattr(settings, "ANYMAIL_SEND_DEFAULTS", {})

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
        encoding = message.encoding
        payload = self.get_base_payload(message)

        # Standard EmailMessage features:
        self.set_payload_from_email(payload, ParsedEmail(message.from_email, encoding), message)
        for recipient_type in ["to", "cc", "bcc"]:
            recipients = getattr(message, recipient_type, [])
            if recipients:
                emails = [ParsedEmail(address, encoding) for address in recipients]
                self.add_payload_recipients(payload, recipient_type, emails, message)
        self.set_payload_subject(payload, message.subject, message)

        if hasattr(message, "reply_to"):
            emails = [ParsedEmail(address, encoding) for address in message.reply_to]
            self.set_payload_reply_to(payload, emails, message)
        if hasattr(message, "extra_headers"):
            self.add_payload_headers(payload, message.extra_headers, message)

        if message.content_subtype == "html":
            self.set_payload_html_body(payload, message.body, message)
        else:
            self.set_payload_text_body(payload, message.body, message)

        if hasattr(message, "alternatives"):
            for (content, mimetype) in message.alternatives:
                self.add_payload_alternative(payload, content, mimetype, message)

        str_encoding = encoding or settings.DEFAULT_CHARSET
        for attachment in message.attachments:
            self.add_payload_attachment(payload, Attachment(attachment, str_encoding), message)

        # Anymail additions:
        metadata = self.get_anymail_merged_attr(message, "metadata")  # merged: changes semantics from Djrill!
        if metadata is not UNSET:
            self.set_payload_metadata(payload, metadata, message)
        send_at = self.get_anymail_attr(message, "send_at")
        if send_at is not UNSET:
            self.set_payload_send_at(payload, send_at, message)
        tags = self.get_anymail_merged_attr(message, "tags")  # merged: changes semantics from Djrill!
        if tags is not UNSET:
            self.set_payload_tags(payload, tags, message)
        track_clicks = self.get_anymail_attr(message, "track_clicks")
        if track_clicks is not UNSET:
            self.set_payload_track_clicks(payload, track_clicks, message)
        track_opens = self.get_anymail_attr(message, "track_opens")
        if track_opens is not UNSET:
            self.set_payload_track_opens(payload, track_opens, message)

        # ESP-specific fallback:
        self.add_payload_esp_options(payload, message)

        return payload

    def get_anymail_attr(self, message, attr):
        default_value = self.send_defaults.get(attr, UNSET)
        message_value = getattr(message, attr, UNSET)
        return last(default_value, message_value)

    def get_anymail_merged_attr(self, message, attr):
        default_value = self.send_defaults.get(attr, UNSET)
        message_value = getattr(message, attr, UNSET)
        return combine(default_value, message_value)

    def unsupported_feature(self, feature):
        # future: check settings.ANYMAIL_UNSUPPORTED_FEATURE_ERRORS
        raise AnymailUnsupportedFeature("%s does not support %s" % (self.esp_name, feature))

    #
    # Payload construction
    #

    def get_base_payload(self, message):
        raise NotImplementedError("%s.%s must implement init_base_payload" %
                                  (self.__class__.__module__, self.__class__.__name__))

    def set_payload_from_email(self, payload, email, message):
        raise NotImplementedError("%s.%s must implement set_payload_from" %
                                  (self.__class__.__module__, self.__class__.__name__))

    def add_payload_recipients(self, payload, recipient_type, emails, message):
        for email in emails:
            self.add_payload_recipient(payload, recipient_type, email, message)

    def add_payload_recipient(self, payload, recipient_type, email, message):
        raise NotImplementedError("%s.%s must implement add_payload_recipient" %
                                  (self.__class__.__module__, self.__class__.__name__))

    def set_payload_subject(self, payload, subject, message):
        raise NotImplementedError("%s.%s must implement set_payload_subject" %
                                  (self.__class__.__module__, self.__class__.__name__))

    def set_payload_reply_to(self, payload, emails, message):
        raise NotImplementedError("%s.%s must implement set_payload_reply_to" %
                                  (self.__class__.__module__, self.__class__.__name__))

    def add_payload_headers(self, payload, headers, message):
        raise NotImplementedError("%s.%s must implement add_payload_heeaders" %
                                  (self.__class__.__module__, self.__class__.__name__))

    def set_payload_text_body(self, payload, body, message):
        raise NotImplementedError("%s.%s must implement set_payload_text_body" %
                                  (self.__class__.__module__, self.__class__.__name__))

    def set_payload_html_body(self, payload, body, message):
        raise NotImplementedError("%s.%s must implement set_payload_html_body" %
                                  (self.__class__.__module__, self.__class__.__name__))

    def add_payload_alternative(self, payload, content, mimetype, message):
        raise NotImplementedError("%s.%s must implement add_payload_alternative" %
                                  (self.__class__.__module__, self.__class__.__name__))

    def add_payload_attachment(self, payload, attachment, message):
        raise NotImplementedError("%s.%s must implement add_payload_attachment" %
                                  (self.__class__.__module__, self.__class__.__name__))

    # Anymail-specific payload construction
    def set_payload_metadata(self, payload, metadata, message):
        self.unsupported_feature("metadata")

    def set_payload_send_at(self, payload, send_at, message):
        self.unsupported_feature("send_at")

    def set_payload_tags(self, payload, tags, message):
        self.unsupported_feature("tags")

    def set_payload_track_clicks(self, payload, track_clicks, message):
        self.unsupported_feature("track_clicks")

    def set_payload_track_opens(self, payload, track_opens, message):
        self.unsupported_feature("track_opens")

    # ESP-specific payload construction
    def add_payload_esp_options(self, payload, message):
        raise NotImplementedError("%s.%s must implement add_payload_esp_options" %
                                  (self.__class__.__module__, self.__class__.__name__))

    #

    def post_to_esp(self, payload, message):
        """Post payload to ESP send API endpoint, and return the raw response.

        payload is the result of build_message_payload
        message is the original EmailMessage
        return should be a raw response

        Can raise AnymailAPIError (or derived exception) for problems posting to the ESP
        """
        raise NotImplementedError("%s.%s must implement post_to_esp" %
                                  (self.__class__.__module__, self.__class__.__name__))

    def deserialize_response(self, response, payload, message):
        """Deserialize a raw ESP response

        Can raise AnymailAPIError (or derived exception) if response is unparsable
        """
        raise NotImplementedError("%s.%s must implement deserialize_response" %
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
