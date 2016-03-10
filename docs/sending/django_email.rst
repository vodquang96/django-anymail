.. currentmodule:: anymail

.. _sending-django-email:

Django email support
====================

Anymail builds on Django's core email functionality. If you are already sending
email using Django's default SMTP :class:`~django.core.mail.backends.smtp.EmailBackend`,
switching to Anymail will be easy. Anymail is designed to "just work" with Django.

If you're not familiar with Django's email functions, please take a look at
":mod:`sending email <django.core.mail>`" in the Django docs first.

Anymail supports most of the functionality of Django's :class:`~django.core.mail.EmailMessage`
and :class:`~django.core.mail.EmailMultiAlternatives` classes.

Anymail handles **all** outgoing email sent through Django's
:mod:`django.core.mail` package, including :func:`~django.core.mail.send_mail`,
:func:`~django.core.mail.send_mass_mail`, the :class:`~django.core.mail.EmailMessage` class,
and even :func:`~django.core.mail.mail_admins`.
If you'd like to selectively send only some messages through Anymail,
or you'd like to use different ESPs for particular messages,
there are ways to use :ref:`multiple email backends <multiple-backends>`.


.. _sending-html:

HTML email
----------

To send an HTML message, you can simply use Django's :func:`~django.core.mail.send_mail`
function with the ``html_message`` parameter:

    .. code-block:: python

        from django.core.mail import send_mail

        send_mail("Subject", "text body", "from@example.com",
                  ["to@example.com"], html_message="<html>html body</html>")

However, many Django email capabilities -- and additional Anymail features --
are only available when working with an :class:`~django.core.mail.EmailMultiAlternatives`
object. Use its :meth:`~django.core.mail.EmailMultiAlternatives.attach_alternative`
method to send HTML:

    .. code-block:: python

        from django.core.mail import EmailMultiAlternatives

        msg = EmailMultiAlternatives("Subject", "text body",
                                     "from@example.com", ["to@example.com"])
        msg.attach_alternative("<html>html body</html>", "text/html")
        # you can set any other options on msg here, then...
        msg.send()

It's good practice to send equivalent content in your plain-text body
and the html version.


.. _sending-attachments:

Attachments
-----------

Anymail will send a message's attachments to your ESP. You can add attachments
with the :meth:`~django.core.mail.EmailMessage.attach` or
:meth:`~django.core.mail.EmailMessage.attach_file` methods
of Django's :class:`~django.core.mail.EmailMessage`.

Note that some ESPs impose limits on the size and type of attachments they
will send.

.. rubric:: Inline images

If your message has any image attachments with :mailheader:`Content-ID` headers,
Anymail will tell your ESP to treat them as inline images rather than ordinary
attached files.

You can construct an inline image attachment yourself with Python's
:class:`python:email.mime.image.MIMEImage`, or you can use the convenience
function :func:`~message.attach_inline_image` included with
Anymail. See :ref:`inline-images` in the "Anymail additions" section.


.. _message-headers:

Additional headers
------------------

Anymail passes additional headers to your ESP. (Some ESPs may limit
which headers they'll allow.)

    .. code-block:: python

        msg = EmailMessage( ...
            headers={
                "List-Unsubscribe": unsubscribe_url,
                "X-Example-Header": "myapp",
            }
        )


.. _unsupported-features:

Unsupported features
--------------------

Some email capabilities aren't supported by all ESPs. When you try to send a
message using features Anymail can't communicate to the current ESP, you'll get an
:exc:`~exceptions.AnymailUnsupportedFeature` error, and the message won't be sent.

For example, very few ESPs support alternative message parts added with
:meth:`~django.core.mail.EmailMultiAlternatives.attach_alternative`
(other than a single :mimetype:`text/html` part that becomes the HTML body).
If you try to send a message with other alternative parts, Anymail will
raise :exc:`~exceptions.AnymailUnsupportedFeature`.

.. setting:: ANYMAIL_UNSUPPORTED_FEATURE_ERRORS

If you'd like to silently ignore :exc:`~exceptions.AnymailUnsupportedFeature`
errors and send the messages anyway, set :setting:`!ANYMAIL_UNSUPPORTED_FEATURE_ERRORS`
to `False` in your settings.py:

  .. code-block:: python

      ANYMAIL = {
          ...
          "UNSUPPORTED_FEATURE_ERRORS": False,
      }


.. _recipients-refused:

Refused recipients
------------------

If *all* recipients (to, cc, bcc) of a message are invalid or rejected by
your ESP *at send time,* the send call will raise an
:exc:`~exceptions.AnymailRecipientsRefused` error.

You can examine the message's :attr:`~message.AnymailMessage.anymail_status`
attribute to determine the cause of the error. (See :ref:`esp-send-status`.)

If a single message is sent to multiple recipients, and *any* recipient is valid
(or the message is queued by your ESP because of rate limiting or
:attr:`~message.AnymailMessage.send_at`), then this exception will not be raised.
You can still examine the message's :attr:`~message.AnymailMessage.anymail_status`
property after the send to determine the status of each recipient.

You can disable this exception by setting :setting:`ANYMAIL_IGNORE_RECIPIENT_STATUS`
to `True` in your settings.py, which will cause Anymail to treat any non-API-error response
from your ESP as a successful send.

.. note::

    Many ESPs don't check recipient status during the send API call. For example,
    Mailgun always queues sent messages, so you'll never catch
    :exc:`AnymailRecipientsRefused` with the Mailgun backend.

    For those ESPs, use Anymail's :ref:`delivery event tracking <event-tracking>`
    if you need to be notified of sends to blacklisted or invalid emails.
