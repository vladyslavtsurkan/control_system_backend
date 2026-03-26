#!/bin/bash
# Script to initialize the Root Certificate Authority (CA) and RabbitMQ Server certificate
# Usage: ./setup-ca-server.sh <server-domain-or-ip>

set -euo pipefail

SERVER_DOMAIN="${1:-}"

if [ -z "$SERVER_DOMAIN" ]; then
    echo "❌ Error: Server Domain or IP is required."
    echo "💡 Usage: ./setup-ca-server.sh <server-domain-or-ip>"
    echo "   Example (Local): ./setup-ca-server.sh 0.0.0.0"
    echo "   Example (Prod):  ./setup-ca-server.sh api.myfactory.com"
    exit 1
fi

CERTS_DIR="infra/rabbitmq/certs"
mkdir -p "$CERTS_DIR"
cd "$CERTS_DIR"

is_ipv4() {
    [[ "$1" =~ ^([0-9]{1,3}\.){3}[0-9]{1,3}$ ]]
}

is_ipv6() {
    [[ "$1" == *:* ]]
}

if is_ipv4 "$SERVER_DOMAIN" || is_ipv6 "$SERVER_DOMAIN"; then
    SAN_VALUE="IP:${SERVER_DOMAIN}"
else
    SAN_VALUE="DNS:${SERVER_DOMAIN}"
fi

rm -f server.csr server_key.pem server_certificate.pem

echo "🔐 1. Creating Root Certificate Authority (Root CA)..."
openssl req -x509 -nodes -days 3650 -newkey rsa:2048 \
    -keyout ca_key.pem -out ca_certificate.pem \
    -subj "/C=UA/ST=Kyiv/L=Kyiv/O=IIoT Platform/CN=IIoT_Root_CA" \
    -addext "basicConstraints=critical,CA:TRUE" \
    -addext "keyUsage=critical,keyCertSign,cRLSign"

echo "🏢 2. Generating certificate for RabbitMQ Server ($SERVER_DOMAIN)..."
# We embed the Server Domain/IP into the Common Name (CN)
# We also add Subject Alternative Name (SAN) which is required by modern strict TLS
openssl req -newkey rsa:2048 -nodes -keyout server_key.pem -out server.csr \
    -subj "/C=UA/ST=Kyiv/L=Kyiv/O=IIoT Platform/CN=${SERVER_DOMAIN}" \
    -addext "subjectAltName=${SAN_VALUE}"

# We use -copy_extensions copyall to move the SAN from the CSR to the final Certificate
openssl x509 -req -in server.csr -CA ca_certificate.pem -CAkey ca_key.pem \
    -CAcreateserial -out server_certificate.pem -days 3650 \
    -copy_extensions copyall

# Cleanup temporary CSR
rm server.csr

if [[ ! -f server_key.pem || ! -f server_certificate.pem ]]; then
    echo "❌ Error: certificate generation failed."
    exit 1
fi

# Set proper permissions for RabbitMQ
chmod 600 server_key.pem ca_key.pem
chmod 644 server_certificate.pem ca_certificate.pem

echo "✅ Infrastructure certificates for $SERVER_DOMAIN generated successfully in $CERTS_DIR"
