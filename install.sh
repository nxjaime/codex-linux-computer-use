#!/usr/bin/env bash
set -Eeuo pipefail

VERSION=v1.0.0
BASE_URL="https://raw.githubusercontent.com/nxjaime/codex-linux-computer-use/$VERSION/runtime"
SOURCE_DIR=''
SKIP_DEPS=0
while (($#)); do
  case "$1" in
    --source-dir) [[ $# -ge 2 ]] || { echo 'Missing source directory' >&2; exit 1; }; SOURCE_DIR=$2; shift 2 ;;
    --skip-deps) SKIP_DEPS=1; shift ;;
    --help) echo 'Usage: bash install.sh [--source-dir PATH] [--skip-deps]'; exit 0 ;;
    *) echo "Unknown argument: $1" >&2; exit 1 ;;
  esac
done

[[ $(uname -s) == Linux ]] || { echo 'This installer requires Linux.' >&2; exit 1; }
[[ $EUID -ne 0 ]] || { echo 'Run as your desktop user, without sudo. Only apt uses sudo.' >&2; exit 1; }

if (( ! SKIP_DEPS )); then
  missing=0
  for tool in python3 node wmctrl xrandr xwininfo gnome-screenshot; do
    command -v "$tool" >/dev/null 2>&1 || missing=1
  done
  if command -v python3 >/dev/null 2>&1; then
    python3 -c 'import ctypes.util; assert ctypes.util.find_library("X11") and ctypes.util.find_library("Xtst")' 2>/dev/null || missing=1
  fi
  if ((missing)); then
    command -v apt-get >/dev/null || { echo 'Install Python 3.11+, Node 18+, wmctrl, x11-utils, x11-xserver-utils, gnome-screenshot, libx11-6, libxtst6 and rerun.' >&2; exit 1; }
    echo 'Installing missing desktop dependencies with apt (sudo may ask for your password).'
    sudo apt-get update
    sudo apt-get install -y python3 nodejs wmctrl x11-utils x11-xserver-utils gnome-screenshot libx11-6 libxtst6
  fi
fi

command -v python3 >/dev/null || { echo 'Python 3.11+ is required.' >&2; exit 1; }
python3 -c 'import tomllib' 2>/dev/null || { echo 'Python 3.11+ is required (Linux Mint 22 / Ubuntu 24.04 or newer).' >&2; exit 1; }
NODE_BIN=$(command -v node) || { echo 'Node.js 18+ is required.' >&2; exit 1; }
"$NODE_BIN" -e 'if (Number(process.versions.node.split(".")[0]) < 18) process.exit(1)' || { echo 'Node.js 18+ is required.' >&2; exit 1; }

STAGE=$(mktemp -d)
trap 'rm -rf -- "$STAGE"' EXIT
for file in linux-computer-use.mjs mcp-stdio.mjs x11-input.py linux-computer-use.SKILL.md; do
  if [[ -n $SOURCE_DIR ]]; then
    cp -- "$SOURCE_DIR/$file" "$STAGE/$file"
  else
    curl --fail --show-error --silent --location --proto '=https' --tlsv1.2 --retry 3 "$BASE_URL/$file" -o "$STAGE/$file"
  fi
done

python3 - "$STAGE" "$NODE_BIN" "$VERSION" <<'PY'
import hashlib
import json
import os
from pathlib import Path
import shutil
import sys
import tempfile
import time
import tomllib

stage = Path(sys.argv[1])
node = str(Path(sys.argv[2]).absolute())
version = sys.argv[3]
HASHES = {
    'linux-computer-use.SKILL.md': '07c7763cc6df5dee3ac3c56968fceb838fd8638dd10f14666bc386c7afcb35f6',
    'linux-computer-use.mjs': '276c8dc2e122f7bd1cd5f7bc96eea9bfafcef4ea4b0ad4b125fd9b4cd3cf67cd',
    'mcp-stdio.mjs': '63d15e6c9c5d89a629500f589df34c415f257af91eff541bacd6c50aba5a52b6',
    'x11-input.py': '72510f433bcf8f3969e7fbcb5f57811411630bc9c8807ca61cd84a132188d346',
}
if len(HASHES) != 4:
    sys.exit('Installer checksum manifest is incomplete.')
for name, expected in HASHES.items():
    if hashlib.sha256((stage / name).read_bytes()).hexdigest() != expected:
        sys.exit(f'Checksum mismatch: {name}. No configuration was changed.')

home = Path.home()
config_home = Path(os.environ.get('CODEX_HOME') or home / '.codex').expanduser().absolute()
data_home = Path(os.environ.get('XDG_DATA_HOME') or home / '.local/share').expanduser().absolute()
target = data_home / 'codex-linux-computer-use' / version
config = config_home / 'config.toml'
skill = config_home / 'skills/linux-computer-use/SKILL.md'
if config.is_symlink() or skill.is_symlink():
    sys.exit('Refusing to replace a symlinked config or skill. Install manually instead.')
original = config.read_bytes().decode('utf-8') if config.exists() else ''
try:
    parsed = tomllib.loads(original)
except tomllib.TOMLDecodeError as error:
    sys.exit(f'Existing config is invalid TOML; left unchanged: {error}')

definition = {
    'command': node,
    'args': [str(target / 'linux-computer-use.mjs')],
    'env_vars': ['DISPLAY', 'XAUTHORITY', 'XDG_SESSION_TYPE', 'XDG_RUNTIME_DIR', 'WAYLAND_DISPLAY', 'DBUS_SESSION_BUS_ADDRESS'],
    'env': {'CODEX_LINUX_COMPUTER_USE': '1'},
}
servers = parsed.get('mcp_servers', {})
if not isinstance(servers, dict):
    sys.exit('Existing mcp_servers configuration has an incompatible format; left unchanged.')
existing = servers.get('linux-computer-use')
if existing is not None and existing != definition:
    sys.exit('Configuration conflict: linux-computer-use already has different settings. Existing files were left unchanged. Back up and remove that server entry to use this installer.')
skill_content = (stage / 'linux-computer-use.SKILL.md').read_bytes()
if skill.exists() and skill.read_bytes() != skill_content:
    sys.exit('Skill conflict: existing linux-computer-use skill differs; left unchanged.')

block = '\n\n[mcp_servers.linux-computer-use]\n'
block += 'command = ' + json.dumps(node) + '\n'
block += 'args = ' + json.dumps(definition['args']) + '\n'
block += 'env_vars = ' + json.dumps(definition['env_vars']) + '\n'
block += '\n[mcp_servers.linux-computer-use.env]\nCODEX_LINUX_COMPUTER_USE = "1"\n'
updated = original if existing is not None else original + block
# Also catches a conflicting parent inline table before writing anything.
tomllib.loads(updated)

def atomic_write(path, content, mode=0o600):
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix='.' + path.name, dir=path.parent)
    try:
        with os.fdopen(fd, 'wb') as stream:
            stream.write(content)
        os.chmod(temporary, mode)
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)

for name in HASHES:
    atomic_write(target / name, (stage / name).read_bytes())
atomic_write(skill, skill_content)
if updated != original:
    if config.exists():
        backup = config.with_name('config.toml.backup-' + str(time.time_ns()))
        # Backups may contain credentials, so never broaden their permissions.
        atomic_write(backup, config.read_bytes())
        print(f'Configuration backup: {backup}')
    atomic_write(config, updated.encode())

print(f'Installed Linux Computer Use {version} at {target}')
print(f'MCP configuration: {config}')
print('Restart Codex, open a local chat on this laptop, and ask:')
print('  Use linux-computer-use to report capabilities and take a screenshot. Do not click anything.')
if os.environ.get('XDG_SESSION_TYPE', '').lower() == 'wayland':
    print('Wayland detected: screenshots only. Log in to an X11 session for mouse and keyboard control.')
else:
    print('Mouse and keyboard control require an unlocked X11 desktop. Wayland supports screenshots only.')
PY
