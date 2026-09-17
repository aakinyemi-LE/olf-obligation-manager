#!/usr/bin/env bash
# release.sh — bump the version atomically across both manifests and run the
# regression guard, so a release is one deterministic step.
#
#   tools/release.sh 0.1.1
#
# It does NOT git-commit or push — it prints the next steps so you stay in
# control. The GitHub repo is the single source of truth.
set -euo pipefail
VER="${1:?usage: tools/release.sh <version>   e.g. 0.1.1}"
cd "$(dirname "$0")/.."   # repo root

python3 - "$VER" <<'PY'
import json, sys
ver = sys.argv[1]
def bump(path, kind):
    d = json.load(open(path))
    if kind == "plugin":
        d["version"] = ver
    else:  # marketplace
        if d.get("metadata", {}).get("version"): d["metadata"]["version"] = ver
        for pl in d.get("plugins", []):
            if pl.get("name") == "olf-obligation-manager": pl["version"] = ver
    json.dump(d, open(path, "w"), indent=2); open(path, "a").write("\n")
    print("  set", path, "->", ver)
bump(".claude-plugin/plugin.json", "plugin")
bump(".claude-plugin/marketplace.json", "marketplace")
PY

echo "Running regression guard…"
python3 tools/check_register.py tests/fixtures/*.register.json

cat <<EOF

Version set to ${VER} and fixtures pass. Next:
  git add -A && git commit -m "Release ${VER}" && git push origin main

Then in Cowork (Sync alone does NOT re-pull files):
  Plugins → remove the plugin AND the marketplace → re-add the marketplace URL → reinstall → new session.
EOF
