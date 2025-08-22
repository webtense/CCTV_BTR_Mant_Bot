#!/usr/bin/env bash
set -euo pipefail
source /opt/CCTV_BTR_Mant_Bot/.env

CAM=${CAM_DIR:-/CAM}
HOST=$(hostname)
NOW=$(date '+%Y-%m-%d %H:%M:%S')

# Disco raíz y /CAM
DF=$(df -hP / "$CAM" | sed '1!s/^/  /')

# Servicio DVR (si existe)
SRV=${SERVICE_RECORDER:-agentdvr.service}
SRV_STATE=$(systemctl is-active "$SRV" 2>/dev/null || true)

TEXT="✅ Bot OK en ${HOST} a las ${NOW}
$DF
Servicio DVR: ${SRV} => ${SRV_STATE}"

curl -sS -X POST "https://api.telegram.org/bot${BOT_TOKEN}/sendMessage" \
  -d chat_id="${CHAT_ID}" \
  --data-urlencode "text=${TEXT}" >/dev/null
