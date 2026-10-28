import importlib.util
import io
import json
from pathlib import Path
import queue
import socket
import threading
import time
from types import SimpleNamespace
import unittest
from unittest.mock import patch

path = Path(__file__).resolve().parent.parent / "CrysisCoopLauncher.py"
spec = importlib.util.spec_from_file_location("discovery_candidate", path)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)
real_socket = socket.socket
real_connect = socket.create_connection


def serve_once(handler):
    listener = real_socket(socket.AF_INET, socket.SOCK_STREAM)
    listener.bind(("127.0.0.1", 0))
    listener.listen(4)
    listener.settimeout(3)
    port = listener.getsockname()[1]

    def serve():
        try:
            conn, addr = listener.accept()
            with conn:
                handler(conn, addr, listener)
        except (OSError, socket.timeout):
            pass
        finally:
            listener.close()

    thread = threading.Thread(target=serve, daemon=True)
    thread.start()
    return port, thread


class DiscoveryTests(unittest.TestCase):
    def scan_announcements(self, replies, probe, local_ips=("192.0.2.1",)):
        pending = iter(replies)

        class Announcements:
            def __enter__(self): return self
            def __exit__(self, *args): pass
            def setsockopt(self, *args): pass
            def settimeout(self, *args): pass
            def sendto(self, *args): pass
            def recvfrom(self, length):
                try:
                    packet, source = next(pending)
                    return json.dumps(packet).encode(), (source, mod.DISCOVERY_PORT)
                except StopIteration:
                    raise socket.timeout()

        import urllib.request
        with patch.object(mod.socket, "socket", return_value=Announcements()), \
             patch.object(mod, "query_live_lobby", side_effect=probe) as query, \
             patch.object(urllib.request, "urlopen", side_effect=OSError("No bridge")):
            result = mod.discover_live_lobbies(local_ips)
        return result, query

    def test_lan_announcement_falls_back_to_bound_vpn_endpoint(self):
        lan, vpn = "192.0.2.44", "26.1.2.3"
        packet = {"type": "LOBBY_ANNOUNCE", "host_ip": vpn, "lobby_name": "VPN host"}

        def probe(ip, fresh_udp):
            return mod.normalize_lobby(fresh_udp, ip) if ip == vpn else None

        # The same host can also answer a direct VPN discovery query. It must
        # still appear once, using the endpoint with a live lobby socket.
        result, query = self.scan_announcements([(packet, lan), (packet, vpn)], probe)
        self.assertEqual([row["host_ip"] for row in result], [vpn])
        self.assertEqual([call.args[0] for call in query.call_args_list], [lan, vpn])

    def test_advertised_local_or_invalid_address_is_not_probed(self):
        for advertised in ("192.0.2.1", "not-an-ip", "0.0.0.0", "239.1.2.3"):
            with self.subTest(advertised=advertised):
                packet = {"type": "LOBBY_ANNOUNCE", "host_ip": advertised}
                result, query = self.scan_announcements([(packet, "192.0.2.44")], lambda *args: None)
                self.assertEqual(result, [])
                self.assertEqual([call.args[0] for call in query.call_args_list], ["192.0.2.44"])

    def test_modern_tcp_query_proves_host_without_joining(self):
        callbacks = []
        fake = SimpleNamespace(
            is_host=True, host_lobby_name="Real localhost squad", profile={"callsign": "Host"},
            settings={"mission_title": "Contact"}, host_clients=[], remote_players={},
            broadcast_lobby_state=lambda: callbacks.append("broadcast"),
            after=lambda *args: callbacks.append("tk"),
        )

        def handler(conn, addr, listener):
            fake.server_sock = listener
            mod.CrysisCoopLauncher.host_client_handler(fake, conn, addr, listener)

        port, thread = serve_once(handler)
        with patch.object(mod, "DEFAULT_PORT", port):
            result = mod.query_live_lobby("127.0.0.1")
        thread.join(2)
        self.assertEqual(result["lobby_name"], "Real localhost squad")
        self.assertEqual(result["player_count"], 1)
        self.assertEqual(fake.host_clients, [])
        self.assertEqual(fake.remote_players, {})
        self.assertEqual(callbacks, [])

    def test_legacy_listener_requires_fresh_udp_proof(self):
        def legacy(conn, *_):
            conn.recv(4096)
            time.sleep(0.8)

        packet = {"lobby_name": "Legacy host", "player_count": 1}
        port, thread = serve_once(legacy)
        with patch.object(mod, "DEFAULT_PORT", port):
            self.assertEqual(mod.query_live_lobby("127.0.0.1", packet)["lobby_name"], "Legacy host")
        thread.join(2)
        port, thread = serve_once(legacy)
        with patch.object(mod, "DEFAULT_PORT", port):
            self.assertIsNone(mod.query_live_lobby("127.0.0.1"))
        thread.join(2)

    def test_closed_tcp_rejects_stale_udp_or_bridge_metadata(self):
        sock = real_socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.bind(("127.0.0.1", 0))
        port = sock.getsockname()[1]
        sock.close()
        with patch.object(mod, "DEFAULT_PORT", port):
            self.assertIsNone(mod.query_live_lobby("127.0.0.1", {"name": "Gone"}))

    def test_unrelated_tcp_service_is_not_a_lobby(self):
        def unrelated(conn, *_):
            conn.recv(4096)
            conn.sendall(b'{"type":"OTHER_SERVICE"}\n')
        port, thread = serve_once(unrelated)
        with patch.object(mod, "DEFAULT_PORT", port):
            self.assertIsNone(mod.query_live_lobby("127.0.0.1"))
        thread.join(2)

    def test_udp_and_http_scan_removes_dead_cached_host(self):
        # All datagrams and TCP probes are redirected to controlled loopback
        # servers. No hard-coded discovery target or HTTP bridge is contacted.
        active_ip = "192.0.2.44"
        dead_ip = "192.0.2.66"
        udp = real_socket(socket.AF_INET, socket.SOCK_DGRAM)
        udp.bind(("127.0.0.1", 0))
        udp.settimeout(0.1)
        udp_address = udp.getsockname()
        stop = threading.Event()

        def udp_host():
            while not stop.is_set():
                try:
                    data, addr = udp.recvfrom(8192)
                    if json.loads(data)["type"] == "DISCOVER":
                        udp.sendto(json.dumps({"type": "LOBBY_ANNOUNCE", "lobby_name": "Active host"}).encode(), addr)
                except socket.timeout:
                    continue
                except OSError:
                    break

        threading.Thread(target=udp_host, daemon=True).start()

        class LocalUDP:
            def __init__(self):
                self.sock = real_socket(socket.AF_INET, socket.SOCK_DGRAM)
            def __enter__(self): return self
            def __exit__(self, *args): self.sock.close()
            def setsockopt(self, *args): self.sock.setsockopt(*args)
            def settimeout(self, value): self.sock.settimeout(value)
            def sendto(self, data, ignored): return self.sock.sendto(data, udp_address)
            def recvfrom(self, length):
                data, address = self.sock.recvfrom(length)
                return data, (active_ip, address[1])

        def modern(conn, *_):
            conn.recv(4096)
            conn.sendall(b'{"type":"LOBBY_STATUS","hosting":true,"lobby_name":"Active host","player_count":1}\n')
        port, thread = serve_once(modern)
        bridge_rows = json.dumps([{"host_ip": active_ip, "name": "Cached active"}, {"host_ip": dead_ip, "name": "Ghost"}]).encode()
        connect_calls = []

        def local_connect(address, timeout):
            connect_calls.append(address[0])
            if address[0] == active_ip:
                return real_connect(("127.0.0.1", port), timeout=timeout)
            raise ConnectionRefusedError()

        import urllib.request
        try:
            with patch.object(mod.socket, "socket", side_effect=lambda *args, **kwargs: LocalUDP() if len(args) > 1 and args[1] == socket.SOCK_DGRAM and "fileno" not in kwargs else real_socket(*args, **kwargs)), \
                 patch.object(mod.socket, "create_connection", side_effect=local_connect), \
                 patch.object(urllib.request, "urlopen", side_effect=lambda *args, **kwargs: io.BytesIO(bridge_rows)):
                # real_connect itself creates socket.socket; override that
                # detail locally so only discovery UDP uses the wrapper.
                def local_connect_actual(address, timeout):
                    connect_calls.append(address[0])
                    if address[0] != active_ip:
                        raise ConnectionRefusedError()
                    conn = real_socket(socket.AF_INET, socket.SOCK_STREAM)
                    conn.settimeout(timeout)
                    conn.connect(("127.0.0.1", port))
                    return conn
                with patch.object(mod.socket, "create_connection", side_effect=local_connect_actual):
                    result = mod.discover_live_lobbies(("192.0.2.1",))
            self.assertEqual([row["host_ip"] for row in result], [active_ip])
            self.assertIn(dead_ip, connect_calls)
        finally:
            stop.set()
            udp.close()
            thread.join(2)

    def test_browser_replaces_snapshot_and_ignores_old_generation(self):
        class Tree:
            def __init__(self): self.rows = {"old": {"values": ("Ghost", "192.0.2.66", "Crysis 1", "Contact", "1/2")}}
            def selection(self): return []
            def get_children(self): return list(self.rows)
            def delete(self, row): del self.rows[row]
            def insert(self, *args, values):
                key = str(len(self.rows))
                self.rows[key] = {"values": values}
                return key
        tasks = {}
        def after(ms, callback):
            key = len(tasks) + 1
            tasks[key] = callback
            return key
        fake = SimpleNamespace(
            _lobby_scan_generation=0, _lobby_scan_inflight=False,
            _lobby_refresh_after=None, _lobby_poll_after=None,
            _lobby_scan_results=queue.Queue(), profile={}, tree_lobbies=Tree(),
            join_browser_frame=SimpleNamespace(winfo_manager=lambda: "pack"),
            after=after, after_cancel=lambda key: tasks.pop(key, None),
            refresh_lobbies_thread=lambda: None,
        )
        class ImmediateThread:
            def __init__(self, target, **kwargs): self.target = target
            def start(self): self.target()
        with patch.object(mod.threading, "Thread", ImmediateThread), \
             patch.object(mod, "get_network_ips", return_value=["192.0.2.1"]), \
             patch.object(mod, "discover_live_lobbies", return_value=[]):
            mod.CrysisCoopLauncher.refresh_lobbies_thread(fake)
            list(tasks.values())[0]()
        self.assertEqual(fake.tree_lobbies.rows, {})
        self.assertFalse(fake._lobby_scan_inflight)
        # A queued result from a page that has since been left cannot insert.
        tasks.clear()
        with patch.object(mod.threading, "Thread", ImmediateThread), \
             patch.object(mod, "get_network_ips", return_value=["192.0.2.1"]), \
             patch.object(mod, "discover_live_lobbies", return_value=[{"host_ip": "stale"}]):
            mod.CrysisCoopLauncher.refresh_lobbies_thread(fake)
            callback = list(tasks.values())[0]
            fake._lobby_scan_generation += 1
            callback()
        self.assertEqual(fake.tree_lobbies.rows, {})


if __name__ == "__main__":
    unittest.main(verbosity=2)
