# -*- coding: utf-8 -*-
"""
Crysis & Crysis Warhead Co-op Launcher
Pure Two-Option Flow: HOST and JOIN
Interactive Lobby Room with real-time peer slot loadouts and host mission/settings control.
"""

import os
import sys
import time
import json
import socket
import threading
import subprocess
import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
from PIL import Image, ImageTk, ImageDraw

try:
    import ctypes
    ctypes.windll.shcore.SetProcessDpiAwareness(1)
except Exception:
    pass

CRYSIS_MOD_DIR = os.path.dirname(os.path.abspath(__file__))
CRYSIS_ROOT_DIR = os.path.abspath(os.path.join(CRYSIS_MOD_DIR, "..", ".."))
CRYSIS_WARHEAD_DIR = r"C:\Program Files (x86)\Steam\steamapps\common\Crysis Warhead"
ICONS_DIR = os.path.join(CRYSIS_MOD_DIR, "weapon_icons")
PROFILE_FILE = os.path.join(CRYSIS_MOD_DIR, "user_profile.json")
SETTINGS_FILE = os.path.join(CRYSIS_MOD_DIR, "coop_settings.json")
SAVES_DIR = os.path.join(CRYSIS_MOD_DIR, "Saves")

DEFAULT_PORT = 64088
DISCOVERY_PORT = 64089

CRYSIS_MISSIONS = [
    ("Contact", "island", "Beach landing and initial scout contact"),
    ("Recovery", "village", "Village hostage recovery operation"),
    ("Relic", "rescue", "Search for Prophet and ancient relics"),
    ("Assault", "harbor", "Harbor strike and naval bombardment"),
    ("Onslaught", "tank", "Armor assault through train station"),
    ("Awakening", "mine", "Infiltrating the mountain quarry and mine"),
    ("Core", "core", "Zero-gravity alien temple interior"),
    ("Paradise Lost", "lost", "Frozen paradise escape from alien ice sphere"),
    ("Exodus", "sphere", "Escort VTOL extraction from freezing canyon"),
    ("Ascension", "ascension", "Piloting VTOL through canyon tornadoes"),
    ("Reckoning", "fleet", "Final battle aboard aircraft carrier USS Constitution"),
]

WARHEAD_MISSIONS = [
    ("Call Me Ishmael", "ambush", "Psycho's beach ambush & resort advance"),
    ("Shore Leave", "cargo", "Pursuing Colonel Lee's cargo submarine"),
    ("Adapt or Perish", "avalanche", "Hovercraft ice assault through frozen rivers"),
    ("Frozen Paradise", "frost", "Infiltrating the frozen radar base & mine"),
    ("Below the Thunder", "cave", "Subterranean mines & train tunnels"),
    ("From Hell's Heart", "train", "Defending the munitions train shipment"),
    ("All the Fury", "airfield", "Final battle at the airfield for the container"),
]

# Slot definitions
SLOT_CONFIGS = [
    {
        "id": "primary1",
        "name": "PRIMARY 1",
        "default": "SCAR",
        "allow_empty": False,
        "weapons": ["SCAR", "FY71", "Shotgun", "SMG", "AY69", "DSG1", "Hurricane"]
    },
    {
        "id": "primary2",
        "name": "PRIMARY 2",
        "default": "None",
        "allow_empty": True,
        "weapons": ["None", "SCAR", "FY71", "Shotgun", "SMG", "AY69", "DSG1", "Hurricane"]
    },
    {
        "id": "secondary",
        "name": "SECONDARY",
        "default": "SOCOM",
        "allow_empty": False,
        "weapons": ["SOCOM", "AY69"]
    },
    {
        "id": "explosive",
        "name": "EXPLOSIVES",
        "default": "Frag Grenade",
        "allow_empty": False,
        "weapons": ["Frag Grenade", "Claymore", "AVMine", "C4"]
    },
    {
        "id": "heavy",
        "name": "LAUNCHER",
        "default": "None",
        "allow_empty": True,
        "weapons": ["None", "LAW", "FGL40"]
    }
]

WEAPON_METADATA = {
    "SCAR": {"name": "SCAR", "label": "SCAR Assault Rifle", "cat": "Assault", "color": "#3eb6e6", "warhead": False},
    "FY71": {"name": "FY71", "label": "FY71 Rifle", "cat": "Assault", "color": "#df9435", "warhead": False},
    "Shotgun": {"name": "Shotgun", "label": "Shotgun", "cat": "Shotgun", "color": "#2ec67f", "warhead": False},
    "SMG": {"name": "SMG", "label": "Submachine Gun", "cat": "SMG", "color": "#3eb6e6", "warhead": False},
    "AY69": {"name": "AY69", "label": "AY69 Machine Pistol", "cat": "Warhead SMG", "color": "#e63e6b", "warhead": True},
    "DSG1": {"name": "DSG1", "label": "DSG1 Sniper Rifle", "cat": "Sniper", "color": "#a26be6", "warhead": False},
    "Hurricane": {"name": "Hurricane", "label": "Hurricane Minigun", "cat": "Heavy", "color": "#df9435", "warhead": False},
    "LAW": {"name": "LAW", "label": "LAW Missile Launcher", "cat": "Launcher", "color": "#e63e3e", "warhead": False},
    "FGL40": {"name": "FGL40", "label": "FGL40 Grenade Launcher", "cat": "Warhead Heavy", "color": "#e6a23e", "warhead": True},
    "SOCOM": {"name": "SOCOM", "label": "SOCOM .45 Pistol", "cat": "Sidearm", "color": "#3eb6e6", "warhead": False},
    "Claymore": {"name": "Claymore", "label": "Claymore Mine", "cat": "Warhead Mine", "color": "#e63e6b", "warhead": True},
    "AVMine": {"name": "AVMine", "label": "Anti-Vehicle Mine", "cat": "Explosive", "color": "#df9435", "warhead": False},
    "C4": {"name": "C4", "label": "C4 Demolition Charge", "cat": "Explosive", "color": "#2ec67f", "warhead": False},
    "Frag Grenade": {"name": "Frag Grenade", "label": "Frag Grenades (x3)", "cat": "Explosive", "color": "#2ec67f", "warhead": False},
    "None": {"name": "None", "label": "Empty Weapon Slot", "cat": "Empty", "color": "#50657c", "warhead": False},
}

DEFAULT_LOADOUT = {
    "primary1": "SCAR",
    "primary2": "None",
    "secondary": "SOCOM",
    "explosive": "Frag Grenade",
    "heavy": "None"
}

DIFFICULTIES = [
    ("Easy", 1),
    ("Normal", 2),
    ("Hard", 3),
    ("Delta", 4)
]

ENEMY_MULTIPLIERS = [1.0, 1.5, 2.0, 3.0]
AMMO_MULTIPLIERS = [1, 2, 3, 999]

class CrysisTheme:
    BG_DARK = "#080c12"
    BG_PANEL = "#0e1520"
    BG_INPUT = "#141f2e"
    BG_CARD = "#111b27"
    BORDER = "#1c2d42"
    BORDER_LIGHT = "#2b4566"
    TEXT_MAIN = "#d6e2ed"
    TEXT_MUTED = "#6f88a3"
    CYAN_ACCENT = "#3eb6e6"
    GREEN_ACCENT = "#2ec67f"
    AMBER_ACCENT = "#df9435"
    RED_ACCENT = "#e63e3e"
    WARHEAD_ACCENT = "#e63e6b"
    FONT_TITLE = "Trebuchet MS"
    FONT_UI = "Segoe UI"
    FONT_MONO = "Consolas"

def get_network_ips():
    ips = []
    try:
        hostname = socket.gethostname()
        for ip in socket.gethostbyname_ex(hostname)[2]:
            if not ip.startswith("127."):
                ips.append(ip)
    except Exception:
        pass
    if not ips:
        ips.append("127.0.0.1")
    return ips

def load_profile():
    if os.path.exists(PROFILE_FILE):
        try:
            with open(PROFILE_FILE, "r", encoding="utf-8") as f:
                d = json.load(f)
                if "loadout" not in d:
                    d["loadout"] = dict(DEFAULT_LOADOUT)
                return d
        except Exception:
            pass
    return {"callsign": "Nomad", "loadout": dict(DEFAULT_LOADOUT)}

def save_profile(data):
    try:
        with open(PROFILE_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4)
    except Exception:
        pass

def load_settings():
    defaults = {
        "difficulty": 2,
        "enemy_multiplier": 1.0,
        "ammo_multiplier": 1,
        "disable_drowning": True,
        "enable_all_attachments": True,
        "game": "crysis",
        "mission_code": "island",
        "mission_title": "Contact",
        "mission_mode": "new_game",
    }
    if os.path.exists(SETTINGS_FILE):
        try:
            with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
                d = json.load(f)
                defaults.update(d)
        except Exception:
            pass
    return defaults

def save_settings(data):
    try:
        with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4)
    except Exception:
        pass

class CrysisCoopLauncher(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Crysis & Warhead Co-op Launcher")
        self.geometry("1180x760")
        self.minsize(1050, 680)
        self.configure(bg=CrysisTheme.BG_DARK)

        self.profile = load_profile()
        self.settings = load_settings()

        # Network State
        self.is_host = False
        self.is_connected = False
        self.is_ready = False
        self.server_sock = None
        self.client_sock = None
        self.host_clients = []
        self.remote_players = {}  # callsign -> {"is_host": bool, "ready": bool, "loadout": dict}

        # Cached weapon images
        self.weapon_images = {}
        self.load_weapon_icons()

        self.setup_styles()
        self.build_ui()

        # Start background UDP discovery listener
        self.stop_threads = False
        self.udp_thread = threading.Thread(target=self.udp_discovery_listener, daemon=True)
        self.udp_thread.start()

    def setup_styles(self):
        self.style = ttk.Style(self)
        self.style.theme_use("clam")
        self.style.configure(".", background=CrysisTheme.BG_DARK, foreground=CrysisTheme.TEXT_MAIN)
        self.style.configure("TScrollbar", background=CrysisTheme.BG_INPUT, troughcolor=CrysisTheme.BG_DARK, borderwidth=0)

    def load_weapon_icons(self):
        for w_id in WEAPON_METADATA.keys():
            fname = w_id.replace(" ", "") + ".png"
            path = os.path.join(ICONS_DIR, fname)
            if os.path.exists(path):
                try:
                    im = Image.open(path)
                    im_thumb = im.resize((150, 82), Image.Resampling.LANCZOS)
                    self.weapon_images[w_id] = ImageTk.PhotoImage(im_thumb)
                except Exception:
                    pass

    def build_ui(self):
        # 1. Top Header Bar
        self.top_bar = tk.Frame(self, bg=CrysisTheme.BG_PANEL, height=64, bd=0, highlightthickness=1,
                                highlightbackground=CrysisTheme.BORDER)
        self.top_bar.pack(fill="x", side="top")
        self.top_bar.pack_propagate(False)

        # Title
        title_box = tk.Frame(self.top_bar, bg=CrysisTheme.BG_PANEL)
        title_box.pack(side="left", padx=20, pady=8)

        lbl_title = tk.Label(title_box, text="CRYSIS // CO-OP OPERATIONS",
                             font=(CrysisTheme.FONT_TITLE, 15, "bold"),
                             fg=CrysisTheme.CYAN_ACCENT, bg=CrysisTheme.BG_PANEL)
        lbl_title.pack(anchor="w")

        lbl_sub = tk.Label(title_box, text="MULTIPLAYER CO-OP PLATFORM",
                           font=(CrysisTheme.FONT_UI, 8),
                           fg=CrysisTheme.TEXT_MUTED, bg=CrysisTheme.BG_PANEL)
        lbl_sub.pack(anchor="w")

        # Network IP & Callsign info on right
        info_box = tk.Frame(self.top_bar, bg=CrysisTheme.BG_PANEL)
        info_box.pack(side="right", padx=20)

        # Callsign badge
        callsign_btn = tk.Button(info_box, text=f"CALLSIGN: {self.profile.get('callsign', 'Nomad')} ✎",
                                 font=(CrysisTheme.FONT_UI, 10, "bold"),
                                 fg=CrysisTheme.CYAN_ACCENT, bg=CrysisTheme.BG_INPUT,
                                 activebackground=CrysisTheme.BORDER_LIGHT,
                                 bd=1, relief="solid", padx=10, pady=4,
                                 command=self.prompt_callsign)
        callsign_btn.pack(side="right", padx=6)
        self.btn_callsign = callsign_btn

        ips = get_network_ips()
        ip_text = f"LAN IP: {ips[0]}" if ips else "OFFLINE"
        lbl_ip = tk.Label(info_box, text=ip_text, font=(CrysisTheme.FONT_MONO, 9),
                          fg=CrysisTheme.TEXT_MUTED, bg=CrysisTheme.BG_PANEL)
        lbl_ip.pack(side="right", padx=10)

        # 2. Main Content Container
        self.content_area = tk.Frame(self, bg=CrysisTheme.BG_DARK)
        self.content_area.pack(fill="both", expand=True)

        # Build Views
        self.build_landing_view()
        self.build_host_setup_view()
        self.build_join_browser_view()
        self.build_lobby_room_view()

        # Start on landing view
        self.show_landing_view()

    def hide_all_views(self):
        for v in [self.landing_frame, self.host_setup_frame, self.join_browser_frame, self.lobby_room_frame]:
            v.pack_forget()

    def show_landing_view(self):
        self.hide_all_views()
        self.landing_frame.pack(fill="both", expand=True)

    def show_host_setup_view(self):
        self.hide_all_views()
        self.host_setup_frame.pack(fill="both", expand=True)

    def show_join_browser_view(self):
        self.hide_all_views()
        self.join_browser_frame.pack(fill="both", expand=True)
        self.refresh_lobbies_thread()

    def show_lobby_room_view(self):
        self.hide_all_views()
        self.lobby_room_frame.pack(fill="both", expand=True)
        self.update_lobby_room_ui()

    def prompt_callsign(self):
        cur = self.profile.get("callsign", "Nomad")
        new_name = simpledialog.askstring("Player Callsign", "Enter your multiplayer callsign:",
                                          parent=self, initialvalue=cur)
        if new_name and new_name.strip():
            self.profile["callsign"] = new_name.strip()[:16]
            save_profile(self.profile)
            self.btn_callsign.config(text=f"CALLSIGN: {self.profile['callsign']} ✎")
            if self.is_connected or self.is_host:
                self.broadcast_loadout_update()
            self.update_lobby_room_ui()

    # =========================================================================
    # VIEW 1: LANDING VIEW (TWO CHOICES: HOST AND JOIN ONLY)
    # =========================================================================
    def build_landing_view(self):
        self.landing_frame = tk.Frame(self.content_area, bg=CrysisTheme.BG_DARK)

        center_box = tk.Frame(self.landing_frame, bg=CrysisTheme.BG_DARK)
        center_box.place(relx=0.5, rely=0.48, anchor="center")

        lbl_prompt = tk.Label(center_box, text="SELECT CO-OP ROLE",
                              font=(CrysisTheme.FONT_TITLE, 18, "bold"),
                              fg=CrysisTheme.TEXT_MAIN, bg=CrysisTheme.BG_DARK)
        lbl_prompt.pack(pady=(0, 24))

        buttons_row = tk.Frame(center_box, bg=CrysisTheme.BG_DARK)
        buttons_row.pack()

        # 1. HOST OPTION
        host_card = tk.Frame(buttons_row, bg=CrysisTheme.BG_PANEL, bd=1, relief="solid",
                             highlightbackground=CrysisTheme.BORDER, highlightthickness=2,
                             width=380, height=360)
        host_card.pack(side="left", padx=20)
        host_card.pack_propagate(False)

        # Accent bar
        bar_host = tk.Frame(host_card, bg=CrysisTheme.CYAN_ACCENT, height=4)
        bar_host.pack(fill="x", side="top")

        lbl_host_badge = tk.Label(host_card, text="SERVER / SQUAD LEADER",
                                  font=(CrysisTheme.FONT_MONO, 9, "bold"),
                                  fg=CrysisTheme.CYAN_ACCENT, bg=CrysisTheme.BG_PANEL)
        lbl_host_badge.pack(anchor="w", padx=24, pady=(20, 4))

        lbl_host_title = tk.Label(host_card, text="HOST CO-OP",
                                  font=(CrysisTheme.FONT_TITLE, 24, "bold"),
                                  fg=CrysisTheme.TEXT_MAIN, bg=CrysisTheme.BG_PANEL)
        lbl_host_title.pack(anchor="w", padx=24)

        desc_host = ("Establish a dedicated squad lobby.\n\n"
                     "• Start New Game for Crysis 1 or Warhead\n"
                     "• Select any mission from either campaign\n"
                     "• Customize AI counts, difficulty & modifiers\n"
                     "• Customize and sync loadouts in real-time")
        lbl_host_desc = tk.Label(host_card, text=desc_host, font=(CrysisTheme.FONT_UI, 10),
                                 fg=CrysisTheme.TEXT_MUTED, bg=CrysisTheme.BG_PANEL,
                                 justify="left")
        lbl_host_desc.pack(anchor="w", padx=24, pady=16)

        btn_host_action = tk.Button(host_card, text="HOST LOBBY  ▶",
                                    font=(CrysisTheme.FONT_UI, 12, "bold"),
                                    fg="#ffffff", bg=CrysisTheme.CYAN_ACCENT,
                                    activebackground="#2aa4d4", activeforeground="#ffffff",
                                    bd=0, relief="flat", cursor="hand2", pady=10,
                                    command=self.show_host_setup_view)
        btn_host_action.pack(side="bottom", fill="x", padx=24, pady=24)

        # 2. JOIN OPTION
        join_card = tk.Frame(buttons_row, bg=CrysisTheme.BG_PANEL, bd=1, relief="solid",
                             highlightbackground=CrysisTheme.BORDER, highlightthickness=2,
                             width=380, height=360)
        join_card.pack(side="left", padx=20)
        join_card.pack_propagate(False)

        # Accent bar
        bar_join = tk.Frame(join_card, bg=CrysisTheme.GREEN_ACCENT, height=4)
        bar_join.pack(fill="x", side="top")

        lbl_join_badge = tk.Label(join_card, text="CLIENT / SQUADMATE",
                                  font=(CrysisTheme.FONT_MONO, 9, "bold"),
                                  fg=CrysisTheme.GREEN_ACCENT, bg=CrysisTheme.BG_PANEL)
        lbl_join_badge.pack(anchor="w", padx=24, pady=(20, 4))

        lbl_join_title = tk.Label(join_card, text="JOIN CO-OP",
                                  font=(CrysisTheme.FONT_TITLE, 24, "bold"),
                                  fg=CrysisTheme.TEXT_MAIN, bg=CrysisTheme.BG_PANEL)
        lbl_join_title.pack(anchor="w", padx=24)

        desc_join = ("Connect to an active squad lobby.\n\n"
                     "• Browse active lobbies on LAN / VPN\n"
                     "• Connect directly via Host IP\n"
                     "• Coordinate weapon loadouts with host\n"
                     "• Seamless client synchronization")
        lbl_join_desc = tk.Label(join_card, text=desc_join, font=(CrysisTheme.FONT_UI, 10),
                                 fg=CrysisTheme.TEXT_MUTED, bg=CrysisTheme.BG_PANEL,
                                 justify="left")
        lbl_join_desc.pack(anchor="w", padx=24, pady=16)

        btn_join_action = tk.Button(join_card, text="FIND LOBBIES  ▶",
                                    font=(CrysisTheme.FONT_UI, 12, "bold"),
                                    fg="#ffffff", bg=CrysisTheme.GREEN_ACCENT,
                                    activebackground="#25a76b", activeforeground="#ffffff",
                                    bd=0, relief="flat", cursor="hand2", pady=10,
                                    command=self.show_join_browser_view)
        btn_join_action.pack(side="bottom", fill="x", padx=24, pady=24)

    # =========================================================================
    # VIEW 2: HOST SETUP MODAL / PANEL
    # =========================================================================
    def build_host_setup_view(self):
        self.host_setup_frame = tk.Frame(self.content_area, bg=CrysisTheme.BG_DARK)

        card = tk.Frame(self.host_setup_frame, bg=CrysisTheme.BG_PANEL, bd=1, relief="solid",
                        highlightbackground=CrysisTheme.BORDER, highlightthickness=1,
                        width=520, height=440)
        card.place(relx=0.5, rely=0.5, anchor="center")
        card.pack_propagate(False)

        bar = tk.Frame(card, bg=CrysisTheme.CYAN_ACCENT, height=4)
        bar.pack(fill="x", side="top")

        lbl_h = tk.Label(card, text="HOST SQUAD LOBBY", font=(CrysisTheme.FONT_TITLE, 18, "bold"),
                         fg=CrysisTheme.TEXT_MAIN, bg=CrysisTheme.BG_PANEL)
        lbl_h.pack(anchor="w", padx=28, pady=(24, 4))

        lbl_s = tk.Label(card, text="Configure your network lobby parameters to begin",
                         font=(CrysisTheme.FONT_UI, 10), fg=CrysisTheme.TEXT_MUTED, bg=CrysisTheme.BG_PANEL)
        lbl_s.pack(anchor="w", padx=28, pady=(0, 20))

        # Lobby Name
        tk.Label(card, text="LOBBY NAME", font=(CrysisTheme.FONT_MONO, 9, "bold"),
                 fg=CrysisTheme.CYAN_ACCENT, bg=CrysisTheme.BG_PANEL).pack(anchor="w", padx=28)
        self.ent_lobby_name = tk.Entry(card, font=(CrysisTheme.FONT_UI, 11), bg=CrysisTheme.BG_INPUT,
                                       fg=CrysisTheme.TEXT_MAIN, bd=1, relief="solid",
                                       highlightbackground=CrysisTheme.BORDER, insertbackground="#ffffff")
        self.ent_lobby_name.pack(fill="x", padx=28, pady=(4, 16))
        callsign = self.profile.get("callsign", "Nomad")
        self.ent_lobby_name.insert(0, f"{callsign}'s Squad")

        # Network IP Interface
        tk.Label(card, text="HOST NETWORK INTERFACE", font=(CrysisTheme.FONT_MONO, 9, "bold"),
                 fg=CrysisTheme.CYAN_ACCENT, bg=CrysisTheme.BG_PANEL).pack(anchor="w", padx=28)
        ips = get_network_ips()
        self.host_ip_var = tk.StringVar(value=ips[0] if ips else "127.0.0.1")
        self.cbo_host_ips = ttk.Combobox(card, textvariable=self.host_ip_var, values=ips, state="readonly",
                                         font=(CrysisTheme.FONT_MONO, 10))
        self.cbo_host_ips.pack(fill="x", padx=28, pady=(4, 16))

        # Port Info
        tk.Label(card, text="SIGNALING PORT: 64088 (GAME PORT: 64087)", font=(CrysisTheme.FONT_MONO, 8),
                 fg=CrysisTheme.TEXT_MUTED, bg=CrysisTheme.BG_PANEL).pack(anchor="w", padx=28, pady=(0, 20))

        # Action Buttons
        btn_box = tk.Frame(card, bg=CrysisTheme.BG_PANEL)
        btn_box.pack(fill="x", padx=28, side="bottom", pady=28)

        btn_cancel = tk.Button(btn_box, text="◀ CANCEL", font=(CrysisTheme.FONT_UI, 10, "bold"),
                               fg=CrysisTheme.TEXT_MUTED, bg=CrysisTheme.BG_INPUT,
                               bd=1, relief="solid", padx=16, pady=8, cursor="hand2",
                               command=self.show_landing_view)
        btn_cancel.pack(side="left")

        btn_confirm = tk.Button(btn_box, text="CREATE & ENTER LOBBY  ▶", font=(CrysisTheme.FONT_UI, 11, "bold"),
                                fg="#ffffff", bg=CrysisTheme.CYAN_ACCENT,
                                activebackground="#2aa4d4", activeforeground="#ffffff",
                                bd=0, relief="flat", padx=20, pady=8, cursor="hand2",
                                command=self.action_create_host_lobby)
        btn_confirm.pack(side="right")

    def action_create_host_lobby(self):
        lobby_name = self.ent_lobby_name.get().strip() or f"{self.profile.get('callsign', 'Nomad')}'s Squad"
        bind_ip = self.host_ip_var.get().strip()

        # Stop any existing server
        self.stop_hosting()

        try:
            self.server_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.server_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.server_sock.bind((bind_ip, DEFAULT_PORT))
            self.server_sock.listen(5)
            self.is_host = True
            self.is_connected = True
            self.is_ready = True
            self.host_clients = []
            self.remote_players = {}

            # Start listener thread
            threading.Thread(target=self.host_accept_loop, daemon=True).start()

            # Start UDP broadcast registration loop
            threading.Thread(target=self.register_lobby_loop, args=(lobby_name, bind_ip), daemon=True).start()

            self.show_lobby_room_view()
        except Exception as e:
            messagebox.showerror("Host Error", f"Failed to start lobby server on {bind_ip}:{DEFAULT_PORT}\n{e}",
                                 parent=self)

    # =========================================================================
    # VIEW 3: JOIN BROWSER PANEL
    # =========================================================================
    def build_join_browser_view(self):
        self.join_browser_frame = tk.Frame(self.content_area, bg=CrysisTheme.BG_DARK)

        header = tk.Frame(self.join_browser_frame, bg=CrysisTheme.BG_DARK)
        header.pack(fill="x", padx=32, pady=(24, 12))

        btn_back = tk.Button(header, text="◀ BACK", font=(CrysisTheme.FONT_UI, 9, "bold"),
                             fg=CrysisTheme.TEXT_MUTED, bg=CrysisTheme.BG_PANEL,
                             bd=1, relief="solid", padx=12, pady=4, cursor="hand2",
                             command=self.show_landing_view)
        btn_back.pack(side="left")

        lbl_t = tk.Label(header, text="AVAILABLE SQUAD LOBBIES", font=(CrysisTheme.FONT_TITLE, 16, "bold"),
                         fg=CrysisTheme.TEXT_MAIN, bg=CrysisTheme.BG_DARK)
        lbl_t.pack(side="left", padx=16)

        btn_refresh = tk.Button(header, text="🔄 REFRESH", font=(CrysisTheme.FONT_UI, 9, "bold"),
                                fg=CrysisTheme.GREEN_ACCENT, bg=CrysisTheme.BG_PANEL,
                                bd=1, relief="solid", padx=12, pady=4, cursor="hand2",
                                command=self.refresh_lobbies_thread)
        btn_refresh.pack(side="right")

        # Table frame
        table_frame = tk.Frame(self.join_browser_frame, bg=CrysisTheme.BG_PANEL, bd=1, relief="solid",
                               highlightbackground=CrysisTheme.BORDER)
        table_frame.pack(fill="both", expand=True, padx=32, pady=8)

        # Treeview for lobbies
        cols = ("Name", "Host IP", "Campaign", "Mission", "Players")
        self.tree_lobbies = ttk.Treeview(table_frame, columns=cols, show="headings", height=8)
        self.tree_lobbies.heading("Name", text="Lobby Name")
        self.tree_lobbies.heading("Host IP", text="Host IP Address")
        self.tree_lobbies.heading("Campaign", text="Campaign")
        self.tree_lobbies.heading("Mission", text="Mission")
        self.tree_lobbies.heading("Players", text="Players")

        self.tree_lobbies.column("Name", width=220)
        self.tree_lobbies.column("Host IP", width=140)
        self.tree_lobbies.column("Campaign", width=120)
        self.tree_lobbies.column("Mission", width=140)
        self.tree_lobbies.column("Players", width=80, anchor="center")

        scroll_tree = ttk.Scrollbar(table_frame, orient="vertical", command=self.tree_lobbies.yview)
        self.tree_lobbies.configure(yscrollcommand=scroll_tree.set)

        self.tree_lobbies.pack(side="left", fill="both", expand=True)
        scroll_tree.pack(side="right", fill="y")

        # Join Selected Button
        btn_join_sel = tk.Button(self.join_browser_frame, text="JOIN SELECTED LOBBY  ▶",
                                 font=(CrysisTheme.FONT_UI, 11, "bold"),
                                 fg="#ffffff", bg=CrysisTheme.GREEN_ACCENT,
                                 activebackground="#25a76b", activeforeground="#ffffff",
                                 bd=0, relief="flat", padx=20, pady=8, cursor="hand2",
                                 command=self.action_join_selected)
        btn_join_sel.pack(anchor="e", padx=32, pady=8)

        # Direct Connect Box
        direct_frame = tk.Frame(self.join_browser_frame, bg=CrysisTheme.BG_PANEL, bd=1, relief="solid",
                                highlightbackground=CrysisTheme.BORDER)
        direct_frame.pack(fill="x", padx=32, pady=(12, 24))

        tk.Label(direct_frame, text="DIRECT IP CONNECT", font=(CrysisTheme.FONT_MONO, 9, "bold"),
                 fg=CrysisTheme.CYAN_ACCENT, bg=CrysisTheme.BG_PANEL).pack(side="left", padx=16, pady=12)

        self.ent_direct_ip = tk.Entry(direct_frame, font=(CrysisTheme.FONT_MONO, 10),
                                      bg=CrysisTheme.BG_INPUT, fg=CrysisTheme.TEXT_MAIN,
                                      bd=1, relief="solid", highlightbackground=CrysisTheme.BORDER, width=22)
        self.ent_direct_ip.pack(side="left", padx=8, pady=12)
        self.ent_direct_ip.insert(0, "192.168.1.")

        btn_direct = tk.Button(direct_frame, text="CONNECT BY IP  ▶", font=(CrysisTheme.FONT_UI, 9, "bold"),
                               fg="#ffffff", bg=CrysisTheme.CYAN_ACCENT,
                               bd=0, relief="flat", padx=16, pady=6, cursor="hand2",
                               command=self.action_direct_connect)
        btn_direct.pack(side="left", padx=12, pady=12)

    def refresh_lobbies_thread(self):
        for item in self.tree_lobbies.get_children():
            self.tree_lobbies.delete(item)

        def worker():
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
            s.settimeout(1.5)
            query = json.dumps({"type": "DISCOVER"}).encode("utf-8")

            # Broadcast on local subnet & 255.255.255.255
            for bcast in ["255.255.255.255", "127.0.0.1"]:
                try:
                    s.sendto(query, (bcast, DISCOVERY_PORT))
                except Exception:
                    pass

            discovered = []
            start = time.time()
            my_ips = get_network_ips()
            while time.time() - start < 1.5:
                try:
                    data, addr = s.recvfrom(2048)
                    pkt = json.loads(data.decode("utf-8"))
                    if pkt.get("type") == "LOBBY_ANNOUNCE":
                        h_ip = pkt.get("host_ip", addr[0])
                        # Filter out self
                        if h_ip in my_ips:
                            continue
                        discovered.append(pkt)
                except Exception:
                    pass
            s.close()

            def update_ui():
                for p in discovered:
                    self.tree_lobbies.insert("", "end", values=(
                        p.get("lobby_name", "Crysis Squad"),
                        p.get("host_ip", ""),
                        p.get("game_title", "Crysis 1"),
                        p.get("mission_title", "Contact"),
                        f"{p.get('player_count', 1)}/2"
                    ))
            self.after(0, update_ui)

        threading.Thread(target=worker, daemon=True).start()

    def action_join_selected(self):
        sel = self.tree_lobbies.selection()
        if not sel:
            messagebox.showinfo("Select Lobby", "Please select a lobby from the list or use Direct Connect.",
                                parent=self)
            return
        vals = self.tree_lobbies.item(sel[0])["values"]
        host_ip = str(vals[1])
        self.start_client_connection(host_ip)

    def action_direct_connect(self):
        ip = self.ent_direct_ip.get().strip()
        if not ip:
            return
        self.start_client_connection(ip)

    def start_client_connection(self, host_ip):
        self.stop_hosting()
        self.is_host = False
        self.is_connected = False
        self.is_ready = False
        self.remote_players = {}

        def worker():
            try:
                s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                s.settimeout(5)
                s.connect((host_ip, DEFAULT_PORT))
                s.settimeout(None)
                self.client_sock = s
                self.is_connected = True

                # Send HELLO with callsign and local loadout
                hello_pkt = {
                    "type": "HELLO",
                    "callsign": self.profile.get("callsign", "Psycho"),
                    "loadout": self.get_local_loadout()
                }
                s.sendall((json.dumps(hello_pkt) + "\n").encode("utf-8"))

                self.after(0, self.show_lobby_room_view)
                threading.Thread(target=self.client_receive_loop, daemon=True).start()
            except Exception as e:
                self.after(0, lambda: messagebox.showerror("Connection Error",
                                                          f"Could not connect to {host_ip}:{DEFAULT_PORT}\n{e}",
                                                          parent=self))

        threading.Thread(target=worker, daemon=True).start()

    # =========================================================================
    # VIEW 4: THE LOBBY ROOM (CORE CO-OP HUB)
    # =========================================================================
    def build_lobby_room_view(self):
        self.lobby_room_frame = tk.Frame(self.content_area, bg=CrysisTheme.BG_DARK)

        # Header Info Bar
        self.lobby_header = tk.Frame(self.lobby_room_frame, bg=CrysisTheme.BG_PANEL, height=54, bd=0,
                                     highlightthickness=1, highlightbackground=CrysisTheme.BORDER)
        self.lobby_header.pack(fill="x", side="top")
        self.lobby_header.pack_propagate(False)

        self.lbl_lobby_info = tk.Label(self.lobby_header, text="MISSION: CRYSIS 1 - CONTACT (ISLAND)",
                                       font=(CrysisTheme.FONT_TITLE, 13, "bold"),
                                       fg=CrysisTheme.CYAN_ACCENT, bg=CrysisTheme.BG_PANEL)
        self.lbl_lobby_info.pack(side="left", padx=24)

        self.lbl_role_status = tk.Label(self.lobby_header, text="ROLE: HOST",
                                        font=(CrysisTheme.FONT_MONO, 10, "bold"),
                                        fg=CrysisTheme.GREEN_ACCENT, bg=CrysisTheme.BG_PANEL)
        self.lbl_role_status.pack(side="right", padx=24)

        # Body: Left/Center Column (Squad & Loadouts) + Right Column (Host Mission & Settings)
        body = tk.Frame(self.lobby_room_frame, bg=CrysisTheme.BG_DARK)
        body.pack(fill="both", expand=True, padx=20, pady=12)

        # Left / Center: Squad Roster & Loadout Cards
        self.roster_panel = tk.Frame(body, bg=CrysisTheme.BG_DARK)
        self.roster_panel.pack(side="left", fill="both", expand=True, padx=(0, 12))

        lbl_roster_title = tk.Label(self.roster_panel, text="SQUAD ROSTER & WEAPON LOADOUTS",
                                    font=(CrysisTheme.FONT_TITLE, 13, "bold"),
                                    fg=CrysisTheme.TEXT_MAIN, bg=CrysisTheme.BG_DARK)
        lbl_roster_title.pack(anchor="w", pady=(0, 8))

        # Canvas with scrollbar for player loadout cards
        canvas_roster = tk.Canvas(self.roster_panel, bg=CrysisTheme.BG_DARK, bd=0, highlightthickness=0)
        scroll_roster = ttk.Scrollbar(self.roster_panel, orient="vertical", command=canvas_roster.yview)
        self.roster_container = tk.Frame(canvas_roster, bg=CrysisTheme.BG_DARK)

        self.roster_container.bind("<Configure>", lambda e: canvas_roster.configure(scrollregion=canvas_roster.bbox("all")))
        canvas_roster.create_window((0, 0), window=self.roster_container, anchor="nw")
        canvas_roster.configure(yscrollcommand=scroll_roster.set)

        canvas_roster.pack(side="left", fill="both", expand=True)
        scroll_roster.pack(side="right", fill="y")

        # Right Column: Mission Selection & Lobby Settings (Host Control / Client View)
        self.controls_panel = tk.Frame(body, bg=CrysisTheme.BG_PANEL, width=380, bd=1, relief="solid",
                                       highlightbackground=CrysisTheme.BORDER)
        self.controls_panel.pack(side="right", fill="y", padx=(12, 0))
        self.controls_panel.pack_propagate(False)

        # Build Host Controls in Right Column
        self.build_host_controls_panel()

        # Bottom Action Bar
        self.bottom_bar = tk.Frame(self.lobby_room_frame, bg=CrysisTheme.BG_PANEL, height=64, bd=0,
                                   highlightthickness=1, highlightbackground=CrysisTheme.BORDER)
        self.bottom_bar.pack(fill="x", side="bottom")
        self.bottom_bar.pack_propagate(False)

        btn_leave = tk.Button(self.bottom_bar, text="◀ LEAVE LOBBY",
                              font=(CrysisTheme.FONT_UI, 10, "bold"),
                              fg=CrysisTheme.RED_ACCENT, bg=CrysisTheme.BG_INPUT,
                              bd=1, relief="solid", padx=16, pady=8, cursor="hand2",
                              command=self.action_leave_lobby)
        btn_leave.pack(side="left", padx=24)

        # Ready / Launch buttons on right
        self.btn_ready = tk.Button(self.bottom_bar, text="READY UP",
                                   font=(CrysisTheme.FONT_UI, 11, "bold"),
                                   fg="#ffffff", bg=CrysisTheme.GREEN_ACCENT,
                                   activebackground="#25a76b", activeforeground="#ffffff",
                                   bd=0, relief="flat", padx=24, pady=8, cursor="hand2",
                                   command=self.action_toggle_ready)

        self.btn_launch = tk.Button(self.bottom_bar, text="LAUNCH MISSION  ▶",
                                    font=(CrysisTheme.FONT_UI, 12, "bold"),
                                    fg="#ffffff", bg=CrysisTheme.CYAN_ACCENT,
                                    activebackground="#2aa4d4", activeforeground="#ffffff",
                                    bd=0, relief="flat", padx=28, pady=8, cursor="hand2",
                                    command=self.action_launch_game)

    # -------------------------------------------------------------------------
    # RIGHT COLUMN: HOST MISSION & SETTINGS PANEL
    # -------------------------------------------------------------------------
    def build_host_controls_panel(self):
        panel = self.controls_panel

        lbl_head = tk.Label(panel, text="MISSION BRIEFING",
                            font=(CrysisTheme.FONT_TITLE, 12, "bold"),
                            fg=CrysisTheme.CYAN_ACCENT, bg=CrysisTheme.BG_PANEL)
        lbl_head.pack(anchor="w", padx=18, pady=(16, 4))

        self.lbl_host_note = tk.Label(panel, text="Host controls mission and game parameters",
                                      font=(CrysisTheme.FONT_UI, 8),
                                      fg=CrysisTheme.TEXT_MUTED, bg=CrysisTheme.BG_PANEL)
        self.lbl_host_note.pack(anchor="w", padx=18, pady=(0, 12))

        # 1. Mission / Campaign Selection Box
        box_mission = tk.Frame(panel, bg=CrysisTheme.BG_INPUT, bd=1, relief="solid",
                               highlightbackground=CrysisTheme.BORDER)
        box_mission.pack(fill="x", padx=18, pady=6)

        tk.Label(box_mission, text="OPERATION OBJECTIVE", font=(CrysisTheme.FONT_MONO, 8, "bold"),
                 fg=CrysisTheme.AMBER_ACCENT, bg=CrysisTheme.BG_INPUT).pack(anchor="w", padx=12, pady=(8, 4))

        self.lbl_active_mission = tk.Label(box_mission, text="Crysis 1: Contact (Island)",
                                           font=(CrysisTheme.FONT_UI, 11, "bold"),
                                           fg=CrysisTheme.TEXT_MAIN, bg=CrysisTheme.BG_INPUT)
        self.lbl_active_mission.pack(anchor="w", padx=12, pady=(0, 8))

        # Quick Actions: Start New Game for either game
        self.mission_btn_frame = tk.Frame(box_mission, bg=CrysisTheme.BG_INPUT)
        self.mission_btn_frame.pack(fill="x", padx=12, pady=(0, 10))

        btn_new_c1 = tk.Button(self.mission_btn_frame, text="▶ New Game: Crysis 1",
                               font=(CrysisTheme.FONT_UI, 9, "bold"),
                               fg=CrysisTheme.CYAN_ACCENT, bg=CrysisTheme.BG_PANEL,
                               bd=1, relief="solid", cursor="hand2", padx=6, pady=4,
                               command=lambda: self.set_lobby_mission("crysis", "island", "Contact", "new_game"))
        btn_new_c1.pack(fill="x", pady=2)

        btn_new_warhead = tk.Button(self.mission_btn_frame, text="▶ New Game: Warhead",
                                    font=(CrysisTheme.FONT_UI, 9, "bold"),
                                    fg=CrysisTheme.WARHEAD_ACCENT, bg=CrysisTheme.BG_PANEL,
                                    bd=1, relief="solid", cursor="hand2", padx=6, pady=4,
                                    command=lambda: self.set_lobby_mission("warhead", "ambush", "Call Me Ishmael", "new_game"))
        btn_new_warhead.pack(fill="x", pady=2)

        btn_pick_mission = tk.Button(self.mission_btn_frame, text="≡ Choose Mission from Campaign...",
                                     font=(CrysisTheme.FONT_UI, 9),
                                     fg=CrysisTheme.TEXT_MAIN, bg=CrysisTheme.BG_PANEL,
                                     bd=1, relief="solid", cursor="hand2", padx=6, pady=4,
                                     command=self.open_mission_picker_modal)
        btn_pick_mission.pack(fill="x", pady=2)

        # 2. Difficulty
        box_diff = tk.Frame(panel, bg=CrysisTheme.BG_PANEL)
        box_diff.pack(fill="x", padx=18, pady=(10, 4))

        tk.Label(box_diff, text="COMBAT DIFFICULTY", font=(CrysisTheme.FONT_MONO, 8, "bold"),
                 fg=CrysisTheme.CYAN_ACCENT, bg=CrysisTheme.BG_PANEL).pack(anchor="w")

        self.diff_btn_frame = tk.Frame(box_diff, bg=CrysisTheme.BG_PANEL)
        self.diff_btn_frame.pack(fill="x", pady=4)

        self.diff_buttons = {}
        for d_title, d_val in DIFFICULTIES:
            b = tk.Button(self.diff_btn_frame, text=d_title, font=(CrysisTheme.FONT_UI, 8, "bold"),
                          fg=CrysisTheme.TEXT_MUTED, bg=CrysisTheme.BG_INPUT,
                          bd=1, relief="solid", padx=8, pady=4, cursor="hand2",
                          command=lambda v=d_val: self.set_difficulty(v))
            b.pack(side="left", expand=True, fill="x", padx=1)
            self.diff_buttons[d_val] = b

        # 3. Tactical Modifiers
        box_mods = tk.Frame(panel, bg=CrysisTheme.BG_PANEL)
        box_mods.pack(fill="x", padx=18, pady=6)

        tk.Label(box_mods, text="GAME MODIFIERS", font=(CrysisTheme.FONT_MONO, 8, "bold"),
                 fg=CrysisTheme.CYAN_ACCENT, bg=CrysisTheme.BG_PANEL).pack(anchor="w", pady=(0, 4))

        # Enemy multiplier
        row_e = tk.Frame(box_mods, bg=CrysisTheme.BG_PANEL)
        row_e.pack(fill="x", pady=2)
        tk.Label(row_e, text="AI Enemies:", font=(CrysisTheme.FONT_UI, 9),
                 fg=CrysisTheme.TEXT_MAIN, bg=CrysisTheme.BG_PANEL).pack(side="left")
        self.enemy_btn_frame = tk.Frame(row_e, bg=CrysisTheme.BG_PANEL)
        self.enemy_btn_frame.pack(side="right")
        self.enemy_buttons = {}
        for em in ENEMY_MULTIPLIERS:
            eb = tk.Button(self.enemy_btn_frame, text=f"{em}x", font=(CrysisTheme.FONT_MONO, 8),
                           fg=CrysisTheme.TEXT_MUTED, bg=CrysisTheme.BG_INPUT,
                           bd=1, relief="solid", padx=6, pady=2, cursor="hand2",
                           command=lambda m=em: self.set_enemy_multiplier(m))
            eb.pack(side="left", padx=1)
            self.enemy_buttons[em] = eb

        # Ammo multiplier
        row_a = tk.Frame(box_mods, bg=CrysisTheme.BG_PANEL)
        row_a.pack(fill="x", pady=2)
        tk.Label(row_a, text="Ammo Pool:", font=(CrysisTheme.FONT_UI, 9),
                 fg=CrysisTheme.TEXT_MAIN, bg=CrysisTheme.BG_PANEL).pack(side="left")
        self.ammo_btn_frame = tk.Frame(row_a, bg=CrysisTheme.BG_PANEL)
        self.ammo_btn_frame.pack(side="right")
        self.ammo_buttons = {}
        for am in AMMO_MULTIPLIERS:
            lbl = "Inf" if am == 999 else f"{am}x"
            ab = tk.Button(self.ammo_btn_frame, text=lbl, font=(CrysisTheme.FONT_MONO, 8),
                           fg=CrysisTheme.TEXT_MUTED, bg=CrysisTheme.BG_INPUT,
                           bd=1, relief="solid", padx=6, pady=2, cursor="hand2",
                           command=lambda m=am: self.set_ammo_multiplier(m))
            ab.pack(side="left", padx=1)
            self.ammo_buttons[am] = ab

        # Checkboxes: Infinite O2 & All Attachments
        self.var_drown = tk.BooleanVar(value=self.settings.get("disable_drowning", True))
        self.chk_drown = tk.Checkbutton(box_mods, text="Disable Drowning (Infinite O2)",
                                        variable=self.var_drown, font=(CrysisTheme.FONT_UI, 9),
                                        fg=CrysisTheme.TEXT_MAIN, bg=CrysisTheme.BG_PANEL,
                                        selectcolor=CrysisTheme.BG_INPUT, activebackground=CrysisTheme.BG_PANEL,
                                        command=self.on_checkbox_changed)
        self.chk_drown.pack(anchor="w", pady=(6, 2))

        self.var_attach = tk.BooleanVar(value=self.settings.get("enable_all_attachments", True))
        self.chk_attach = tk.Checkbutton(box_mods, text="Enable All Attachments",
                                         variable=self.var_attach, font=(CrysisTheme.FONT_UI, 9),
                                         fg=CrysisTheme.TEXT_MAIN, bg=CrysisTheme.BG_PANEL,
                                         selectcolor=CrysisTheme.BG_INPUT, activebackground=CrysisTheme.BG_PANEL,
                                         command=self.on_checkbox_changed)
        self.chk_attach.pack(anchor="w", pady=2)

    def set_lobby_mission(self, game, code, title, mode="mission_select"):
        if not self.is_host:
            return
        self.settings["game"] = game
        self.settings["mission_code"] = code
        self.settings["mission_title"] = title
        self.settings["mission_mode"] = mode
        save_settings(self.settings)
        self.broadcast_lobby_state()
        self.update_lobby_room_ui()

    def set_difficulty(self, val):
        if not self.is_host:
            return
        self.settings["difficulty"] = val
        save_settings(self.settings)
        self.broadcast_lobby_state()
        self.update_lobby_room_ui()

    def set_enemy_multiplier(self, val):
        if not self.is_host:
            return
        self.settings["enemy_multiplier"] = val
        save_settings(self.settings)
        self.broadcast_lobby_state()
        self.update_lobby_room_ui()

    def set_ammo_multiplier(self, val):
        if not self.is_host:
            return
        self.settings["ammo_multiplier"] = val
        save_settings(self.settings)
        self.broadcast_lobby_state()
        self.update_lobby_room_ui()

    def on_checkbox_changed(self):
        if not self.is_host:
            return
        self.settings["disable_drowning"] = self.var_drown.get()
        self.settings["enable_all_attachments"] = self.var_attach.get()
        save_settings(self.settings)
        self.broadcast_lobby_state()

    def open_mission_picker_modal(self):
        if not self.is_host:
            return

        modal = tk.Toplevel(self)
        modal.title("Select Campaign Mission")
        modal.geometry("640x520")
        modal.configure(bg=CrysisTheme.BG_DARK)
        modal.transient(self)
        modal.grab_set()

        # Tabs: Crysis 1 & Warhead
        top_tabs = tk.Frame(modal, bg=CrysisTheme.BG_PANEL)
        top_tabs.pack(fill="x", padx=16, pady=(16, 8))

        active_tab = tk.StringVar(value=self.settings.get("game", "crysis"))

        list_frame = tk.Frame(modal, bg=CrysisTheme.BG_DARK)
        list_frame.pack(fill="both", expand=True, padx=16, pady=8)

        def populate(game_type):
            for w in list_frame.winfo_children():
                w.destroy()

            canvas = tk.Canvas(list_frame, bg=CrysisTheme.BG_DARK, bd=0, highlightthickness=0)
            scrollbar = ttk.Scrollbar(list_frame, orient="vertical", command=canvas.yview)
            scroll_frame = tk.Frame(canvas, bg=CrysisTheme.BG_DARK)

            scroll_frame.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
            canvas.create_window((0, 0), window=scroll_frame, anchor="nw")
            canvas.configure(yscrollcommand=scrollbar.set)

            canvas.pack(side="left", fill="both", expand=True)
            scrollbar.pack(side="right", fill="y")

            missions = CRYSIS_MISSIONS if game_type == "crysis" else WARHEAD_MISSIONS
            accent = CrysisTheme.CYAN_ACCENT if game_type == "crysis" else CrysisTheme.WARHEAD_ACCENT

            for title, code, desc in missions:
                row = tk.Frame(scroll_frame, bg=CrysisTheme.BG_PANEL, bd=1, relief="solid",
                               highlightbackground=CrysisTheme.BORDER)
                row.pack(fill="x", pady=4, padx=4)

                tk.Label(row, text=title, font=(CrysisTheme.FONT_TITLE, 11, "bold"),
                         fg=CrysisTheme.TEXT_MAIN, bg=CrysisTheme.BG_PANEL).pack(anchor="w", padx=12, pady=(6, 2))
                tk.Label(row, text=f"{code}  •  {desc}", font=(CrysisTheme.FONT_UI, 8),
                         fg=CrysisTheme.TEXT_MUTED, bg=CrysisTheme.BG_PANEL).pack(anchor="w", padx=12, pady=(0, 6))

                def pick_mission(c=code, t=title, g=game_type):
                    self.set_lobby_mission(g, c, t, "mission_select")
                    modal.destroy()

                btn = tk.Button(row, text="SELECT", font=(CrysisTheme.FONT_UI, 8, "bold"),
                                fg=accent, bg=CrysisTheme.BG_INPUT,
                                bd=1, relief="solid", padx=12, pady=4, cursor="hand2",
                                command=pick_mission)
                btn.place(relx=0.96, rely=0.5, anchor="e")

        btn_tab_c1 = tk.Button(top_tabs, text="CRYSIS 1 CAMPAIGN (11 Missions)",
                               font=(CrysisTheme.FONT_UI, 10, "bold"),
                               fg=CrysisTheme.CYAN_ACCENT, bg=CrysisTheme.BG_INPUT,
                               bd=1, relief="solid", padx=12, pady=6, cursor="hand2",
                               command=lambda: [active_tab.set("crysis"), populate("crysis")])
        btn_tab_c1.pack(side="left", padx=4)

        btn_tab_wh = tk.Button(top_tabs, text="CRYSIS WARHEAD CAMPAIGN (7 Missions)",
                               font=(CrysisTheme.FONT_UI, 10, "bold"),
                               fg=CrysisTheme.WARHEAD_ACCENT, bg=CrysisTheme.BG_INPUT,
                               bd=1, relief="solid", padx=12, pady=6, cursor="hand2",
                               command=lambda: [active_tab.set("warhead"), populate("warhead")])
        btn_tab_wh.pack(side="left", padx=4)

        populate(active_tab.get())

    # -------------------------------------------------------------------------
    # SQUAD ROSTER & WEAPON LOADOUT RENDERING
    # -------------------------------------------------------------------------
    def get_local_loadout(self):
        cur = self.profile.get("loadout", {})
        res = dict(DEFAULT_LOADOUT)
        res.update(cur)
        return res

    def update_lobby_room_ui(self):
        # 1. Update Header & Host Info
        game_name = "CRYSIS WARHEAD" if self.settings.get("game") == "warhead" else "CRYSIS 1"
        m_title = self.settings.get("mission_title", "Contact")
        m_code = self.settings.get("mission_code", "island")
        self.lbl_lobby_info.config(text=f"MISSION: {game_name} - {m_title.upper()} ({m_code})")
        self.lbl_active_mission.config(text=f"{game_name}: {m_title} ({m_code})")

        role_str = "SQUAD LEADER (HOST)" if self.is_host else "SQUADMATE (CLIENT)"
        role_color = CrysisTheme.CYAN_ACCENT if self.is_host else CrysisTheme.GREEN_ACCENT
        self.lbl_role_status.config(text=role_str, fg=role_color)

        # 2. Update Settings Controls state
        cur_diff = self.settings.get("difficulty", 2)
        for d_val, b in self.diff_buttons.items():
            if d_val == cur_diff:
                b.config(fg="#ffffff", bg=CrysisTheme.CYAN_ACCENT)
            else:
                b.config(fg=CrysisTheme.TEXT_MUTED, bg=CrysisTheme.BG_INPUT)

        cur_em = self.settings.get("enemy_multiplier", 1.0)
        for em_val, b in self.enemy_buttons.items():
            if abs(em_val - cur_em) < 0.05:
                b.config(fg="#ffffff", bg=CrysisTheme.AMBER_ACCENT)
            else:
                b.config(fg=CrysisTheme.TEXT_MUTED, bg=CrysisTheme.BG_INPUT)

        cur_am = self.settings.get("ammo_multiplier", 1)
        for am_val, b in self.ammo_buttons.items():
            if am_val == cur_am:
                b.config(fg="#ffffff", bg=CrysisTheme.GREEN_ACCENT)
            else:
                b.config(fg=CrysisTheme.TEXT_MUTED, bg=CrysisTheme.BG_INPUT)

        self.var_drown.set(self.settings.get("disable_drowning", True))
        self.var_attach.set(self.settings.get("enable_all_attachments", True))

        # Disable host controls for clients
        state_str = "normal" if self.is_host else "disabled"
        self.chk_drown.config(state=state_str)
        self.chk_attach.config(state=state_str)
        self.lbl_host_note.config(text="Host controls mission and parameters" if self.is_host else "Game parameters set by Squad Leader (Read-Only)")

        # 3. Update Bottom Buttons
        self.btn_ready.pack_forget()
        self.btn_launch.pack_forget()

        if self.is_host:
            self.btn_launch.pack(side="right", padx=24)
        else:
            self.btn_ready.pack(side="right", padx=24)
            ready_color = CrysisTheme.GREEN_ACCENT if self.is_ready else CrysisTheme.BG_INPUT
            ready_text = "READY ✓" if self.is_ready else "READY UP"
            self.btn_ready.config(text=ready_text, bg=ready_color)

        # 4. Render Squad Roster & Loadout Cards
        for w in self.roster_container.winfo_children():
            w.destroy()

        local_callsign = self.profile.get("callsign", "Nomad")
        local_loadout = self.get_local_loadout()

        # Render Local Player Card First
        self.render_player_loadout_card(
            callsign=local_callsign,
            is_host=self.is_host,
            is_local=True,
            ready=self.is_ready,
            loadout=local_loadout
        )

        # Render Remote Players Cards
        for callsign, pdata in self.remote_players.items():
            self.render_player_loadout_card(
                callsign=callsign,
                is_host=pdata.get("is_host", False),
                is_local=False,
                ready=pdata.get("ready", False),
                loadout=pdata.get("loadout", DEFAULT_LOADOUT)
            )

    def render_player_loadout_card(self, callsign, is_host, is_local, ready, loadout):
        card = tk.Frame(self.roster_container, bg=CrysisTheme.BG_PANEL, bd=1, relief="solid",
                        highlightbackground=CrysisTheme.BORDER)
        card.pack(fill="x", pady=6, padx=4)

        # Header of player card
        header = tk.Frame(card, bg=CrysisTheme.BG_CARD)
        header.pack(fill="x", padx=0, pady=0)

        accent = CrysisTheme.CYAN_ACCENT if is_host else CrysisTheme.GREEN_ACCENT
        tk.Frame(header, bg=accent, width=4).pack(side="left", fill="y")

        name_text = f"{callsign} (YOU)" if is_local else callsign
        lbl_name = tk.Label(header, text=name_text, font=(CrysisTheme.FONT_TITLE, 12, "bold"),
                            fg=CrysisTheme.TEXT_MAIN, bg=CrysisTheme.BG_CARD)
        lbl_name.pack(side="left", padx=14, pady=8)

        tag_text = "SQUAD LEADER" if is_host else "SQUADMATE"
        tk.Label(header, text=f"[{tag_text}]", font=(CrysisTheme.FONT_MONO, 8, "bold"),
                 fg=accent, bg=CrysisTheme.BG_CARD).pack(side="left", padx=2)

        status_text = "READY ✓" if ready else "NOT READY"
        status_color = CrysisTheme.GREEN_ACCENT if ready else CrysisTheme.AMBER_ACCENT
        tk.Label(header, text=status_text, font=(CrysisTheme.FONT_MONO, 9, "bold"),
                 fg=status_color, bg=CrysisTheme.BG_CARD).pack(side="right", padx=16)

        # Slots Row (5 Slots)
        slots_row = tk.Frame(card, bg=CrysisTheme.BG_PANEL)
        slots_row.pack(fill="x", padx=12, pady=10)

        for slot_idx, slot_cfg in enumerate(SLOT_CONFIGS):
            s_id = slot_cfg["id"]
            s_name = slot_cfg["name"]
            equipped_id = loadout.get(s_id, slot_cfg["default"])
            w_meta = WEAPON_METADATA.get(equipped_id, WEAPON_METADATA["None"])

            slot_frame = tk.Frame(slots_row, bg=CrysisTheme.BG_INPUT, bd=1, relief="solid",
                                  highlightbackground=CrysisTheme.BORDER, width=128, height=130)
            slot_frame.pack(side="left", fill="both", expand=True, padx=4)
            slot_frame.pack_propagate(False)

            # Slot title
            lbl_st = tk.Label(slot_frame, text=s_name, font=(CrysisTheme.FONT_MONO, 7, "bold"),
                              fg=CrysisTheme.CYAN_ACCENT, bg=CrysisTheme.BG_INPUT)
            lbl_st.pack(anchor="w", padx=6, pady=(4, 2))

            # Weapon Image
            img = self.weapon_images.get(equipped_id)
            if img:
                lbl_img = tk.Label(slot_frame, image=img, bg=CrysisTheme.BG_INPUT)
                lbl_img.pack(pady=2)
            else:
                lbl_box = tk.Label(slot_frame, text=equipped_id, font=(CrysisTheme.FONT_MONO, 9, "bold"),
                                   fg=w_meta.get("color", "#ffffff"), bg=CrysisTheme.BG_CARD, height=3)
                lbl_box.pack(fill="x", padx=4, pady=2)

            # Weapon name label
            lbl_wn = tk.Label(slot_frame, text=equipped_id, font=(CrysisTheme.FONT_UI, 8, "bold"),
                              fg=w_meta.get("color", CrysisTheme.TEXT_MAIN), bg=CrysisTheme.BG_INPUT)
            lbl_wn.pack()

            # If LOCAL player: entire slot card is interactive and clickable
            if is_local:
                btn_chg = tk.Button(slot_frame, text="CHANGE ▾", font=(CrysisTheme.FONT_UI, 7, "bold"),
                                    fg=CrysisTheme.CYAN_ACCENT, bg=CrysisTheme.BG_PANEL,
                                    activebackground=CrysisTheme.BORDER_LIGHT, activeforeground="#ffffff",
                                    bd=1, relief="solid", cursor="hand2", pady=2,
                                    command=lambda s=s_id, sn=s_name: self.open_weapon_picker_for_slot(s, sn))
                btn_chg.pack(side="bottom", fill="x", padx=6, pady=(2, 6))

                # Bind click on every element in the slot
                def make_slot_click_handler(sid=s_id, sname=s_name):
                    return lambda e=None: self.open_weapon_picker_for_slot(sid, sname)

                slot_click = make_slot_click_handler(s_id, s_name)
                slot_frame.config(cursor="hand2")
                lbl_st.config(cursor="hand2")
                lbl_wn.config(cursor="hand2")

                slot_frame.bind("<Button-1>", slot_click)
                lbl_st.bind("<Button-1>", slot_click)
                lbl_wn.bind("<Button-1>", slot_click)

                if img:
                    lbl_img.config(cursor="hand2")
                    lbl_img.bind("<Button-1>", slot_click)
                else:
                    lbl_box.config(cursor="hand2")
                    lbl_box.bind("<Button-1>", slot_click)

                # Hover highlight
                def on_enter(e, f=slot_frame): f.config(highlightbackground=CrysisTheme.CYAN_ACCENT)
                def on_leave(e, f=slot_frame): f.config(highlightbackground=CrysisTheme.BORDER)
                slot_frame.bind("<Enter>", on_enter)
                slot_frame.bind("<Leave>", on_leave)

    # -------------------------------------------------------------------------
    # WEAPON PICKER MODAL (PER-SLOT, ENFORCES NO DUPLICATES RULE)
    # -------------------------------------------------------------------------
    def open_weapon_picker_for_slot(self, slot_id, slot_name):
        modal = tk.Toplevel(self)
        modal.title(f"Equip Weapon: {slot_name}")
        modal.geometry("680x560")
        modal.configure(bg=CrysisTheme.BG_DARK)
        modal.transient(self)
        modal.grab_set()

        head = tk.Frame(modal, bg=CrysisTheme.BG_PANEL)
        head.pack(fill="x", padx=16, pady=(16, 8))

        tk.Label(head, text=f"SELECT WEAPON: {slot_name}", font=(CrysisTheme.FONT_TITLE, 13, "bold"),
                 fg=CrysisTheme.CYAN_ACCENT, bg=CrysisTheme.BG_PANEL).pack(anchor="w", padx=12, pady=(8, 2))
        tk.Label(head, text="Weapons already equipped in another slot cannot be selected.",
                 font=(CrysisTheme.FONT_UI, 9), fg=CrysisTheme.TEXT_MUTED, bg=CrysisTheme.BG_PANEL).pack(anchor="w", padx=12, pady=(0, 8))

        # Determine currently equipped weapons in OTHER slots
        local_loadout = self.get_local_loadout()
        equipped_in_other_slots = {}
        for s_cfg in SLOT_CONFIGS:
            s = s_cfg["id"]
            if s != slot_id:
                w = local_loadout.get(s, "None")
                if w and w != "None" and w != "Frag Grenade":
                    equipped_in_other_slots[w] = s_cfg["name"]

        # Scrollable container for weapon choices
        canvas = tk.Canvas(modal, bg=CrysisTheme.BG_DARK, bd=0, highlightthickness=0)
        scrollbar = ttk.Scrollbar(modal, orient="vertical", command=canvas.yview)
        scroll_frame = tk.Frame(canvas, bg=CrysisTheme.BG_DARK)

        scroll_frame.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=scroll_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        canvas.pack(side="left", fill="both", expand=True, padx=(16, 0), pady=8)
        scrollbar.pack(side="right", fill="y", padx=(0, 16), pady=8)

        # Get list of allowed weapons for this slot
        target_slot_cfg = next(c for c in SLOT_CONFIGS if c["id"] == slot_id)
        weapons_list = target_slot_cfg["weapons"]

        for w_id in weapons_list:
            w_meta = WEAPON_METADATA.get(w_id, WEAPON_METADATA["None"])
            in_use_by = equipped_in_other_slots.get(w_id)
            is_disabled = (in_use_by is not None)

            card = tk.Frame(scroll_frame, bg=CrysisTheme.BG_PANEL, bd=1, relief="solid",
                            highlightbackground=CrysisTheme.BORDER)
            card.pack(fill="x", pady=4, padx=4)

            # Weapon thumbnail
            img = self.weapon_images.get(w_id)
            if img:
                lbl_icon = tk.Label(card, image=img, bg=CrysisTheme.BG_PANEL)
                lbl_icon.pack(side="left", padx=8, pady=4)
            else:
                lbl_icon = tk.Label(card, text="[EMPTY]" if w_id == "None" else w_id,
                                    font=(CrysisTheme.FONT_MONO, 8, "bold"),
                                    fg=w_meta.get("color", "#ffffff"), bg=CrysisTheme.BG_INPUT,
                                    width=14, height=3)
                lbl_icon.pack(side="left", padx=8, pady=4)

            # Metadata info
            info = tk.Frame(card, bg=CrysisTheme.BG_PANEL)
            info.pack(side="left", fill="both", expand=True, padx=8, pady=8)

            lbl_name = tk.Label(info, text=w_meta["label"], font=(CrysisTheme.FONT_TITLE, 11, "bold"),
                                fg=w_meta.get("color", CrysisTheme.TEXT_MAIN), bg=CrysisTheme.BG_PANEL)
            lbl_name.pack(anchor="w")

            tag_cat = w_meta["cat"].upper()
            if w_meta.get("warhead"):
                tag_cat += " [WARHEAD WEAPON - COMPATIBLE WITH CRYSIS 1]"
            lbl_cat = tk.Label(info, text=tag_cat, font=(CrysisTheme.FONT_MONO, 8),
                               fg=CrysisTheme.TEXT_MUTED, bg=CrysisTheme.BG_PANEL)
            lbl_cat.pack(anchor="w")

            # Selection Action or Disabled Notice
            if is_disabled:
                lbl_dis = tk.Label(card, text=f"EQUIPPED IN {in_use_by}",
                                   font=(CrysisTheme.FONT_MONO, 8, "bold"),
                                   fg=CrysisTheme.AMBER_ACCENT, bg=CrysisTheme.BG_PANEL)
                lbl_dis.pack(side="right", padx=16)
            else:
                is_currently_equipped = (local_loadout.get(slot_id) == w_id)
                btn_text = "EQUIPPED ✓" if is_currently_equipped else "EQUIP ▶"
                btn_bg = CrysisTheme.GREEN_ACCENT if is_currently_equipped else CrysisTheme.CYAN_ACCENT

                def make_select_handler(wid=w_id):
                    def do_select(e=None):
                        self.set_local_loadout_slot(slot_id, wid)
                        modal.destroy()
                    return do_select

                sel_handler = make_select_handler(w_id)

                btn_eq = tk.Button(card, text=btn_text, font=(CrysisTheme.FONT_UI, 9, "bold"),
                                   fg="#ffffff", bg=btn_bg,
                                   bd=0, relief="flat", padx=16, pady=6, cursor="hand2",
                                   command=sel_handler)
                btn_eq.pack(side="right", padx=16)

                # Make the entire card row clickable
                for w_elem in [card, lbl_icon, info, lbl_name, lbl_cat]:
                    w_elem.config(cursor="hand2")
                    w_elem.bind("<Button-1>", sel_handler)

                def on_c_enter(e, c=card): c.config(highlightbackground=CrysisTheme.CYAN_ACCENT)
                def on_c_leave(e, c=card): c.config(highlightbackground=CrysisTheme.BORDER)
                card.bind("<Enter>", on_c_enter)
                card.bind("<Leave>", on_c_leave)

    def set_local_loadout_slot(self, slot_id, weapon_id):
        loadout = self.get_local_loadout()
        loadout[slot_id] = weapon_id
        self.profile["loadout"] = loadout
        save_profile(self.profile)

        # Broadcast update to peers
        self.broadcast_loadout_update()
        self.update_lobby_room_ui()

    def broadcast_loadout_update(self):
        pkt = {
            "type": "LOADOUT_UPDATE",
            "callsign": self.profile.get("callsign", "Nomad"),
            "loadout": self.get_local_loadout()
        }
        msg = (json.dumps(pkt) + "\n").encode("utf-8")

        if self.is_host:
            for c in list(self.host_clients):
                try:
                    c.sendall(msg)
                except Exception:
                    pass
        elif self.client_sock:
            try:
                self.client_sock.sendall(msg)
            except Exception:
                pass

    def action_toggle_ready(self):
        self.is_ready = not self.is_ready
        self.btn_ready.config(text="READY ✓" if self.is_ready else "READY UP",
                              bg=CrysisTheme.GREEN_ACCENT if self.is_ready else CrysisTheme.BG_INPUT)
        if self.client_sock:
            pkt = {
                "type": "READY_UPDATE",
                "callsign": self.profile.get("callsign", "Psycho"),
                "ready": self.is_ready
            }
            try:
                self.client_sock.sendall((json.dumps(pkt) + "\n").encode("utf-8"))
            except Exception:
                pass

    def action_leave_lobby(self):
        self.stop_hosting()
        self.is_host = False
        self.is_connected = False
        self.is_ready = False
        self.remote_players = {}
        self.show_landing_view()

    # =========================================================================
    # NETWORKING ENGINE (HOST ACCEPT, CLIENT RECEIVE, DISCOVERY, LAUNCH SYNC)
    # =========================================================================
    def register_lobby_loop(self, lobby_name, bind_ip):
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)

        while self.is_host and not self.stop_threads:
            pkt = {
                "type": "LOBBY_ANNOUNCE",
                "lobby_name": lobby_name,
                "host_ip": bind_ip,
                "game_title": "Crysis Warhead" if self.settings.get("game") == "warhead" else "Crysis 1",
                "mission_title": self.settings.get("mission_title", "Contact"),
                "player_count": 1 + len(self.remote_players)
            }
            data = json.dumps(pkt).encode("utf-8")
            for bcast in ["255.255.255.255", "127.0.0.1"]:
                try:
                    s.sendto(data, (bcast, DISCOVERY_PORT))
                except Exception:
                    pass
            time.sleep(2)
        s.close()

    def udp_discovery_listener(self):
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            s.bind(("", DISCOVERY_PORT))
            while not self.stop_threads:
                try:
                    data, addr = s.recvfrom(2048)
                    pkt = json.loads(data.decode("utf-8"))
                    if pkt.get("type") == "DISCOVER" and self.is_host:
                        reply = {
                            "type": "LOBBY_ANNOUNCE",
                            "lobby_name": f"{self.profile.get('callsign', 'Nomad')}'s Squad",
                            "host_ip": addr[0],
                            "game_title": "Crysis Warhead" if self.settings.get("game") == "warhead" else "Crysis 1",
                            "mission_title": self.settings.get("mission_title", "Contact"),
                            "player_count": 1 + len(self.remote_players)
                        }
                        s.sendto(json.dumps(reply).encode("utf-8"), addr)
                except Exception:
                    pass
        except Exception:
            pass
        finally:
            s.close()

    def host_accept_loop(self):
        while self.is_host and self.server_sock:
            try:
                conn, addr = self.server_sock.accept()
                self.host_clients.append(conn)
                threading.Thread(target=self.host_client_handler, args=(conn, addr), daemon=True).start()
            except Exception:
                break

    def host_client_handler(self, conn, addr):
        buffer = ""
        client_callsign = None
        try:
            while self.is_host:
                data = conn.recv(4096)
                if not data:
                    break
                buffer += data.decode("utf-8", errors="ignore")
                while "\n" in buffer:
                    line, buffer = buffer.split("\n", 1)
                    line = line.strip()
                    if not line:
                        continue
                    pkt = json.loads(line)
                    ptype = pkt.get("type")

                    if ptype == "HELLO":
                        client_callsign = pkt.get("callsign", "Psycho")
                        self.remote_players[client_callsign] = {
                            "is_host": False,
                            "ready": False,
                            "loadout": pkt.get("loadout", DEFAULT_LOADOUT)
                        }
                        self.broadcast_lobby_state()
                        self.after(0, self.update_lobby_room_ui)

                    elif ptype == "LOADOUT_UPDATE":
                        c_name = pkt.get("callsign", client_callsign)
                        if c_name in self.remote_players:
                            self.remote_players[c_name]["loadout"] = pkt.get("loadout", DEFAULT_LOADOUT)
                        self.broadcast_lobby_state()
                        self.after(0, self.update_lobby_room_ui)

                    elif ptype == "READY_UPDATE":
                        c_name = pkt.get("callsign", client_callsign)
                        if c_name in self.remote_players:
                            self.remote_players[c_name]["ready"] = pkt.get("ready", False)
                        self.broadcast_lobby_state()
                        self.after(0, self.update_lobby_room_ui)

        except Exception:
            pass
        finally:
            if conn in self.host_clients:
                self.host_clients.remove(conn)
            if client_callsign in self.remote_players:
                del self.remote_players[client_callsign]
            try:
                conn.close()
            except Exception:
                pass
            self.broadcast_lobby_state()
            self.after(0, self.update_lobby_room_ui)

    def broadcast_lobby_state(self):
        if not self.is_host:
            return

        state_pkt = {
            "type": "LOBBY_STATE",
            "settings": self.settings,
            "remote_players": {
                self.profile.get("callsign", "Nomad"): {
                    "is_host": True,
                    "ready": True,
                    "loadout": self.get_local_loadout()
                }
            }
        }
        for c_name, pdata in self.remote_players.items():
            state_pkt["remote_players"][c_name] = pdata

        data = (json.dumps(state_pkt) + "\n").encode("utf-8")
        for c in list(self.host_clients):
            try:
                c.sendall(data)
            except Exception:
                pass

    def client_receive_loop(self):
        buffer = ""
        while self.is_connected and self.client_sock:
            try:
                data = self.client_sock.recv(4096)
                if not data:
                    break
                buffer += data.decode("utf-8", errors="ignore")
                while "\n" in buffer:
                    line, buffer = buffer.split("\n", 1)
                    line = line.strip()
                    if not line:
                        continue
                    pkt = json.loads(line)
                    ptype = pkt.get("type")

                    if ptype == "LOBBY_STATE":
                        self.settings.update(pkt.get("settings", {}))
                        rem = pkt.get("remote_players", {})
                        local_callsign = self.profile.get("callsign", "Psycho")
                        # Keep only other players in remote_players
                        self.remote_players = {k: v for k, v in rem.items() if k != local_callsign}
                        self.after(0, self.update_lobby_room_ui)

                    elif ptype == "LAUNCH":
                        # Host triggered launch
                        m_code = pkt.get("mission_code", "island")
                        diff_val = pkt.get("difficulty", 2)
                        emult = pkt.get("enemy_multiplier", 1.0)
                        amult = pkt.get("ammo_multiplier", 1)
                        o2 = pkt.get("disable_drowning", True)
                        att = pkt.get("enable_all_attachments", True)
                        h_ip = pkt.get("host_ip", "127.0.0.1")

                        self.after(0, lambda: self.launch_crysis_client(
                            host_ip=h_ip,
                            mission_code=m_code,
                            difficulty_val=diff_val,
                            enemy_mult=emult,
                            ammo_mult=amult,
                            disable_drowning=o2,
                            enable_attachments=att,
                            loadout=self.get_local_loadout()
                        ))

            except Exception:
                break

    def stop_hosting(self):
        if self.server_sock:
            try:
                self.server_sock.close()
            except Exception:
                pass
            self.server_sock = None
        for c in list(self.host_clients):
            try:
                c.close()
            except Exception:
                pass
        self.host_clients = []
        if self.client_sock:
            try:
                self.client_sock.close()
            except Exception:
                pass
            self.client_sock = None

    # =========================================================================
    # LAUNCH GAME ACTIONS
    # =========================================================================
    def action_launch_game(self):
        if not self.is_host:
            return

        mission_code = self.settings.get("mission_code", "island")
        difficulty_val = self.settings.get("difficulty", 2)
        enemy_mult = self.settings.get("enemy_multiplier", 1.0)
        ammo_mult = self.settings.get("ammo_multiplier", 1)
        disable_drowning = self.settings.get("disable_drowning", True)
        enable_attachments = self.settings.get("enable_all_attachments", True)

        # Notify connected clients to launch
        ips = get_network_ips()
        host_ip = ips[0] if ips else "127.0.0.1"
        game_type = self.settings.get("game", "crysis")
        launch_pkt = {
            "type": "LAUNCH",
            "game": game_type,
            "host_ip": host_ip,
            "mission_code": mission_code,
            "difficulty": difficulty_val,
            "enemy_multiplier": enemy_mult,
            "ammo_multiplier": ammo_mult,
            "disable_drowning": disable_drowning,
            "enable_all_attachments": enable_attachments
        }
        msg = (json.dumps(launch_pkt) + "\n").encode("utf-8")
        for c in list(self.host_clients):
            try:
                c.sendall(msg)
            except Exception:
                pass

        # Launch local host
        self.launch_crysis_host(
            mission_code=mission_code,
            difficulty_val=difficulty_val,
            enemy_mult=enemy_mult,
            ammo_mult=ammo_mult,
            disable_drowning=disable_drowning,
            enable_attachments=enable_attachments,
            loadout=self.get_local_loadout()
        )

    def extract_weapon_list_from_loadout(self, loadout_dict):
        weapons = []
        for s in ["primary1", "primary2", "secondary", "heavy", "explosive"]:
            w = loadout_dict.get(s, "None")
            if w and w != "None" and w != "Frag Grenade":
                weapons.append(w)
        return weapons

    def launch_crysis_host(self, mission_code, difficulty_val, enemy_mult, ammo_mult,
                           disable_drowning, enable_attachments, loadout):
        callsign = self.profile.get("callsign", "Nomad")
        equipped_weapons = self.extract_weapon_list_from_loadout(loadout)
        loadout_str = ",".join(equipped_weapons)

        cfg_content = f"""sys_spec_ObjectDetail 1
sys_spec_Physics 1
sv_bind 0.0.0.0
sv_servername CrysisCoopServer
sv_gamerules Coop
sv_port 64087
sv_lanonly 1
sv_cheatprotection 0
net_lanbrowser 1
log_verbosity 3
net_log 0
net_disconnect_on_rmi_error 0
net_inactivitytimeout 120
sv_timeout_disconnect 120
net_enable_voice_chat 0
sv_gs_trackstats 0
sv_gs_report 0
g_breaktimeoutframes 1000000
r_Fullscreen 0
r_Width 1280
r_Height 720
g_skipIntro = 0
cl_hud 1
net_name {callsign}
cl_gs_nick {callsign}
g_difficultyLevel = {difficulty_val}
coop_loadout = "{loadout_str}"
coop_all_attachments = {1 if enable_attachments else 0}
coop_disable_o2 = {1 if disable_drowning else 0}
coop_enemy_mult = {int(enemy_mult)}
coop_ammo_multiplier = {ammo_mult}
hud_subtitles = 1
hud_startPaused = 0
bind f10 coop_teleport
bind f8 coop_skip_cutscene
bind f9 coop_menu
bind f11 coop_god
map {mission_code} s
"""
        try:
            subprocess.run(["taskkill", "/F", "/IM", "Crysis.exe", "/IM", "Crysis64.exe"],
                           capture_output=True, timeout=5)
            time.sleep(0.5)
        except Exception:
            pass

        cfg_paths = [
            os.path.join(CRYSIS_ROOT_DIR, "host.cfg"),
            os.path.join(CRYSIS_ROOT_DIR, "Game", "host.cfg"),
            os.path.join(CRYSIS_MOD_DIR, "host.cfg")
        ]
        for cp in cfg_paths:
            try:
                with open(cp, "w", encoding="utf-8") as f:
                    f.write(cfg_content)
            except Exception:
                pass

        bin_dirs = [
            os.path.join(CRYSIS_ROOT_DIR, "Bin32"),
            os.path.join(CRYSIS_ROOT_DIR, "Bin64"),
        ]
        exe_path = None
        for bd in bin_dirs:
            for ex in ["Crysis.exe", "Crysis64.exe"]:
                p = os.path.join(bd, ex)
                if os.path.exists(p):
                    exe_path = p
                    break
            if exe_path:
                break

        game_type = self.settings.get("game", "crysis")
        if game_type == "warhead":
            # Crysis Warhead Standalone (Co-op mod is NOT installed or meant for Warhead)
            warhead_bin_dirs = [
                os.path.join(CRYSIS_WARHEAD_DIR, "Bin32"),
                os.path.join(CRYSIS_WARHEAD_DIR, "Bin64"),
            ]
            warhead_exe = None
            for bd in warhead_bin_dirs:
                for ex in ["Crysis.exe", "Crysis64.exe"]:
                    p = os.path.join(bd, ex)
                    if os.path.exists(p):
                        warhead_exe = p
                        break
                if warhead_exe:
                    break

            if not warhead_exe:
                messagebox.showerror("Error", f"Could not find Crysis Warhead executable in:\n{CRYSIS_WARHEAD_DIR}", parent=self)
                return

            cmd = [
                warhead_exe,
                "-devmode",
                f"+map {mission_code}"
            ]
            subprocess.Popen(cmd, cwd=os.path.dirname(warhead_exe))
            return

        if not exe_path:
            messagebox.showerror("Error", "Could not locate Crysis.exe or Crysis64.exe!", parent=self)
            return

        cmd = [
            exe_path,
            "-mod", "CrysisCoop",
            "-devmode",
            "+exec", "host.cfg"
        ]
        subprocess.Popen(cmd, cwd=os.path.dirname(exe_path))

    def launch_crysis_client(self, host_ip, mission_code, difficulty_val, enemy_mult, ammo_mult,
                             disable_drowning, enable_attachments, loadout):
        callsign = self.profile.get("callsign", "Psycho")
        equipped_weapons = self.extract_weapon_list_from_loadout(loadout)
        loadout_str = ",".join(equipped_weapons)

        cfg_content = f"""sys_spec_ObjectDetail 1
sys_spec_Physics 1
log_verbosity 3
net_log 0
net_disconnect_on_rmi_error 0
net_inactivitytimeout 120
sv_timeout_disconnect 120
net_enable_voice_chat 0
sv_lanonly 1
cl_serverport 64087
g_skipIntro = 0
cl_hud 1
net_name {callsign}
cl_gs_nick {callsign}
sv_gs_trackstats 0
sv_gs_report 0
g_breaktimeoutframes 1000000
r_Fullscreen 0
r_Width 1280
r_Height 720
g_difficultyLevel = {difficulty_val}
coop_loadout = "{loadout_str}"
coop_all_attachments = {1 if enable_attachments else 0}
coop_disable_o2 = {1 if disable_drowning else 0}
coop_enemy_mult = {int(enemy_mult)}
coop_ammo_multiplier = {ammo_mult}
connect {host_ip}:64087
hud_subtitles = 1
hud_startPaused = 0
bind f10 coop_teleport
bind f8 coop_skip_cutscene
bind f9 coop_menu
bind f11 coop_god
"""
        try:
            subprocess.run(["taskkill", "/F", "/IM", "Crysis.exe", "/IM", "Crysis64.exe"],
                           capture_output=True, timeout=5)
            time.sleep(0.5)
        except Exception:
            pass

        cfg_paths = [
            os.path.join(CRYSIS_ROOT_DIR, "client.cfg"),
            os.path.join(CRYSIS_ROOT_DIR, "Game", "client.cfg"),
            os.path.join(CRYSIS_MOD_DIR, "client.cfg")
        ]
        for cp in cfg_paths:
            try:
                with open(cp, "w", encoding="utf-8") as f:
                    f.write(cfg_content)
            except Exception:
                pass

        bin_dirs = [
            os.path.join(CRYSIS_ROOT_DIR, "Bin32"),
            os.path.join(CRYSIS_ROOT_DIR, "Bin64"),
        ]
        exe_path = None
        for bd in bin_dirs:
            for ex in ["Crysis.exe", "Crysis64.exe"]:
                p = os.path.join(bd, ex)
                if os.path.exists(p):
                    exe_path = p
                    break
            if exe_path:
                break

        game_type = self.settings.get("game", "crysis")
        if game_type == "warhead":
            warhead_bin_dirs = [
                os.path.join(CRYSIS_WARHEAD_DIR, "Bin32"),
                os.path.join(CRYSIS_WARHEAD_DIR, "Bin64"),
            ]
            warhead_exe = None
            for bd in warhead_bin_dirs:
                for ex in ["Crysis.exe", "Crysis64.exe"]:
                    p = os.path.join(bd, ex)
                    if os.path.exists(p):
                        warhead_exe = p
                        break
                if warhead_exe:
                    break

            if warhead_exe:
                cmd = [warhead_exe, "-devmode", f"+map {mission_code}"]
                subprocess.Popen(cmd, cwd=os.path.dirname(warhead_exe))
            return

        if not exe_path:
            messagebox.showerror("Error", "Could not locate Crysis.exe or Crysis64.exe!", parent=self)
            return

        cmd = [
            exe_path,
            "-mod", "CrysisCoop",
            "-devmode",
            "+exec", "client.cfg"
        ]
        subprocess.Popen(cmd, cwd=os.path.dirname(exe_path))

if __name__ == "__main__":
    app = CrysisCoopLauncher()
    app.mainloop()
