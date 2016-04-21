.. _mandrill-backend:

Mandrill
========

Anymail integrates with the `Mandrill <http://mandrill.com/>`_
transactional email service from MailChimp.

.. note:: **Limited Support for Mandrill**

    Anymail is developed to the public Mandrill documentation, but unlike
    other supported ESPs, we are unable to test or debug against the live
    Mandrill APIs. (MailChimp discourages use of Mandrill by "developers,"
    and doesn't offer testing access for packages like Anymail.)

    As a result, Anymail bugs with Mandrill will generally be discovered
    by Anymail's users, in production; Anymail's maintainers often won't
    be able to answer Mandrill-specific questions; and fixes and improvements
    for Mandrill will tend to lag other ESPs.

    If you are integrating only Mandrill, and not considering one of Anymail's
    other ESPs, you might prefer using MailChimp's official
    `mandrill <https://pypi.python.org/pypi/mandrill/>`_ python package
    instead of Anymail.


Settings
--------

.. rubric:: EMAIL_BACKEND

To use Anymail's Mandrill backend, set:

  .. code-block:: python

      EMAIL_BACKEND = "anymail.backends.mandrill.MandrillBackend"

in your settings.py.


.. setting:: ANYMAIL_MANDRILL_API_KEY

.. rubric:: MANDRILL_API_KEY

Required. Your Mandrill API key:

  .. code-block:: python

      ANYMAIL = {
          ...
          "MANDRILL_API_KEY": "<your API key>",
      }

Anymail will also look for ``MANDRILL_API_KEY`` at the
root of the settings file if neither ``ANYMAIL["MANDRILL_API_KEY"]``
nor ``ANYMAIL_MANDRILL_API_KEY`` is set.


.. setting:: ANYMAIL_MANDRILL_WEBHOOK_KEY

.. rubric:: MANDRILL_WEBHOOK_KEY

Required if using Anymail's webhooks. The "webhook authentication key"
issued by Mandrill.
`More info <https://mandrill.zendesk.com/hc/en-us/articles/205583257>`_
in Mandrill's KB.


.. setting:: ANYMAIL_MANDRILL_WEBHOOK_URL

.. rubric:: MANDRILL_WEBHOOK_URL

Required only if using Anymail's webhooks *and* the hostname your
Django server sees is different from the public webhook URL
you provided Mandrill. (E.g., if you have a proxy in front
of your Django server that forwards
"https\://yoursite.example.com" to "http\://localhost:8000/").

If you are seeing :exc:`AnymailWebhookValidationFailure` errors
from your webhooks, set this to the exact webhook URL you entered
in Mandrill's settings.


.. setting:: ANYMAIL_MANDRILL_API_URL

.. rubric:: MANDRILL_API_URL

The base url for calling the Mandrill API. The default is
``MANDRILL_API_URL = "https://mandrillapp.com/api/1.0"``,
which is the secure, production version of Mandrill's 1.0 API.

(It's unlikely you would need to change this.)


.. _mandrill-esp-extra:

esp_extra support
-----------------

Anymail's Mandrill backend does not yet implement the
:attr:`~anymail.message.AnymailMessage.esp_extra` feature.


.. _mandrill-webhooks:

Status tracking webhooks
------------------------

If you are using Anymail's normalized :ref:`status tracking <event-tracking>`,
follow `Mandrill's instructions`_ to add Anymail's webhook URL:

   :samp:`https://{random}:{random}@{yoursite.example.com}/anymail/mandrill/tracking/`

     * *random:random* is an :setting:`ANYMAIL_WEBHOOK_AUTHORIZATION` shared secret
     * *yoursite.example.com* is your Django site

Be sure to check the boxes in the Mandrill settings for the event types you want to receive.
The same Anymail tracking URL can handle all Mandrill "message" and "sync" events.

Mandrill implements webhook signing on the entire event payload, and Anymail will
verify the signature. You must set :setting:`ANYMAIL_MANDRILL_WEBHOOK_KEY` to the
webhook key authentication key issued by Mandrill. You may also need to set
:setting:`ANYMAIL_MANDRILL_WEBHOOK_URL` depending on your server config.

Mandrill will report these Anymail :attr:`~anymail.signals.AnymailTrackingEvent.event_type`\s:
sent, rejected, deferred, bounced, opened, clicked, complained, unsubscribed. Mandrill does
not support delivered events. Mandrill "whitelist" and "blacklist" sync events will show up
as Anymail's unknown event_type.

The event's :attr:`~anymail.signals.AnymailTrackingEvent.esp_event` field will be
a `dict` of Mandrill event fields, for a single event. (Although Mandrill calls
webhooks with batches of events, Anymail will invoke your signal receiver separately
for each event in the batch.)

.. _Mandrill's instructions:
    https://mandrill.zendesk.com/hc/en-us/articles/205583217-Introduction-to-Webhooks


.. _migrating-from-djrill:

Migrating from Djrill
---------------------

Anymail has its origins as a fork of the `Djrill`_
package, which supported only Mandrill. If you are migrating
from Djrill to Anymail -- e.g., because you are thinking
of switching ESPs -- you'll need to make a few changes
to your code.

.. _Djrill: https://github.com/brack3t/Djrill

Changes to settings
~~~~~~~~~~~~~~~~~~~

``MANDRILL_API_KEY``
  Will still work, but consider moving it into the :setting:`ANYMAIL`
  settings dict, or changing it to :setting:`ANYMAIL_MANDRILL_API_KEY`.

``MANDRILL_SETTINGS``
  Use :setting:`ANYMAIL_SEND_DEFAULTS` and/or :setting:`ANYMAIL_MANDRILL_SEND_DEFAULTS`
  (see :ref:`send-defaults`).

  There is one slight behavioral difference between :setting:`ANYMAIL_SEND_DEFAULTS`
  and Djrill's ``MANDRILL_SETTINGS``: in Djrill, setting :attr:`tags` or
  :attr:`merge_vars` on a message would completely override any global
  settings defaults. In Anymail, those message attributes are merged with
  the values from :setting:`ANYMAIL_SEND_DEFAULTS`.

``MANDRILL_SUBACCOUNT``
  Use :setting:`ANYMAIL_MANDRILL_SEND_DEFAULTS`:

    .. code-block:: python

        ANYMAIL = {
            ...
            "MANDRILL_SEND_DEFAULTS": {
                "subaccount": "<your subaccount>"
            }
        }

``MANDRILL_IGNORE_RECIPIENT_STATUS``
  Renamed to :setting:`ANYMAIL_IGNORE_RECIPIENT_STATUS`
  (or just `IGNORE_RECIPIENT_STATUS` in the :setting:`ANYMAIL`
  settings dict).

``DJRILL_WEBHOOK_SECRET`` and ``DJRILL_WEBHOOK_SECRET_NAME``
  Replaced with HTTP basic auth. See :ref:`securing-webhooks`.

``DJRILL_WEBHOOK_SIGNATURE_KEY``
  Use :setting:`ANYMAIL_MANDRILL_WEBHOOK_KEY` instead.

``DJRILL_WEBHOOK_URL``
  Use :setting:`ANYMAIL_MANDRILL_WEBHOOK_URL`, or eliminate if
  your Django server is not behind a proxy that changes hostnames.


Changes to EmailMessage attributes
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

``message.send_at``
  If you are using an aware datetime for :attr:`send_at`,
  it will keep working unchanged with Anymail.

  If you are using a date (without a time), or a naive datetime,
  be aware that these now default to Django's current_timezone,
  rather than UTC as in Djrill.

  (As with Djrill, it's best to use an aware datetime
  that says exactly when you want the message sent.)


``message.mandrill_response``
  Anymail normalizes ESP responses, so you don't have to be familiar
  with the format of Mandrill's JSON. See :attr:`anymail_status`.

  The *raw* ESP response is attached to a sent message as
  ``anymail_status.esp_response``, so the direct replacement
  for message.mandrill_response is:

    .. code-block:: python

        mandrill_response = message.anymail_status.esp_response.json()

**Templates and merge variables**
  Coming to Anymail soon.

  However, no other ESPs support MailChimp's templating language, so
  you'll need to rewrite your templates as you switch ESPs.

  Consider converting to :ref:`Django templates <django-templates>`
  instead, as these can be used with any email backend.

**Other Mandrill-specific attributes**
  Are currently still supported by Anymail's Mandrill backend,
  but will be ignored by other Anymail backends.

  It's best to eliminate them if they're not essential
  to your code. In the future, the Mandrill-only attributes
  will be moved into the
  :attr:`~anymail.message.AnymailMessage.esp_extra` dict.

**Inline images**
  Djrill (incorrectly) used the presence of a :mailheader:`Content-ID`
  header to decide whether to treat an image as inline. Anymail
  looks for :mailheader:`Content-Disposition: inline`.

  If you were constructing MIMEImage inline image attachments
  for your Djrill messages, in addition to setting the Content-ID,
  you should also add::

      image.add_header('Content-Disposition', 'inline')

  Or better yet, use Anymail's new :ref:`inline-images`
  helper functions to attach your inline images.


Changes to webhooks
~~~~~~~~~~~~~~~~~~~

Anymail uses HTTP basic auth as a shared secret for validating webhook
calls, rather than Djrill's "secret" query parameter. See
:ref:`securing-webhooks`. (A slight advantage of basic auth over query
parameters is that most logging and analytics systems are aware of the
need to keep auth secret.)

Anymail replaces `djrill.signals.webhook_event` with
`anymail.signals.tracking` and (in a future release)
`anymail.signals.inbound`. Anymail parses and normalizes
the event data passed to the signal receiver: see :ref:`event-tracking`.

The equivalent of Djrill's ``data`` parameter is available
to your signal receiver as
:attr:`event.esp_event <anymail.signals.AnymailTrackingEvent.esp_event>`,
and for most events, the equivalent of Djrill's ``event_type`` parameter
is `event.esp_event['event']`. But consider working with Anymail's
normalized :class:`~anymail.signals.AnymailTrackingEvent` instead.
