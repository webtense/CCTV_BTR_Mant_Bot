#!/usr/bin/env bash
set -euo pipefail
source /opt/CCTV_BTR_Mant_Bot/.env
mask(){ [ -z "$1" ] && echo "-" || echo "${1:0:6}********${1: -4}"; }
echo "BOT_TOKEN=$(mask "$BOT_TOKEN")"
echo "CHAT_ID=${CHAT_ID:-}"
echo "AUTHORIZED_CHAT_ID=${AUTHORIZED_CHAT_ID:-(no filtrado)}"
echo "CAM_DIR=${CAM_DIR:-/CAM}"
echo "SERVICE_RECORDER=${SERVICE_RECORDER:-agentdvr.service}"
echo "THRESHOLD=${THRESHOLD:-90} TARGET=${TARGET:-85} DAYS=${DAYS:-15}"
