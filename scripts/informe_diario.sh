#!/usr/bin/env bash
set -euo pipefail
source /opt/CCTV_BTR_Mant_Bot/.env

CAM=${CAM_DIR:-/CAM}
SRV=${SERVICE_RECORDER:-agentdvr.service}
HOST=$(hostname)
NOW=$(date '+%Y-%m-%d %H:%M')

ROOT=$(df -hP / | sed -n '2{s/^/  /;p}')
CAMDF=$(df -hP "$CAM" | sed -n '2{s/^/  /;p}' 2>/dev/null || echo "  (sin montar)")
SRV_STATE=$(systemctl is-active "$SRV" 2>/dev/null || echo "desconocido")
UPTIME=$(uptime -p | sed 's/up //')

TEXT="📣 Informe diario ${NOW}
Host: ${HOST}
Uptime: ${UPTIME}
Raíz:
${ROOT}
CAM:
${CAMDF}
DVR: ${SRV} => ${SRV_STATE}"

curl -sS -X POST "https://api.telegram.org/bot${BOT_TOKEN}/sendMessage" \
  -d chat_id="${CHAT_ID}" \
  --data-urlencode "text=${TEXT}" >/dev/null
