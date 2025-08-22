#!/usr/bin/env bash
set -euo pipefail
CID="${1:-}"
[ -z "$CID" ] && { echo "Uso: $0 -100XXXXXXXXXX"; exit 1; }
sed -i "s/^CHAT_ID=.*/CHAT_ID=${CID}/" /opt/CCTV_BTR_Mant_Bot/.env
echo "CHAT_ID actualizado a ${CID}"
