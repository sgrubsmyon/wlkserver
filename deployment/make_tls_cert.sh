#!/usr/bin/env bash
# Create an internal CA (once) and a server certificate for the LAN hostname.
#
#   sudo deployment/make_tls_cert.sh wlk.example.lan 192.168.1.50
#
# Writes /etc/ssl/wlkserver/{ca.pem,ca.key,server.crt,server.key}. The CA key
# is the trust anchor for every client - back it up and keep it offline; losing
# it means re-trusting a new CA on all POS devices.
set -euo pipefail

if [ $# -lt 1 ]; then
    echo "usage: $0 <hostname> [more hostnames or IPs...]" >&2
    exit 2
fi

OUT=${OUT:-/etc/ssl/wlkserver}
CN=$1
shift

san="DNS:$CN"
for value in "$@"; do
    if [[ $value =~ ^[0-9]+(\.[0-9]+){3}$ ]]; then
        san+=",IP:$value"
    else
        san+=",DNS:$value"
    fi
done

install -d -m 700 "$OUT"
cd "$OUT"

# The CA survives certificate renewals; never regenerate it silently.
if [ ! -f ca.pem ]; then
    openssl req -x509 -newkey rsa:4096 -nodes -days 3650 \
        -keyout ca.key -out ca.pem \
        -subj "/CN=Weltladenkasse internal CA"
    chmod 600 ca.key
    echo "created new CA: $OUT/ca.pem"
fi

openssl req -newkey rsa:2048 -nodes -keyout server.key -out server.csr \
    -subj "/CN=$CN"
openssl x509 -req -in server.csr -CA ca.pem -CAkey ca.key -CAcreateserial \
    -days 825 -out server.crt \
    -extfile <(printf 'subjectAltName=%s\n' "$san")
rm -f server.csr
chmod 600 server.key
chmod 644 ca.pem server.crt

echo
echo "certificate for $san written to $OUT"
echo "trust this file on the POS devices and scripts: $OUT/ca.pem"
echo "reload nginx after a renewal: sudo systemctl reload nginx"
