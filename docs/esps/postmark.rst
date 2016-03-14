.. _postmark-backend:

Postmark
========

Anymail integrates with the `Postmark`_ transactional email service,
using their `HTTP email API`_.

.. _Postmark: https://postmarkapp.com/
.. _HTTP email API: http://developer.postmarkapp.com/developer-api-email.html


Settings
--------

.. rubric:: EMAIL_BACKEND

To use Anymail's Postmark backend, set:

  .. code-block:: python

      EMAIL_BACKEND = "anymail.backends.postmark.PostmarkBackend"

in your settings.py. (Watch your capitalization: Postmark spells their name with a
lowercase "m", so Anymail does too.)


.. setting:: ANYMAIL_POSTMARK_SERVER_TOKEN

.. rubric:: POSTMARK_SERVER_TOKEN

Required. A Postmark server token.

  .. code-block:: python

      ANYMAIL = {
          ...
          "POSTMARK_SERVER_TOKEN": "<your server token>",
      }

Anymail will also look for ``POSTMARK_SERVER_TOKEN`` at the
root of the settings file if neither ``ANYMAIL["POSTMARK_SERVER_TOKEN"]``
nor ``ANYMAIL_POSTMARK_SERVER_TOKEN`` is set.

You can override the server token for an individual message in
its :ref:`esp_extra <postmark-esp-extra>`.


.. setting:: ANYMAIL_POSTMARK_API_URL

.. rubric:: POSTMARK_API_URL

The base url for calling the Postmark API.

The default is ``POSTMARK_API_URL = "https://api.postmarkapp.com/"``
(It's unlikely you would need to change this.)


.. _postmark-esp-extra:

esp_extra support
-----------------

To use Postmark features not directly supported by Anymail, you can
set a message's :attr:`~anymail.message.AnymailMessage.esp_extra` to
a `dict` that will be merged into the json sent to Postmark's
`email API`_.

Example:

    .. code-block:: python

        message.esp_extra = {
            'HypotheticalFuturePostmarkParam': '2022',  # merged into send params
            'server_token': '<API server token for just this message>',
        }


(You can also set `"esp_extra"` in Anymail's
:ref:`global send defaults <send-defaults>` to apply it to all
messages.)


.. _email API: http://developer.postmarkapp.com/developer-api-email.html


Limitations and quirks
----------------------

Postmark has excellent support for standard email functionality, but does
not support all the tracking and reporting additions offered by some other
ESPs.

Anymail normally raises an :exc:`~anymail.exceptions.AnymailUnsupportedFeature`
error when you try to send a message using features that Postmark doesn't support
You can tell Anymail to suppress these errors and send the messages anyway --
see :ref:`unsupported-features`.

**Single tag**
  Postmark allows a maximum of one tag per message. If your message has two or more
  :attr:`~anymail.message.AnymailMessage.tags`, you'll get an
  :exc:`~anymail.exceptions.AnymailUnsupportedFeature` error---or
  if you've enabled :setting:`ANYMAIL_IGNORE_UNSUPPORTED_FEATURES`,
  Anymail will use only the first tag.

**No metadata**
  Postmark does not support attaching :attr:`~anymail.message.AnymailMessage.metadata`
  to messages.

**No click-tracking**
  Postmark supports :attr:`~anymail.message.AnymailMessage.track_open`,
  but not :attr:`~anymail.message.AnymailMessage.track_clicks`.

**No delayed sending**
  Postmark does not support :attr:`~anymail.message.AnymailMessage.send_at`.
