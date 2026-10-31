import base64
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

SOURCE = Path(__file__).resolve().parent.parent / 'tools/host_bridge/bridge_client.py'
spec = importlib.util.spec_from_file_location('bridge_client', SOURCE)
client = importlib.util.module_from_spec(spec)
spec.loader.exec_module(client)


class BridgeClientTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(dir=Path(__file__).parent)
        self.addCleanup(self.temp.cleanup)
        self.directory = Path(self.temp.name)
        self.config = dict(host='26.196.29.208', user='HostUser', port=22,
                           host_public_key='ssh-ed25519 ' + base64.b64encode(b'x' * 40).decode())
        self.path = self.directory / 'connection.json'
        self.path.write_text(json.dumps(self.config))

    def test_requires_vpn_address_and_well_formed_user(self):
        for key, bad in [('host', 'example.com'), ('host', '127.0.0.1'),
                         ('user', 'HostUser\ncommand'), ('port', True)]:
            data = dict(self.config, **{key: bad})
            self.path.write_text(json.dumps(data))
            with self.subTest(key=key), self.assertRaises(ValueError):
                client.load_connection(self.path)

    def test_rejects_changed_pin_and_mismatched_fingerprint(self):
        connection = client.load_connection(self.path)
        client.pin_host(connection, self.directory)
        changed = dict(connection, host_public_key='ssh-ed25519 different')
        with self.assertRaisesRegex(ValueError, 'Pinned host key changed'):
            client.pin_host(changed, self.directory)
        self.config['fingerprint'] = 'SHA256:incorrect'
        self.path.write_text(json.dumps(self.config))
        with self.assertRaisesRegex(ValueError, 'fingerprint'):
            client.load_connection(self.path)

    def test_command_request_preserves_data_without_shell_interpretation(self):
        payload = {'prompt': 'quotes " and $(command)\nremain data'}
        encoded = client.make_request('ollama_ask', payload)
        self.assertEqual(json.loads(base64.b64decode(encoded)), {'operation': 'ollama_ask', 'args': payload})
        with self.assertRaises(ValueError):
            client.make_request('shell', {})
        with self.assertRaises(ValueError):
            client.make_request('ollama_ask', {'prompt': 'x' * client.MAX_REQUEST})

    def test_ssh_uses_pinned_key_and_never_prompts_for_password(self):
        identity = self.directory / 'private-key'
        identity.write_text('fixture only')
        connection = client.load_connection(self.path)
        pin = client.pin_host(connection, self.directory)
        with patch.object(client.shutil, 'which', return_value='ssh'), patch.object(client.subprocess, 'run') as run:
            run.return_value.stdout = b'{"ok":true,"result":{}}'
            run.return_value.stderr = b''
            run.return_value.returncode = 0
            self.assertTrue(client.call_bridge(connection, identity, pin, 'status', {})['ok'])
        command = run.call_args.args[0]
        self.assertIn('StrictHostKeyChecking=yes', command)
        self.assertIn('PasswordAuthentication=no', command)
        self.assertIn('IdentitiesOnly=yes', command)
        self.assertFalse(run.call_args.kwargs['shell'])


if __name__ == '__main__':
    unittest.main()
