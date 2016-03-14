Installation and configuration
==============================

.. _installation:

Installing Anymail
------------------

It's easiest to install Anymail from PyPI using pip.

    .. code-block:: console

        $ pip install django-anymail

If you don't want to use pip, you'll also need to install Anymail's
dependencies (requests and six).


.. _backend-configuration:

Configuring Django's email backend
----------------------------------

To use Anymail for sending email, edit your Django project's :file:`settings.py`:

1. Add :mod:`anymail` to your :setting:`INSTALLED_APPS`:

    .. code-block:: python

        INSTALLED_APPS = (
            ...
            "anymail",
        )

2. Add an :setting:`ANYMAIL` settings dict, substituting the appropriate settings for
   your ESP:

    .. code-block:: python

        ANYMAIL = {
            "MAILGUN_API_KEY" = "<your Mailgun key>",
        }

3. Change your existing Django :setting:`EMAIL_BACKEND` to the Anymail backend
   for your ESP. For example, to send using Mailgun by default:

    .. code-block:: python

        EMAIL_BACKEND = "anymail.backends.mailgun.MailgunBackend"

   (:setting:`EMAIL_BACKEND` sets Django's default for sending emails; you can also
   use :ref:`multiple Anymail backends <multiple-backends>` to send particular
   messages through different ESPs.)

   The exact backend name and required settings vary by ESP.
   See the :ref:`supported ESPs <supported-esps>` section for specifics.

Also, if you don't already have a :setting:`DEFAULT_FROM_EMAIL` in your settings,
this is a good time to add one. (Django's default is "webmaster\@localhost",
which some ESPs will reject.)


Configuring status tracking webhooks
------------------------------------

Anymail can optionally connect to your ESPs event webhooks to notify your app
of status like bounced and rejected emails, successful delivery, message opens
and clicks, and other tracking.

If you want to use Anymail's status tracking webhooks, follow the steps above
to :ref:`configure an Anymail backend <backend-configuration>`, and then
follow the instructions in the :ref:`event-tracking` section to set up
the delivery webhooks.


Configuring inbound email
-------------------------

Anymail can optionally connect to your ESPs inbound webhook to notify your app
of inbound messages.

If you want to use inbound email with Anymail, first follow the first two
:ref:`backend configuration <backend-configuration>` steps above. (You can
skip changing your :setting:`EMAIL_BACKEND` if you don't want to us Anymail
for *sending* messages.) Then follow the instructions in the
:ref:`inbound-webhooks` section to set up the inbound webhooks.



.. setting:: ANYMAIL

Anymail settings reference
--------------------------

You can add Anymail settings to your project's :file:`settings.py` either as
a single ``ANYMAIL`` dict, or by breaking out individual settings prefixed with
``ANYMAIL_``. So this settings dict:

    .. code-block:: python

        ANYMAIL = {
            "MAILGUN_API_KEY": "12345",
            "SEND_DEFAULTS": {
                "tags": ["myapp"]
            },
        }

...is equivalent to these individual settings:

    .. code-block:: python

        ANYMAIL_MAILGUN_API_KEY = "12345"
        ANYMAIL_SEND_DEFAULTS = {"tags": ["myapp"]}

In addition, for some ESP settings like API keys, Anymail will look for a setting
without the ``ANYMAIL_`` prefix if it can't find the Anymail one. (This can be helpful
if you are using other Django apps that work with the same ESP.)

    .. code-block:: python

        MAILGUN_API_KEY = "12345"  # used only if neither ANYMAIL["MAILGUN_API_KEY"]
                                   # nor ANYMAIL_MAILGUN_API_KEY have been set


There are specific Anymail settings for each ESP (like API keys and urls).
See the :ref:`supported ESPs <supported-esps>` section for details.
Here are the other settings Anymail supports:


.. setting:: ANYMAIL_IGNORE_RECIPIENT_STATUS

.. rubric:: IGNORE_RECIPIENT_STATUS

Set to `True` to disable :exc:`AnymailRecipientsRefused` exceptions
on invalid or rejected recipients. (Default `False`.)
See :ref:`recipients-refused`.

  .. code-block:: python

      ANYMAIL = {
          ...
          "IGNORE_RECIPIENT_STATUS": True,
      }


.. rubric:: SEND_DEFAULTS and *ESP*\ _SEND_DEFAULTS`

A `dict` of default options to apply to all messages sent through Anymail.
See :ref:`send-defaults`.


.. rubric:: IGNORE_UNSUPPORTED_FEATURES

Whether Anymail should raise :exc:`~anymail.exceptions.AnymailUnsupportedFeature`
errors for email with features that can't be accurately communicated to the ESP.
Set to `True` to ignore these problems and send the email anyway. See
:ref:`unsupported-features`. (Default `False`.)
