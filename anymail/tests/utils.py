# Anymail test utils
import os
import unittest
from base64 import b64decode

import six


def decode_att(att):
    """Returns the original data from base64-encoded attachment content"""
    return b64decode(att.encode('ascii'))


SAMPLE_IMAGE_FILENAME = "sample_image.png"


def sample_image_path(filename=SAMPLE_IMAGE_FILENAME):
    """Returns path to an actual image file in the tests directory"""
    test_dir = os.path.dirname(os.path.abspath(__file__))
    path = os.path.join(test_dir, filename)
    return path


def sample_image_content(filename=SAMPLE_IMAGE_FILENAME):
    """Returns contents of an actual image file from the tests directory"""
    filename = sample_image_path(filename)
    with open(filename, "rb") as f:
        return f.read()


class AnymailTestMixin:
    """Helpful additional methods for Anymail tests"""

    pass
    # Plus these methods added below:
    # assertCountEqual
    # assertRaisesRegex
    # assertRegex

# Add the Python 3 TestCase assertions, if they're not already there.
# (The six implementations cause infinite recursion if installed on
# a py3 TestCase.)
for method in ('assertCountEqual', 'assertRaisesRegex', 'assertRegex'):
    try:
        getattr(unittest.TestCase, method)
    except AttributeError:
        setattr(AnymailTestMixin, method, getattr(six, method))
