import importlib.util
import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('workstation_setup', ROOT / 'setup.py')
setup = importlib.util.module_from_spec(spec)
spec.loader.exec_module(setup)


class ProfileTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.home = Path(self.temp.name)
        self.host = dict(alias='test-vps', hostname='example.com', user='test', port=22)
        self.profile = dict(version=1, ssh_hosts=[self.host])
        self.path = self.home / 'profile.json'
        self.path.write_text(json.dumps(self.profile))

    def tearDown(self):
        self.temp.cleanup()

    def defaults(self, alias):
        return dict(hostname=alias, user='local', port='22')

    def test_rejects_credentials_and_config_injection(self):
        for field, value in [('hostname', 'host\nProxyCommand evil'), ('alias', '*'), ('user', '-x'), ('port', True)]:
            host = dict(self.host, **{field: value})
            with self.assertRaises(ValueError):
                setup.validate(dict(version=1, ssh_hosts=[host]))
        with self.assertRaises(ValueError):
            setup.validate(dict(version=1, ssh_hosts=[dict(self.host, private_key='secret')]))
        with self.assertRaises(ValueError):
            setup.validate(dict(version=1, ssh_hosts=[self.host, self.host]))

    def test_apply_preserves_config_creates_key_and_reruns(self):
        ssh = self.home / '.ssh'
        ssh.mkdir()
        config = ssh / 'config'
        original = 'Host unrelated\n    HostName other.example\n'
        config.write_text(original)
        with patch.object(Path, 'home', return_value=self.home), patch.object(setup, 'resolve', side_effect=self.defaults):
            setup.apply_profile(SimpleNamespace(profile=str(self.path)))
        self.assertTrue((ssh / 'id_ed25519_codex_test-vps').exists())
        self.assertEqual(config.stat().st_mode & 0o777, 0o600)
        self.assertIn(original, config.read_text())
        self.assertEqual(next(ssh.glob('config.backup-*')).read_text(), original)
        subprocess.run(['ssh-keygen', '-lf', str(ssh / 'id_ed25519_codex_test-vps.pub')], check=True, capture_output=True)
        before = config.read_bytes()
        key = (ssh / 'id_ed25519_codex_test-vps').read_bytes()
        with patch.object(Path, 'home', return_value=self.home), patch.object(setup, 'resolve', return_value=self.host):
            setup.apply_profile(SimpleNamespace(profile=str(self.path)))
        self.assertEqual(before, config.read_bytes())
        self.assertEqual(key, (ssh / 'id_ed25519_codex_test-vps').read_bytes())

    def test_conflict_is_preflighted_before_any_key_creation(self):
        self.profile['ssh_hosts'].append(dict(self.host, alias='conflict'))
        self.path.write_text(json.dumps(self.profile))
        def resolution(alias):
            return self.defaults(alias) if alias != 'conflict' else dict(hostname='existing.example', user='local', port=22)
        with patch.object(Path, 'home', return_value=self.home), patch.object(setup, 'resolve', side_effect=resolution):
            with self.assertRaises(ValueError):
                setup.apply_profile(SimpleNamespace(profile=str(self.path)))
        self.assertFalse((self.home / '.ssh').exists())

    def test_export_has_no_private_material_or_local_paths(self):
        target = self.home / 'export.json'
        resolved = dict(self.host, identityfile='/private/key', proxycommand='secret')
        with patch.object(setup, 'resolve', return_value=resolved):
            setup.export_profile(SimpleNamespace(host=['test-vps'], output=str(target)))
        self.assertEqual(json.loads(target.read_text()), self.profile)
        self.assertEqual(target.stat().st_mode & 0o777, 0o600)
        with self.assertRaises(ValueError):
            setup.export_profile(SimpleNamespace(host=[], output=str(target)))
