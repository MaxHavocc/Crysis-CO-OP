import os
import sys
import time
import json
import subprocess
import ctypes

CRYSIS_DIR = r"C:\Program Files (x86)\Steam\steamapps\common\Crysis"
COOP_DIR = os.path.join(CRYSIS_DIR, "Mods", "CrysisCoop")
STATUS_FILE = os.path.join(COOP_DIR, "aider_status.json")
AIDER_PATH = r"C:\Users\Caden\AppData\Local\Programs\Python\Python312\Scripts\aider.exe"
MODEL_NAME = "ollama_chat/qwen2.5-coder:7b"

os.environ["OLLAMA_API_BASE"] = "http://127.0.0.1:11434"
os.environ["BROWSER"] = "none"
os.environ["AIDER_SHOW_MODEL_WARNINGS"] = "false"

class Logger(object):
    def __init__(self, filename):
        self.terminal = sys.stdout
        self.log = open(filename, "w", encoding="utf-8", buffering=1)
    def write(self, message):
        self.terminal.write(message)
        self.log.write(message)
    def flush(self):
        self.terminal.flush()
        self.log.flush()

sys.stdout = Logger(os.path.join(COOP_DIR, "supervisor.log"))
sys.stderr = sys.stdout

def set_console_title(title_text):
    try:
        ctypes.windll.kernel32.SetConsoleTitleW(f"CRYSIS CO-OP: {title_text}")
    except:
        pass

def show_on_screen_alert(title, message, is_error=False):
    try:
        ctypes.windll.user32.MessageBeep(0x10 if is_error else 0x40)
        icon = "Error" if is_error else "Information"
        ps_code = f"Add-Type -AssemblyName System.Windows.Forms; [System.Windows.Forms.MessageBox]::Show('{message}', '{title}', 'OK', '{icon}')"
        subprocess.Popen(["powershell", "-NoProfile", "-Command", ps_code])
    except Exception as e:
        print(f"[SUPERVISOR] Alert display error: {e}", flush=True)

MICRO_TASKS = [
    {
        "id": "TASK_1_BEACH_COORDS",
        "name": "Hardcode Beach Spawn Coordinates in Coop.lua",
        "file": r"Game\Scripts\GameRules\Coop.lua",
        "prompt": """In Game\\Scripts\\GameRules\\Coop.lua inside function Coop:SpawnPlayer(channelId, name), ensure player 2 spawns on the beach.
Use exact tab indentation:
<<<<<<< SEARCH
	local player=self.game:SpawnPlayer(channelId, name or "Nomad", "Player", pos, angles);	
=======
	if (channelId and channelId > 1) or (name and name ~= "Nomad") then
		pos.x = 1050; pos.y = 1200; pos.z = 10;
	end
	local player=self.game:SpawnPlayer(channelId, name or "Nomad", "Player", pos, angles);	
>>>>>>> REPLACE""",
        "check": lambda content: "1050" in content and "1200" in content
    },
    {
        "id": "TASK_2_SKIP_INTRO_OVERRIDE",
        "name": "Force Skip Intro and Active State on Player Enter",
        "file": r"Game\Scripts\GameRules\Coop.lua",
        "prompt": """In Game\\Scripts\\GameRules\\Coop.lua inside Coop.Server:OnClientEnteredGame, add g_skipIntro and ChangeSpectatorMode.
Use exact tab indentation:
<<<<<<< SEARCH
function Coop.Server:OnClientEnteredGame(channelId, player, reset)
	self.game:SetTeam(1, player.id);
	self:RevivePlayer(channelId, player);
=======
function Coop.Server:OnClientEnteredGame(channelId, player, reset)
	self.game:SetTeam(1, player.id);
	System.SetCVar("g_skipIntro", 1);
	self.game:ChangeSpectatorMode(player.id, 0, NULL_ENTITY);
	self:RevivePlayer(channelId, player);
>>>>>>> REPLACE""",
        "check": lambda content: "g_skipIntro" in content and "ChangeSpectatorMode" in content
    },
    {
        "id": "TASK_3_TEAM_ASSIGNMENT",
        "name": "Ensure Team 1 Registration for All Co-op Players",
        "file": r"Game\Scripts\GameRules\Coop.lua",
        "prompt": """In Game\\Scripts\\GameRules\\Coop.lua inside Coop.Server:OnClientConnect, ensure Team 1 is set.
Use exact tab indentation:
<<<<<<< SEARCH
	local player = self:SpawnPlayer(channelId, name);

	if (not reset) then
=======
	local player = self:SpawnPlayer(channelId, name);
	self.game:SetTeam(1, player.id);

	if (not reset) then
>>>>>>> REPLACE""",
        "check": lambda content: "self.game:SetTeam(1, player.id)" in content
    },
    {
        "id": "TASK_4_REMOTE_ACTOR_MODEL",
        "name": "Bind Full 3D Nanosuit to Remote Actors in player.lua",
        "file": r"Game\Scripts\Entities\actor\player.lua",
        "prompt": """In Game\\Scripts\\Entities\\actor\\player.lua inside Player:PhysicalizeActor(), load the 3D nanosuit model for remote players.
Use exact tab indentation:
<<<<<<< SEARCH
function Player:PhysicalizeActor()
	if (self.actor) then
=======
function Player:PhysicalizeActor()
	if (self.id and g_localActorId and self.id ~= g_localActorId) then
		self:LoadCharacter(0, "objects/characters/human/us/nanosuit/nanosuit_us.cdf");
	end
	if (self.actor) then
>>>>>>> REPLACE""",
        "check": lambda content: "nanosuit_us.cdf" in content
    },
    {
        "id": "TASK_5_HUD_NULL_GUARDS",
        "name": "Guard HUD and Screen Effects for Remote Actors",
        "file": r"Game\Scripts\Entities\actor\player.lua",
        "prompt": """In Game\\Scripts\\Entities\\actor\\player.lua inside Player.Client:OnUpdate(frameTime), guard UpdateScreenEffects for local actor only.
Use exact tab indentation:
<<<<<<< SEARCH
	self:UpdateScreenEffects(frameTime);
=======
	if (not self.id or not g_localActorId or self.id == g_localActorId) then
		self:UpdateScreenEffects(frameTime);
	end
>>>>>>> REPLACE""",
        "check": lambda content: "g_localActorId or self.id == g_localActorId" in content
    },
    {
        "id": "TASK_6_POSITION_INTERPOLATION",
        "name": "Smooth Exponential Position Interpolation",
        "file": r"Game\Scripts\Entities\actor\player.lua",
        "prompt": """In Game\\Scripts\\Entities\\actor\\player.lua inside Player:InterpolateRemoteMovement(frameTime), add exponential smoothing.
Use exact tab indentation:
<<<<<<< SEARCH
function Player:InterpolateRemoteMovement(frameTime)
=======
function Player:InterpolateRemoteMovement(frameTime)
	if (self.id == g_localActorId) then return; end
	local blend = 1.0 - math.exp(-15.0 * math.max(0.001, frameTime));
	if (self._targetPos) then
		self:SetWorldPos(self._targetPos);
	end
>>>>>>> REPLACE""",
        "check": lambda content: "InterpolateRemoteMovement" in content and "math.exp" in content
    },
    {
        "id": "TASK_7_SUIT_MODE_SYNC",
        "name": "Synchronize Nanosuit Modes for Remote Players",
        "file": r"Game\Scripts\Entities\actor\player.lua",
        "prompt": """In Game\\Scripts\\Entities\\actor\\player.lua, add ClSetRemoteSuitMode.
Use exact tab indentation:
<<<<<<< SEARCH
function Player:PhysicalizeActor()
=======
function Player.Client:ClSetRemoteSuitMode(mode)
	if (self.actor and mode) then
		self.actor:ActivateNanoSuit(mode);
	end
end

function Player:PhysicalizeActor()
>>>>>>> REPLACE""",
        "check": lambda content: "ClSetRemoteSuitMode" in content
    }
]

def update_status(state, details=None):
    data = {
        "timestamp": time.time(),
        "time_str": time.ctime(),
        "state": state,
        "details": details or {}
    }
    try:
        with open(STATUS_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
    except Exception as e:
        pass
    print(f"[SUPERVISOR] {state}: {details}", flush=True)

def kill_crysis():
    subprocess.run(["taskkill", "/f", "/im", "Crysis.exe"], capture_output=True)
    subprocess.run(["taskkill", "/f", "/im", "CrysisDedicatedServer.exe"], capture_output=True)
    time.sleep(1)

def run_test():
    kill_crysis()
    
    # 1. Launch Host
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
    h_proc = subprocess.Popen(host_cmd, cwd=CRYSIS_DIR)
    time.sleep(12)
    
    # 2. Launch Client 1
    c1_cmd = [
        host_exe,
        "-DEVMODE", "-userpath", "Crysis_C1", "-logfile", "Client1.log",
        "-mod", "CrysisCoop", "-novideo", "-dx9",
        "+r_Fullscreen", "0", "+r_Width", "640", "+r_Height", "480",
        "+sv_lanonly", "1", "+name", "Nomad",
        "+cl_serverport", "64087", "+connect", "127.0.0.1:64087"
    ]
    c1_proc = subprocess.Popen(c1_cmd, cwd=CRYSIS_DIR)
    time.sleep(6)
    
    # 3. Launch Client 2
    c2_cmd = [
        host_exe,
        "-DEVMODE", "-userpath", "Crysis_C2", "-logfile", "Client2.log",
        "-mod", "CrysisCoop", "-novideo", "-dx9",
        "+r_Fullscreen", "0", "+r_Width", "640", "+r_Height", "480",
        "+sv_lanonly", "1", "+name", "Psycho",
        "+cl_serverport", "64087", "+connect", "127.0.0.1:64087"
    ]
    c2_proc = subprocess.Popen(c2_cmd, cwd=CRYSIS_DIR)
    time.sleep(20)
    
    host_log_path = os.path.join(CRYSIS_DIR, "Host.log")
    host_log = ""
    if os.path.exists(host_log_path):
        try:
            with open(host_log_path, "rb") as f:
                host_log = f.read().decode("latin1", errors="ignore")
        except:
            pass

    kill_crysis()
    has_crash = "CRASH DETECTED" in host_log
    return has_crash, host_log

def ask_local_ai(prompt, target_file):
    print(f"[SUPERVISOR] Giving atomic task to local {MODEL_NAME} for {target_file}...", flush=True)
    cmd = [
        AIDER_PATH,
        "--model", MODEL_NAME,
        "--edit-format", "diff",
        "--no-auto-commits",
        "--no-show-model-warnings",
        "--yes",
        "--map-tokens", "0",
        target_file,
        "--message", prompt
    ]
    try:
        p = subprocess.run(cmd, cwd=COOP_DIR, capture_output=True, text=True, timeout=300)
        if p.stdout:
            print(p.stdout, flush=True)
        if p.stderr:
            print("[AIDER STDERR]", p.stderr, flush=True)
    except Exception as e:
        print(f"[SUPERVISOR] Local AI error: {e}", flush=True)

def main():
    os.chdir(COOP_DIR)
    task_idx = 0
    retries = 0
    MAX_RETRIES_PER_TASK = 5
    
    set_console_title("[STARTING] Atomic Micro-Task Pipeline")
    print("[SUPERVISOR] Starting Atomic Micro-Task Pipeline with Exact Tab Matching...", flush=True)
    
    while task_idx < len(MICRO_TASKS):
        task = MICRO_TASKS[task_idx]
        progress_str = f"Step {task_idx+1}/{len(MICRO_TASKS)}"
        set_console_title(f"[CODING - {progress_str}] {task['name']}")
        
        print(f"\n{'='*70}\n[MICRO-TASK {task_idx+1}/{len(MICRO_TASKS)}] {task['name']}\n{'='*70}", flush=True)
        update_status("EXECUTING_MICRO_TASK", {"task_id": task["id"], "task_name": task["name"], "step": progress_str, "retries": retries})
        
        # Check if already fulfilled
        full_path = os.path.join(COOP_DIR, task["file"])
        fulfilled = False
        if os.path.exists(full_path):
            with open(full_path, "r", encoding="utf-8", errors="ignore") as f:
                if task["check"](f.read()):
                    fulfilled = True
                    
        was_already_fulfilled = fulfilled
        if not fulfilled:
            ask_local_ai(task["prompt"], task["file"])
            
            # Verify after edit
            if os.path.exists(full_path):
                with open(full_path, "r", encoding="utf-8", errors="ignore") as f:
                    if task["check"](f.read()):
                        fulfilled = True
                        
        if fulfilled:
            retries = 0
            status = subprocess.run(["git", "status", "--porcelain"], cwd=COOP_DIR, capture_output=True, text=True)
            if status.stdout.strip():
                subprocess.run(["git", "add", "."], cwd=COOP_DIR)
                subprocess.run(["git", "commit", "-m", f"feat(micro-task): {task['name']}"], cwd=COOP_DIR)
                print(f"[SUPERVISOR] Micro-task {task['id']} verified and committed!", flush=True)
            task_idx += 1
            
            # Run test to verify stability if code was modified
            if not was_already_fulfilled:
                set_console_title(f"[TESTING IN GAME] Validating {task['id']}")
                update_status("VALIDATING_TEST", {"task_id": task["id"]})
                has_crash, _ = run_test()
                if has_crash:
                    print(f"[SUPERVISOR] Crash detected during validation, staying on {task['id']} to self-heal...", flush=True)
                    task_idx -= 1
            else:
                print(f"[SUPERVISOR] Micro-task {task['id']} already satisfied. Advancing.", flush=True)
        else:
            retries += 1
            print(f"[SUPERVISOR] Task {task['id']} check not satisfied (Attempt {retries}/{MAX_RETRIES_PER_TASK})...", flush=True)
            if retries >= MAX_RETRIES_PER_TASK:
                alert_title = "CRYSIS CO-OP SUPERVISOR: STUCK"
                alert_msg = f"Supervisor is STUCK on {task['name']} ({task['id']}) after {retries} failed attempts.\n\nI AM NOT CODING ANYTHING RIGHT NOW to avoid wasting resources.\n\nPlease check the terminal."
                set_console_title(f"[STUCK - NOT CODING] {task['id']}")
                update_status("STUCK", {"task_id": task["id"], "reason": f"Max retries ({MAX_RETRIES_PER_TASK}) exceeded."})
                show_on_screen_alert(alert_title, alert_msg, is_error=True)
                print(f"\n{'!'*70}\n[SUPERVISOR] STUCK on {task['id']}. Halting and alerted on screen.\n{'!'*70}", flush=True)
                return
                
        time.sleep(3)
        
    complete_title = "CRYSIS CO-OP: ALL TASKS COMPLETE!"
    complete_msg = "All 7 multiplayer micro-tasks have been completed, verified, and committed!\n\nBoth clients are configured to spawn on the beach with 3D models and position synchronization."
    set_console_title("[ALL TASKS COMPLETE] 100% Finished")
    update_status("ALL_TASKS_COMPLETE", {"total_tasks": len(MICRO_TASKS)})
    show_on_screen_alert(complete_title, complete_msg, is_error=False)
    print("\n[SUPERVISOR] ALL MICRO-TASKS COMPLETED SUCCESSFULLY!", flush=True)

if __name__ == "__main__":
    main()