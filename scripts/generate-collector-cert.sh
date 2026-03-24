#!/bin/bash
# Script to provision a new Edge Collector with mTLS certificates
# Usage: ./generate-collector-cert.sh <organization-uuid>

ORG_UUID=$1

if [ -z "$ORG_UUID" ]; then
    echo "❌ Error: Organization UUID is required."
    echo "💡 Usage: ./generate-collector-cert.sh <your-organization-uuid>"
    exit 1
fi

CERTS_DIR="infra/rabbitmq/certs"

if [ ! -f "$CERTS_DIR/ca_key.pem" ]; then
    echo "❌ Error: Root CA not found. Please run setup-ca-server.sh first."
    exit 1
fi

cd $CERTS_DIR

echo "🏭 Generating certificate for Edge Collector (Org: $ORG_UUID)..."
# We embed the provided UUID directly into the CN field
openssl req -newkey rsa:2048 -nodes \
    -keyout "collector_${ORG_UUID}_key.pem" \
    -out "collector_${ORG_UUID}.csr" \
    -subj "/C=UA/ST=Kyiv/L=Kyiv/O=Client Factory/CN=${ORG_UUID}"

openssl x509 -req -in "collector_${ORG_UUID}.csr" \
    -CA ca_certificate.pem -CAkey ca_key.pem -CAcreateserial \
    -out "collector_${ORG_UUID}_certificate.pem" -days 3650

# Cleanup the temporary CSR file
rm "collector_${ORG_UUID}.csr"

# Set secure permissions
chmod 600 "collector_${ORG_UUID}_key.pem"
chmod 644 "collector_${ORG_UUID}_certificate.pem"

echo "✅ Done! Client certificates for $ORG_UUID generated."
echo "📦 Files to send to the Raspberry Pi:"
echo "   - ca_certificate.pem"
echo "   - collector_${ORG_UUID}_certificate.pem"
echo "   - collector_${ORG_UUID}_key.pem"
