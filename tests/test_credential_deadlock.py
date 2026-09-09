from librespot.core import Session, Authentication
from unittest.mock import Mock
import faulthandler
faulthandler.dump_traceback_later(5, exit=True)
s = Session.__new__(Session)
s._Session__auth_lock_bool = True
s.ap_welcome = Mock(side_effect=AssertionError('Must not wait for complete authentication'))
s._Session__ap_welcome = Authentication.APWelcome(
    canonical_username='test',
    reusable_auth_credentials=b'fake-test-credential',
    reusable_auth_credentials_type=Authentication.AuthenticationType.AUTHENTICATION_STORED_SPOTIFY_CREDENTIALS)
result = s.credentials()
assert result['username'] == 'test'
s.ap_welcome.assert_not_called()
del s._Session__ap_welcome
try:
    s.credentials()
    raise AssertionError('Must reject missing welcome')
except RuntimeError:
    pass
faulthandler.cancel_dump_traceback_later()
print('PASS: credentials available during unfinished authentication; missing welcome rejected')
