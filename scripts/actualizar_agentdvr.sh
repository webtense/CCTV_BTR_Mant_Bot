#!/usr/bin/env bash
set -euo pipefail
source /opt/CCTV_BTR_Mant_Bot/.env
SRV=${SERVICE_RECORDER:-agentdvr.service}

DO_UPDATE() {
  # ← Pon aquí tu procedimiento real de actualización.
  # Por defecto: simple restart del servicio.
  systemctl restart "$SRV"
}

DO_UPDATE

if [ -n "${BOT_TOKEN:-}" ] && [ -n "${CHAT_ID:-}" ]; then
  state=$(systemctl is-active "$SRV" 2>/dev/null || true)
  curl -sS -X POST "https://api.telegram.org/bot${BOT_TOKEN}/sendMessage" \
    -d chat_id="${CHAT_ID}" \
    --data-urlencode "text=🔄 ${SRV} actualizado/reiniciado. Estado: ${state}" >/dev/null
fi
