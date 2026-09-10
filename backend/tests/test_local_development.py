import unittest
from unittest.mock import patch
from starlette.requests import Request
from app.auth import local_development_request

class LocalDevelopmentTest(unittest.TestCase):
    def request(self, client='127.0.0.1', host='127.0.0.1:8000', token='x' * 48, origin=None):
        headers = [(b'host', host.encode()), (b'x-local-dev-token', token.encode())]
        if origin:
            headers.append((b'origin', origin.encode()))
        return Request(dict(type='http', method='GET', scheme='http', path='/auth/me', query_string=b'', headers=headers, client=(client, 12345), server=('127.0.0.1', 8000)))

    def test_requires_explicit_development_flags_and_private_proxy_token(self):
        with patch.dict('os.environ', {'APP_ENV':'development', 'LOCAL_DEV_AUTH':'1', 'LOCAL_DEV_TOKEN':'x' * 48}):
            self.assertTrue(local_development_request(self.request()))
            self.assertTrue(local_development_request(self.request(origin='http://localhost:5173')))
            for request in (self.request(client='192.168.1.20'), self.request(host='public.example'), self.request(token=''), self.request(origin='https://untrusted.example')):
                self.assertFalse(local_development_request(request))
            with patch.dict('os.environ', {'APP_ENV':'production'}):
                self.assertFalse(local_development_request(self.request()))
            with patch.dict('os.environ', {'LOCAL_DEV_AUTH':'0'}):
                self.assertFalse(local_development_request(self.request()))
            with patch.dict('os.environ', {'LOCAL_DEV_TOKEN':''}):
                self.assertFalse(local_development_request(self.request()))
