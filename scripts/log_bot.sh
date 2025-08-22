#!/usr/bin/env bash
set -euo pipefail
N=${1:-100}
journalctl -u cctv-maint-bot.service -n "$N" --no-pager
