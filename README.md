# Linux Computer Use for Codex

Add screenshot, window, mouse, keyboard, scrolling, and dragging tools to the current Codex desktop app on Linux. This is a community MCP server, not an OpenAI product. It installs into your user account without modifying the app.

## Install on the laptop

Run this in a terminal **on the laptop**, as your normal desktop user:

```bash
bash -c 'set -e; f=$(mktemp); trap '\''rm -f -- "$f"'\'' EXIT; curl -fsSL --proto "=https" --tlsv1.2 https://raw.githubusercontent.com/nxjaime/codex-linux-computer-use/v1.0.0/install.sh -o "$f"; bash "$f"'
```

The download must complete successfully before Bash executes it. Review [install.sh](install.sh) first if desired. The installer fetches the v1.0.0 runtime and verifies its files against embedded SHA-256 hashes. Hashes detect a mismatched runtime; they do not independently authenticate the installer itself.

Requirements: Linux Mint 22 / Ubuntu 24.04 or newer, Python 3.11+, and Node.js 18+. Missing desktop tools are installed using `sudo apt-get`, which may ask for your password. Network downloads require `curl`; if your system lacks it, install it with `sudo apt install curl` first. Other Linux distributions can install the listed dependencies manually and run with `--skip-deps`.

Restart the desktop app after installation. Open a **local chat running on the laptop** and ask:

> Use linux-computer-use to report capabilities and take a screenshot. Do not click anything.

Check MCP servers in the app's settings if the tools are missing. For current MCP configuration guidance, see the [OpenAI documentation](https://learn.chatgpt.com/docs/extend/mcp?surface=cli).

## Desktop support and permissions

- **X11:** full desktop control, including screenshots, window focus, clicks, typing, scrolling, and dragging. Keep the desktop unlocked. Check your session with `echo "$XDG_SESSION_TYPE"`.
- **Wayland:** screenshots only, when a supported screenshot tool works in your desktop session. Mouse, keyboard, and window control are unavailable. Use an X11 session for full control; the installer does not change your login session or pretend Wayland is X11.
- The server operates with your desktop user's access. Screenshots can contain private information. Use it only in chats you trust.
- The included skill instructs Codex to inspect state before and after input and follow confirmation policy for external side effects. This is agent guidance, not a server-enforced authorization system; normal Codex tool approval settings still apply.
- This package provides its own `computer_*` MCP tools. It does not enable or patch Codex's built-in native Computer Use or Browser runtime.

## What changes

Runtime files go under `${XDG_DATA_HOME:-$HOME/.local/share}/codex-linux-computer-use/v1.0.0`. A server entry and skill are added under `${CODEX_HOME:-$HOME/.codex}`:

- `config.toml`: adds `mcp_servers.linux-computer-use` with a local Node command and explicitly forwarded desktop environment variables.
- `skills/linux-computer-use/SKILL.md`: adds usage instructions.
- Before changing existing config, a private `config.toml.backup-<timestamp>` is saved alongside it.

Unrelated settings stay intact. Repeating the same installer is supported. A different existing server definition or skill produces a conflict error and leaves configuration unchanged. The installer honors `CODEX_HOME` and `XDG_DATA_HOME`; run it without sudo.

## Remove

Disable or remove `linux-computer-use` in the app's MCP settings. To remove the config manually, remove only `[mcp_servers.linux-computer-use]` and `[mcp_servers.linux-computer-use.env]` and their contents from your config. Remove the `skills/linux-computer-use` folder and `codex-linux-computer-use` runtime folder listed above, then restart the app. Preserve backups and unrelated configuration. Avoid restoring an entire old backup over newer settings.

## Local install and testing

```bash
bash install.sh --source-dir ./runtime
python3 -m unittest discover -s tests -v
bash -n install.sh
```

`--skip-deps` skips apt and desktop-tool checks; Python 3.11+ and Node 18+ are still required. Tests use temporary user directories, preserve your real configuration, and do not click or type on your desktop.

The runtime was extracted without changes from the MIT-licensed [nxjaime/linex-project](https://github.com/nxjaime/linex-project). The old Browser compatibility patches and whole-app updater are intentionally outside this package. See [LICENSE](LICENSE).
