#!/usr/bin/env bash
# Refresh the Cloudflare IP allowlist in infra/Caddyfile, then reload Caddy.
set -euo pipefail
cd "$(dirname "$0")/.."
R=$( (curl -fsS https://www.cloudflare.com/ips-v4; echo; curl -fsS https://www.cloudflare.com/ips-v6) | tr '\n' ' ' | tr -s ' ')
sed -i -E "s#(@not_cloudflare not remote_ip ).*#\1${R}#" infra/Caddyfile
docker compose --profile origin restart caddy
