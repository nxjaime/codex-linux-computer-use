# Restore a Linux Codex workstation

`setup.sh` combines the computer-use installer, optional SSH profile import, and a read-only capability check. Run it as your desktop user. It supports Linux Mint 22 / Ubuntu 24.04 or newer; full desktop control requires X11. Python 3.11+, curl, and Node.js 18+ are required. The script can find the Node bundled with the desktop app. Missing apt-managed desktop/OpenSSH dependencies may request your sudo password.

## One setup command

After cloning or downloading this repository:

```bash
bash setup.sh --source-dir "$PWD" --profile /path/to/workstation-profile.json
```

To install computer-use without SSH hosts, omit `--profile`. Repeating setup preserves matching settings and existing keys. Conflicting settings stop the affected operation; computer-use installation happens before SSH import, so a later profile conflict does not roll back the already completed MCP install.

For a download-only bootstrap, pin a reviewed commit in **both** the installer URL and `--ref`:

```bash
ref=REPLACE_WITH_REVIEWED_COMMIT_SHA
file=$(mktemp)
curl -fsSL --proto '=https' --tlsv1.2 "https://raw.githubusercontent.com/nxjaime/codex-linux-computer-use/$ref/setup.sh" -o "$file" && bash "$file" --ref "$ref" --profile /path/to/workstation-profile.json
rm -f -- "$file"
```

Downloads must finish successfully before execution. A ref selects all setup/runtime sources consistently. `install.sh` verifies runtime SHA-256 hashes. The bootstrap itself is trusted code from the selected GitHub commit; hashes do not independently authenticate it.

## Save a profile from a working machine

```bash
python3 setup.py export --host hermes-vps --output workstation-profile.json
```

Repeat `--host` for more aliases. Keep this JSON privately with your backups. It includes only aliases, host addresses, usernames, and ports. It excludes private keys, passwords, OAuth tokens, local paths, SSH ProxyCommand directives, app data, and phone pairings. Never commit your personal profile to the public repository. The exporter writes mode 0600 and refuses to overwrite an existing file.

## What still needs your action

- New SSH hosts get a separate, device-local Ed25519 key with an empty passphrase for unattended Codex access. Existing matching host definitions and keys are preserved. Authorize the new public key through an existing server login; setup prints an `ssh-copy-id` command and the public key. It never logs into or changes a remote server automatically. If password login is disabled, use an already authorized machine or administrator. Server host-key verification remains enabled.
- In Codex, choose **Settings > Connections > SSH > Add** and select your host. Setup writes standard SSH configuration, not Codex's private app database.
- Restart Codex to load MCP tools. Ask it to report capabilities and capture a screenshot.
- Sign in to the same account, check installed apps/plugins, and complete any reconnect prompts. App enablement and successful account authentication are separate checks; this package cannot port or validate cloud OAuth sessions.
- Install/enable the official Chrome extension through the app's Computer use settings. Browser profiles and cookies are not copied.
- Connect Android through ChatGPT Remote and approve pairing on the device. Test an actual connection; an old paired-device entry does not establish live connectivity. Some app versions may not expose desktop-to-desktop pairing.
- Project folders are separate from app connections; clone repositories or add existing folders as needed.

## Diagnose later

```bash
python3 setup.py doctor
```

Reports local prerequisites, desktop session, and the MCP capability response. It does not click, type, capture a screenshot, connect to SSH hosts, or inspect account content. It reports configured capabilities, not a completed desktop-control or cloud-login test.

## Reversal

SSH changes are appended as a specific host block before existing wildcard defaults. Before changing an existing SSH config, setup saves a private `config.backup-<timestamp>`. Remove only the added host block and its `id_ed25519_codex_<alias>` key pair when no longer needed. Remove that public key from the server separately if you authorized it. Preserve unrelated config and newer changes. For computer-use removal, follow the README removal instructions.

## Tests

```bash
bash -n install.sh setup.sh
python3 -m unittest discover -s tests -v
```

Tests use temporary directories and keys, reject unsafe profiles, check conflict preservation and repeat runs, and never authorize a server or interact with the desktop.
