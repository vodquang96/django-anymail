# Exposing all TestCases at the 'tests' module level
# is required by the old (<=1.5) DjangoTestSuiteRunner.

from .test_mailgun_backend import *

from .test_mandrill_integration import *
from .test_mandrill_send import *
from .test_mandrill_send_template import *
from .test_mandrill_session_sharing import *
from .test_mandrill_subaccounts import *
from .test_mandrill_webhook import *
