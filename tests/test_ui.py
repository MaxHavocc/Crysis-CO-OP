"""Hidden Tk regression checks; no discovery sockets or game processes are started."""
from contextlib import ExitStack
import importlib.util
from pathlib import Path
import sys
import unittest
from unittest.mock import patch


sys.dont_write_bytecode = True
SOURCE = Path(__file__).resolve().parent.parent / "CrysisCoopLauncher.py"
INSTALLED_REPO = SOURCE.parent


def contrast_ratio(first, second):
    def luminance(color):
        channels = [int(color[index:index + 2], 16) / 255 for index in (1, 3, 5)]
        channels = [value / 12.92 if value <= 0.04045 else ((value + 0.055) / 1.055) ** 2.4
                    for value in channels]
        return sum(value * weight for value, weight in zip(channels, (0.2126, 0.7152, 0.0722)))
    light, dark = sorted((luminance(first), luminance(second)), reverse=True)
    return (light + 0.05) / (dark + 0.05)


class LobbyUiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        spec = importlib.util.spec_from_file_location("launcher_ui_check", SOURCE)
        cls.module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(cls.module)
        cls.theme = cls.module.CrysisTheme
        cls.stack = ExitStack()
        cls.addClassCleanup(cls.stack.close)
        for name, value in {
            "CRYSIS_MOD_DIR": str(INSTALLED_REPO),
            "CRYSIS_ROOT_DIR": str(INSTALLED_REPO.parent.parent),
            "ICONS_DIR": str(INSTALLED_REPO / "weapon_icons"),
            "PROFILE_FILE": str(INSTALLED_REPO / "user_profile.json"),
            "SETTINGS_FILE": str(INSTALLED_REPO / "coop_settings.json"),
        }.items():
            cls.stack.enter_context(patch.object(cls.module, name, value))
        cls.stack.enter_context(patch.object(cls.module, "get_network_ips", return_value=["127.0.0.1"]))
        cls.stack.enter_context(patch.object(cls.module, "load_profile", return_value={
            "callsign": "UI test", "loadout": dict(cls.module.DEFAULT_LOADOUT),
        }))
        cls.stack.enter_context(patch.object(cls.module, "load_settings", return_value={
            "game": "crysis", "mission_code": "island", "mission_title": "Contact",
            "mission_mode": "new_game", "difficulty": 2, "enemy_multiplier": 1.0,
            "ammo_multiplier": 1, "disable_drowning": True, "enable_all_attachments": True,
        }))
        cls.stack.enter_context(patch.object(cls.module, "save_profile", side_effect=AssertionError("Unexpected profile write")))
        cls.stack.enter_context(patch.object(cls.module, "save_settings", side_effect=AssertionError("Unexpected settings write")))
        cls.stack.enter_context(patch.object(cls.module.threading, "Thread"))
        cls.stack.enter_context(patch.object(cls.module.socket, "socket", side_effect=AssertionError("Unexpected socket")))
        cls.stack.enter_context(patch.object(cls.module.socket, "create_connection", side_effect=AssertionError("Unexpected connection")))
        cls.stack.enter_context(patch.object(cls.module.subprocess, "Popen", side_effect=AssertionError("Unexpected subprocess")))
        cls.app = cls.module.CrysisCoopLauncher()
        cls.app.withdraw()
        cls.callback_errors = []
        cls.app.report_callback_exception = lambda *exc: cls.callback_errors.append(exc)
        cls.addClassCleanup(cls.close_app)
        cls.app.update_idletasks()

    @classmethod
    def close_app(cls):
        cls.app.stop_threads = True
        cls.app.destroy()

    def test_empty_and_unselected_table_stay_dark_in_every_state(self):
        style_name = str(self.app.tree_lobbies.cget("style"))
        self.assertEqual(style_name, "Lobby.Treeview")
        for state in ((), ("focus",), ("!focus",), ("active",), ("disabled",)):
            with self.subTest(state=state):
                self.assertEqual(self.app.style.lookup(style_name, "background", state), self.theme.BG_PANEL)
                self.assertEqual(self.app.style.lookup(style_name, "fieldbackground", state), self.theme.BG_PANEL)
                foreground = self.app.style.lookup(style_name, "foreground", state)
                self.assertGreaterEqual(contrast_ratio(foreground, self.theme.BG_PANEL), 4.5)

    def test_selection_and_headings_keep_dark_readable_state_colors(self):
        for state in (("selected",), ("selected", "focus"), ("selected", "!focus"), ("selected", "disabled")):
            with self.subTest(state=state):
                background = self.app.style.lookup("Lobby.Treeview", "background", state)
                foreground = self.app.style.lookup("Lobby.Treeview", "foreground", state)
                self.assertEqual(background, self.theme.BORDER_LIGHT)
                self.assertGreaterEqual(contrast_ratio(foreground, background), 4.5)
        for state in ((), ("active",), ("pressed",), ("disabled",)):
            with self.subTest(heading_state=state):
                background = self.app.style.lookup("Lobby.Treeview.Heading", "background", state)
                self.assertIn(background, (self.theme.BG_INPUT, self.theme.BORDER_LIGHT))
                foreground = self.app.style.lookup("Lobby.Treeview.Heading", "foreground", state)
                self.assertGreaterEqual(contrast_ratio(foreground, background), 4.5)

    def test_installed_icons_and_client_roster_render(self):
        self.assertEqual(set(self.app.weapon_images), set(self.module.WEAPON_METADATA))
        self.assertEqual(len(self.app.weapon_images), 15)
        self.app.remote_players = {
            "Fixture host": {"is_host": True, "ready": True, "loadout": dict(self.module.DEFAULT_LOADOUT)}
        }
        self.app.is_host = False
        self.app.update_lobby_room_ui()
        self.app.update_idletasks()
        self.assertEqual(len(self.app.roster_container.winfo_children()), 2)
        self.assertFalse(self.callback_errors)


if __name__ == "__main__":
    unittest.main(verbosity=2)
