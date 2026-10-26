#!/usr/bin/env bash
# scripts/gen_cert.sh
# Génération d'un certificat SSL auto-signé pour HTTPS (requis pour l'accès micro et caméra depuis smartphone)

CERT_DIR="certs"
mkdir -p "$CERT_DIR"

echo "Génération de la clé privée et du certificat auto-signé..."
openssl req -x509 -newkey rsa:4096 -sha256 -days 365 -nodes \
  -keyout "$CERT_DIR/server.key" \
  -out "$CERT_DIR/server.crt" \
  -subj "/CN=dobot.local/O=ENSIL-ENSCI/C=FR" \
  -addext "subjectAltName=DNS:dobot.local,DNS:raspberrypi.local,IP:192.168.4.1,IP:127.0.0.1"

echo "Certificat généré dans $CERT_DIR/server.crt et clé dans $CERT_DIR/server.key"
