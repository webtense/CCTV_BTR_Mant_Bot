#!/usr/bin/env bash
set -euo pipefail
source /opt/CCTV_BTR_Mant_Bot/.env

CAM=${CAM_DIR:-/CAM}
DAYS=${DAYS:-15}
THRESHOLD=${THRESHOLD:-90}
TARGET=${TARGET:-85}

# 1) Borrado por antigüedad
find "$CAM" -type f -mtime +${DAYS} -print -delete 2>/dev/null || true

# 2) Si disco supera THRESHOLD, borra por orden de antigüedad hasta bajar a TARGET
usage() { df -P "$CAM" | awk 'NR==2 {gsub("%","",$5); print $5}'; }
cur=$(usage)
if [ "$cur" -ge "$THRESHOLD" ]; then
  # Lista por fecha ascendente
  mapfile -t files < <(find "$CAM" -type f -printf '%T@ %p\n' 2>/dev/null | sort -n | awk '{ $1=""; sub(/^ /,""); print }')
  for f in "${files[@]}"; do
    rm -f -- "$f" || true
    cur=$(usage)
    [ "$cur" -le "$TARGET" ] && break
  done
fi

# Informe a Telegram (opcional)
if [ -n "${BOT_TOKEN:-}" ] && [ -n "${CHAT_ID:-}" ]; then
  dfout=$(df -hP "$CAM" | sed '1!s/^/  /')
  curl -sS -X POST "https://api.telegram.org/bot${BOT_TOKEN}/sendMessage" \
    -d chat_id="${CHAT_ID}" \
    --data-urlencode "text=🧹 Limpieza /CAM completada\n${dfout}" >/dev/null
fi
