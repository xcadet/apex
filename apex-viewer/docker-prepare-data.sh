#!/bin/sh
# Runs (via nginx's /docker-entrypoint.d/ hook) before nginx starts.
#
# The image already has the design data baked in. If a workflows JSONL is mounted at
# runtime (default /data/all_workflows.jsonl) we re-split it to override the baked data;
# otherwise we serve what was baked in. So `docker run` and Skiff both work with no flags.
set -e

: "${DESIGNS_JSONL:=/data/all_workflows.jsonl}"
export DESIGNS_JSONL
export OUT_DIR=/usr/share/nginx/html/data

if [ -f "$DESIGNS_JSONL" ]; then
  echo "apex-viewer: mounted $DESIGNS_JSONL found — re-exporting to override baked-in data"
  node /app/export-data.mjs
else
  echo "apex-viewer: serving data baked into the image (mount a JSONL at $DESIGNS_JSONL to override)"
fi
