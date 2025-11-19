#!/usr/bin/env sh

echo "[run.sh] Alexa List Import starting..."

# Dynamisch Version aus config.yaml lesen
ADDON_VERSION=$(grep '^version:' /etc/hassio/addons/data/*/config.yaml | head -n 1 | awk '{print $2}' | tr -d '"')

echo "[run.sh] Version: ${ADDON_VERSION}"

echo "[run.sh] Reading options from /data/options.json"

# options.json laden
python3 - << 'EOF'
import json
import sys

try:
    with open("/data/options.json", "r") as f:
        opts = json.load(f)
except Exception as e:
    print("[run.sh] ERROR reading options.json:", e)
    sys.exit(1)

for k, v in opts.items():
    if "password" in k:
        print(f"[run.sh]   {k}= ********")
    else:
        print(f"[run.sh]   {k}= {v}")

EOF

echo "[run.sh] Starting app.py"
exec python3 /app/app.py
