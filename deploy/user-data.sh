#!/bin/bash
# Runs as root on first boot. Installs everything slow (apt, caddy, uv, swap) while
# the instance is still coming up, so the deploy script doesn't have to wait for it.
set -x
exec > /var/log/idatasight-bootstrap.log 2>&1

export DEBIAN_FRONTEND=noninteractive

# Swap first — the bun frontend build is the memory spike on this box.
if [ ! -f /swapfile ]; then
  fallocate -l 2G /swapfile
  chmod 600 /swapfile
  mkswap /swapfile
  swapon /swapfile
  echo '/swapfile none swap sw 0 0' >> /etc/fstab
fi

apt-get update -qq
apt-get install -y -qq python3.12-venv rsync curl unzip \
  debian-keyring debian-archive-keyring apt-transport-https

# Caddy — auto TLS + websocket-aware reverse proxy
curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/gpg.key' \
  | gpg --dearmor -o /usr/share/keyrings/caddy-stable-archive-keyring.gpg
curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/debian.deb.txt' \
  > /etc/apt/sources.list.d/caddy-stable.list
apt-get update -qq
apt-get install -y -qq caddy

# uv, as the app user
sudo -u ubuntu bash -lc 'curl -LsSf https://astral.sh/uv/install.sh | sh'

install -d -o ubuntu -g ubuntu /home/ubuntu/idatasight

touch /opt/bootstrap-done
