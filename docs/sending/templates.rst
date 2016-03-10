.. _merge-vars:

Mail merge and ESP templates
============================

Anymail has some features to simplify using your ESP's email
templates and merge-variable features in a portable way.

However, ESP templating languages are generally proprietary,
which makes them inherently non-portable. Although Anymail
can normalize the Django code you write to supply merge
variables to your ESP, it can't help you avoid needing
to rewrite your email templates if you switch ESPs.

:ref:`Using Django templates <django-templates>` can be a
better, portable and maintainable option.


.. note::

    Normalized merge variables and template identification
    are coming to Anymail soon.


.. currentmodule:: anymail.message

.. _esp-templates:

ESP templates
-------------

.. To use a *Mandrill* (MailChimp) template stored in your Mandrill account,
.. set a :attr:`template_name` and (optionally) :attr:`template_content`
.. on your :class:`~django.core.mail.EmailMessage` object::
..
..     from django.core.mail import EmailMessage
..
..     msg = EmailMessage(subject="Shipped!", from_email="store@example.com",
..                        to=["customer@example.com", "accounting@example.com"])
..     msg.template_name = "SHIPPING_NOTICE"           # A Mandrill template name
..     msg.template_content = {                        # Content blocks to fill in
..         'TRACKING_BLOCK': "<a href='.../*|TRACKINGNO|*'>track it</a>"
..     }
..     msg.global_merge_vars = {                       # Merge tags in your template
..         'ORDERNO': "12345", 'TRACKINGNO': "1Z987"
..     }
..     msg.merge_vars = {                              # Per-recipient merge tags
..         'accounting@example.com': {'NAME': "Pat"},
..         'customer@example.com':   {'NAME': "Kim"}
..     }
..     msg.send()
..
.. If :attr:`template_name` is set, Djrill will use Mandrill's
.. `messages/send-template API <https://mandrillapp.com/api/docs/messages.html#method=send-template>`_,
.. and will ignore any `body` text set on the `EmailMessage`.
..
.. All of Djrill's other :ref:`Mandrill-specific options <anymail-send-features>`
.. can be used with templates.


.. attribute:: AnymailMessage.template_name


.. attribute:: AnymailMessage.global_merge_vars

..     ``dict``: merge variables to use for all recipients (most useful with :ref:`mandrill-templates`). ::
..
..         message.global_merge_vars = {'company': "ACME", 'offer': "10% off"}
..
..     Merge data must be strings or other JSON-serializable types.
..     (See :ref:`formatting-merge-data` for details.)

.. attribute:: AnymailMessage.merge_vars

..     ``dict``: per-recipient merge variables (most useful with :ref:`mandrill-templates`). The keys
..     in the dict are the recipient email addresses, and the values are dicts of merge vars for
..     each recipient::
..
..         message.merge_vars = {
..             'wiley@example.com': {'offer': "15% off anvils"},
..             'rr@example.com':    {'offer': "instant tunnel paint"}
..         }
..
..     Merge data must be strings or other JSON-serializable types.
..     (See :ref:`formatting-merge-data` for details.)


.. _formatting-merge-data:

Formatting merge data
~~~~~~~~~~~~~~~~~~~~~

If you're using a `date`, `datetime`, `Decimal`, or anything other
than strings and integers,
you'll need to format them into strings for use as merge data::

    product = Product.objects.get(123)  # A Django model
    total_cost = Decimal('19.99')
    ship_date = date(2015, 11, 18)

    # Won't work -- you'll get "not JSON serializable" exceptions:
    msg.global_merge_vars = {
        'PRODUCT': product,
        'TOTAL_COST': total_cost,
        'SHIP_DATE': ship_date
    }

    # Do something this instead:
    msg.global_merge_vars = {
        'PRODUCT': product.name,  # assuming name is a CharField
        'TOTAL_COST': "%.2f" % total_cost,
        'SHIP_DATE': ship_date.strftime('%B %d, %Y')  # US-style "March 15, 2015"
    }

These are just examples. You'll need to determine the best way to format
your merge data as strings.

Although floats are allowed in merge vars, you'll generally want to format them
into strings yourself to avoid surprises with floating-point precision.

Anymail will raise :exc:`~anymail.exceptions.AnymailSerializationError` if you attempt
to send a message with non-json-serializable data.


.. How To Use Default Mandrill Subject and From fields
.. ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
..
.. To use default Mandrill "subject" or "from" field from your template definition
.. (overriding your EmailMessage and Django defaults), set the following attrs:
.. :attr:`use_template_subject` and/or :attr:`use_template_from` on
.. your :class:`~django.core.mail.EmailMessage` object::
..
..     msg.use_template_subject = True
..     msg.use_template_from = True
..     msg.send()
..
.. .. attribute:: use_template_subject
..
..     If `True`, Djrill will omit the subject, and Mandrill will
..     use the default subject from the template.
..
.. .. attribute:: use_template_from
..
..     If `True`, Djrill will omit the "from" field, and Mandrill will
..     use the default "from" from the template.

