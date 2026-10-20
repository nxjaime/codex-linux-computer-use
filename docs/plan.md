# Implementation plan

1. Write isolated installer tests with temporary HOME, CODEX_HOME, and XDG_DATA_HOME. Assert runtime placement, valid MCP configuration, backup preservation, repeat installation, conflict refusal, and hash verification before mutation. Run and observe failure before implementing.
2. Copy the three existing runtime source files, skill instructions, and MIT license. Write install.sh with dependency checks, fixed-version downloads, embedded SHA-256 verification, and atomic user configuration updates.
3. Run tests, shell syntax checks, MCP handshake/capability checks, and review the diff for secrets and app-specific assumptions.
4. Document installation, permissions, X11/Wayland limits, updates, and removal. Publish the dedicated public repository and v1.0.0 tag. Download the public installer and exercise the network install in a temporary home; return the exact verified command.
