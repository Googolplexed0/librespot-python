import importlib.util
from pathlib import Path
from unittest.mock import Mock, patch

import librespot.core as m

response = Mock(status_code=200)
response.json.return_value = {'accesspoint': ['example:443']}
with patch.object(m.requests, 'get', return_value=response) as get:
    m.ApResolver.request('accesspoint')
    assert get.call_args.kwargs['timeout'] == (10, 30)

sock = Mock()
sock.connect.side_effect = TimeoutError('test timeout')
with patch.object(m.socket, 'socket', return_value=sock):
    try:
        m.Session.ConnectionHolder.create('example:443', None)
        raise AssertionError('Expected timeout')
    except TimeoutError:
        pass
    sock.settimeout.assert_called_with(30)
    sock.close.assert_called_once()

session = m.Session.__new__(m.Session)
session.connection = Mock()
session.cipher_pair = Mock()
session.cipher_pair.receive_encoded.side_effect = RuntimeError('Failed to receive packet')
session._Session__inner = Mock(device_id='0' * 40)
session._Session__send_unchecked = Mock()
creds = m.Authentication.LoginCredentials(typ=m.Authentication.AuthenticationType.AUTHENTICATION_SPOTIFY_TOKEN, auth_data=b'test')
try:
    session._Session__authenticate_partial(creds, False)
    raise AssertionError('Expected authentication failure')
except RuntimeError as exc:
    assert 'Spotify session authentication did not complete' in str(exc)
session.connection.set_timeout.assert_called_with(30)
session.connection.close.assert_called_once()
print('PASS: resolver timeout, connection timeout cleanup, authentication failure cleanup')
