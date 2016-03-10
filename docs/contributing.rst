.. _contributing:

Contributing
============

Anymail is maintained by its users. Your contributions are encouraged!

The `Anymail source code`_ is on GitHub.

.. _Anymail source code: https://github.com/anymail/django-anymail


Contributors
------------

See `AUTHORS.txt`_ for a list of some of the people who have helped
improve Anymail.

Anymail evolved from the `Djrill`_ project. Special thanks to the
folks from `brack3t`_ who developed the original version of Djrill.

.. _AUTHORS.txt: https://github.com/anymail/django-anymail/blob/master/AUTHORS.txt
.. _brack3t: http://brack3t.com/
.. _Djrill: https://github.com/brack3t/Djrill


Bugs
----

You can report problems or request features in `Anymail's GitHub issue tracker`_.

We also have some :ref:`troubleshooting` information that may be helpful.

.. _Anymail's GitHub issue tracker: https://github.com/anymail/django-anymail/issues


Pull requests
-------------

Pull requests are always welcome to fix bugs and improve support for ESP and Django features.

* Please include test cases.
* We try to follow the `Django coding style`_
  (basically, :pep:`8` with longer lines OK).
* By submitting a pull request, you're agreeing to release your changes under under
  the same BSD license as the rest of this project.

.. Intentionally point to Django dev branch for coding docs (rather than Django stable):
.. _Django coding style:
    https://docs.djangoproject.com/en/dev/internals/contributing/writing-code/coding-style/


Testing
-------

Anymail is `tested on Travis`_ against several combinations of Django
and Python versions. (Full list in `.travis.yml`_.)

Most of the included tests verify that Anymail constructs the expected ESP API
calls, without actually calling the ESP's API or sending any email. So these tests
don't require API keys, but they *do* require `mock`_ (``pip install mock``).

To run the tests, either:

    .. code-block:: console

        $ python -Wall setup.py test

or:

    .. code-block:: console

        $ python -Wall runtests.py

Anymail also includes some integration tests, which do call the live ESP APIs.
These integration tests require API keys (and sometimes other settings) they
get from from environment variables. Look in the ``*_integration_tests.py``
files in the `tests source`_ for specific requirements.

.. _.travis.yml: https://github.com/anymail/django-anymail/blob/master/.travis.yml
.. _tests source: https://github.com/anymail/django-anymail/blob/master/anymail/tests
.. _mock: http://www.voidspace.org.uk/python/mock/index.html
.. _tested on Travis: https://travis-ci.org/anymail/django-anymail
