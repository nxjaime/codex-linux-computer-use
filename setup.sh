#!/usr/bin/env bash
set -Eeuo pipefail
REF=main
SOURCE_DIR=''
PROFILE=''
SKIP_DEPS=0
while (($#)); do
  case "$1" in
    --ref) REF=${2:?Missing ref}; shift 2 ;;
    --source-dir) SOURCE_DIR=${2:?Missing source directory}; shift 2 ;;
    --profile) PROFILE=${2:?Missing profile}; shift 2 ;;
    --skip-deps) SKIP_DEPS=1; shift ;;
    --help) echo 'Usage: bash setup.sh [--ref COMMIT] [--profile PRIVATE_JSON] [--source-dir CHECKOUT] [--skip-deps]'; exit 0 ;;
    *) echo "Unknown argument: $1" >&2; exit 1 ;;
  esac
done
[[ $(uname -s) == Linux && $EUID -ne 0 ]] || { echo 'Run as your normal Linux desktop user, without sudo.' >&2; exit 1; }
# Desktop app bundles may supply Node even when it is absent from the shell PATH.
if ! command -v node >/dev/null; then
  bundled_node="$HOME/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/bin"
  if [[ -x $bundled_node/node ]]; then export PATH="$bundled_node:$PATH"; fi
fi
if [[ -z $SOURCE_DIR ]]; then
  [[ $REF =~ ^[a-zA-Z0-9._-]+$ ]] || { echo 'Invalid ref' >&2; exit 1; }
  SOURCE_DIR=$(mktemp -d)
  trap 'rm -rf -- "$SOURCE_DIR"' EXIT
  mkdir -p "$SOURCE_DIR/runtime"
  for file in install.sh setup.py runtime/linux-computer-use.mjs runtime/mcp-stdio.mjs runtime/x11-input.py runtime/linux-computer-use.SKILL.md; do
    curl -fsSL --proto '=https' --tlsv1.2 "https://raw.githubusercontent.com/nxjaime/codex-linux-computer-use/$REF/$file" -o "$SOURCE_DIR/$file"
  done
fi
if ! command -v ssh >/dev/null || ! command -v ssh-keygen >/dev/null; then
  if ((SKIP_DEPS)) || ! command -v apt-get >/dev/null; then
    echo 'OpenSSH client is required: install openssh-client and rerun.' >&2
    exit 1
  fi
  sudo apt-get update
  sudo apt-get install -y openssh-client
fi
install_args=(--source-dir "$SOURCE_DIR/runtime")
if ((SKIP_DEPS)); then install_args+=(--skip-deps); fi
bash "$SOURCE_DIR/install.sh" "${install_args[@]}"
if [[ -n $PROFILE ]]; then
  python3 "$SOURCE_DIR/setup.py" apply --profile "$PROFILE"
fi
python3 "$SOURCE_DIR/setup.py" doctor
printf '\nSetup complete. Restart Codex to load MCP tools.\n'
