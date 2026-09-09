import importlib.util
from pathlib import Path
from unittest.mock import patch, Mock
import requests
import threading
import urllib.request
import socket

import librespot.oauth as module
OAuth = module.OAuth

oauth = OAuth('test-client', 'http://127.0.0.1:4381/login', None)
oauth.set_code('test-code')
response = Mock(status_code=200)
response.json.return_value = {'access_token': 'test-token', 'expires_in': 3600}
with patch.object(module.requests, 'post', return_value=response) as post:
    oauth.request_token()
    assert post.call_args.kwargs['timeout'] == (10, 30)
    assert oauth.has_token()

oauth2 = OAuth('test', 'http://127.0.0.1:4381/login', None)
with patch.object(oauth2, 'run_callback_server'), patch.object(oauth2, 'request_token', side_effect=requests.Timeout):
    try:
        oauth2.flow()
        raise AssertionError('Expected timeout')
    except RuntimeError as exc:
        assert 'timed out' in str(exc)

with socket.socket() as probe:
    probe.bind(('127.0.0.1', 0))
    port = probe.getsockname()[1]
callback = OAuth('test', f'http://127.0.0.1:{port}/login', None).set_timeout(5)
ready = threading.Event()
original_init = OAuth.CallbackServer.__init__
def signal_ready(self, *args, **kwargs):
    original_init(self, *args, **kwargs)
    ready.set()
with patch.object(OAuth.CallbackServer, '__init__', signal_ready):
    thread = threading.Thread(target=callback.run_callback_server)
    thread.start()
    assert ready.wait(5)
    with urllib.request.urlopen(f'http://127.0.0.1:{port}/login?code=test-code', timeout=5) as result:
        assert result.status == 200
    thread.join(5)
    assert not thread.is_alive()
    assert callback._OAuth__code == 'test-code'
    assert callback._OAuth__server.socket.fileno() == -1
    callback.close()
print('PASS: token request timeout, timeout error, real local callback, server cleanup')
