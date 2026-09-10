"""Run the explicit local-only mode. No credentials or flags are persisted."""
import os
import argparse
from pathlib import Path
import secrets
import shutil
import socket
import subprocess
import sys
import time

root = Path(__file__).resolve().parents[1]
parser = argparse.ArgumentParser()
parser.add_argument('--api-port', type=int, default=8000)
parser.add_argument('--port', type=int, default=5173)
args = parser.parse_args()
if any(port < 1024 or port > 65535 for port in (args.api_port, args.port)) or args.api_port == args.port:
    parser.error('Choose two different ports between 1024 and 65535.')
for port in (args.api_port, args.port):
    with socket.socket() as probe:
        try:
            probe.bind(('127.0.0.1', port))
        except OSError:
            raise SystemExit(f'Port {port} is already in use. Stop that server before starting local mode.')
env = dict(os.environ, APP_ENV='development', LOCAL_DEV_AUTH='1', LOCAL_DEV_TOKEN=secrets.token_urlsafe(48), VITE_LOCAL_DEV_MODE='true')
env['LOCAL_DEV_API_PORT'] = str(args.api_port)
env['LOCAL_DEV_PORT'] = str(args.port)
env['VITE_API_URL'] = '/api'
flags = subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
node = shutil.which('node')
if not node:
    raise SystemExit('Node.js is required.')
children = []
try:
    children.append(subprocess.Popen([sys.executable, '-m', 'uvicorn', 'app.main:app', '--host', '127.0.0.1', '--port', str(args.api_port), '--no-proxy-headers'], cwd=root / 'backend', env=env, creationflags=flags))
    children.append(subprocess.Popen([node, str(root / 'frontend/node_modules/vite/bin/vite.js'), '--host', '127.0.0.1', '--port', str(args.port)], cwd=root / 'frontend', env=env, creationflags=flags))
    print(f'Modo local: http://127.0.0.1:{args.port} — Ctrl+C para detener ambos servidores.', flush=True)
    while all(child.poll() is None for child in children):
        time.sleep(0.5)
finally:
    for child in children:
        if child.poll() is None:
            child.terminate()
    for child in children:
        child.wait(timeout=10)
