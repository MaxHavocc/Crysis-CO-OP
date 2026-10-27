import os
import subprocess
import time

CRYSIS_DIR = r"C:\Program Files (x86)\Steam\steamapps\common\Crysis"
COOP_DIR = os.path.join(CRYSIS_DIR, "Mods", "CrysisCoop")

# Clean up any lingering instances
subprocess.run(["taskkill", "/f", "/im", "Crysis.exe"], capture_output=True)
subprocess.run(["taskkill", "/f", "/im", "CrysisDedicatedServer.exe"], capture_output=True)
time.sleep(1)

# 1. Start Host using Crysis.exe
host_exe = os.path.join(CRYSIS_DIR, "Bin32", "Crysis.exe")
host_cmd = [
    host_exe,
    "-DEVMODE", "-userpath", "Crysis_Host", "-logfile", "Host.log",
    "-mod", "CrysisCoop", "-novideo", "-dx9",
    "+r_Fullscreen", "0", "+r_Width", "640", "+r_Height", "480",
    "+sv_lanonly", "1", "+sv_port", "64087",
    "+exec", "Mods/CrysisCoop/host.cfg",
    "+map", "island"
]
print("[TEST] Launching Crysis Host on 64087...", flush=True)
s_proc = subprocess.Popen(host_cmd, cwd=CRYSIS_DIR)
time.sleep(15) # Give host time to load island


# 2. Launch Client 1 (Player 1)
client_exe = os.path.join(CRYSIS_DIR, "Bin32", "Crysis.exe")
c1_cmd = [
    client_exe,
    "-DEVMODE", "-userpath", "Crysis_C1", "-logfile", "Client1.log",
    "-mod", "CrysisCoop", "-novideo", "-dx9",
    "+r_Fullscreen", "0", "+r_Width", "800", "+r_Height", "600",
    "+r_displayinfo", "1", "+sv_lanonly", "1",
    "+name", "Nomad",
    "+cl_serverport", "64087", "+connect", "127.0.0.1:64087"
]
print("[TEST] Launching Client 1 (Nomad)...", flush=True)
c1_proc = subprocess.Popen(c1_cmd, cwd=CRYSIS_DIR)
time.sleep(8)

# 3. Launch Client 2 (Player 2)
c2_cmd = [
    client_exe,
    "-DEVMODE", "-userpath", "Crysis_C2", "-logfile", "Client2.log",
    "-mod", "CrysisCoop", "-novideo", "-dx9",
    "+r_Fullscreen", "0", "+r_Width", "800", "+r_Height", "600",
    "+r_displayinfo", "1", "+sv_lanonly", "1",
    "+name", "Psycho",
    "+cl_serverport", "64087", "+connect", "127.0.0.1:64087"
]
print("[TEST] Launching Client 2 (Psycho)...", flush=True)
c2_proc = subprocess.Popen(c2_cmd, cwd=CRYSIS_DIR)

print("[TEST] Both clients launched. Running test for 50 seconds...", flush=True)
time.sleep(50)

# Read logs
for log_name in ["Server.log", "Client1.log", "Client2.log"]:
    p = os.path.join(CRYSIS_DIR, log_name)
    if os.path.exists(p):
        print(f"=== {log_name} (Last 20 lines) ===")
        with open(p, "rb") as f:
            f.seek(max(0, f.seek(0, 2) - 4000))
            chunk = f.read().decode("latin1", errors="ignore")
            for l in chunk.splitlines()[-20:]:
                print(l)


# Clean up
subprocess.run(["taskkill", "/f", "/im", "Crysis.exe"], capture_output=True)
subprocess.run(["taskkill", "/f", "/im", "CrysisDedicatedServer.exe"], capture_output=True)
print("[TEST] Test completed.")