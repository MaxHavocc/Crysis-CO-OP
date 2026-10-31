"""Call the Crysis host's restricted SSH bridge using a pinned host key."""
import argparse
import base64
import hashlib
import ipaddress
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys

MAX_REQUEST = 16 * 1024
MAX_RESPONSE = 2 * 1024 * 1024
OPERATIONS = {
    'info', 'status', 'read_log', 'read_config', 'read_file', 'git_status', 'git_diff',
    'git_log', 'git_pull', 'run_tests', 'build', 'ollama_models', 'ollama_ask',
}


def load_connection(path):
    text = Path(path).read_text(encoding='utf-8-sig').strip()
    if text.startswith('BRIDGE_CONNECTION '):
        text = text[len('BRIDGE_CONNECTION '):]
    config = json.loads(text)
    address = ipaddress.IPv4Address(config['host'])
    if str(address).split('.')[0] != '26':
        raise ValueError('Expected a Radmin VPN IPv4 address (26.x.x.x).')
    user = config['user']
    if not isinstance(user, str) or not re.fullmatch(r'[A-Za-z0-9_.@\\-]{1,100}', user):
        raise ValueError('Invalid SSH account name.')
    port = config.get('port', 22)
    if type(port) is not int or not 1 <= port <= 65535:
        raise ValueError('Invalid SSH port.')
    key = config['host_public_key']
    if not isinstance(key, str) or '\n' in key or '\r' in key:
        raise ValueError('Invalid host public key.')
    fields = key.split()
    if len(fields) < 2 or fields[0] not in ('ssh-ed25519', 'ecdsa-sha2-nistp256', 'ssh-rsa'):
        raise ValueError('Unsupported host public key.')
    blob = base64.b64decode(fields[1], validate=True)
    if len(blob) < 20:
        raise ValueError('Host key is incomplete.')
    fingerprint = 'SHA256:' + base64.b64encode(hashlib.sha256(blob).digest()).decode().rstrip('=')
    supplied_fingerprint = config.get('fingerprint')
    if supplied_fingerprint and supplied_fingerprint != fingerprint:
        raise ValueError('The supplied host key and fingerprint do not match.')
    return dict(host=str(address), user=user, port=port,
                host_public_key=' '.join(fields[:2]), fingerprint=fingerprint)


def pin_host(connection, directory):
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    host = connection['host']
    port = connection['port']
    target = host if port == 22 else f'[{host}]:{port}'
    expected = f"{target} {connection['host_public_key']}\n"
    path = directory / f'host_{host}_{port}.known_hosts'
    if path.exists():
        if path.read_text(encoding='ascii') != expected:
            raise ValueError('Pinned host key changed. Verify the new connection record with Caden before replacing the pin.')
    else:
        with path.open('x', encoding='ascii', newline='\n') as handle:
            handle.write(expected)
    return path


def make_request(operation, args):
    if operation not in OPERATIONS:
        raise ValueError('Unsupported bridge operation.')
    if not isinstance(args, dict):
        raise ValueError('Operation arguments must be a JSON object.')
    raw = json.dumps({'operation': operation, 'args': args}, ensure_ascii=True,
                     separators=(',', ':')).encode('utf-8')
    if len(raw) > MAX_REQUEST:
        raise ValueError('Request exceeds 16 KiB. Use a shorter prompt or smaller context.')
    return base64.b64encode(raw).decode('ascii')


def call_bridge(connection, identity, pin_file, operation, args):
    identity = Path(identity).resolve(strict=True)
    ssh = shutil.which('ssh.exe') if os.name == 'nt' else shutil.which('ssh')
    if not ssh:
        raise RuntimeError('OpenSSH client is not installed.')
    null_file = 'NUL' if os.name == 'nt' else '/dev/null'
    request = make_request(operation, args)
    command = [ssh, '-F', null_file, '-T', '-i', str(identity),
               '-o', 'BatchMode=yes', '-o', 'IdentitiesOnly=yes',
               '-o', 'PasswordAuthentication=no', '-o', 'PreferredAuthentications=publickey',
               '-o', 'StrictHostKeyChecking=yes', '-o', f'UserKnownHostsFile={Path(pin_file).resolve()}',
               '-o', f'GlobalKnownHostsFile={null_file}', '-o', 'LogLevel=ERROR',
               '-o', 'ConnectTimeout=10', '-o', 'ServerAliveInterval=15',
               '-o', 'ServerAliveCountMax=2', '-p', str(connection['port']),
               '-l', connection['user'], connection['host'], request]
    timeout = {'build': 960, 'run_tests': 360, 'ollama_ask': 240, 'git_pull': 150}.get(operation, 90)
    result = subprocess.run(command, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE, timeout=timeout, shell=False)
    if len(result.stdout) > MAX_RESPONSE:
        raise RuntimeError('Host response exceeded the bridge output limit.')
    output = result.stdout.decode('utf-8-sig', errors='replace').strip()
    try:
        response = json.loads(output)
    except (ValueError, TypeError):
        detail = result.stderr.decode('utf-8', errors='replace')[-2000:].strip()
        raise RuntimeError(f'No valid bridge response (SSH exit {result.returncode}): {detail}') from None
    if not isinstance(response, dict) or type(response.get('ok')) is not bool:
        raise RuntimeError('Invalid bridge response envelope.')
    if result.returncode and response['ok']:
        raise RuntimeError(f'SSH failed after response (exit {result.returncode}).')
    return response


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--connection', required=True, help='One-time connection JSON from host setup')
    parser.add_argument('--identity', required=True, help='Private SSH key stored on this PC')
    parser.add_argument('--args-file', help='JSON operation arguments; avoids shell quoting')
    parser.add_argument('operation', choices=sorted(OPERATIONS))
    options = parser.parse_args()
    try:
        path = Path(options.connection).resolve(strict=True)
        connection = load_connection(path)
        pin_file = pin_host(connection, path.parent)
        args = json.loads(Path(options.args_file).read_text(encoding='utf-8-sig')) if options.args_file else {}
        result = call_bridge(connection, options.identity, pin_file, options.operation, args)
    except (OSError, ValueError, KeyError, RuntimeError, subprocess.TimeoutExpired) as error:
        result = {'ok': False, 'error': str(error)}
    print(json.dumps(result, ensure_ascii=True, indent=2))
    return 0 if result['ok'] else 1


if __name__ == '__main__':
    sys.exit(main())
