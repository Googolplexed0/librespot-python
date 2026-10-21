"""Offline regression check for atomic, owner-only OAuth credential files."""
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from librespot.oauth import OAuth


class CredentialFileTests(unittest.TestCase):
    """Exercise dummy files without opening an account session."""
    def test_oauth_credentials_are_atomic_and_owner_only(self):
        """A permissive old dummy file is replaced safely, including failure."""
        with tempfile.TemporaryDirectory(prefix='librespot-oauth-test-') as temp:
            path = Path(temp) / 'credentials.json'
            path.write_text('{"old":true}')
            path.chmod(0o644)
            oauth = OAuth('fixture-client', 'http://127.0.0.1/callback', None)
            previous_umask = os.umask(0o022)
            try:
                with patch('requests.sessions.Session.request', side_effect=AssertionError('Network forbidden')):
                    oauth.save_creds(path)
            finally:
                os.umask(previous_umask)
            self.assertEqual(path.stat().st_mode & 0o777, 0o600)
            saved = path.read_bytes()
            self.assertEqual(json.loads(saved)['client_id'], 'fixture-client')
            with patch('librespot.oauth.json.dump', side_effect=ValueError('serialization failed')):
                with self.assertRaises(ValueError):
                    oauth.save_creds(path)
            self.assertEqual(path.read_bytes(), saved)
            self.assertEqual(list(Path(temp).glob('.credentials.json-*')), [])


if __name__ == "__main__":
    unittest.main()
