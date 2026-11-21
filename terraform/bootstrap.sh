#!/usr/bin/env bash
set -euo pipefail

exec > >(tee -a /var/log/travel-expenses-bootstrap.log) 2>&1

apt-get update
apt-get install -y ca-certificates curl gnupg

# Install Docker Engine and the Compose plugin from Docker's official APT repo.
install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg -o /etc/apt/keyrings/docker.asc
chmod a+r /etc/apt/keyrings/docker.asc

docker_arch="$(dpkg --print-architecture)"
ubuntu_codename="$(. /etc/os-release && echo "$VERSION_CODENAME")"
printf 'Types: deb\nURIs: https://download.docker.com/linux/ubuntu\nSuites: %s\nComponents: stable\nArchitectures: %s\nSigned-By: /etc/apt/keyrings/docker.asc\n' \
  "$ubuntu_codename" "$docker_arch" > /etc/apt/sources.list.d/docker.sources

# Install Caddy from its official stable APT repo.
curl -1sLf https://dl.cloudsmith.io/public/caddy/stable/gpg.key \
  | gpg --dearmor -o /usr/share/keyrings/caddy-stable-archive-keyring.gpg
curl -1sLf https://dl.cloudsmith.io/public/caddy/stable/debian.deb.txt \
  -o /etc/apt/sources.list.d/caddy-stable.list
chmod o+r /usr/share/keyrings/caddy-stable-archive-keyring.gpg
chmod o+r /etc/apt/sources.list.d/caddy-stable.list

apt-get update
DEBIAN_FRONTEND=noninteractive apt-get install -y \
  docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin caddy

systemctl enable --now docker

# Serve HTTP on the instance IP for initial smoke checks. Replace :80 with the
# chosen DNS name later so Caddy can provision HTTPS certificates automatically.
cat > /etc/caddy/Caddyfile <<'CADDYFILE'
:80 {
    reverse_proxy 127.0.0.1:5173
}
CADDYFILE

systemctl enable caddy
systemctl restart caddy
