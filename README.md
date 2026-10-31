# Crysis Co-op Multiplayer Project: Collaborator Handover Brief

Welcome to the **Crysis Co-op Project**! This document provides a complete technical overview of the codebase, project architecture, build environment, completed systems, and current development backlog.

---

## 1. Project Overview & Background

* **Engine**: CryEngine 2.0 / 2.1 (Crysis 1 v1.2.1 / Crysis Warhead).
* **Language & Tech Stack**:
  * **C++ (Win32)**: `GameDll.dll` (renamed to `CrysisCoop.dll`), compiled via MSBuild / Visual Studio 2022 (`v143` toolset, `Profile|Win32` configuration).
  * **Lua (v5.1)**: Game rules (`Game/Scripts/GameRules/Coop.lua`), Actor scripts (`Game/Scripts/Entities/actor/player.lua`), flowgraph music nodes, and entity events.
  * **Python 3.10+ (Tkinter / PIL / Sockets)**: Custom launcher (`CrysisCoopLauncher.py`) handling peer discovery (UDP 64089), lobby signaling (TCP 64088), visual 5-slot weapon loadouts, and mission launch parameters.
* **Is this on GitHub?**
  * **Yes:** [MaxHavocc/Crysis-CO-OP](https://github.com/MaxHavocc/Crysis-CO-OP) contains the mod source and external Python co-op launcher.
  * Pull `main` on each machine and restart the launcher after updating. Local desktop shortcuts are generated per machine with `Setup_Desktop_Shortcut.ps1`.

---

## 2. System Architecture

```
Crysis Root Directory (C:\Program Files (x86)\Steam\steamapps\common\Crysis)
├── Bin32/
│   ├── Crysis.exe            # 32-bit Crysis executable (runs -mod CrysisCoop)
│   └── CrysisCoop.dll        # [ENGINE TARGET] Built from Code/GameDll.vcxproj
├── Game/
│   ├── Warhead_GameData.pak  # Linked from Warhead (weapon XMLs, equipment packs)
│   └── Levels/               # Campaign levels (island, village, rescue, etc.)
└── Mods/CrysisCoop/          # [PROJECT REPO]
    ├── Code/                 # C++ Source Code (GameDll.sln, GameDll.vcxproj)
    │   ├── Coop/             # Co-op specific actors & networking
    │   │   ├── Actors/       # CoopPlayer.cpp, CoopGrunt.cpp
    │   ├── HUD/              # HUD.cpp (HUD reboot, PDA suppression, US team flag)
    │   ├── Menus/            # FlashMenuObject.cpp (loading theme cleanup)
    │   └── Player.cpp        # Breathing/O2 drowning hooks, cloak scaling
    ├── Game/
    │   ├── Scripts/
    │   │   ├── GameRules/    # Coop.lua (Server/Client mission flow, equips, cvars)
    │   │   ├── Entities/     # player.lua (Perception, AI species recognition)
    │   │   └── Sound/        # MusicThemeSelector.lua (networked music themes)
    │   └── Levels/island/    # Level XML overrides & mission flowgraph tweaks
    ├── weapon_icons/         # High-tech card thumbnails for loadout slots
    └── CrysisCoopLauncher.py # 2-Option Launcher (Host & Join, Lobby Room, 5 Slots)
```

---

## 3. What is Completed & Working ([X] Checklist)

### A. Launcher & Lobby Architecture
* [x] **Streamlined 2-Option Flow**: Main menu contains only **HOST CO-OP** and **JOIN CO-OP**.
* [x] **Interactive Lobby Room**:
  * Real-time peer roster showing Host and connected Squadmates.
  * **5 Tactical Loadout Slots**:
    1. Primary 1 (Assault Rifles, Shotguns, SMGs, Snipers, Minigun)
    2. Primary 2 (Empty or second primary)
    3. Secondary (SOCOM Pistol or Warhead AY69)
    4. Explosives (Frag Grenades, Warhead Claymores, AV Mines, C4)
    5. Launcher (Empty, LAW, Warhead FGL40 Grenade Launcher)
  * **Interactive Slot Cards**: Entire card row, icon, and button are clickable with hover glow.
  * **No-Duplicates Rule**: If a weapon is equipped in one slot, it is locked (`[EQUIPPED IN PRIMARY 1]`) and cannot be selected twice.
  * **Profile Persistence**: Loadouts save to `user_profile.json` and restore automatically.
  * **Peer Synchronization**: Slot changes broadcast live over TCP socket (port 64088) so players see each other's loadouts update in real time.
* [x] **Host Mission & Game Settings**:
  * Host can trigger "New Game: Crysis 1" (starts `island`) or "New Game: Warhead" (starts standalone `ambush`).
  * Full Campaign Selector tabs: 11 Crysis 1 missions and 7 Warhead missions.
  * Modifiers: Difficulty (Easy to Delta), AI Multiplier (1x-3x), Ammo Pool (1x-Infinite), Infinite Underwater O2, and Enable All Attachments.
  * Settings persist to `coop_settings.json` and sync live to clients.
* [x] **Crysis Warhead Integration**:
  * Standalone Warhead binary launching supported from the launcher without mod flags.
  * Warhead `.pak` archives linked so Warhead weapons (`AY69`, `FGL40`, `Claymore`) and accessories are fully usable in Crysis 1 Co-op missions.
  * Ammo pools for all Warhead weapons configured in `Coop.lua` (`ay69bullet`, `fgl40fraggrenade`, `fgl40empgrenade`, `claymoreexplosive`, `avexplosive`).

### B. C++ Engine & Gameplay Overhauls (`CrysisCoop.dll`)
* [x] **Cinematic Input Suppression (`HUD.cpp`)**:
  * Blocked `Tab` and `M` keypresses during cinematics (`m_bCutscenePlaying || m_cineHideHUD`), preventing PDA map from opening over cutscenes.
* [x] **US Team Flag Fix (`HUD.cpp`)**:
  * PDA map team check sets `PlayerTeam` to `"US"` in Co-op, resolving the North Korean flag bug.
* [x] **Threat & Stealth HUD Meter Isolation (`CoopPlayer.cpp`)**:
  * Replaced global AI awareness queries with individual player `IAIObject*` detection (`gEnv->pAISystem->GetDetectionLevels(pAI, aiDetectionLevels)`). One player being spotted no longer spikes the other player's threat meter.
* [x] **AI Target Recognition (`player.lua`)**:
  * Player script enforces `species = 0`, `soclasses_SmartObjectClass = "Player"`, `voiceType = "player"`, and perception parameters so AI treats both host and client as hostile targets immediately without needing to take damage first.
* [x] **AI Distance Sleep Fix (`Coop.lua`)**:
  * Enforced `ai_UpdateAllAlways = 1` on the server so CryAISystem never puts AI to sleep when players move far away from the host.
* [x] **Dual Pistols Bug Fix (`CoopGrunt.cpp`)**:
  * Added inventory check preventing duplicate equipment packs from firing, and stripped unintended slave SOCOMs from Grunts.
* [x] **Music & Audio Transitions (`FlashMenuObject.cpp`, `MusicThemeSelector.lua`, `Coop.lua`)**:
  * Unblocked menu music fadeout in Co-op so loading music stops upon mission start.
  * Networked broadcast `ClSetMusicTheme` synchronizes flowgraph music changes across all clients (fixing missing music in Mission 5 `tank`).
* [x] **Underwater Drowning Hook (`Player.cpp`)**:
  * Hooked `coop_disable_o2` into `UpdateUWBreathing` for infinite underwater oxygen when enabled.

---

## 4. Current Backlog & Open Development Tasks ([ ] To-Do)

1. **Halo Jump / Opening Cinematic Synchronization (`island`)**:
   * *Status*: In progress.
   * *Issue*: Opening C17 jump sequence and alien scout impact have timing discrepancies between host and client depending on loading times.
   * *Target*: Implement a pre-sequence connection barrier (e.g. wait for client packet before starting the sequence flowgraph or spawning players directly at the beach parachute landing site).
2. **First-Person Arms / Weapon Attachment on Connect**:
   * *Status*: Resolved on beach spawn; verify across all 11 missions on initial level load.
3. **Mid-Mission Cutscene Network Barriers**:
   * *Target*: In levels with interactive cinematics (e.g. Village schoolhouse, Excavation site, Temple entrance), ensure both players trigger cinematics simultaneously or freeze non-cinematic players cleanly.
4. **Mission Objective Labels**:
   * *Status*: Some objectives occasionally display internal string keys (e.g. `@objective_2`) instead of localized strings. Verify string table lookups in `HUD.cpp`.

---

## 5. Development & Build Setup Instructions

### Prerequisites
* Windows 10 or 11 (64-bit).
* Visual Studio 2022 Community (with **Desktop development with C++** and the `v143` build tools).
* Python 3.10+ installed with `Pillow`: `pip install Pillow`.
* Steam installation of Crysis 1 (and optionally Crysis Warhead).

### Building `CrysisCoop.dll`
1. Open Developer Command Prompt or PowerShell.
2. Run MSBuild targeting `Code\GameDll.vcxproj`:
   ```bat
   "C:\Program Files\Microsoft Visual Studio\2022\Community\MSBuild\Current\Bin\MSBuild.exe" "C:\Program Files (x86)\Steam\steamapps\common\Crysis\Mods\CrysisCoop\Code\GameDll.vcxproj" /p:Configuration=Profile /p:Platform=Win32 /p:PlatformToolset=v143 /t:Build -verbosity:minimal
   ```
3. Output DLL will be placed in `Bin32\CrysisCoop.dll`.

### Running the Mod
* **One-time setup on each machine:** run `.\Setup_Coop_Runtime.ps1` from this mod folder in PowerShell. It installs the verified x86 C1-Launcher runtime as `<Crysis>\Bin32\CrysisCoop.exe` alongside the original executable, enabling direct connections without the obsolete GameSpy login requirement. See [launcher fixes and setup details](LAUNCHER_FIXES.md).
* **Open the external launcher:** double-click `Play Crysis Co-op.cmd` in this folder. It finds Python 3.10+ with Tkinter and Pillow on your PC and opens `CrysisCoopLauncher.py`.
* **Create the desktop shortcut:** run `.\Setup_Desktop_Shortcut.ps1` in PowerShell from this folder, then double-click **Play Crysis Co-op** on the Desktop. Keep the mod in this folder; rerun the shortcut installer if you move it or change Python installations.
* **Compare launcher builds:** the top bar shows the launcher version and build fingerprint; both should match your co-op partner. Click **Version history** for recent changes. The fingerprint identifies the launcher source, not the engine DLL or installed game files. Restart the launcher after every update.
* If PowerShell blocks a setup script under its default execution policy, run it for this invocation only with `powershell -NoProfile -ExecutionPolicy Bypass -File .\Setup_Desktop_Shortcut.ps1` (or substitute `Setup_Coop_Runtime.ps1` for runtime setup).
* Select **HOST CO-OP** on the host machine, and **JOIN CO-OP** on the squadmate machine.
* Configure your loadouts in the lobby, click Ready, and launch!

### Remote host diagnostics and local AI

The [host development bridge](tools/host_bridge/HOST_BRIDGE.md) provides a one-time Windows OpenSSH setup for a teammate on Radmin VPN. It supports game logs, source/configuration reads, version checks, fast-forward Git updates, project tests/builds, and advice from an existing local Ollama model. Authentication uses a dedicated public key restricted to the developer's VPN address; Ollama stays on localhost. The host runs setup once and shares one connection record. Private SSH keys and connection records stay outside this repository.
