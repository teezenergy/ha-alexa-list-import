#!/bin/sh
set -e

echo "[run.sh] Alexa List Import starting..."

OPTIONS_FILE=/data/options.json

echo "[run.sh] Reading options from $OPTIONS_FILE"

# Use Python to parse the JSON options
cat << 'EOF' > /app/options_loader.py
import json, os

data = json.load(open("/data/options.json"))

for k, v in data.items():
    print(f"{k}={v}")
EOF

python3 /app/options_loader.py > /data/options.env

# Load variables
set -a
. /data/options.env
set +a

echo "[run.sh] Options loaded:"
echo "  region=$region"
echo "  interval=$interval"
echo "  clear_after_import=$clear_after_import"
echo "  debug=$debug"

echo "[run.sh] Starting app.py"
exec python3 /app/app.py
