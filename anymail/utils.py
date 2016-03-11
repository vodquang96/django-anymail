import mimetypes
from base64 import b64encode
from datetime import datetime
from email.mime.base import MIMEBase
from email.utils import parseaddr, formatdate
from time import mktime

import six
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.core.mail.message import sanitize_address, DEFAULT_ATTACHMENT_MIME_TYPE
from django.utils.timezone import utc


UNSET = object()  # Used as non-None default value


def combine(*args):
    """
    Combines all non-UNSET args, by shallow merging mappings and concatenating sequences

    >>> combine({'a': 1, 'b': 2}, UNSET, {'b': 3, 'c': 4}, UNSET)
    {'a': 1, 'b': 3, 'c': 4}
    >>> combine([1, 2], UNSET, [3, 4], UNSET)
    [1, 2, 3, 4]
    >>> combine({'a': 1}, None, {'b': 2})  # None suppresses earlier args
    {'b': 2}
    >>> combine()
    UNSET

    """
    result = UNSET
    for value in args:
        if value is None:
            # None is a request to suppress any earlier values
            result = UNSET
        elif value is not UNSET:
            if result is UNSET:
                try:
                    result = value.copy()  # will shallow merge if dict-like
                except AttributeError:
                    result = value  # will concatenate if sequence-like
            else:
                try:
                    result.update(value)  # shallow merge if dict-like
                except AttributeError:
                    result = result + value  # concatenate if sequence-like
    return result


def last(*args):
    """Returns the last of its args which is not UNSET.

    (Essentially `combine` without the merge behavior)

    >>> last(1, 2, UNSET, 3, UNSET, UNSET)
    3
    >>> last(1, 2, None, UNSET)  # None suppresses earlier args
    UNSET
    >>> last()
    UNSET

    """
    for value in reversed(args):
        if value is None:
            # None is a request to suppress any earlier values
            return UNSET
        elif value is not UNSET:
            return value
    return UNSET


class ParsedEmail(object):
    """A sanitized, full email address with separate name and email properties"""

    def __init__(self, address, encoding):
        self.address = sanitize_address(address, encoding)
        self._name = None
        self._email = None

    def _parse(self):
        if self._email is None:
            self._name, self._email = parseaddr(self.address)

    def __str__(self):
        return self.address

    @property
    def name(self):
        self._parse()
        return self._name

    @property
    def email(self):
        self._parse()
        return self._email


class Attachment(object):
    """A normalized EmailMessage.attachments item with additional functionality

    Normalized to have these properties:
    name: attachment filename; may be empty string
    content: bytestream
    mimetype: the content type; guessed if not explicit
    inline: bool, True if attachment has a Content-ID header
    content_id: for inline, the Content-ID (*with* <>)
    cid: for inline, the Content-ID *without* <>
    """

    def __init__(self, attachment, encoding):
        # Note that an attachment can be either a tuple of (filename, content, mimetype)
        # or a MIMEBase object. (Also, both filename and mimetype may be missing.)
        self._attachment = attachment
        self.encoding = encoding  # should we be checking attachment["Content-Encoding"] ???
        self.inline = False
        self.content_id = None
        self.cid = ""

        if isinstance(attachment, MIMEBase):
            self.name = attachment.get_filename()
            self.content = attachment.get_payload(decode=True)
            self.mimetype = attachment.get_content_type()
            # Treat image attachments that have content ids as inline:
            if attachment.get_content_maintype() == "image" and attachment["Content-ID"] is not None:
                self.inline = True
                self.content_id = attachment["Content-ID"]  # including the <...>
                self.cid = self.content_id[1:-1]  # without the <, >
        else:
            (self.name, self.content, self.mimetype) = attachment

        # Guess missing mimetype from filename, borrowed from
        # django.core.mail.EmailMessage._create_attachment()
        if self.mimetype is None and self.name is not None:
            self.mimetype, _ = mimetypes.guess_type(self.name)
        if self.mimetype is None:
            self.mimetype = DEFAULT_ATTACHMENT_MIME_TYPE

    @property
    def b64content(self):
        """Content encoded as a base64 ascii string"""
        content = self.content
        if isinstance(content, six.text_type):
            content = content.encode(self.encoding)
        return b64encode(content).decode("ascii")


def get_anymail_setting(setting, default=UNSET, allow_bare=False):
    """Returns a Django Anymail setting.

    Returns first of:
    - settings.ANYMAIL[setting]
    - settings.ANYMAIL_<setting>
    - settings.<setting> (only if allow_bare)
    - default if provided; else raises ImproperlyConfigured

    ANYMAIL = { "MAILGUN_SEND_DEFAULTS" : { ... }, ... }
    ANYMAIL_MAILGUN_SEND_DEFAULTS = { ... }

    If allow_bare, allows settings.<setting> without the ANYMAIL_ prefix:
    ANYMAIL = { "MAILGUN_API_KEY": "xyz", ... }
    ANYMAIL_MAILGUN_API_KEY = "xyz"
    MAILGUN_API_KEY = "xyz"
    """

    anymail_setting = "ANYMAIL_%s" % setting
    try:
        return settings.ANYMAIL[setting]
    except (AttributeError, KeyError):
        try:
            return getattr(settings, anymail_setting)
        except AttributeError:
            if allow_bare:
                try:
                    return getattr(settings, setting)
                except AttributeError:
                    pass
            if default is UNSET:
                message = "You must set %s or ANYMAIL = {'%s': ...}" % (anymail_setting, setting)
                if allow_bare:
                    message += " or %s" % setting
                message += " in your Django settings"
                raise ImproperlyConfigured(message)
            else:
                return default


EPOCH = datetime(1970, 1, 1, tzinfo=utc)


def timestamp(dt):
    """Return the unix timestamp (seconds past the epoch) for datetime dt"""
    # This is the equivalent of Python 3.3's datetime.timestamp
    try:
        return dt.timestamp()
    except AttributeError:
        if dt.tzinfo is None:
            return mktime(dt.timetuple())
        else:
            return (dt - EPOCH).total_seconds()


def rfc2822date(dt):
    """Turn a datetime into a date string as specified in RFC 2822."""
    # This is almost the equivalent of Python 3.3's email.utils.format_datetime,
    # but treats naive datetimes as local rather than "UTC with no information ..."
    timeval = timestamp(dt)
    return formatdate(timeval, usegmt=True)
