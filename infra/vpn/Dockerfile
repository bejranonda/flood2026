# OpenVPN client + tiny HTTP proxy in ONE network namespace. Only traffic sent to the proxy (port 8888)
# leaves through the VPN; the host and the other containers keep their normal routes (D-014).
FROM alpine:3.20
RUN apk add --no-cache openvpn tinyproxy iproute2 curl
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh
ENTRYPOINT ["/entrypoint.sh"]
