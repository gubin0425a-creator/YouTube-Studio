#!/usr/bin/env sh
set -eu

if [ -e .env ]; then
  echo ".env already exists; refusing to overwrite it." >&2
  exit 1
fi

cp .env.example .env
python3 - <<'PY'
from pathlib import Path
import secrets

path = Path('.env')
text = path.read_text()
replacements = {
    'replace-with-a-long-random-password': secrets.token_urlsafe(32),
    'replace-with-at-least-32-random-characters': secrets.token_urlsafe(48),
}
for old, new in replacements.items():
    text = text.replace(old, new, 1)
# The worker token placeholder occurs after the encryption-key placeholder.
text = text.replace(
    'replace-with-at-least-32-random-characters', secrets.token_urlsafe(48), 1
)
text = text.replace('replace-with-a-random-studio-password', secrets.token_urlsafe(24), 1)
text = text.replace('replace-with-a-random-session-secret', secrets.token_urlsafe(48), 1)
path.write_text(text)
PY
chmod 600 .env
printf '%s\n' ".env created with random local secrets."
printf '%s\n' "Now edit N8N_HOST, STUDIO_HOST, GEMINI_API_KEY, and YOUTUBE_DATA_API_KEY."
