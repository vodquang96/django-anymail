# Exposing all TestCases at the 'tests' module level
# is required by the old (<=1.5) DjangoTestSuiteRunner.

from .test_mailgun_backend import *
from .test_mailgun_integration import *

from .test_mandrill_backend import *
from .test_mandrill_integration import *

from .test_postmark_backend import *
from .test_postmark_integration import *

from .test_sendgrid_backend import *
from .test_sendgrid_integration import *

# Djrill leftovers:
from .test_mandrill_djrill_features import *
from .test_mandrill_webhook import *
