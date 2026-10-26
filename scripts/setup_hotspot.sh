#!/usr/bin/env bash
# scripts/setup_hotspot.sh
# Configuration d'un point d'accès Wi-Fi autonome sur Raspberry Pi avec NetworkManager (nmcli)

SSID="Dobot-AI-Hotspot"
PASSWORD="ensil-robotique"

echo "Configuration du Hotspot Wi-Fi : $SSID"

# Suppression de l'ancienne connexion si existante
nmcli connection delete "$SSID" 2>/dev/null || true

# Création du hotspot
nmcli connection add type wifi ifname wlan0 con-name "$SSID" autoconnect yes ssid "$SSID"
nmcli connection modify "$SSID" 802-11-wireless.mode ap 802-11-wireless.band bg ipv4.method shared
nmcli connection modify "$SSID" wifi-sec.key-mgmt wpa-psk wifi-sec.psk "$PASSWORD"

# Activation
nmcli connection up "$SSID"

echo "Hotspot activé avec succès ! Adresse par défaut du Raspberry Pi : 10.42.0.1 ou 192.168.4.1"
