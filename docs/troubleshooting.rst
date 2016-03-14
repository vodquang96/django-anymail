.. _troubleshooting:

Troubleshooting
===============

Anymail throwing errors? Not sending what you want? Here are some tips...


Figuring out what's wrong
-------------------------

**Check the error message**

  Look for an Anymail error message in your
  web browser or console (running Django in dev mode) or in your server
  error logs. If you see something like "invalid API key"
  or "invalid email address", that's probably 90% of what you'll need to know
  to solve the problem.

**Check your ESPs API logs**

  Most ESPs offer some sort of API activity log in their dashboards.
  Check the logs to see if the
  data you thought you were sending actually made it to your ESP, and
  if they recorded any errors there.

**Double-check common issues**

  * Did you add any required settings for your ESP to your settings.py?
    (E.g., `ANYMAIL_SENDGRID_API_KEY` for SendGrid.) See :ref:`supported-esps`.
  * Did you add ``'anymail'`` to the list of :setting:`INSTALLED_APPS` in settings.py?
  * Are you using a valid from address? Django's default is "webmaster@localhost",
    which won't cut it. Either specify the ``from_email`` explicitly on every message
    you send through Anymail, or add :setting:`DEFAULT_FROM_EMAIL` to your settings.py.

**Try it without Anymail**

  Try switching your :setting:`EMAIL_BACKEND` setting to
  Django's :ref:`File backend <django:topic-email-file-backend>` and then running your
  email-sending code again. If that causes errors, you'll know the issue is somewhere
  other than Anymail. And you can look through the :setting:`EMAIL_FILE_PATH`
  file contents afterward to see if you're generating the email you want.


Getting help
------------

If you've gone through the suggestions above and still aren't sure what's wrong,
the Anymail community is happy to help. Anymail is supported and maintained by the
people who use it -- like you! (We're not employees of any ESP.)

For questions or problems with Anymail, you can open a `GitHub issue`_.
(And if you've found a bug, you're welcome to :ref:`contribute <contributing>` a fix!)

Whenever you open an issue, it's always helpful to mention which ESP you're using,
include the relevant portions of your code and settings, the text of any error messages,
and any exception stack traces.


.. _GitHub issue: https://github.com/anymail/django-anymail/issues
