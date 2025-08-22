#!/usr/bin/env bash
set -euo pipefail
if git -C /opt/CCTV_BTR_Mant_Bot rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  (cd /opt/CCTV_BTR_Mant_Bot && git describe --tags --always --dirty)
else
  python3 - <<'PY'
import re, sys
p='/opt/CCTV_BTR_Mant_Bot/bot.py'
try:
  with open(p, 'r', encoding='utf-8') as f:
    for line in f:
      m=re.search(r"__version__\s*=\s*['\"]([^'\"]+)['\"]", line)
      if m:
        print(m.group(1)); sys.exit(0)
except: pass
print('desconocida')
PY
fi
