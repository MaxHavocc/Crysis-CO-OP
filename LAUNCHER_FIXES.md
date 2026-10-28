# Lobby and connection fixes

Based on upstream `main` commit `d3fae6e00143c458ed5568b8acaef5d880ee9ac1`.

## Join browser

The lobby table now uses a dark Treeview style for its empty area, rows, headings, and selections. The list refreshes automatically while open. Each completed scan replaces the previous results, so offline hosts disappear instead of remaining as cached entries. Late results from an older scan cannot repopulate a page that was left.

HTTP bridge entries are treated as discovery candidates. A listed lobby must respond to a live TCP status query, or, for older launchers, provide a fresh UDP discovery reply plus a reachable TCP lobby socket. New `LOBBY_QUERY` probes do not add fake players to the roster. Closing hosting clears the hosting flags; old registration/accept threads cannot advertise a replacement session.

Older launchers remain discoverable when their UDP responses are reachable. An old host reachable only through a stale HTTP listing cannot be verified; Direct Connect remains available. Update both launchers for the TCP status-query support.

## Client stuck at the main menu

The captured game log showed that `client.cfg` and `connect.cfg` executed and attempted the correct host address, but CryNetwork rejected the VPN address with a GameSpy-login requirement. Adding another connect command does not resolve that rejection.

Co-op now starts the x86 C1-Launcher runtime at `<Crysis>\Bin32\CrysisCoop.exe`, with `-mod CrysisCoop`. The original `Bin32\Crysis.exe` remains in place. C1-Launcher applies its direct-connection compatibility fix in memory and supports the mod's DLL.

Install this dependency once on each machine using PowerShell from the mod directory:

```powershell
.\Setup_Coop_Runtime.ps1
```

The script downloads the official v8 archive, verifies its SHA-256 digest, and installs only its Crysis x86 executable under the alternate name. A nonstandard location can be supplied with `-CrysisRoot 'D:\path\to\Crysis'`. The binary is an external runtime dependency and is not added to the mod repository.

- [Official C1-Launcher v8 release](https://github.com/ccomrade/c1-launcher/releases/tag/v8)
- [Upstream command-line and mod documentation](https://github.com/ccomrade/c1-launcher/blob/v8/README.md)
- [Game startup source, including FixInternetConnect](https://github.com/ccomrade/c1-launcher/blob/v8/Code/Launcher/Game/GameLauncher.cpp)
- Archive SHA-256: `a61c631b990b46dac67f47407b7e5906d82fcabfdd8e64478d05bc51d61b08fa`
- Installed x86 executable SHA-256: `cf095b6a73ee5f6db7463842da8d9b4a0f206112c357cd9d4cb5907b8ad6cdd5`

Missing runtime support produces an installation message before starting the game. The host checks this before sending a launch message to peers. Generated console scripts now use command syntax without `=` and the registered `name` command. Reconnect hotkeys still execute `connect.cfg`.

## Verification

Run from the mod directory with Python and Pillow installed:

```powershell
python -m unittest discover -s tests -v
```

The checks use hidden Tk widgets, controlled local UDP/TCP fixtures, temporary configuration directories, and mocked game launches. They cover stale cached hosts, current/legacy liveness checks, probe isolation from the roster, stale browser scan results, dark theme states, icon rendering, runtime selection, and generated connection scripts.

No full two-PC map-loading test was performed during these changes. Next validation: host a mission on one machine, join/ready on the other, launch, and check both players enter the host's map. Then close the host lobby and confirm it disappears from the browser on the next refresh. Firewall, VPN routing, and host loading time can still affect a real connection.

Separate existing issue: `coop_loadout`, `coop_all_attachments`, and `coop_ammo_multiplier` registrations were not found in the current C++ source. Corrected console syntax does not establish that those settings are registered; this change does not rebuild the engine DLL or resolve their registrations.
