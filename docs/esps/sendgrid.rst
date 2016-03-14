.. _sendgrid-backend:

SendGrid
========

Anymail integrates with the `SendGrid`_ email service,
using their `Web API v2`_. (Their v3 API does not support sending mail,
but the v3 API calls *do* get information about mail sent through v2.)

.. _SendGrid: https://sendgrid.com/
.. _Web API v2: https://sendgrid.com/docs/API_Reference/Web_API/mail.html


Settings
--------


.. rubric:: EMAIL_BACKEND

To use Anymail's SendGrid backend, set:

  .. code-block:: python

      EMAIL_BACKEND = "anymail.backends.sendgrid.SendGridBackend"

in your settings.py. (Watch your capitalization: SendGrid spells
their name with an uppercase "G", so Anymail does too.)


.. setting:: ANYMAIL_SENDGRID_API_KEY

.. rubric:: SENDGRID_API_KEY

A SendGrid API key with "Mail Send" permission.
(Manage API keys in your `SendGrid API key settings`_.)
Either an API key or both :setting:`SENDGRID_USERNAME <ANYMAIL_SENDGRID_USERNAME>`
and :setting:`SENDGRID_PASSWORD <ANYMAIL_SENDGRID_PASSWORD>` are required.

  .. code-block:: python

      ANYMAIL = {
          ...
          "SENDGRID_API_KEY": "<your API key>",
      }

Anymail will also look for ``SENDGRID_API_KEY`` at the
root of the settings file if neither ``ANYMAIL["SENDGRID_API_KEY"]``
nor ``ANYMAIL_SENDGRID_API_KEY`` is set.

.. _SendGrid API key settings: https://app.sendgrid.com/settings/api_keys


.. setting:: ANYMAIL_SENDGRID_USERNAME
.. setting:: ANYMAIL_SENDGRID_PASSWORD

.. rubric:: SENDGRID_USERNAME and SENDGRID_PASSWORD

SendGrid credentials with the "Mail" permission. You should **not**
use the username/password that you use to log into SendGrid's
dashboard. Create credentials specifically for sending mail in the
`SendGrid credentials settings`_.

  .. code-block:: python

      ANYMAIL = {
          ...
          "SENDGRID_USERNAME": "<sendgrid credential with Mail permission>",
          "SENDGRID_PASSWORD": "<password for that credential>",
      }

Either username/password or :setting:`SENDGRID_API_KEY <ANYMAIL_SENDGRID_API_KEY>`
are required (but not both).

Anymail will also look for ``SENDGRID_USERNAME`` and ``SENDGRID_PASSWORD`` at the
root of the settings file if neither ``ANYMAIL["SENDGRID_USERNAME"]``
nor ``ANYMAIL_SENDGRID_USERNAME`` is set.

.. _SendGrid credentials settings: https://app.sendgrid.com/settings/credentials


.. setting:: ANYMAIL_SENDGRID_API_URL

.. rubric:: SENDGRID_API_URL

The base url for calling the SendGrid v2 API.

The default is ``SENDGRID_API_URL = "https://api.sendgrid.com/api/"``
(It's unlikely you would need to change this.)


.. _sendgrid-esp-extra:

esp_extra support
-----------------

To use SendGrid features not directly supported by Anymail, you can
set a message's :attr:`~anymail.message.AnymailMessage.esp_extra` to
a `dict` of parameters for SendGrid's `mail.send API`_. Any keys in
your :attr:`esp_extra` dict will override Anymail's normal values
for that parameter, except that `'x-smtpapi'` will be merged.

Example:

    .. code-block:: python

        message.esp_extra = {
            'x-smtpapi': {
                "asm_group": 1,  # Assign SendGrid unsubscribe group for this message
                "asm_groups_to_display": [1, 2, 3]
            }
        }


(You can also set `"esp_extra"` in Anymail's
:ref:`global send defaults <send-defaults>` to apply it to all
messages.)


.. _mail.send API: https://sendgrid.com/docs/API_Reference/Web_API/mail.html#-send



Limitations and quirks
----------------------

**Duplicate attachment filenames**
  Anymail is not capable of communicating multiple attachments with
  the same filename to SendGrid. (This also applies to multiple attachments
  with *no* filename, though not to inline images.)

  If you are sending multiple attachments on a single message,
  make sure each one has a unique, non-empty filename.


**Message-ID**
  SendGrid does not return any sort of unique id from its send API call.
  Knowing a sent message's ID can be important for later queries about
  the message's status.

  To work around this, Anymail generates a new Message-ID for each
  outgoing message, provides it to SendGrid, and includes it in the
  :attr:`~anymail.message.AnymailMessage.anymail_status`
  attribute after you send the message.

  In later SendGrid API calls, you can match that Message-ID
  to SendGrid's ``smtp-id`` event field.

  Anymail will use the domain of the message's :attr:`from_email`
  to generate the Message-ID. (If this isn't desired, you can supply
  your own Message-ID in the message's :attr:`extra_headers`.)


**Invalid Addresses**
  SendGrid will accept *and send* just about anything as
  a message's :attr:`from_email`. (And email protocols are
  actually OK with that.)

  (Tested March, 2016)
