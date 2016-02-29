import mimetypes
from base64 import b64encode
from datetime import date, datetime
from email.mime.base import MIMEBase
from email.utils import parseaddr
try:
    from urlparse import urljoin  # python 2
except ImportError:
    from urllib.parse import urljoin  # python 3

from django.conf import settings
from django.core.mail.message import sanitize_address, DEFAULT_ATTACHMENT_MIME_TYPE

from ..exceptions import (AnymailImproperlyConfigured,
                          AnymailRequestsAPIError, AnymailRecipientsRefused,
                          AnymailUnsupportedFeature)

from .base import AnymailRequestsBackend


class MandrillBackend(AnymailRequestsBackend):
    """
    Mandrill API Email Backend
    """

    def __init__(self, **kwargs):
        """Init options from Django settings"""
        api_url = getattr(settings, "MANDRILL_API_URL", "https://mandrillapp.com/api/1.0")
        if not api_url.endswith("/"):
            api_url += "/"

        super(MandrillBackend, self).__init__(api_url, **kwargs)

        try:
            self.api_key = settings.MANDRILL_API_KEY
        except AttributeError:
            raise AnymailImproperlyConfigured("Set MANDRILL_API_KEY in settings.py to use Anymail Mandrill backend")

        self.global_settings = {}
        try:
            self.global_settings.update(settings.MANDRILL_SETTINGS)
        except AttributeError:
            pass  # no MANDRILL_SETTINGS setting
        except (TypeError, ValueError):  # e.g., not enumerable
            raise AnymailImproperlyConfigured("MANDRILL_SETTINGS must be a dict or mapping")

        try:
            self.global_settings["subaccount"] = settings.MANDRILL_SUBACCOUNT
        except AttributeError:
            pass  # no MANDRILL_SUBACCOUNT setting

        self.ignore_recipient_status = getattr(settings, "MANDRILL_IGNORE_RECIPIENT_STATUS", False)
        self.session = None

    def build_message_payload(self, message):
        """Modify payload to add all message-specific options for Mandrill send call.

        payload is a dict that will become the Mandrill send data
        message is an EmailMessage, possibly with additional Mandrill-specific attrs

        Can raise AnymailUnsupportedFeature for unsupported options in message.
        """
        msg_dict = self._build_standard_message_dict(message)
        self._add_mandrill_options(message, msg_dict)
        if getattr(message, 'alternatives', None):
            self._add_alternatives(message, msg_dict)
        self._add_attachments(message, msg_dict)

        payload = {
            "key": self.api_key,
            "message": msg_dict,
        }
        if hasattr(message, 'template_name'):
            payload['template_name'] = message.template_name
            payload['template_content'] = \
                self._expand_merge_vars(getattr(message, 'template_content', {}))
        self._add_mandrill_toplevel_options(message, payload)
        return payload

    def get_api_url(self, payload, message):
        """Return the correct Mandrill API url for sending payload

        Override this to substitute your own logic for determining API endpoint.
        """
        if 'template_name' in payload:
            api_method = "messages/send-template.json"
        else:
            api_method = "messages/send.json"
        return urljoin(self.api_url, api_method)

    def validate_response(self, parsed_response, response, payload, message):
        """Validate parsed_response, raising exceptions for any problems.
        """
        try:
            unique_statuses = set([item["status"] for item in parsed_response])
        except (KeyError, TypeError):
            raise AnymailRequestsAPIError("Invalid Mandrill API response format",
                                          email_message=message, payload=payload, response=response)

        if unique_statuses == {"sent"}:
            return "sent"
        elif unique_statuses == {"queued"}:
            return "queued"
        elif unique_statuses.issubset({"invalid", "rejected"}):
            if self.ignore_recipient_status:
                return "refused"
            else:
                # Error if *all* recipients are invalid or refused
                # (This behavior parallels smtplib.SMTPRecipientsRefused from Django's SMTP EmailBackend)
                raise AnymailRecipientsRefused(email_message=message, payload=payload, response=response)
        else:
            return "multi"

    #
    # Payload construction
    #

    def _build_standard_message_dict(self, message):
        """Create a Mandrill send message struct from a Django EmailMessage.

        Builds the standard dict that Django's send_mail and send_mass_mail
        use by default. Standard text email messages sent through Django will
        still work through Mandrill.

        Raises AnymailUnsupportedFeature for any standard EmailMessage
        features that cannot be accurately communicated to Mandrill.
        """
        sender = sanitize_address(message.from_email, message.encoding)
        from_name, from_email = parseaddr(sender)

        to_list = self._make_mandrill_to_list(message, message.to, "to")
        to_list += self._make_mandrill_to_list(message, message.cc, "cc")
        to_list += self._make_mandrill_to_list(message, message.bcc, "bcc")

        content = "html" if message.content_subtype == "html" else "text"
        msg_dict = {
            content: message.body,
            "to": to_list
        }

        if not getattr(message, 'use_template_from', False):
            msg_dict["from_email"] = from_email
            if from_name:
                msg_dict["from_name"] = from_name

        if not getattr(message, 'use_template_subject', False):
            msg_dict["subject"] = message.subject

        if hasattr(message, 'reply_to'):
            reply_to = [sanitize_address(addr, message.encoding) for addr in message.reply_to]
            msg_dict["headers"] = {'Reply-To': ', '.join(reply_to)}
            # Note: An explicit Reply-To header will override the reply_to attr below
            # (matching Django's own behavior)

        if message.extra_headers:
            msg_dict["headers"] = msg_dict.get("headers", {})
            msg_dict["headers"].update(message.extra_headers)

        return msg_dict

    def _add_mandrill_toplevel_options(self, message, api_params):
        """Extend api_params to include Mandrill global-send options set on message"""
        # Mandrill attributes that can be copied directly:
        mandrill_attrs = [
            'async', 'ip_pool'
        ]
        for attr in mandrill_attrs:
            if attr in self.global_settings:
                api_params[attr] = self.global_settings[attr]
            if hasattr(message, attr):
                api_params[attr] = getattr(message, attr)

        # Mandrill attributes that require conversion:
        if hasattr(message, 'send_at'):
            api_params['send_at'] = self.encode_date_for_mandrill(message.send_at)
            # setting send_at in global_settings wouldn't make much sense

    def _make_mandrill_to_list(self, message, recipients, recipient_type="to"):
        """Create a Mandrill 'to' field from a list of emails.

        Parses "Real Name <address@example.com>" format emails.
        Sanitizes all email addresses.
        """
        parsed_rcpts = [parseaddr(sanitize_address(addr, message.encoding))
                        for addr in recipients]
        return [{"email": to_email, "name": to_name, "type": recipient_type}
                for (to_name, to_email) in parsed_rcpts]

    def _add_mandrill_options(self, message, msg_dict):
        """Extend msg_dict to include Mandrill per-message options set on message"""
        # Mandrill attributes that can be copied directly:
        mandrill_attrs = [
            'from_name', # overrides display name parsed from from_email above
            'important',
            'track_opens', 'track_clicks', 'auto_text', 'auto_html',
            'inline_css', 'url_strip_qs',
            'tracking_domain', 'signing_domain', 'return_path_domain',
            'merge_language',
            'tags', 'preserve_recipients', 'view_content_link', 'subaccount',
            'google_analytics_domains', 'google_analytics_campaign',
            'metadata']

        for attr in mandrill_attrs:
            if attr in self.global_settings:
                msg_dict[attr] = self.global_settings[attr]
            if hasattr(message, attr):
                msg_dict[attr] = getattr(message, attr)

        # Allow simple python dicts in place of Mandrill
        # [{name:name, value:value},...] arrays...

        # Merge global and per message global_merge_vars
        # (in conflicts, per-message vars win)
        global_merge_vars = {}
        if 'global_merge_vars' in self.global_settings:
            global_merge_vars.update(self.global_settings['global_merge_vars'])
        if hasattr(message, 'global_merge_vars'):
            global_merge_vars.update(message.global_merge_vars)
        if global_merge_vars:
            msg_dict['global_merge_vars'] = \
                self._expand_merge_vars(global_merge_vars)

        if hasattr(message, 'merge_vars'):
            # For testing reproducibility, we sort the recipients
            msg_dict['merge_vars'] = [
                { 'rcpt': rcpt,
                  'vars': self._expand_merge_vars(message.merge_vars[rcpt]) }
                for rcpt in sorted(message.merge_vars.keys())
            ]
        if hasattr(message, 'recipient_metadata'):
            # For testing reproducibility, we sort the recipients
            msg_dict['recipient_metadata'] = [
                { 'rcpt': rcpt, 'values': message.recipient_metadata[rcpt] }
                for rcpt in sorted(message.recipient_metadata.keys())
            ]

    def _expand_merge_vars(self, vardict):
        """Convert a Python dict to an array of name-content used by Mandrill.

        { name: value, ... } --> [ {'name': name, 'content': value }, ... ]
        """
        # For testing reproducibility, we sort the keys
        return [{'name': name, 'content': vardict[name]}
                for name in sorted(vardict.keys())]

    def _add_alternatives(self, message, msg_dict):
        """
        There can be only one! ... alternative attachment, and it must be text/html.

        Since mandrill does not accept image attachments or anything other
        than HTML, the assumption is the only thing you are attaching is
        the HTML output for your email.
        """
        if len(message.alternatives) > 1:
            raise AnymailUnsupportedFeature(
                "Too many alternatives attached to the message. "
                "Mandrill only accepts plain text and html emails.",
                email_message=message)

        (content, mimetype) = message.alternatives[0]
        if mimetype != 'text/html':
            raise AnymailUnsupportedFeature(
                "Invalid alternative mimetype '%s'. "
                "Mandrill only accepts plain text and html emails."
                % mimetype,
                email_message=message)

        msg_dict['html'] = content

    def _add_attachments(self, message, msg_dict):
        """Extend msg_dict to include any attachments in message"""
        if message.attachments:
            str_encoding = message.encoding or settings.DEFAULT_CHARSET
            mandrill_attachments = []
            mandrill_embedded_images = []
            for attachment in message.attachments:
                att_dict, is_embedded = self._make_mandrill_attachment(attachment, str_encoding)
                if is_embedded:
                    mandrill_embedded_images.append(att_dict)
                else:
                    mandrill_attachments.append(att_dict)
            if len(mandrill_attachments) > 0:
                msg_dict['attachments'] = mandrill_attachments
            if len(mandrill_embedded_images) > 0:
                msg_dict['images'] = mandrill_embedded_images

    def _make_mandrill_attachment(self, attachment, str_encoding=None):
        """Returns EmailMessage.attachments item formatted for sending with Mandrill.

        Returns mandrill_dict, is_embedded_image:
        mandrill_dict: {"type":..., "name":..., "content":...}
        is_embedded_image: True if the attachment should instead be handled as an inline image.

        """
        # Note that an attachment can be either a tuple of (filename, content,
        # mimetype) or a MIMEBase object. (Also, both filename and mimetype may
        # be missing.)
        is_embedded_image = False
        if isinstance(attachment, MIMEBase):
            name = attachment.get_filename()
            content = attachment.get_payload(decode=True)
            mimetype = attachment.get_content_type()
            # Treat image attachments that have content ids as embedded:
            if attachment.get_content_maintype() == "image" and attachment["Content-ID"] is not None:
                is_embedded_image = True
                name = attachment["Content-ID"]
        else:
            (name, content, mimetype) = attachment

        # Guess missing mimetype from filename, borrowed from
        # django.core.mail.EmailMessage._create_attachment()
        if mimetype is None and name is not None:
            mimetype, _ = mimetypes.guess_type(name)
        if mimetype is None:
            mimetype = DEFAULT_ATTACHMENT_MIME_TYPE

        # b64encode requires bytes, so let's convert our content.
        try:
            # noinspection PyUnresolvedReferences
            if isinstance(content, unicode):
                # Python 2.X unicode string
                content = content.encode(str_encoding)
        except NameError:
            # Python 3 doesn't differentiate between strings and unicode
            # Convert python3 unicode str to bytes attachment:
            if isinstance(content, str):
                content = content.encode(str_encoding)

        content_b64 = b64encode(content)

        mandrill_attachment = {
            'type': mimetype,
            'name': name or "",
            'content': content_b64.decode('ascii'),
        }
        return mandrill_attachment, is_embedded_image

    @classmethod
    def encode_date_for_mandrill(cls, dt):
        """Format a date or datetime for use as a Mandrill API date field

        datetime becomes "YYYY-MM-DD HH:MM:SS"
                 converted to UTC, if timezone-aware
                 microseconds removed
        date     becomes "YYYY-MM-DD 00:00:00"
        anything else gets returned intact
        """
        if isinstance(dt, datetime):
            dt = dt.replace(microsecond=0)
            if dt.utcoffset() is not None:
                dt = (dt - dt.utcoffset()).replace(tzinfo=None)
            return dt.isoformat(' ')
        elif isinstance(dt, date):
            return dt.isoformat() + ' 00:00:00'
        else:
            return dt
