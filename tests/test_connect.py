import os
from pathlib import Path
import runpy
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

MODULE = runpy.run_path(str(Path(__file__).resolve().parent.parent / 'CrysisCoopLauncher.py'))
Launcher = MODULE['CrysisCoopLauncher']
GLOBALS = Launcher.launch_crysis_client.__globals__


class ConnectConfigTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(dir=Path(__file__).parent)
        self.root = Path(self.temp.name)
        self.mod = self.root / 'Mods' / 'CrysisCoop'
        self.mod.mkdir(parents=True)
        self.bin32 = self.root / 'Bin32'
        self.bin32.mkdir()
        # Stock Crysis is deliberately present; it must not silently be used.
        (self.bin32 / 'Crysis.exe').touch()
        self.app = SimpleNamespace(profile={'callsign': 'Test Player'}, settings={'game': 'crysis'})
        self.app.extract_weapon_list_from_loadout = lambda loadout: Launcher.extract_weapon_list_from_loadout(self.app, loadout)
        self.app.get_crysis_network_executable = lambda: Launcher.get_crysis_network_executable(self.app)
        self.options = dict(mission_code='island', difficulty_val=2, enemy_mult=1.5,
                            ammo_mult=2, disable_drowning=True, enable_attachments=True,
                            loadout=dict(MODULE['DEFAULT_LOADOUT']))
        self.globals_patch = patch.dict(GLOBALS, CRYSIS_ROOT_DIR=str(self.root),
                                       CRYSIS_MOD_DIR=str(self.mod),
                                       get_network_ips=lambda: ['26.1.2.3'])
        self.globals_patch.start()
        self.run_patch = patch.object(GLOBALS['subprocess'], 'run')
        self.popen_patch = patch.object(GLOBALS['subprocess'], 'Popen')
        self.sleep_patch = patch.object(GLOBALS['time'], 'sleep')
        self.error_patch = patch.object(GLOBALS['messagebox'], 'showerror')
        self.kill = self.run_patch.start()
        self.launch = self.popen_patch.start()
        self.sleep_patch.start()
        self.error = self.error_patch.start()

    def tearDown(self):
        self.error_patch.stop()
        self.sleep_patch.stop()
        self.popen_patch.stop()
        self.run_patch.stop()
        self.globals_patch.stop()
        self.temp.cleanup()

    def test_missing_client_runtime_does_not_kill_or_launch_stock_game(self):
        Launcher.launch_crysis_client(self.app, host_ip='26.196.29.208', **self.options)
        self.kill.assert_not_called()
        self.launch.assert_not_called()
        self.assertFalse((self.root / 'connect.cfg').exists())
        self.assertIn('Setup_Coop_Runtime.ps1', self.error.call_args.args[1])
        self.assertIn('CrysisCoop.exe', self.error.call_args.args[1])

    def test_missing_host_runtime_does_not_tell_peers_to_launch(self):
        self.app.is_host = True
        peer = Mock()
        self.app.host_clients = [peer]
        Launcher.action_launch_game(self.app)
        peer.sendall.assert_not_called()
        self.kill.assert_not_called()
        self.launch.assert_not_called()

    def test_vanished_lobby_error_survives_deferred_callback(self):
        callbacks = []
        app = SimpleNamespace(stop_hosting=lambda: None, client_sock=None,
                              after=lambda delay, callback: callbacks.append(callback))
        sock = Mock()
        sock.connect.side_effect = OSError('Host is offline')

        class ImmediateThread:
            def __init__(self, target, **kwargs): self.target = target
            def start(self): self.target()

        with patch.object(GLOBALS['socket'], 'socket', return_value=sock), \
             patch.object(GLOBALS['threading'], 'Thread', ImmediateThread):
            Launcher.start_client_connection(app, '192.0.2.66')
        self.assertEqual(len(callbacks), 1)
        callbacks[0]()
        self.assertIn('Host is offline', self.error.call_args.args[1])
        sock.close.assert_called_once()
        self.assertFalse(app.is_connected)

    def test_client_uses_x86_compatibility_runtime_and_preserves_direct_address(self):
        runtime = self.bin32 / 'CrysisCoop.exe'
        runtime.touch()
        Launcher.launch_crysis_client(self.app, host_ip='26.196.29.208', **self.options)
        self.error.assert_not_called()
        self.assertEqual(self.launch.call_args.args[0],
                         [str(runtime), '-mod', 'CrysisCoop', '-devmode', '+exec', 'client.cfg'])
        self.assertEqual(self.launch.call_args.kwargs['cwd'], str(self.bin32))
        connect = (self.root / 'connect.cfg').read_text()
        self.assertIn('connect 26.196.29.208 64087', connect)
        cfg = (self.mod / 'client.cfg').read_text()
        self.assertIn('exec connect.cfg', cfg)
        self.assertIn('name "Test Player"', cfg)
        self.assertNotIn('net_name', cfg)
        self.assertNotIn(' = ', cfg)
        self.assertIn('coop_loadout "SCAR,SOCOM"', cfg)
        self.assertIn('CrysisCoop.exe', self.kill.call_args.args[0])

    def test_host_uses_same_runtime_and_keeps_requested_mission(self):
        runtime = self.bin32 / 'CrysisCoop.exe'
        runtime.touch()
        Launcher.launch_crysis_host(self.app, **self.options)
        self.assertEqual(self.launch.call_args.args[0],
                         [str(runtime), '-mod', 'CrysisCoop', '-devmode', '+exec', 'host.cfg'])
        cfg = (self.mod / 'host.cfg').read_text()
        self.assertIn('sv_gamerules Coop', cfg)
        self.assertIn('map island s', cfg)
        self.assertNotIn(' = ', cfg)


if __name__ == '__main__':
    unittest.main(verbosity=2)
