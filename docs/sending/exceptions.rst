.. _anymail-exceptions:

Exceptions
----------

.. module:: anymail.exceptions

.. exception:: AnymailUnsupportedFeature

    If the email tries to use features that aren't supported by the ESP, the send
    call will raise an :exc:`!AnymailUnsupportedFeature` error (a subclass
    of :exc:`ValueError`), and the message won't be sent.

    You can disable this exception (ignoring the unsupported features and
    sending the message anyway, without them) by setting
    :setting:`ANYMAIL_UNSUPPORTED_FEATURE_ERRORS` to ``False``.


.. exception:: AnymailRecipientsRefused

    Raised when *all* recipients (to, cc, bcc) of a message are invalid or rejected by
    your ESP *at send time.* See :ref:`recipients-refused`.

    You can disable this exception by setting :setting:`ANYMAIL_IGNORE_RECIPIENT_STATUS`
    to `True` in your settings.py, which will cause Anymail to treat any
    non-:exc:`AnymailAPIError` response from your ESP as a successful send.


.. exception:: AnymailAPIError

    If the ESP's API fails or returns an error response, the send call will
    raise an :exc:`!AnymailAPIError`.

    The exception's :attr:`status_code` and :attr:`response` attributes may
    help explain what went wrong. (Tip: you may also be able to check the API log in
    your ESP's dashboard. See :ref:`troubleshooting`.)


.. exception:: AnymailSerializationError

    The send call will raise a :exc:`!AnymailSerializationError`
    if there are message attributes Anymail doesn't know how to represent
    to your ESP.

    The most common cause of this error is including values other than
    strings and numbers in your :attr:`merge_data` or :attr:`metadata`.
    (E.g., you need to format `Decimal` and `date` data to
    strings before setting them into :attr:`merge_data`.)

    See :ref:`formatting-merge-data` for more information.
