"""Run the explicit local-only mode. No credentials or flags are persisted."""
import os
import json
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
parser.add_argument('--auth', action='store_true', help='Use Supabase authentication from auth.local.json.')
args = parser.parse_args()
if any(port < 1024 or port > 65535 for port in (args.api_port, args.port)) or args.api_port == args.port:
    parser.error('Choose two different ports between 1024 and 65535.')
requested_api_port = args.api_port
for candidate in range(requested_api_port, min(requested_api_port + 100, 65536)):
    if candidate == args.port:
        continue
    with socket.socket() as probe:
        try:
            probe.bind(('127.0.0.1', candidate))
        except OSError:
            continue
        args.api_port = candidate
        break
else:
    raise SystemExit('No hay un puerto libre para la API. Detén una ejecución anterior e inténtalo de nuevo.')
if args.api_port != requested_api_port:
    print(f'Puerto API {requested_api_port} ocupado; se usará {args.api_port}.', flush=True)
for port in (args.port,):
    with socket.socket() as probe:
        try:
            probe.bind(('127.0.0.1', port))
        except OSError:
            raise SystemExit(f'El puerto de la app {port} está ocupado. Detén la ejecución anterior con Ctrl+C. Para modo sin sesión puedes elegir otro con --port 5179; con Supabase, la dirección debe estar autorizada en Redirect URLs.')
env = dict(os.environ, APP_ENV='development', LOCAL_DEV_AUTH='1', LOCAL_DEV_TOKEN=secrets.token_urlsafe(48), VITE_LOCAL_DEV_MODE='true')
if args.auth:
    try:
        config = json.loads((root / 'auth.local.json').read_text(encoding='utf-8'))
        url = config['SUPABASE_URL'].rstrip('/')
        key = config['SUPABASE_PUBLISHABLE_KEY']
        if not url.startswith('https://') or not key.startswith('sb_publishable_'):
            raise ValueError()
    except (OSError, ValueError, KeyError, AttributeError, TypeError):
        raise SystemExit('Configure SUPABASE_URL and a public Publishable key in auth.local.json.') from None
    env.update(SUPABASE_URL=url, SUPABASE_PUBLISHABLE_KEY=key,
               VITE_SUPABASE_URL=url, VITE_SUPABASE_PUBLISHABLE_KEY=key,
               LOCAL_DEV_AUTH='0', VITE_LOCAL_DEV_MODE='false')
    env.pop('LOCAL_DEV_TOKEN', None)
env['LOCAL_DEV_API_PORT'] = str(args.api_port)
env['LOCAL_DEV_PORT'] = str(args.port)
env['VITE_API_URL'] = '/api'
flags = subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
node = shutil.which('node')
if not node:
    raise SystemExit('Node.js is required.')
children = []
try:
    children.append(subprocess.Popen([sys.executable, '-m', 'uvicorn', 'app.main:app', '--host', '127.0.0.1', '--port', str(args.api_port), '--no-proxy-headers', '--reload', '--reload-dir', str(root / 'backend' / 'app')], cwd=root / 'backend', env=env, creationflags=flags))
    children.append(subprocess.Popen([node, str(root / 'frontend/node_modules/vite/bin/vite.js'), '--host', '127.0.0.1', '--port', str(args.port)], cwd=root / 'frontend', env=env, creationflags=flags))
    mode = 'Supabase' if args.auth else 'Modo local'
    print(f'{mode}: http://127.0.0.1:{args.port} — Ctrl+C para detener ambos servidores.', flush=True)
    while all(child.poll() is None for child in children):
        time.sleep(0.5)
finally:
    for child in children:
        if child.poll() is None:
            child.terminate()
    for child in children:
        child.wait(timeout=10)
