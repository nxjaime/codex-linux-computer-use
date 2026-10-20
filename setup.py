#!/usr/bin/env python3
"""Portable, credential-free Codex workstation setup profiles."""
import argparse
import json
import os
from pathlib import Path
import re
import shlex
import shutil
import subprocess
import tempfile
import time
import tomllib


def run(args):
    return subprocess.run(args, text=True, capture_output=True, timeout=15)


def resolve(alias):
    result = run(['ssh', '-G', alias])
    if result.returncode:
        raise ValueError(result.stderr.strip())
    return dict(line.split(None, 1) for line in result.stdout.splitlines() if ' ' in line)


def validate(profile):
    if set(profile) != {'version', 'ssh_hosts'} or profile['version'] != 1:
        raise ValueError('Expected version 1 with only version and ssh_hosts fields')
    if not isinstance(profile['ssh_hosts'], list):
        raise ValueError('ssh_hosts must be a list')
    seen = set()
    for host in profile['ssh_hosts']:
        if not isinstance(host, dict) or set(host) != {'alias', 'hostname', 'user', 'port'}:
            raise ValueError('Host fields must be alias, hostname, user, port; credentials are never imported')
        for field in ('alias', 'hostname', 'user'):
            value = host[field]
            pattern = r'[A-Za-z0-9][A-Za-z0-9_.-]{0,127}' if field != 'hostname' else r'[A-Za-z0-9][A-Za-z0-9.:-]{0,252}'
            if not isinstance(value, str) or not re.fullmatch(pattern, value):
                raise ValueError(f'Invalid {field}')
        if type(host['port']) is not int or not 1 <= host['port'] <= 65535:
            raise ValueError('Invalid port')
        if host['alias'] in seen:
            raise ValueError('Duplicate SSH alias')
        seen.add(host['alias'])
    return profile


def atomic(path, content):
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temp = tempfile.mkstemp(dir=path.parent, prefix='.' + path.name)
    try:
        with os.fdopen(fd, 'w') as stream:
            stream.write(content)
        os.chmod(temp, 0o600)
        os.replace(temp, path)
    finally:
        if os.path.exists(temp):
            os.unlink(temp)


def export_profile(args):
    hosts = []
    for alias in args.host:
        values = resolve(alias)
        hosts.append(dict(alias=alias, hostname=values['hostname'], user=values['user'], port=int(values['port'])))
    profile = validate(dict(version=1, ssh_hosts=hosts))
    target = Path(args.output).expanduser()
    if target.exists():
        raise ValueError('Output exists; choose a new filename')
    atomic(target, json.dumps(profile, indent=2) + '\n')
    print(f'Exported {len(hosts)} host(s) to {target}. Contains addresses/usernames, no keys or tokens. Keep private.')


def apply_profile(args):
    profile = validate(json.loads(Path(args.profile).read_text()))
    ssh_dir = Path.home() / '.ssh'
    config = ssh_dir / 'config'
    if ssh_dir.is_symlink() or config.is_symlink():
        raise ValueError('Symlinked SSH config: configure manually')
    original = config.read_text() if config.exists() else ''
    plans = []
    # Validate every conflict before creating keys or changing config.
    for host in profile['ssh_hosts']:
        existing = resolve(host['alias'])
        same = all(str(host[k]) == str(existing[k]) for k in ('hostname', 'user', 'port'))
        if same:
            print(f"Preserved existing SSH host: {host['alias']}")
            continue
        explicit = any(host['alias'] in line.split()[1:] for line in original.splitlines()
                       if line.strip().lower().startswith('host '))
        if explicit or existing['hostname'] != host['alias']:
            raise ValueError(f"SSH conflict for {host['alias']}; existing settings left unchanged")
        key = ssh_dir / ('id_ed25519_codex_' + host['alias'])
        if key.exists() or key.with_suffix('.pub').exists():
            raise ValueError(f'Key path exists: {key}; existing key left unchanged')
        plans.append((host, key))
    if plans:
        ssh_dir.mkdir(mode=0o700, parents=True, exist_ok=True)
        for host, key in plans:
            # Empty passphrase permits unattended Codex SSH sessions. The key stays on this device.
            result = run(['ssh-keygen', '-q', '-t', 'ed25519', '-N', '', '-C', 'codex-' + host['alias'], '-f', str(key)])
            if result.returncode:
                raise ValueError(result.stderr)
        blocks = []
        for host, key in plans:
            blocks.append(f"\nHost {host['alias']}\n    HostName {host['hostname']}\n    User {host['user']}\n    Port {host['port']}\n    IdentityFile {key}\n    IdentitiesOnly yes\n")
        # Put specific profiles before wildcard defaults (OpenSSH uses first obtained values).
        if config.exists():
            atomic(config.with_name('config.backup-' + str(time.time_ns())), original)
        atomic(config, '\n'.join(blocks) + '\n' + original)
        for host, key in plans:
            command = ['ssh-copy-id', '-i', str(key) + '.pub', '-p', str(host['port']), host['user'] + '@' + host['hostname']]
            print(f"Prepared {host['alias']}. Authorize this device using an existing login:")
            print('  ' + shlex.join(command))
            print('Or have your administrator add this public key to the server:')
            print(key.with_suffix('.pub').read_text().strip())
    print('In Codex: Settings > Connections > SSH > Add, select the profile host(s).')
    print('New hosts need authorization before login works. No private keys were copied.')


def doctor(_args):
    config = Path(os.environ.get('CODEX_HOME') or Path.home() / '.codex') / 'config.toml'
    print('Session:', os.environ.get('XDG_SESSION_TYPE', 'unknown'))
    for tool in ('node', 'python3', 'ssh', 'ssh-keygen', 'wmctrl', 'xrandr', 'xwininfo', 'gnome-screenshot'):
        print(f'{tool}: {shutil.which(tool) or "MISSING"}')
    data = tomllib.loads(config.read_text()) if config.exists() else {}
    server = data.get('mcp_servers', {}).get('linux-computer-use')
    if server:
        env = dict(os.environ, **server.get('env', {}))
        request = {'jsonrpc': '2.0', 'id': 1, 'method': 'tools/call', 'params': {'name': 'computer_get_capabilities', 'arguments': {}}}
        result = subprocess.run([server['command'], *server.get('args', [])], input=json.dumps(request)+'\n',
                                text=True, capture_output=True, timeout=15, env=env)
        response = json.loads(result.stdout)
        if result.returncode or response.get('result', {}).get('isError'):
            raise ValueError('MCP capability check failed')
        print('MCP capabilities:', response['result']['content'][0]['text'])
    else:
        print('Computer-use MCP: MISSING; run setup.sh')
    print('Manual checks: restart Codex; verify Chrome extension and app sign-ins in Settings.')
    print('Android: connect from ChatGPT Remote; a saved pairing alone does not verify a live session.')
    print('App OAuth sessions, phone pairing, projects, and private keys are not exported.')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    export = sub.add_parser('export', help='Export SSH addresses only; no credentials')
    export.add_argument('--host', action='append', default=[])
    export.add_argument('--output', required=True)
    export.set_defaults(func=export_profile)
    apply = sub.add_parser('apply', help='Prepare SSH hosts and device-specific keys; never authorizes automatically')
    apply.add_argument('--profile', required=True)
    apply.set_defaults(func=apply_profile)
    sub.add_parser('doctor', help='Read-only capability checks; never clicks or types').set_defaults(func=doctor)
    args = parser.parse_args()
    try:
        args.func(args)
    except (ValueError, OSError, KeyError, TypeError, subprocess.TimeoutExpired) as error:
        parser.exit(1, f'Error: {error}\n')


if __name__ == '__main__':
    main()
