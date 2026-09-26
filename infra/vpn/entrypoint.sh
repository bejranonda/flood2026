#!/bin/sh
set -eu
CONF=$(ls /vpn/*.ovpn 2>/dev/null | head -1)
[ -n "$CONF" ] || { echo "no .ovpn in /vpn"; exit 1; }
printf 'Port 8888\nListen 0.0.0.0\nTimeout 120\nAllow 0.0.0.0/0\nMaxClients 20\nLogLevel Warning\n' > /etc/tinyproxy.conf
tinyproxy -c /etc/tinyproxy.conf
# The container's default DNS (the host's upstream) is unreachable once all traffic goes through the relay.
printf 'nameserver 8.8.8.8\nnameserver 1.1.1.1\n' > /etc/resolv.conf
# Public VPN Gate relays are untrusted and flaky: HTTPS certificates are still verified by our client, and no secrets
# are ever sent through it. A watchdog exits the container (compose restarts it) when the tunnel stops carrying traffic.
openvpn --config "$CONF" --data-ciphers AES-128-CBC:AES-256-GCM:AES-128-GCM --allow-compression yes \
  --script-security 2 --pull-filter ignore "dhcp-option" --connect-retry-max 5 &
OVPN=$!
sleep 30
fails=0
while kill -0 "$OVPN" 2>/dev/null; do
  if curl -s --max-time 12 -o /dev/null https://1.1.1.1/cdn-cgi/trace; then fails=0; else fails=$((fails + 1)); fi
  [ "$fails" -ge 3 ] && { echo "watchdog: tunnel dead, restarting"; kill "$OVPN"; sleep 2; exit 1; }
  sleep 60
done
exit 1
