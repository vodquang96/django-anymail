.. _mandrill-backend:

Mandrill
--------

Anymail integrates with the `Mandrill <http://mandrill.com/>`_
transactional email service from MailChimp.


Settings
========

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


.. setting:: ANYMAIL_MANDRILL_API_URL

.. rubric:: MANDRILL_API_URL

The base url for calling the Mandrill API. The default is
``MANDRILL_API_URL = "https://mandrillapp.com/api/1.0"``,
which is the secure, production version of Mandrill's 1.0 API.

(It's unlikely you would need to change this.)


Mandrill esp_extra
==================

Anymail's Mandrill backend does not yet implement the
:attr:`~anymail.message.AnymailMessage.esp_extra` feature.


.. _migrating-from-djrill:

Migrating from Djrill
=====================

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
  Use :attr:`esp_extra` in :setting:`ANYMAIL_MANDRILL_SEND_DEFAULTS`:

    .. code-block:: python

        ANYMAIL = {
            ...
            "MANDRILL_SEND_DEFAULTS": {
                "esp_extra": {"subaccount": "<your subaccount>"}
            }
        }

``MANDRILL_IGNORE_RECIPIENT_STATUS``
  Renamed to :setting:`ANYMAIL_IGNORE_RECIPIENT_STATUS`
  (or just `IGNORE_RECIPIENT_STATUS` in the :setting:`ANYMAIL`
  settings dict).


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
