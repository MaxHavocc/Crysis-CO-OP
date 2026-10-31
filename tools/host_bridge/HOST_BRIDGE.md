# Host development bridge

Caden runs setup once while Radmin VPN is connected. After that, the co-developer can inspect the host's game logs, compare installed files, run the supported development checks, and ask a model served by the host's local Ollama. No repeated log copying is needed.

The transport is Windows OpenSSH with a dedicated client public key. The private key stays on the developer PC. Requests use a fixed command dispatcher; this key cannot open an interactive shell, SFTP session, or port forward. Ollama remains at `127.0.0.1:11434` and is never opened in the firewall. Model replies are advice, not commands that execute automatically.

## One-time host setup

Use the supplied setup package, or place `Setup_Host_Bridge.ps1`, `Stop_Host_Bridge.ps1`, and `bridge_agent.py` together. Open **PowerShell as Administrator using Caden's normal Windows account**, then run:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\Setup_Host_Bridge.ps1 -ClientPublicKey 'ssh-ed25519 PUBLIC_KEY_FROM_DEVELOPER' -ClientVpnAddress '26.x.x.x'
```

Supply `-CrysisRoot 'D:\SteamLibrary\steamapps\common\Crysis'` if automatic Steam-library detection cannot select one installation. Supply `-HostVpnAddress '26.x.x.x'` if multiple Radmin addresses are assigned. Python 3.10+ must already be installed. `-ValidateOnly` checks paths, Python, the public key, and VPN addresses without installing or changing anything.

Setup installs the Windows OpenSSH Server optional feature if needed. On a fresh SSH installation it binds SSH to the host's Radmin address, disables password authentication, and creates a firewall rule limited to the developer's VPN address. Existing SSH settings and unrelated keys are preserved. The bridge key itself is always restricted to the specified VPN source address and the fixed dispatcher. Windows Update may be needed to install the optional feature; if Windows asks for a restart, rerun the same setup afterward.

At the end, send the single `BRIDGE_CONNECTION {...}` line to the co-developer. This contains the host address, Windows login name, SSH port, and public host key so the client can pin the correct server. It contains no password or private key. This is the only connection handoff; subsequent diagnostics come directly through the bridge.

Keep both PCs connected to Radmin VPN. OpenSSH starts automatically with Windows. Ollama must be running locally for model requests; ordinary diagnostics work without it. If the VPN address or developer public key changes, rerun setup with the new value. Updating repository code does not silently replace the protected dispatcher: rerun setup when the bridge helper itself is intentionally updated.

The helper and its configuration live in `%ProgramData%\CrysisCoopBridge`, with write access limited to Administrators and SYSTEM. Log access is restricted by the helper to the game/mod paths; diagnostics can include player names and VPN addresses.

## Developer use

Save the one-time connection line as a local `connection.json` outside the repository, beside the private client key. The client pins the public SSH host key from that record and rejects a changed key. Run from the mod folder:

```powershell
python .\tools\host_bridge\bridge_client.py --connection 'C:\private\connection.json' --identity 'C:\private\id_ed25519' status
```

Supported operations: `info`, `status`, `read_log`, `read_config`, `read_file`, `git_status`, `git_diff`, `git_log`, `git_pull`, `run_tests`, `build`, `ollama_models`, and `ollama_ask`. Supply operation arguments in a JSON file with `--args-file 'C:\private\request.json'`. For example, `read_log` accepts `{"name":"Game.log","lines":500}` and `ollama_ask` accepts `{"model":"installed-local-model","prompt":"Explain these connection failures","context":"relevant log excerpt"}`. Requests are limited to 16 KiB.

Updates use `git pull --ff-only origin main` and stop on conflicts; they never reset local work. Builds target `Code/GameDll.vcxproj`, `Profile|Win32`, with v143. Builds and tests execute the checked-out project code under the host Windows account. The bridge does not launch or close games; interactive playtests still need the players. Ollama responses cannot execute commands, and cloud-backed models are rejected.

## Revoke access

Run this once in an elevated PowerShell window:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File "$env:ProgramData\CrysisCoopBridge\Stop_Host_Bridge.ps1"
```

It removes only this bridge's authorized key and firewall rule. Unrelated SSH keys and service settings are preserved. Already-running requests may finish, but new connections using the revoked key are rejected. No game files are deleted.

Windows OpenSSH references: [installation and service setup](https://learn.microsoft.com/en-us/windows-server/administration/openssh/openssh_install_firstuse), [server configuration and administrator key ACLs](https://learn.microsoft.com/en-us/windows-server/administration/openssh/openssh-server-configuration).
