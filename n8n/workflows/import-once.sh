#!/bin/sh
set -eu

marker=/home/node/.n8n/.youtube-workflows-v1-imported
workflow_name='YouTube Shorts - 24x7 Create and Scheduled Upload'

if [ -f "$marker" ]; then
  echo "YouTube workflow template already imported."
  exit 0
fi

# CLI imports need an owner/personal project. A fresh n8n instance does not have
# one until the browser setup form is completed, so wait instead of importing an
# invisible/unowned workflow or incorrectly writing the marker.
echo "Waiting for the n8n owner account to be created..."
while :; do
  settings="$(wget -q -O - http://n8n:5678/rest/settings 2>/dev/null || true)"
  if printf '%s' "$settings" | grep -Eq '"showSetupOnFirstLoad"[[:space:]]*:[[:space:]]*false'; then
    break
  fi
  sleep 15
done

n8n import:workflow --input=/workflows/youtube-shorts-24x7.json

# n8n's CLI handles command errors internally in some releases. Verify the
# imported object exists before making this bootstrap step one-shot.
export_file=/tmp/youtube-workflow-export.json
n8n export:workflow --all --output="$export_file"
if ! grep -q "\"name\":\"$workflow_name\"\|\"name\": \"$workflow_name\"" "$export_file"; then
  echo "Workflow import verification failed; marker was not written." >&2
  rm -f "$export_file"
  exit 1
fi
rm -f "$export_file"

mkdir -p "$(dirname "$marker")"
touch "$marker"
echo "Imported YouTube workflow template (unpublished until credentials are configured)."
