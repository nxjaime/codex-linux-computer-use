# Standalone Linux Computer Use installer

Provide a public GitHub repository and one copy-and-paste command for a Linux Mint laptop running the current Codex desktop app. Reuse the MIT-licensed desktop MCP server from nxjaime/linex-project. Do not patch the app or copy the old Browser runtime.

Install verified runtime files into the user's data directory and register a local stdio server in CODEX_HOME/config.toml (default ~/.codex/config.toml). Preserve unrelated settings, back up config before changes, reject conflicting server definitions, and support repeat installation. Install missing Debian/Ubuntu dependencies through apt with sudo; never run the whole installer as root. Detect session type without forcing X11. Explain that Wayland input is unavailable.

The download path uses a fixed version tag and hashes embedded in the installer. A local-source mode supports offline installation and isolated tests. Test installation, config preservation and conflicts, idempotency, tampered payloads, custom paths, and MCP startup in temporary homes before publishing. Verify the published download against the local installer and repeat installation from GitHub in an isolated home. Laptop hardware validation remains separate.
