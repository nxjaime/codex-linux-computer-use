import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import tomllib
import unittest

ROOT = Path(__file__).resolve().parents[1]


class InstallerTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='cua installer ')
        self.home = Path(self.temp.name)
        self.config_home = self.home / 'codex settings'
        self.config_home.mkdir()
        self.config = self.config_home / 'config.toml'
        self.original = 'model = "test-model"\n\n[mcp_servers.other]\ncommand = "other"\n'
        self.config.write_text(self.original)
        self.env = dict(os.environ, HOME=str(self.home), CODEX_HOME=str(self.config_home),
                        XDG_DATA_HOME=str(self.home / 'user data'), XDG_SESSION_TYPE='wayland')

    def tearDown(self):
        self.temp.cleanup()

    def install(self, source=ROOT / 'runtime'):
        return subprocess.run(['bash', str(ROOT / 'install.sh'), '--skip-deps',
                               '--source-dir', str(source)], env=self.env,
                              text=True, capture_output=True, timeout=30)

    def test_install_preserves_config_and_reruns_without_duplication(self):
        result = self.install()
        self.assertEqual(result.returncode, 0, result.stderr)
        data = tomllib.loads(self.config.read_text())
        self.assertEqual(data['model'], 'test-model')
        self.assertEqual(data['mcp_servers']['other']['command'], 'other')
        server = data['mcp_servers']['linux-computer-use']
        self.assertEqual(server['env']['CODEX_LINUX_COMPUTER_USE'], '1')
        self.assertNotIn('XDG_SESSION_TYPE', server['env'])
        self.assertTrue(Path(server['args'][0]).is_file())
        self.assertEqual(next(self.config_home.glob('config.toml.backup-*')).read_text(), self.original)
        self.assertIn('Wayland', result.stdout)
        before = self.config.read_bytes()
        rerun = self.install()
        self.assertEqual(rerun.returncode, 0, rerun.stderr)
        self.assertEqual(self.config.read_bytes(), before)
        self.assertTrue((self.config_home / 'skills/linux-computer-use/SKILL.md').is_file())
        message = {'jsonrpc': '2.0', 'id': 1, 'method': 'tools/call',
                   'params': {'name': 'computer_get_capabilities', 'arguments': {}}}
        child = subprocess.run([server['command'], *server['args']],
                               input=json.dumps(message) + '\n', text=True,
                               capture_output=True, timeout=10,
                               env=dict(self.env, **server['env']))
        self.assertEqual(child.returncode, 0, child.stderr)
        capability = json.loads(json.loads(child.stdout)['result']['content'][0]['text'])
        self.assertTrue(capability['enabled'])
        self.assertEqual(capability['session_type'], 'wayland')

    def test_conflicting_server_is_preserved(self):
        self.config.write_text(self.original + '\n[mcp_servers.linux-computer-use]\ncommand = "custom"\n')
        before = self.config.read_bytes()
        result = self.install()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('conflict', result.stderr.lower())
        self.assertEqual(self.config.read_bytes(), before)
        self.assertFalse((self.home / 'user data/codex-linux-computer-use').exists())

    def test_tampered_payload_is_rejected_before_mutation(self):
        source = self.home / 'bad-runtime'
        shutil.copytree(ROOT / 'runtime', source)
        with (source / 'linux-computer-use.mjs').open('a') as stream:
            stream.write('\n// corrupted\n')
        result = self.install(source)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('checksum', result.stderr.lower())
        self.assertEqual(self.config.read_text(), self.original)

    def test_invalid_toml_is_preserved(self):
        self.config.write_text('not valid [ toml')
        result = self.install()
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(self.config.read_text(), 'not valid [ toml')

    def test_clean_home_and_conflicting_skill(self):
        self.config.unlink()
        skill = self.config_home / 'skills/linux-computer-use/SKILL.md'
        skill.parent.mkdir(parents=True)
        skill.write_text('Personal skill')
        result = self.install()
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(skill.read_text(), 'Personal skill')
        self.assertFalse(self.config.exists())
        skill.unlink()
        result = self.install()
        self.assertEqual(result.returncode, 0, result.stderr)
        tomllib.loads(self.config.read_text())


if __name__ == '__main__':
    unittest.main()
