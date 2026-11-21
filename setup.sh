#!/usr/bin/env sh
# One-command setup: creates .env with fresh secrets, asks for your Gemini key, starts the app.
set -e
[ -f .env ] || cp .env.example .env
get() { grep -E "^$1=" .env | head -1 | cut -d= -f2-; }
set_var() { awk -v k="$1" -v v="$2" 'BEGIN{FS=OFS="="} $1==k{$0=k"="v} {print}' .env > .env.tmp && mv .env.tmp .env; }
gen() { if command -v openssl >/dev/null 2>&1; then openssl rand -base64 32 | tr -d '=+/\n'; else python3 -c "import secrets;print(secrets.token_urlsafe(32))"; fi; }

for k in API_KEY SEND_WEBHOOK_SECRET N8N_ENCRYPTION_KEY; do [ -n "$(get $k)" ] || set_var $k "$(gen)"; done
if [ -z "$(get GEMINI_API_KEY)" ]; then
  printf "Paste your Gemini API key (https://aistudio.google.com/apikey): "
  read -r k; set_var GEMINI_API_KEY "$k"
fi
chmod 600 .env
docker compose up -d --build
echo
echo "Ready: http://localhost:8000"
echo "Your unlock key (also in .env as API_KEY): $(get API_KEY)"
