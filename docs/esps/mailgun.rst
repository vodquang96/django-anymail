.. _mailgun-backend:

Mailgun
=======

Anymail integrates with the `Mailgun <https://mailgun.com>`_
transactional email service from Rackspace, using their
REST API.


Settings
--------

.. rubric:: EMAIL_BACKEND

To use Anymail's Mailgun backend, set:

  .. code-block:: python

      EMAIL_BACKEND = "anymail.backends.mailgun.MailgunBackend"

in your settings.py. (Watch your capitalization: Mailgun spells their name with a
lowercase "g", so Anymail does too.)


.. setting:: ANYMAIL_MAILGUN_API_KEY

.. rubric:: MAILGUN_API_KEY

Required. Your Mailgun API key:

  .. code-block:: python

      ANYMAIL = {
          ...
          "MAILGUN_API_KEY": "<your API key>",
      }

Anymail will also look for ``MAILGUN_API_KEY`` at the
root of the settings file if neither ``ANYMAIL["MAILGUN_API_KEY"]``
nor ``ANYMAIL_MAILGUN_API_KEY`` is set.


.. setting:: ANYMAIL_MAILGUN_API_URL

.. rubric:: MAILGUN_API_URL

The base url for calling the Mailgun API. It does not include
the sender domain. (Anymail :ref:`figures this out <mailgun-sender-domain>`
for you.)

The default is ``MAILGUN_API_URL = "https://api.mailgun.net/v3"``
(It's unlikely you would need to change this.)


.. _mailgun-sender-domain:

Email sender domain
-------------------

Mailgun's API requires a sender domain `in the API url <base-url>`_.
By default, Anymail will use the domain of each email's from address
as the domain for the Mailgun API.

If you need to override this default, you can use Anymail's
:attr:`esp_extra` dict, either on an individual message:

    .. code-block:: python

        message = EmailMessage(from_email="sales@europe.example.com", ...)
        message.esp_extra = {"sender_domain": "example.com"}


... or as a global :ref:`send default <send-defaults>` setting that applies
to all messages:

    .. code-block:: python

        ANYMAIL = {
            ...
            "MAILGUN_SEND_DEFAULTS": {
                "esp_extra": {"sender_domain": "example.com"}
            }
        }

.. _base-url: https://documentation.mailgun.com/api-intro.html#base-url


.. _mailgun-esp-extra:

exp_extra support
-----------------

Anymail's Mailgun backend will pass all :attr:`~anymail.message.AnymailMessage.esp_extra`
values directly to Mailgun. You can use any of the (non-file) parameters listed in the
`Mailgun sending docs`_. Example:

  .. code-block:: python

      message = AnymailMessage(...)
      message.esp_extra = {
          'o:testmode': 'yes',  # use Mailgun's test mode
      }

.. _Mailgun sending docs: https://documentation.mailgun.com/api-sending.html#sending
