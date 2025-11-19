#!/usr/bin/env sh

echo "[run.sh] Alexa List Import starting..."

# Version sicher aus options.json
ADDON_VERSION=$(python3 - << 'EOF'
import json
try:
    with open("/data/options.json") as f:
        opts = json.load(f)
        print(opts.get("addon_version", "1.0.0"))
except:
    print("1.0.0")
EOF
)

echo "[run.sh] Version: $ADDON_VERSION"

echo "[run.sh] Reading options from /data/options.json"

python3 - << 'EOF'
import json

with open("/data/options.json", "r") as f:
    opts = json.load(f)

for k,v in opts.items():
    if "password" in k:
        print(f"[run.sh]   {k}= ********")
    else:
        print(f"[run.sh]   {k}= {v}")
EOF

echo "[run.sh] Starting app.py"
exec python3 /app/app.py
