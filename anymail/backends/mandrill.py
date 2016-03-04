from datetime import date, datetime
try:
    from urlparse import urljoin  # python 2
except ImportError:
    from urllib.parse import urljoin  # python 3

from django.conf import settings

from ..exceptions import (AnymailImproperlyConfigured, AnymailRequestsAPIError,
                          AnymailRecipientsRefused, AnymailUnsupportedFeature)

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

        # Djrill compat! MANDRILL_SETTINGS
        try:
            self.send_defaults.update(settings.MANDRILL_SETTINGS)
        except AttributeError:
            pass  # no MANDRILL_SETTINGS setting
        except (TypeError, ValueError):  # e.g., not enumerable
            raise AnymailImproperlyConfigured("MANDRILL_SETTINGS must be a dict or mapping")

        # Djrill compat! MANDRILL_SUBACCOUNT
        try:
            self.send_defaults["subaccount"] = settings.MANDRILL_SUBACCOUNT
        except AttributeError:
            pass  # no MANDRILL_SUBACCOUNT setting

        self.global_settings = self.send_defaults
        self.ignore_recipient_status = getattr(settings, "MANDRILL_IGNORE_RECIPIENT_STATUS", False)
        self.session = None

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

    def get_base_payload(self, message):
        return {
            "key": self.api_key,
            "message": {},
        }

    def set_payload_from_email(self, payload, email, message):
        if not getattr(message, "use_template_from", False):  # Djrill compat!
            payload["message"]["from_email"] = email.email
            if email.name:
                payload["message"]["from_name"] = email.name

    def add_payload_recipient(self, payload, recipient_type, email, message):
        assert recipient_type in ["to", "cc", "bcc"]
        to_list = payload["message"].setdefault("to", [])
        to_list.append({"email": email.email, "name": email.name, "type": recipient_type})

    def set_payload_subject(self, payload, subject, message):
        if not getattr(message, "use_template_subject", False):  # Djrill compat!
            payload["message"]["subject"] = subject

    def set_payload_reply_to(self, payload, emails, message):
        reply_to = ", ".join([email.address for email in emails])
        payload["message"].setdefault("headers", {})["Reply-To"] = reply_to

    def add_payload_headers(self, payload, headers, message):
        payload["message"].setdefault("headers", {}).update(headers)

    def set_payload_text_body(self, payload, body, message):
        payload["message"]["text"] = body

    def set_payload_html_body(self, payload, body, message):
        payload["message"]["html"] = body

    def add_payload_alternative(self, payload, content, mimetype, message):
        if mimetype != 'text/html':
            raise AnymailUnsupportedFeature(
                "Invalid alternative mimetype '%s'. "
                "Mandrill only accepts plain text and html emails."
                % mimetype,
                email_message=message)

        if "html" in payload["message"]:
            raise AnymailUnsupportedFeature(
                "Too many alternatives attached to the message. "
                "Mandrill only accepts plain text and html emails.",
                email_message=message)

        payload["message"]["html"] = content

    def add_payload_attachment(self, payload, attachment, message):
        key = "images" if attachment.inline else "attachments"
        payload["message"].setdefault(key, []).append({
            "type": attachment.mimetype,
            "name": attachment.name or "",
            "content": attachment.b64content
        })

    def set_payload_metadata(self, payload, metadata, message):
        payload["message"]["metadata"] = metadata

    def set_payload_send_at(self, payload, send_at, message):
        payload["send_at"] = self.encode_date_for_mandrill(send_at)

    def set_payload_tags(self, payload, tags, message):
        payload["message"]["tags"] = tags

    def set_payload_track_clicks(self, payload, track_clicks, message):
        payload["message"]["track_clicks"] = track_clicks

    def set_payload_track_opens(self, payload, track_opens, message):
        payload["message"]["track_opens"] = track_opens

    def add_payload_esp_options(self, payload, message):
        self._add_mandrill_options(message, payload["message"])
        if hasattr(message, 'template_name'):
            payload['template_name'] = message.template_name
            payload['template_content'] = \
                self._expand_merge_vars(getattr(message, 'template_content', {}))
        self._add_mandrill_toplevel_options(message, payload)

    # unported

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

    def _add_mandrill_options(self, message, msg_dict):
        """Extend msg_dict to include Mandrill per-message options set on message"""
        # Mandrill attributes that can be copied directly:
        mandrill_attrs = [
            'from_name', # overrides display name parsed from from_email above
            'important',
            'auto_text', 'auto_html',
            'inline_css', 'url_strip_qs',
            'tracking_domain', 'signing_domain', 'return_path_domain',
            'merge_language',
            'preserve_recipients', 'view_content_link', 'subaccount',
            'google_analytics_domains', 'google_analytics_campaign',
        ]

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
