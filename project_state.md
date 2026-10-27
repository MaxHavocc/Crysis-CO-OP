# CRYSIS 1 CO-OP LAN MULTIPLAYER MOD — PROJECT STATE & HANDOFF

## 1. Project Overview & Goal
* **Game:** Crysis 1 (2007, 32-bit DirectX 9 release build 6156, CryEngine 2).
* **Mod:** `CrysisCoop` (based on Crysis Co-op mod source by the community).
* **Network Model:** LAN Listen Server.
  * **Host (Laptop):** `192.168.88.36` — Runs server on UDP `0.0.0.0:64087`, gamerules `Coop`, map `island` (Mission 1 Contact).
  * **Client (Desktop):** `192.168.88.18` — Connects outbound via `+connect 192.168.88.36:64087`.
* **Primary Objective:** Two players spawn together on the beach in first-person view, see each other's 3D nanosuit character models, replicate