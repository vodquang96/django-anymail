#!/usr/bin/env python

# python setup.py test
#   or
# runtests.py [tests.test_x tests.test_y.SomeTestCase ...]

import sys

import django
import os
import warnings
from django.conf import settings
from django.test.utils import get_runner


def runtests(test_labels=None):
    """Discover and run project tests. Returns number of failures."""
    test_labels = test_labels or ['tests']

    # noinspection PyStringFormat
    os.environ['DJANGO_SETTINGS_MODULE'] = \
        'tests.test_settings.settings_%d_%d' % django.VERSION[:2]
    django.setup()

    TestRunner = get_runner(settings)
    test_runner = TestRunner(verbosity=1)
    return test_runner.run_tests(test_labels)


if __name__ == '__main__':
    warnings.simplefilter('default')  # show DeprecationWarning and other default-ignored warnings
    failures = runtests(test_labels=sys.argv[1:])
    sys.exit(bool(failures))
