#!/bin/sh
set -e

echo "[run.sh] Alexa List Import starting..."
OPTIONS_FILE=/data/options.json
echo "[run.sh] Reading options from $OPTIONS_FILE"

# Use Python to parse JSON → erzeugt garantiert KEINE LEERZEICHEN
cat << 'EOF' > /app/load_options.py
import json

data = json.load(open("/data/options.json"))

def clean(x):
    if isinstance(x, str):
        return x.strip().replace(" ", "")
    return x

for key, val in data.items():
    v = clean(val)
    print(f"{key}={v}")
EOF

python3 /app/load_options.py > /data/options.env

# Environment übernehmen
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
