#!/usr/bin/env bash
set -e

echo "[run.sh] Alexa List Import starting..."

# Options
OPTIONS_FILE=/data/options.json

echo "[run.sh] Reading options from $OPTIONS_FILE"

# Let Python parse JSON instead of jq (not available)
cat <<EOF > /app/options_loader.py
import json, sys
data = json.load(open("/data/options.json"))
for k, v in data.items():
    print(f"{k}={v}")
EOF

python3 /app/options_loader.py > /data/options.env

# Source the env file
set -a
source /data/options.env
set +a

echo "[run.sh] Options loaded:"
echo "  region=$region  interval=$interval clear_after_import=$clear_after_import"

echo "[run.sh] Starting app.py"
exec python3 /app/app.py
