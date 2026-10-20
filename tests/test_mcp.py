import json
import os
from pathlib import Path
import shutil
import subprocess
import unittest

ROOT = Path(__file__).resolve().parents[1]


class McpTests(unittest.TestCase):
    def request(self, method, params=None, enabled='1'):
        message = {'jsonrpc': '2.0', 'id': 1, 'method': method, 'params': params or {}}
        env = dict(os.environ, XDG_SESSION_TYPE='wayland', CODEX_LINUX_COMPUTER_USE=enabled)
        process = subprocess.run([shutil.which('node'), str(ROOT / 'runtime/linux-computer-use.mjs')],
                                 input=json.dumps(message) + '\n', env=env,
                                 text=True, capture_output=True, timeout=10)
        self.assertEqual(process.returncode, 0, process.stderr)
        return json.loads(process.stdout)['result']

    def test_initialize_and_list_tools(self):
        result = self.request('initialize', {'protocolVersion': '2025-03-26'})
        self.assertEqual(result['serverInfo']['name'], 'linux-computer-use')
        tools = self.request('tools/list')['tools']
        self.assertIn('computer_get_state', [tool['name'] for tool in tools])
        self.assertIn('computer_click', [tool['name'] for tool in tools])

    def test_wayland_reports_capabilities_without_input(self):
        result = self.request('tools/call', {'name': 'computer_get_capabilities', 'arguments': {}})
        data = json.loads(result['content'][0]['text'])
        self.assertEqual(data['session_type'], 'wayland')
        self.assertFalse(data['control_supported'])
        self.assertTrue(data['enabled'])

    def test_wayland_rejects_input(self):
        result = self.request('tools/call', {'name': 'computer_click', 'arguments': {'x': 1, 'y': 1}})
        self.assertTrue(result['isError'])
        self.assertIn('X11', result['content'][0]['text'])

    def test_disabled_server_rejects_actions(self):
        result = self.request('tools/call', {'name': 'computer_get_state', 'arguments': {}}, enabled='0')
        self.assertTrue(result['isError'])
        self.assertIn('disabled', result['content'][0]['text'])


if __name__ == '__main__':
    unittest.main()
